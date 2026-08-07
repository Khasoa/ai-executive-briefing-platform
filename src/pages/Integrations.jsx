import { useState } from "react"
import { CheckCircle2, CircleAlert, CircleDashed, Loader2, Plug } from "lucide-react"
import { Card } from "@/components/ui/card"
import { PageHeader, SectionHeading } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import { IntegrationCard } from "@/components/cards/IntegrationCard"
import {
  EmptyState,
  ListSkeleton,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useToast } from "@/hooks/useToast"
import { useApiQuery } from "@/hooks/useApiQuery"
import { useAsyncAction } from "@/hooks/useAsyncAction"
import { getIntegrations, syncIntegration } from "@/api/integrations"
import { cn } from "@/lib/utils"

const SYNC_STATUS = {
  success: { Icon: CheckCircle2, className: "text-primary" },
  running: { Icon: Loader2, className: "text-accent animate-spin" },
  warning: { Icon: CircleAlert, className: "text-accent" },
  error: { Icon: CircleAlert, className: "text-critical" },
}

export function IntegrationsPage() {
  const toast = useToast()
  const { data, loading, refreshing, error, refreshError, refetch, setData, clearRefreshError } =
    useApiQuery(getIntegrations)
  const [syncingId, setSyncingId] = useState(null)
  const sync = useAsyncAction(syncIntegration)

  async function handleSync(integrationId) {
    setSyncingId(integrationId)
    const { data: refreshed, error: actionError } = await sync.run(integrationId)
    setSyncingId(null)
    if (refreshed) {
      setData(refreshed)
      const name =
        refreshed.integrations.find((item) => item.id === integrationId)?.name ?? "Integration"
      toast.success(`${name} sync started`)
      return
    }
    if (actionError) toast.error(actionError.message)
  }

  if (loading) return <ListSkeleton rows={3} maxWidth="max-w-5xl" />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { integrations, syncHistory, connectedCount, totalCount } = data

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow="Integrations"
        title="Where your brief comes from"
        description={`${connectedCount} of ${totalCount} systems are connected. Briefly reads from each of them every morning and cites them in every recommendation.`}
        actions={<RefreshButton onClick={refetch} refreshing={refreshing} />}
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      {integrations.length === 0 ? (
        <EmptyState
          icon={Plug}
          title="No systems connected yet"
          description="Briefly builds every brief from your connected tools. Add Gmail, Calendar, Notion or GoHighLevel to start receiving cited recommendations."
        />
      ) : (
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
      )}

      <div className="mt-10">
        <SectionHeading
          title="Sync history"
          description="Every read Briefly has made across your systems."
        />

        {syncHistory.length === 0 ? (
          <EmptyState
            icon={Loader2}
            title="No sync events yet"
            description="After you connect a system and run a sync — or when your morning brief generates — activity appears here."
            className="py-10"
          />
        ) : (
          <Card>
            <ul className="divide-y divide-border">
              {syncHistory.map((event) => {
                const status = SYNC_STATUS[event.status] ?? SYNC_STATUS.success
                return (
                  <li key={event.id} className="flex items-start gap-3 px-4 py-3.5 sm:px-5">
                    <status.Icon
                      className={cn("mt-0.5 h-4 w-4 shrink-0", status.className)}
                      strokeWidth={1.75}
                      aria-hidden="true"
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
        )}
      </div>

      <div className="mt-8 flex items-start gap-3 rounded-xl border border-dashed border-border bg-subtle px-4 py-4 sm:px-5">
        <CircleDashed
          className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground"
          strokeWidth={1.75}
          aria-hidden="true"
        />
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
