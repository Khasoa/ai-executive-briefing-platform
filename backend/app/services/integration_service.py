import logging
from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.models import Integration, SyncEvent, User
from app.schemas.integrations import IntegrationCheckResponse, IntegrationsResponse
from app.services import demo_data
from app.services.db_fallback import load_rows_with_fallback
from app.services.demo_user import is_demo_user
from app.services.integration_catalog import (
    SUPPORTED_INTEGRATIONS,
    auth_type_for,
    disconnected_entry,
    resolve_row_for_entry,
)
from app.services.mapping_utils import jsonb_or_default, relative_time_label, stringify_id

logger = logging.getLogger("briefly.integrations")

GOOGLE_SYNC_IDS = frozenset({"google-calendar", "gmail", "google"})


class IntegrationService:
    """Connection state and sync history for every upstream system.

    The Integrations page is built from a canonical supported-provider catalog
    merged with the *current user's* `integrations` rows. Credentials, tokens,
    last-sync timestamps, and connection status never come from another user.
    Demo users may still see curated `demo_data` overlays when they have no
    row for a catalog entry.

    OpenAI (API key) and n8n (webhook secret) are environment-configured — not
    OAuth — and surface as configured / not configured from server settings.
    """

    def __init__(
        self, db: Session, user: User, settings: Settings | None = None
    ) -> None:
        self.db = db
        self.user = user
        self.settings = settings or get_settings()

    def get_integrations(self) -> IntegrationsResponse:
        integrations = self.list_integrations()
        return IntegrationsResponse(
            connectedCount=sum(
                1
                for i in integrations
                if i["status"] in ("connected", "syncing", "configured")
            ),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=self.list_sync_history(),
        )

    def check_configuration(self, integration_id: str) -> IntegrationCheckResponse:
        """Safe configuration probe for API-key / webhook providers (no secrets)."""
        entry = next((e for e in SUPPORTED_INTEGRATIONS if e["id"] == integration_id), None)
        if entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration '{integration_id}' not found",
            )
        auth_type = auth_type_for(entry)

        if integration_id == "openai":
            configured = bool(self.settings.openai_api_key.strip())
            return IntegrationCheckResponse(
                id="openai",
                configured=configured,
                status="configured" if configured else "not-connected",
                message=(
                    "OpenAI is configured and available for briefs."
                    if configured
                    else "OpenAI API key is not configured."
                ),
                authType="api_key",
                details={
                    "model": self.settings.openai_model if configured else "",
                    "fallback": "curated" if not configured else "openai",
                },
            )

        if integration_id == "n8n":
            configured = bool(self.settings.n8n_webhook_secret.strip())
            return IntegrationCheckResponse(
                id="n8n",
                configured=configured,
                status="configured" if configured else "not-connected",
                message=(
                    "n8n webhook secret is configured. Call POST /webhooks/n8n/run|daily|weekly "
                    "with header X-Briefly-N8N-Secret."
                    if configured
                    else "n8n webhook secret is not configured."
                ),
                authType="webhook",
                details={
                    "endpoints": "run,daily,weekly",
                    "header": "X-Briefly-N8N-Secret",
                },
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{entry['name']} uses {auth_type} authentication — "
                "use Connect / Sync instead of configuration check."
            ),
        )

    def trigger_sync(self, integration_id: str) -> IntegrationsResponse:
        """Start a manual sync for OAuth-backed providers."""
        integrations = self.list_integrations()
        integration = next((i for i in integrations if i["id"] == integration_id), None)

        if integration is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Integration '{integration_id}' not found",
            )

        if integration.get("authType") in ("api_key", "webhook"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{integration['name']} is configured via server environment — "
                    "use Check configuration instead of Sync."
                ),
            )

        if integration["status"] == "not-connected":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{integration['name']} is not connected yet",
            )

        google_row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == self.user.id,
                Integration.provider == "google",
                Integration.status == "connected",
            )
            .first()
        )

        if google_row is not None and integration_id in GOOGLE_SYNC_IDS:
            try:
                if integration_id in ("google-calendar", "google"):
                    from app.services.calendar_sync_service import CalendarSyncService

                    CalendarSyncService(self.db, self.settings).sync_user(
                        self.user, reason="manual"
                    )
                if integration_id in ("gmail", "google"):
                    from app.services.gmail_sync_service import GmailSyncService

                    GmailSyncService(self.db, self.settings).sync_user(
                        self.user, reason="manual"
                    )
            except HTTPException as exc:
                self._record_google_sync_failure(integration_id, str(exc.detail))
                raise
            except Exception:
                logger.exception("Unexpected Google sync failure for %s", integration_id)
                self._record_google_sync_failure(
                    integration_id,
                    f"{integration['name']} sync failed unexpectedly. Try again shortly.",
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"{integration['name']} sync failed. Try again shortly.",
                ) from None
            return self.get_integrations()

        notion_row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == self.user.id,
                Integration.provider == "notion",
                Integration.status == "connected",
            )
            .first()
        )
        if notion_row is not None and integration_id == "notion":
            from app.services.notion_sync_service import NotionSyncService

            try:
                NotionSyncService(self.db).sync_user(self.user, reason="manual")
            except HTTPException as exc:
                self._record_provider_sync_failure("notion", str(exc.detail))
                raise
            return self.get_integrations()

        ghl_row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == self.user.id,
                Integration.provider == "gohighlevel",
                Integration.status == "connected",
            )
            .first()
        )
        if ghl_row is not None and integration_id in ("gohighlevel", "ghl"):
            from app.services.ghl_sync_service import GHLSyncService

            try:
                GHLSyncService(self.db).sync_user(self.user, reason="manual")
            except HTTPException as exc:
                self._record_provider_sync_failure("gohighlevel", str(exc.detail))
                raise
            return self.get_integrations()

        monday_row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == self.user.id,
                Integration.provider == "monday",
                Integration.status == "connected",
            )
            .first()
        )
        if monday_row is not None and integration_id == "monday":
            from app.services.monday_sync_service import MondaySyncService

            try:
                MondaySyncService(self.db).sync_user(self.user, reason="manual")
            except HTTPException as exc:
                self._record_provider_sync_failure("monday", str(exc.detail))
                raise
            return self.get_integrations()

        clickup_row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == self.user.id,
                Integration.provider == "clickup",
                Integration.status == "connected",
            )
            .first()
        )
        if clickup_row is not None and integration_id == "clickup":
            from app.services.clickup_sync_service import ClickUpSyncService

            try:
                ClickUpSyncService(self.db).sync_user(self.user, reason="manual")
            except HTTPException as exc:
                self._record_provider_sync_failure("clickup", str(exc.detail))
                raise
            return self.get_integrations()

        detail = f"Requested from Integrations · {', '.join(integration['scopes'])}"
        persisted = self._persist_sync(integration_id, detail)

        integration["status"] = "syncing"
        integration["lastSyncLabel"] = "syncing now"

        if not persisted:
            demo_data.SYNC_HISTORY.insert(
                0,
                {
                    "id": f"sync_{uuid4().hex[:8]}",
                    "integrationId": integration["id"],
                    "integration": integration["name"],
                    "event": "Manual sync started",
                    "status": "running",
                    "time": datetime.now().strftime("%H:%M"),
                    "detail": detail,
                },
            )

        if persisted:
            return self.get_integrations()

        return IntegrationsResponse(
            connectedCount=sum(
                1 for i in integrations if i["status"] in ("connected", "syncing", "configured")
            ),
            totalCount=len(integrations),
            integrations=integrations,
            syncHistory=self.list_sync_history(),
        )

    def list_integrations(self) -> list[dict]:
        """Return the full supported catalog merged with this user's connection rows."""
        rows = self._load_user_integration_rows()
        rows_by_provider = {row.provider: row for row in rows}
        demo_by_id = (
            {item["id"]: item for item in demo_data.INTEGRATIONS}
            if is_demo_user(self.user)
            else {}
        )

        result: list[dict] = []
        consumed_providers: set[str] = set()

        for entry in SUPPORTED_INTEGRATIONS:
            auth_type = auth_type_for(entry)

            if auth_type in ("api_key", "webhook"):
                result.append(self._env_config_entry(entry))
                consumed_providers.update(entry["provider_keys"])
                continue

            row = resolve_row_for_entry(entry, rows_by_provider)
            if row is not None:
                result.append(self._merge_catalog_entry(entry, row, rows_by_provider))
                consumed_providers.update(entry["provider_keys"])
                continue

            if entry["id"] in demo_by_id:
                curated = deepcopy(demo_by_id[entry["id"]])
                curated.setdefault("authType", auth_type)
                curated.setdefault("statusDetail", None)
                curated.setdefault("canSync", True)
                curated.setdefault("canConnect", auth_type == "oauth")
                curated.setdefault("canDisconnect", False)
                curated.setdefault("canCheck", False)
                result.append(curated)
                continue

            result.append(disconnected_entry(entry))

        for provider, row in sorted(rows_by_provider.items(), key=lambda item: item[0]):
            if provider in consumed_providers:
                continue
            if any(provider in entry["provider_keys"] for entry in SUPPORTED_INTEGRATIONS):
                continue
            result.append(self._to_dict(row))

        return result

    def _env_config_entry(self, entry: dict) -> dict:
        """OpenAI / n8n cards driven by server env — never OAuth, never secrets."""
        base = disconnected_entry(entry)
        if entry["id"] == "openai":
            configured = bool(self.settings.openai_api_key.strip())
            base.update(
                {
                    "status": "configured" if configured else "not-connected",
                    "account": "Server API key" if configured else None,
                    "lastSyncLabel": "Ready" if configured else "Not configured",
                    "statusDetail": (
                        f"Model {self.settings.openai_model} · curated fallback when unavailable"
                        if configured
                        else "API key required on the API server"
                    ),
                    "metrics": [
                        {
                            "label": "Model",
                            "value": self.settings.openai_model if configured else "—",
                        },
                        {"label": "Briefs generated", "value": "—"},
                    ],
                    "canSync": False,
                    "canConnect": False,
                    "canDisconnect": False,
                    "canCheck": True,
                }
            )
            return base

        if entry["id"] == "n8n":
            configured = bool(self.settings.n8n_webhook_secret.strip())
            base.update(
                {
                    "status": "configured" if configured else "not-connected",
                    "account": "Webhook secret" if configured else None,
                    "lastSync": None,
                    "lastSyncLabel": "Ready" if configured else "Not configured",
                    "statusDetail": (
                        "Secret configured · POST /webhooks/n8n/run|daily|weekly"
                        if configured
                        else "Webhook secret required on the API server"
                    ),
                    "metrics": [
                        {"label": "Workflows", "value": "Webhook"},
                        {"label": "Runs this month", "value": "—"},
                    ],
                    "canSync": False,
                    "canConnect": False,
                    "canDisconnect": False,
                    "canCheck": True,
                }
            )
            return base

        return base

    def _load_user_integration_rows(self) -> list[Integration]:
        try:
            return (
                self.db.query(Integration)
                .filter(Integration.user_id == self.user.id)
                .order_by(Integration.provider.asc())
                .all()
            )
        except SQLAlchemyError:
            logger.warning(
                "Could not read integrations — catalog-only fallback for user %s",
                self.user.id,
                exc_info=True,
            )
            self.db.rollback()
            return []

    def _merge_catalog_entry(
        self,
        entry: dict,
        row: Integration,
        rows_by_provider: dict[str, Integration],
    ) -> dict:
        config = jsonb_or_default(row.config)
        auth_type = auth_type_for(entry)

        alias = rows_by_provider.get(entry["id"])
        status_value = row.status or "not-connected"
        last_sync_at = row.last_sync_at
        status_detail = None

        if alias is not None and entry["id"] != row.provider:
            if alias.status == "error":
                status_value = "error"
                status_detail = (alias.config or {}).get("last_error") or "Sync failed"
            if alias.last_sync_at is not None and (
                last_sync_at is None or alias.last_sync_at > last_sync_at
            ):
                last_sync_at = alias.last_sync_at

        if status_value not in ("connected", "syncing", "not-connected", "error", "configured"):
            status_value = "error" if status_value else "not-connected"

        if (
            status_value == "connected"
            and last_sync_at is None
            and auth_type in ("oauth", "derived")
        ):
            status_detail = status_detail or "Connected — never synced"

        if status_value == "error" and not status_detail:
            status_detail = (config.get("last_error") if isinstance(config, dict) else None) or (
                "Sync failed — try Sync again"
            )

        metrics = config.get("metrics")
        if not metrics:
            metrics = deepcopy(entry["metrics"])

        scopes = list(row.scopes or []) or list(entry["scopes"])
        oauth_connected = status_value in ("connected", "syncing", "error")

        return {
            "id": entry["id"],
            "name": entry["name"],
            "category": entry["category"],
            "description": entry["description"],
            "status": status_value,
            "account": row.account,
            "lastSync": last_sync_at.isoformat() if last_sync_at else None,
            "lastSyncLabel": self._format_sync_label(status_value, last_sync_at),
            "scopes": scopes,
            "metrics": metrics,
            "poweredBy": entry["poweredBy"] or config.get("poweredBy", ""),
            "authType": auth_type,
            "statusDetail": status_detail,
            "canSync": auth_type in ("oauth", "derived") and oauth_connected,
            "canConnect": auth_type in ("oauth", "derived") and status_value == "not-connected",
            "canDisconnect": auth_type in ("oauth", "derived") and oauth_connected,
            "canCheck": False,
        }

    def _record_google_sync_failure(self, integration_id: str, detail: str) -> None:
        targets: list[str] = []
        if integration_id in ("google-calendar", "google"):
            targets.append("google-calendar")
        if integration_id in ("gmail", "google"):
            targets.append("gmail")
        if not targets:
            targets = [integration_id]

        safe_detail = (detail or "Sync failed")[:500]
        now = datetime.now(timezone.utc)
        google = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == self.user.id,
                Integration.provider == "google",
            )
            .first()
        )

        for provider in targets:
            row = (
                self.db.query(Integration)
                .filter(
                    Integration.user_id == self.user.id,
                    Integration.provider == provider,
                )
                .first()
            )
            display = {
                "name": "Gmail" if provider == "gmail" else "Google Calendar",
                "category": "Email" if provider == "gmail" else "Calendar",
                "last_error": safe_detail,
                "token_provider": "google",
            }
            if row is None:
                row = Integration(
                    user_id=self.user.id,
                    provider=provider,
                    status="error",
                    account=google.account if google else None,
                    scopes=[],
                    config=display,
                    connected_at=now,
                    last_sync_at=None,
                )
                self.db.add(row)
                self.db.flush()
            else:
                cfg = dict(row.config or {})
                cfg["last_error"] = safe_detail
                row.config = cfg
                row.status = "error"
                if google and google.account:
                    row.account = google.account

            self.db.add(
                SyncEvent(
                    integration_id=row.id,
                    event="Manual sync failed",
                    status="error",
                    detail=safe_detail,
                    occurred_at=now,
                )
            )
        try:
            self.db.commit()
        except SQLAlchemyError:
            logger.warning("Could not persist Google sync failure", exc_info=True)
            self.db.rollback()

    def _record_provider_sync_failure(self, provider: str, detail: str) -> None:
        safe_detail = (detail or "Sync failed")[:500]
        now = datetime.now(timezone.utc)
        try:
            row = (
                self.db.query(Integration)
                .filter(
                    Integration.user_id == self.user.id,
                    Integration.provider == provider,
                )
                .first()
            )
            if row is None:
                return
            cfg = dict(row.config or {})
            cfg["last_error"] = safe_detail
            row.config = cfg
            row.status = "error"
            self.db.add(
                SyncEvent(
                    integration_id=row.id,
                    event="Manual sync failed",
                    status="error",
                    detail=safe_detail,
                    occurred_at=now,
                )
            )
            self.db.commit()
        except SQLAlchemyError:
            logger.warning("Could not persist sync failure for %s", provider, exc_info=True)
            self.db.rollback()

    def list_sync_history(self) -> list[dict]:
        fallback = demo_data.SYNC_HISTORY if is_demo_user(self.user) else []
        return load_rows_with_fallback(
            query=lambda: (
                self.db.query(SyncEvent)
                .options(joinedload(SyncEvent.integration))
                .join(Integration)
                .filter(Integration.user_id == self.user.id)
                .order_by(SyncEvent.occurred_at.desc())
                .limit(50)
                .all()
            ),
            to_dict=self._sync_event_to_dict,
            fallback=fallback,
            logger=logger,
            label="sync_events",
            db=self.db,
        )

    def _persist_sync(self, provider: str, detail: str) -> bool:
        try:
            row = (
                self.db.query(Integration)
                .filter(
                    Integration.user_id == self.user.id,
                    Integration.provider == provider,
                )
                .first()
            )
            if row is None:
                return False

            now = datetime.now(timezone.utc)
            row.status = "syncing"
            row.last_sync_at = now
            self.db.add(
                SyncEvent(
                    integration_id=row.id,
                    event="Manual sync started",
                    status="running",
                    detail=detail,
                    occurred_at=now,
                )
            )
            self.db.commit()
            return True
        except SQLAlchemyError:
            logger.warning(
                "Could not persist sync for %s — falling back to demo_data",
                provider,
                exc_info=True,
            )
            self.db.rollback()
            return False

    @staticmethod
    def _to_dict(integration: Integration) -> dict:
        config = jsonb_or_default(integration.config)
        return {
            "id": integration.provider,
            "name": config.get("name", integration.provider),
            "category": config.get("category", ""),
            "description": config.get("description", ""),
            "status": integration.status,
            "account": integration.account,
            "lastSync": integration.last_sync_at.isoformat() if integration.last_sync_at else None,
            "lastSyncLabel": IntegrationService._format_sync_label(
                integration.status, integration.last_sync_at
            ),
            "scopes": integration.scopes or [],
            "metrics": config.get("metrics", []),
            "poweredBy": config.get("poweredBy", ""),
            "authType": "oauth",
            "statusDetail": config.get("last_error"),
            "canSync": True,
            "canConnect": False,
            "canDisconnect": True,
            "canCheck": False,
        }

    @staticmethod
    def _sync_event_to_dict(event: SyncEvent) -> dict:
        integration = event.integration
        config = jsonb_or_default(integration.config if integration else None)
        provider = integration.provider if integration else ""
        name = config.get("name", provider)
        occurred = event.occurred_at
        return {
            "id": stringify_id(event.id),
            "integrationId": provider,
            "integration": name,
            "event": event.event,
            "status": event.status,
            "time": occurred.strftime("%H:%M") if occurred else "",
            "detail": event.detail,
        }

    @staticmethod
    def _format_sync_label(integration_status: str, last_sync_at: datetime | None) -> str:
        if integration_status == "syncing":
            return "syncing now"
        if integration_status == "configured":
            return "Ready"
        if last_sync_at is None:
            return "Never"
        return relative_time_label(last_sync_at)
