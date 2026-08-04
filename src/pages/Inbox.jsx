import { useCallback, useMemo, useState } from "react"
import { Inbox as InboxIcon, Sparkles } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Tabs } from "@/components/ui/tabs"
import { PageHeader } from "@/components/common/PageHeader"
import { EmailCard } from "@/components/cards/EmailCard"
import { EmptyState, ListSkeleton, PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getInbox } from "@/services/briefly"
import { bySignal } from "@/lib/signals"

const ALL_TAB = "all"

export function InboxPage() {
  const fetchInbox = useCallback((options) => getInbox(options), [])
  const { data, loading, error, refetch } = useApiQuery(fetchInbox)
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
  if (error) return <PageError message={error} onRetry={refetch} />

  const { summary, categories } = data
  const activeCategory = categories.find((category) => category.id === activeTab)

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow="Inbox"
        title={summary.headline}
        description={`Briefly read ${summary.totalUnread} threads this morning and handled ${summary.handledAutomatically} with your rules. What remains is about ${summary.estimatedClearTime} of work.`}
      />

      <Card className="mb-6">
        <dl className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            ["Unread threads", summary.totalUnread],
            ["Need your reply", categories.find((c) => c.id === "needs-reply")?.count ?? 0],
            ["Handled by rules", summary.handledAutomatically],
            ["Time to clear", summary.estimatedClearTime],
          ].map(([label, value]) => (
            <div key={label} className="px-5 py-4">
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[18px] font-semibold numeric">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Tabs tabs={tabs} value={activeTab} onChange={setActiveTab} className="mb-5" />

      {activeCategory && (
        <div className="mb-4 flex items-start gap-2">
          <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" strokeWidth={1.75} />
          <p className="text-[13px] text-muted-foreground">{activeCategory.description}</p>
        </div>
      )}

      {visibleEmails.length === 0 ? (
        <EmptyState
          icon={InboxIcon}
          title="Nothing here"
          description="No threads in this category need your attention right now."
        />
      ) : (
        <div className="space-y-3">
          {visibleEmails.map((email, index) => (
            <EmailCard key={email.id} email={email} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}
