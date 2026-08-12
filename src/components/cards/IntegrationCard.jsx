import { motion } from "framer-motion"
import {
  Calendar,
  CheckSquare,
  Database,
  FileText,
  LayoutGrid,
  Loader2,
  Mail,
  RefreshCw,
  Sparkles,
  Workflow,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { enter } from "@/lib/motion"

const PROVIDER_ICONS = {
  "google-calendar": Calendar,
  gmail: Mail,
  google: Mail,
  notion: FileText,
  gohighlevel: Database,
  monday: LayoutGrid,
  clickup: CheckSquare,
  openai: Sparkles,
  n8n: Workflow,
}

const STATUS = {
  connected: { label: "Connected", badge: "primary", dot: "bg-primary" },
  configured: { label: "Configured", badge: "primary", dot: "bg-primary" },
  syncing: { label: "Syncing", badge: "accent", dot: "bg-accent-strong pulse-soft" },
  "not-connected": { label: "Not configured", badge: "quiet", dot: "bg-faint" },
  error: { label: "Sync failed", badge: "critical", dot: "bg-critical" },
}

function statusPresentation(integration) {
  const authType = integration.authType || "oauth"
  const status = integration.status
  if (authType === "oauth" || authType === "derived") {
    if (status === "not-connected") {
      return { label: "Disconnected", badge: "quiet", dot: "bg-faint" }
    }
    if (status === "connected" && (!integration.lastSync || integration.lastSyncLabel === "Never")) {
      return { label: "Connected", badge: "primary", dot: "bg-primary" }
    }
  }
  return STATUS[status] ?? STATUS["not-connected"]
}

export function IntegrationCard({
  integration,
  index = 0,
  onSync,
  onConnect,
  onDisconnect,
  onCheck,
  syncing = false,
  connecting = false,
  checking = false,
}) {
  const Icon = PROVIDER_ICONS[integration.id] ?? Database
  const status = statusPresentation(integration)
  const authType = integration.authType || "oauth"
  const isOAuthFamily = authType === "oauth" || authType === "derived"
  const isEnvConfig = authType === "api_key" || authType === "webhook"
  const canSync = integration.canSync ?? isOAuthFamily
  const canConnect =
    integration.canConnect ??
    ((authType === "oauth" || authType === "derived") && integration.status === "not-connected")
  const canDisconnect =
    integration.canDisconnect ??
    (isOAuthFamily &&
      (integration.status === "connected" ||
        integration.status === "syncing" ||
        integration.status === "error"))
  const canCheck = integration.canCheck ?? isEnvConfig
  const showConnectedActions =
    isOAuthFamily &&
    (integration.status === "connected" ||
      integration.status === "syncing" ||
      integration.status === "error")

  return (
    <motion.div {...enter(index)}>
      <Card interactive className="flex h-full flex-col">
        <div className="flex flex-1 flex-col p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-subtle">
                <Icon className="h-4 w-4 text-secondary-foreground" strokeWidth={1.75} />
              </span>
              <div>
                <h3 className="text-[14px] font-semibold leading-tight tracking-tight">
                  {integration.name}
                </h3>
                <p className="mt-0.5 text-[11px] text-muted-foreground">{integration.category}</p>
              </div>
            </div>

            <Badge variant={status.badge} className="gap-1.5">
              <span className={cn("h-1.5 w-1.5 rounded-full", status.dot)} />
              {status.label}
            </Badge>
          </div>

          <p className="mt-3 text-[13px] leading-relaxed text-secondary-foreground">
            {integration.description}
          </p>

          {integration.statusDetail ? (
            <p className="mt-2 text-[12px] leading-snug text-muted-foreground">
              {integration.statusDetail}
            </p>
          ) : null}

          <dl className="mt-4 grid grid-cols-2 gap-3 rounded-lg bg-subtle px-3.5 py-3">
            {integration.metrics.map((metric) => (
              <div key={metric.label}>
                <dt className="text-[11px] text-muted-foreground">{metric.label}</dt>
                <dd className="mt-0.5 text-[13px] font-medium numeric">{metric.value}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-4 space-y-1.5 text-[12px]">
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">
                {isEnvConfig ? "Configuration" : "Account"}
              </span>
              <span className="truncate text-secondary-foreground">
                {integration.account ?? "—"}
              </span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">
                {isEnvConfig ? "Status" : "Last sync"}
              </span>
              <span className="text-secondary-foreground">{integration.lastSyncLabel}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">
                {authType === "webhook" ? "Auth" : authType === "api_key" ? "Auth" : "Scopes"}
              </span>
              <span className="truncate text-secondary-foreground">
                {authType === "api_key"
                  ? "API key (server)"
                  : authType === "webhook"
                    ? "Shared webhook secret"
                    : integration.scopes.join(", ")}
              </span>
            </div>
          </div>

          <p className="mt-auto pt-4 text-[11px] text-faint">via {integration.poweredBy}</p>
        </div>

        <div className="flex flex-col gap-2 border-t border-border px-5 py-3">
          {showConnectedActions ? (
            <div className="flex items-center gap-2">
              {canSync ? (
                <Button
                  size="sm"
                  variant="secondary"
                  className="gap-1.5"
                  disabled={syncing || integration.status === "syncing"}
                  onClick={() => onSync?.(integration.id)}
                  aria-label={`Sync ${integration.name}`}
                >
                  {syncing ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} aria-hidden="true" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
                  )}
                  Sync now
                </Button>
              ) : null}
              {canDisconnect ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onDisconnect?.(integration.id)}
                  aria-label={`Disconnect ${integration.name}`}
                >
                  Disconnect
                </Button>
              ) : null}
            </div>
          ) : canConnect ? (
            <Button
              type="button"
              size="sm"
              variant="primary"
              className="w-full"
              disabled={connecting}
              aria-busy={connecting || undefined}
              onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                if (connecting) return
                onConnect?.(integration.id)
              }}
              aria-label={`Connect ${integration.name}`}
            >
              {connecting ? "Redirecting…" : `Connect ${integration.name}`}
            </Button>
          ) : canCheck ? (
            <div className="space-y-1.5">
              <Button
                size="sm"
                variant="secondary"
                className="w-full gap-1.5"
                disabled={checking}
                onClick={() => onCheck?.(integration.id)}
                aria-label={`Check ${integration.name} configuration`}
              >
                {checking ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} aria-hidden="true" />
                ) : null}
                Check configuration
              </Button>
              <p className="text-[11px] leading-snug text-muted-foreground">
                {authType === "api_key"
                  ? integration.status === "configured"
                    ? "Server API key is set — the key is never shown here."
                    : "Ask your admin to configure the OpenAI API key on the server. The key is never shown here."
                  : integration.status === "configured"
                    ? "Webhook secret is set — the secret is never shown here."
                    : "Ask your admin to configure the n8n webhook secret on the server. The secret is never shown here."}
              </p>
            </div>
          ) : (
            <p className="text-[11px] leading-snug text-muted-foreground">
              Additional actions are not available for this provider.
            </p>
          )}
        </div>
      </Card>
    </motion.div>
  )
}
