import { useMemo, useState } from "react"
import { Inbox as InboxIcon, Sparkles } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Tabs } from "@/components/ui/tabs"
import { PageHeader } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import { EmailCard } from "@/components/cards/EmailCard"
import {
  EmptyState,
  ListSkeleton,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getInbox } from "@/api/inbox"
import { bySignal } from "@/lib/signals"

const ALL_TAB = "all"

export function InboxPage() {
  const { data, loading, refreshing, error, refreshError, refetch, clearRefreshError } =
    useApiQuery(getInbox)
  const [activeTab, setActiveTab] = useState(ALL_TAB)

  const tabs = useMemo(() => {
    if (!data) return []
    return [
      { id: ALL_TAB, label: "All", count: data.emails.length },
      ...data.categories.map((category) => ({
        id: category.id,
        label: category.label,
        count: category.count,
      })),
    ]
  }, [data])

  const visibleEmails = useMemo(() => {
    if (!data) return []
    const filtered =
      activeTab === ALL_TAB
        ? data.emails
        : data.emails.filter((email) => email.category === activeTab)
    return [...filtered].sort(bySignal("priority"))
  }, [data, activeTab])

  if (loading) return <ListSkeleton rows={4} />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { summary, categories, emails } = data
  const activeCategory = categories.find((category) => category.id === activeTab)
  const inboxEmpty = emails.length === 0

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow="Inbox"
        title={summary.headline}
        description={`${summary.totalUnread} threads reviewed · ${summary.handledAutomatically} handled by rules · ~${summary.estimatedClearTime} left`}
        actions={<RefreshButton onClick={refetch} refreshing={refreshing} />}
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <Card className="mb-6">
        <dl className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            ["Unread threads", summary.totalUnread],
            ["Need your reply", categories.find((c) => c.id === "needs-reply")?.count ?? 0],
            ["Handled by rules", summary.handledAutomatically],
            ["Time to clear", summary.estimatedClearTime],
          ].map(([label, value]) => (
            <div key={label} className="px-3 py-3 sm:px-5 sm:py-4">
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[16px] font-semibold numeric sm:text-[18px]">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {inboxEmpty ? (
        <EmptyState
          icon={InboxIcon}
          title="No emails need your attention"
          description="When Gmail is connected, Briefly prioritises threads that need a reply and clears the rest with your rules. Connect Gmail to start filling this inbox."
          actionLabel="Open Integrations"
          actionTo="/integrations"
        />
      ) : (
        <>
          <Tabs tabs={tabs} value={activeTab} onChange={setActiveTab} className="mb-5" />

          {activeCategory && (
            <div className="mb-4 flex items-start gap-2">
              <Sparkles
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              <p className="text-[13px] text-muted-foreground">{activeCategory.description}</p>
            </div>
          )}

          {visibleEmails.length === 0 ? (
            <EmptyState
              icon={InboxIcon}
              title="Nothing in this category"
              description="No threads match this filter right now. Switch to All, or refresh after your next sync."
              action={
                <RefreshButton onClick={refetch} refreshing={refreshing} label="Refresh inbox" />
              }
            />
          ) : (
            <div className="space-y-3">
              {visibleEmails.map((email, index) => (
                <EmailCard key={email.id} email={email} index={index} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
