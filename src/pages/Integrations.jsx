import { useCallback, useState } from "react"
import { CheckCircle2, CircleAlert, CircleDashed, Loader2 } from "lucide-react"
import { Card } from "@/components/ui/card"
import { PageHeader, SectionHeading } from "@/components/common/PageHeader"
import { IntegrationCard } from "@/components/cards/IntegrationCard"
import { ListSkeleton, PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { useAsyncAction } from "@/hooks/useAsyncAction"
import { getIntegrations, syncIntegration } from "@/services/briefly"
import { cn } from "@/lib/utils"

const SYNC_STATUS = {
  success: { Icon: CheckCircle2, className: "text-primary" },
  running: { Icon: Loader2, className: "text-accent animate-spin" },
  warning: { Icon: CircleAlert, className: "text-accent" },
  error: { Icon: CircleAlert, className: "text-critical" },
}

export function IntegrationsPage() {
  const fetchIntegrations = useCallback((options) => getIntegrations(options), [])
  const { data, loading, error, refetch, setData } = useApiQuery(fetchIntegrations)
  const [syncingId, setSyncingId] = useState(null)
  const sync = useAsyncAction(syncIntegration)

  async function handleSync(integrationId) {
    setSyncingId(integrationId)
    const refreshed = await sync.run(integrationId)
    setSyncingId(null)
    if (refreshed) setData(refreshed)
  }

  if (loading) return <ListSkeleton rows={3} maxWidth="max-w-5xl" />
  if (error) return <PageError message={error} onRetry={refetch} />

  const { integrations, syncHistory, connectedCount, totalCount } = data

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow="Integrations"
        title="Where your brief comes from"
        description={`${connectedCount} of ${totalCount} systems are connected. Briefly reads from each of them every morning and cites them in every recommendation.`}
      />

      {sync.error && <p className="mb-4 text-[13px] text-critical">{sync.error}</p>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {integrations.map((integration, index) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            index={index}
            onSync={handleSync}
            syncing={syncingId === integration.id}
          />
        ))}
      </div>

      <div className="mt-10">
        <SectionHeading
          title="Sync history"
          description="Every read Briefly has made across your systems."
        />

        <Card>
          <ul className="divide-y divide-border">
            {syncHistory.map((event) => {
              const status = SYNC_STATUS[event.status] ?? SYNC_STATUS.success
              return (
                <li key={event.id} className="flex items-start gap-3 px-5 py-3.5">
                  <status.Icon
                    className={cn("mt-0.5 h-4 w-4 shrink-0", status.className)}
                    strokeWidth={1.75}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium leading-snug">
                      {event.integration}
                      <span className="ml-1.5 font-normal text-muted-foreground">
                        {event.event}
                      </span>
                    </p>
                    <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                      {event.detail}
                    </p>
                  </div>
                  <span className="shrink-0 text-[11px] text-faint numeric">{event.time}</span>
                </li>
              )
            })}
          </ul>
        </Card>
      </div>

      <div className="mt-8 flex items-start gap-3 rounded-xl border border-dashed border-border bg-subtle px-5 py-4">
        <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
        <div>
          <p className="text-[13px] font-medium">Read-only by design</p>
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
            Briefly requests read scopes only. It can summarise a thread and draft a reply, but it
            cannot send mail, move a deal or accept a meeting on your behalf.
          </p>
        </div>
      </div>
    </div>
  )
}
