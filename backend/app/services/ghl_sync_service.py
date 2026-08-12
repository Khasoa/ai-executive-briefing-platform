"""Synchronize GoHighLevel opportunities into `Opportunity` rows."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.integrations.gohighlevel import GHLClient, GHLError, GHLUnauthorized
from app.models import Integration, Opportunity, SyncEvent, User
from app.services.oauth_service import OAuthService

logger = logging.getLogger("briefly.ghl_sync")

GHL_PROVIDER = "gohighlevel"
SOURCE = "GoHighLevel"
EXTERNAL_PREFIX = "ghl:"


class GHLSyncService:
    """Idempotent GHL → Opportunity sync. Preserves local AI/risk fields."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.oauth = OAuthService(db, self.settings)

    def sync_user(self, user: User, *, reason: str = "manual") -> dict[str, int]:
        integration = self._require_ghl_integration(user)
        access_token = self.oauth.refresh_provider_access_token(user, GHL_PROVIDER)
        client = GHLClient(access_token, self.settings)

        meta = dict((integration.config or {}).get("ghl") or {})
        location_id = (
            meta.get("location_id")
            or ((integration.config or {}).get("profile") or {}).get("location_id")
            or ""
        ).strip()
        if not location_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="GoHighLevel locationId missing — reconnect the location",
            )

        try:
            stage_names = self._load_stage_names(client, location_id)
            counts = self._sync_opportunities(user, client, location_id, stage_names)
        except GHLUnauthorized as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="GoHighLevel authorization expired — reconnect required",
            ) from exc
        except GHLError as exc:
            logger.warning("GHL sync failed for user %s: %s", user.id, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc

        meta["location_id"] = location_id
        meta["last_sync_reason"] = reason
        meta["last_synced_at"] = datetime.now(timezone.utc).isoformat()
        self._save_ghl_meta(integration, meta)
        self._record_sync_event(integration, reason, counts)
        return counts

    def _load_stage_names(self, client: GHLClient, location_id: str) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for pipeline in client.list_pipelines(location_id):
            for stage in pipeline.get("stages") or []:
                if not isinstance(stage, dict):
                    continue
                stage_id = stage.get("id")
                name = stage.get("name")
                if stage_id and name:
                    mapping[str(stage_id)] = str(name)
        return mapping

    def _sync_opportunities(
        self,
        user: User,
        client: GHLClient,
        location_id: str,
        stage_names: dict[str, str],
    ) -> dict[str, int]:
        upserted = 0
        closed = 0
        pages = 0
        seen_external: set[str] = set()

        for status_filter in ("open", "won", "lost", "abandoned"):
            skip = 0
            while True:
                payload = client.search_opportunities(
                    location_id=location_id,
                    status=status_filter,
                    limit=100,
                    skip=skip,
                )
                pages += 1
                batch = list(payload.get("opportunities") or [])
                if not batch:
                    break
                for raw in batch:
                    external_id = self._external_id(raw)
                    if not external_id:
                        continue
                    seen_external.add(external_id)
                    if self._upsert(user, raw, stage_names, status_filter):
                        upserted += 1
                if len(batch) < 100:
                    break
                skip += len(batch)

        # Local open deals no longer returned as open → mark closed carefully.
        local_open = (
            self.db.query(Opportunity)
            .filter(
                Opportunity.user_id == user.id,
                Opportunity.external_id.isnot(None),
                Opportunity.external_id.like(f"{EXTERNAL_PREFIX}%"),
            )
            .all()
        )
        for row in local_open:
            if row.external_id in seen_external:
                continue
            li = dict(row.last_interaction or {})
            ghl = dict(li.get("ghl") or {})
            prior_status = (ghl.get("status") or "").lower()
            if prior_status in ("won", "lost", "abandoned"):
                continue
            # Preserve AI fields; only annotate CRM status.
            ghl["status"] = "closed"
            ghl["removedFromOpenSearch"] = True
            li["ghl"] = ghl
            sources = list(li.get("sources") or [])
            if SOURCE not in sources:
                sources.append(SOURCE)
            li["sources"] = sources
            if row.stage and "closed" not in row.stage.lower():
                row.stage = f"{row.stage} (closed)"
            row.last_interaction = li
            closed += 1
        if closed:
            self.db.commit()

        return {"upserted": upserted, "closed": closed, "pages": pages}

    def _upsert(
        self,
        user: User,
        raw: dict[str, Any],
        stage_names: dict[str, str],
        status_filter: str,
    ) -> bool:
        external_id = self._external_id(raw)
        if not external_id:
            return False

        contact = raw.get("contact") or {}
        company = (
            contact.get("companyName")
            or contact.get("name")
            or raw.get("name")
            or "Untitled opportunity"
        )
        stage_id = str(raw.get("pipelineStageId") or raw.get("pipeline_stage_id") or "")
        stage = stage_names.get(stage_id) or raw.get("stageName") or status_filter.title()
        value = float(raw.get("monetaryValue") or raw.get("monetary_value") or 0)
        owner = (
            raw.get("assignedTo")
            or (raw.get("assigned_to") if isinstance(raw.get("assigned_to"), str) else None)
            or "Unassigned"
        )
        if isinstance(owner, dict):
            owner = owner.get("name") or owner.get("email") or "Unassigned"
        close_date = _parse_date(
            raw.get("expectedCloseDate") or raw.get("expected_close_date")
        )
        probability = _probability_for_status(status_filter, stage)

        existing = (
            self.db.query(Opportunity)
            .filter(
                Opportunity.user_id == user.id,
                Opportunity.external_id == external_id,
            )
            .first()
        )

        last_interaction = {
            "type": "crm",
            "summary": (raw.get("name") or company)[:240],
            "time": _relative_updated(raw.get("updatedAt") or raw.get("lastStatusChangeAt")),
            "sources": [SOURCE],
            "ghl": {
                "opportunityId": raw.get("id"),
                "pipelineId": raw.get("pipelineId"),
                "pipelineStageId": stage_id,
                "status": raw.get("status") or status_filter,
                "locationId": raw.get("locationId"),
                "contactId": raw.get("contactId") or contact.get("id"),
                "updatedAt": raw.get("updatedAt"),
            },
        }

        if existing is None:
            logo = "".join(part[0] for part in str(company).split()[:2]).upper()[:4] or "GHL"
            self.db.add(
                Opportunity(
                    user_id=user.id,
                    external_id=external_id,
                    company=str(company)[:255],
                    logo=logo,
                    industry="",
                    stage=str(stage)[:100],
                    value=value,
                    probability=probability,
                    owner=str(owner)[:255],
                    close_date=close_date,
                    risk_level="medium",
                    last_interaction=last_interaction,
                    ai_summary="",
                    recommended_action="",
                    signals=[],
                )
            )
        else:
            existing.company = str(company)[:255]
            existing.stage = str(stage)[:100]
            existing.value = value
            existing.probability = probability
            existing.owner = str(owner)[:255]
            existing.close_date = close_date
            # Preserve AI / risk fields; merge CRM metadata into last_interaction.
            prior = dict(existing.last_interaction or {})
            merged = {**prior, **last_interaction}
            merged["ghl"] = {
                **dict(prior.get("ghl") or {}),
                **last_interaction["ghl"],
            }
            sources = list(prior.get("sources") or [])
            if SOURCE not in sources:
                sources.append(SOURCE)
            merged["sources"] = sources
            # Keep any executive-facing summary text already present.
            if prior.get("summary") and not last_interaction.get("summary"):
                merged["summary"] = prior["summary"]
            existing.last_interaction = merged
            # Explicitly do not touch ai_summary, recommended_action, risk_level, signals.

        self.db.commit()
        return True

    @staticmethod
    def _external_id(raw: dict[str, Any]) -> str | None:
        opp_id = raw.get("id")
        if not opp_id:
            return None
        return f"{EXTERNAL_PREFIX}{opp_id}"

    def _require_ghl_integration(self, user: User) -> Integration:
        row = (
            self.db.query(Integration)
            .filter(
                Integration.user_id == user.id,
                Integration.provider == GHL_PROVIDER,
                Integration.status == "connected",
            )
            .first()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="GoHighLevel is not connected",
            )
        return row

    def _save_ghl_meta(self, integration: Integration, meta: dict[str, Any]) -> None:
        config = dict(integration.config or {})
        config["ghl"] = meta
        integration.config = config
        integration.last_sync_at = datetime.now(timezone.utc)
        integration.status = "connected"
        self.db.commit()

    def _record_sync_event(
        self, integration: Integration, reason: str, counts: dict[str, int]
    ) -> None:
        detail = (
            f"{reason} · upserted {counts.get('upserted', 0)} · "
            f"closed {counts.get('closed', 0)} · pages {counts.get('pages', 0)}"
        )
        self.db.add(
            SyncEvent(
                integration_id=integration.id,
                event="GoHighLevel sync",
                status="success",
                detail=detail,
                occurred_at=datetime.now(timezone.utc),
            )
        )
        self.db.commit()


def _probability_for_status(status_filter: str, stage: str) -> int:
    status = (status_filter or "").lower()
    if status == "won":
        return 100
    if status in ("lost", "abandoned"):
        return 0
    lower = (stage or "").lower()
    if "negotiat" in lower or "proposal" in lower:
        return 65
    if "qualified" in lower or "discovery" in lower:
        return 40
    if "closed" in lower:
        return 90
    return 50


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value)
    try:
        if len(text) >= 10:
            return date.fromisoformat(text[:10])
    except ValueError:
        return None
    return None


def _relative_updated(value: Any) -> str:
    if not value:
        return "Recently"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - parsed
        days = delta.days
        if days <= 0:
            hours = int(delta.total_seconds() // 3600)
            return f"{max(hours, 1)}h ago"
        if days == 1:
            return "Yesterday"
        return f"{days} days ago"
    except ValueError:
        return str(value)[:40]
