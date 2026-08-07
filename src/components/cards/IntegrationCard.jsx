import { motion } from "framer-motion"
import {
  Calendar,
  Database,
  FileText,
  Loader2,
  Mail,
  RefreshCw,
  Settings2,
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
  notion: FileText,
  gohighlevel: Database,
  openai: Sparkles,
  n8n: Workflow,
}

const STATUS = {
  connected: { label: "Connected", badge: "primary", dot: "bg-primary" },
  syncing: { label: "Syncing", badge: "accent", dot: "bg-accent-strong pulse-soft" },
  "not-connected": { label: "Not connected", badge: "quiet", dot: "bg-faint" },
  error: { label: "Needs attention", badge: "critical", dot: "bg-critical" },
}

export function IntegrationCard({ integration, index = 0, onSync, syncing = false }) {
  const Icon = PROVIDER_ICONS[integration.id] ?? Database
  const status = STATUS[integration.status] ?? STATUS["not-connected"]
  const isConnected = integration.status !== "not-connected"

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
              <span className="text-muted-foreground">Account</span>
              <span className="truncate text-secondary-foreground">
                {integration.account ?? "—"}
              </span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Last sync</span>
              <span className="text-secondary-foreground">{integration.lastSyncLabel}</span>
            </div>
            <div className="flex justify-between gap-3">
              <span className="text-muted-foreground">Scopes</span>
              <span className="truncate text-secondary-foreground">
                {integration.scopes.join(", ")}
              </span>
            </div>
          </div>

          <p className="mt-auto pt-4 text-[11px] text-faint">via {integration.poweredBy}</p>
        </div>

        <div className="flex items-center gap-2 border-t border-border px-5 py-3">
          {isConnected ? (
            <>
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
              <Button
                size="sm"
                variant="ghost"
                className="gap-1.5"
                aria-label={`Configure ${integration.name}`}
              >
                <Settings2 className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
                Configure
              </Button>
            </>
          ) : (
            <Button size="sm" variant="primary" className="w-full">
              Connect {integration.name}
            </Button>
          )}
        </div>
      </Card>
    </motion.div>
  )
}
