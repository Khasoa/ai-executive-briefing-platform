import { useState } from "react"
import { CheckCircle2, CircleAlert, CircleDashed, Loader2, Plug } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
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
import { getIntegrations, syncIntegration, checkIntegration } from "@/api/integrations"
import { resolveOAuthStartProvider } from "@/lib/oauthConnect"
import { cn } from "@/lib/utils"

const SYNC_STATUS = {
  success: { Icon: CheckCircle2, className: "text-primary" },
  running: { Icon: Loader2, className: "text-accent animate-spin" },
  warning: { Icon: CircleAlert, className: "text-accent" },
  error: { Icon: CircleAlert, className: "text-critical" },
}

export function IntegrationsPage() {
  const toast = useToast()
  const {
    beginOAuth,
    disconnectGoogle,
    disconnectNotion,
    disconnectGhl,
    disconnectMonday,
    disconnectClickup,
    refreshGoogleStatus,
    refreshNotionStatus,
    refreshGhlStatus,
    refreshMondayStatus,
    refreshClickupStatus,
  } = useAuth()
  const { data, loading, refreshing, error, refreshError, refetch, setData, clearRefreshError } =
    useApiQuery(getIntegrations)
  const [syncingId, setSyncingId] = useState(null)
  const [connectingId, setConnectingId] = useState(null)
  const [checkingId, setCheckingId] = useState(null)
  const sync = useAsyncAction(syncIntegration)
  const check = useAsyncAction(checkIntegration)

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
    // Refresh list so Sync failed / statusDetail is visible after a provider error.
    refetch()
  }

  async function handleCheck(integrationId) {
    setCheckingId(integrationId)
    const { data: result, error: actionError } = await check.run(integrationId)
    setCheckingId(null)
    if (result) {
      refetch()
      if (result.configured) toast.success(result.message)
      else toast.error(result.message)
      return
    }
    if (actionError) toast.error(actionError.message)
  }

  async function handleConnect(integrationId) {
    const provider = resolveOAuthStartProvider(integrationId)
    if (!provider) {
      toast.error("This integration does not use OAuth Connect.")
      return
    }

    setConnectingId(integrationId)
    try {
      // One provider only — never fan out to sibling OAuth starts.
      await beginOAuth(provider)
    } catch (err) {
      setConnectingId(null)
      const labels = {
        notion: "Notion",
        gohighlevel: "GoHighLevel",
        monday: "monday.com",
        clickup: "ClickUp",
        google: "Google",
      }
      const label = labels[provider] || "OAuth"
      toast.error(err?.message || `Could not start ${label} OAuth.`)
    }
  }

  async function handleDisconnect(integrationId) {
    try {
      if (integrationId === "notion") {
        await disconnectNotion()
        await refreshNotionStatus()
        refetch()
        toast.success("Notion disconnected")
        return
      }
      if (integrationId === "gohighlevel") {
        await disconnectGhl()
        await refreshGhlStatus()
        refetch()
        toast.success("GoHighLevel disconnected")
        return
      }
      if (integrationId === "monday") {
        await disconnectMonday()
        await refreshMondayStatus()
        refetch()
        toast.success("monday.com disconnected")
        return
      }
      if (integrationId === "clickup") {
        await disconnectClickup()
        await refreshClickupStatus()
        refetch()
        toast.success("ClickUp disconnected")
        return
      }
      // Google family (google / gmail / google-calendar) shares one OAuth row.
      if (
        integrationId === "google" ||
        integrationId === "gmail" ||
        integrationId === "google-calendar"
      ) {
        await disconnectGoogle()
        await refreshGoogleStatus()
        refetch()
        toast.success("Google disconnected")
        return
      }
      toast.error("Disconnect is not available for this integration.")
    } catch (err) {
      toast.error(err?.message || "Could not disconnect integration.")
    }
  }

  if (loading) return <ListSkeleton rows={3} maxWidth="max-w-5xl" />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { integrations, syncHistory, connectedCount, totalCount } = data

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow="Integrations"
        title="Where your brief comes from"
        description={`${connectedCount} of ${totalCount} systems are ready. Briefly reads from each of them every morning and cites them in every recommendation.`}
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
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onCheck={handleCheck}
              syncing={syncingId === integration.id}
              connecting={connectingId === integration.id}
              checking={checkingId === integration.id}
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
