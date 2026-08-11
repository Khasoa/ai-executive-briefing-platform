import { Link } from "react-router-dom"
import { motion } from "framer-motion"
import {
  ArrowRight,
  CalendarRange,
  Inbox,
  Loader2,
  RefreshCw,
  Sparkles,
  Sun,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { RefreshButton } from "@/components/common/RefreshButton"
import {
  DocumentSkeleton,
  EmptyState,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useToast } from "@/hooks/useToast"
import { useApiQuery } from "@/hooks/useApiQuery"
import { useAsyncAction } from "@/hooks/useAsyncAction"
import { getWeeklyDigest, regenerateWeeklyDigest } from "@/api/weeklyDigest"
import { fadeUp } from "@/lib/motion"

function DigestSection({ title, description, items, emptyHint }) {
  if (!items?.length) {
    if (!emptyHint) return null
    return (
      <section className="mt-8">
        <div className="mb-2">
          <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
          {description ? (
            <p className="mt-0.5 text-[12px] text-muted-foreground">{description}</p>
          ) : null}
        </div>
        <p className="text-[13px] text-muted-foreground">{emptyHint}</p>
      </section>
    )
  }

  return (
    <section className="mt-8">
      <div className="mb-3">
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {description ? (
          <p className="mt-0.5 text-[12px] text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <ul className="divide-y divide-border rounded-xl border border-border bg-card">
        {items.map((item) => (
          <li key={item.id} className="px-4 py-3.5 sm:px-5">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="text-[13px] font-medium leading-snug text-foreground">{item.title}</p>
              <div className="flex flex-wrap items-center gap-1.5">
                {item.kind === "recommendation" ? (
                  <Badge variant="quiet">Recommendation</Badge>
                ) : null}
                <SourceChip source={item.source || "Gmail"} />
              </div>
            </div>
            {item.detail ? (
              <p className="mt-1 text-[13px] leading-relaxed text-secondary-foreground">
                {item.detail}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  )
}

function OutlookGroup({ title, items }) {
  if (!items?.length) return null
  return (
    <div className="mt-4 first:mt-0">
      <p className="mb-2 text-[12px] font-medium text-muted-foreground">{title}</p>
      <ul className="space-y-2.5">
        {items.map((item) => (
          <li key={item.id} className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-medium leading-snug">{item.title}</p>
              {item.detail ? (
                <p className="mt-0.5 text-[12px] leading-relaxed text-secondary-foreground">
                  {item.detail}
                </p>
              ) : null}
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-1.5">
              {item.kind === "recommendation" ? (
                <Badge variant="quiet">Recommendation</Badge>
              ) : (
                <Badge variant="quiet">Fact</Badge>
              )}
              <SourceChip source={item.source || "Gmail"} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}

function hasOutlookContent(outlook) {
  if (!outlook) return false
  return Boolean(
    outlook.upcomingMeetings?.length ||
      outlook.upcomingDeadlines?.length ||
      outlook.overdueWork?.length ||
      outlook.crmAttention?.length ||
      outlook.emailFollowUps?.length ||
      outlook.workItems?.length ||
      outlook.carryForward?.length ||
      outlook.recommendedPriorities?.length ||
      outlook.risksAndWatchouts?.length ||
      outlook.workloadSignals?.length,
  )
}

export function WeeklyDigestPage() {
  const toast = useToast()
  const { data, loading, refreshing, error, refreshError, refetch, setData, clearRefreshError } =
    useApiQuery(getWeeklyDigest)
  const regenerate = useAsyncAction(regenerateWeeklyDigest)

  async function handleRegenerate() {
    const { data: fresh, error: actionError } = await regenerate.run()
    if (fresh) {
      setData(fresh)
      toast.success("Weekly Digest regenerated")
      return
    }
    if (actionError) toast.error(actionError.message)
  }

  if (loading) return <DocumentSkeleton label="Loading weekly digest" />
  if (error) return <PageError error={error} onRetry={refetch} />

  const coverage = data.dataCoverage || {}
  const sourcesWithData = coverage.sourcesWithData || data.sources || []
  const outlook = data.nextWeekOutlook || {}
  const emailCount = data.emailCount || coverage.emailCount || 0
  const empty =
    !emailCount &&
    !sourcesWithData.length &&
    !data.importantConversations?.length &&
    !data.followUps?.length &&
    !data.notableActivity?.length &&
    !data.carryIntoNextWeek?.length &&
    !hasOutlookContent(outlook)

  if (empty) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <EmptyState
          icon={Inbox}
          title="No weekly activity yet"
          description="Once your integrations sync records, Briefly turns the last 7 days into weekly intelligence and a next-week outlook — only from your data."
          actionLabel="Open Integrations"
          actionTo="/integrations"
        />
      </div>
    )
  }

  const curated = data.generatedBy === "curated"
  const weekSummary = data.weekSummary || data.summary

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <motion.header {...fadeUp} className="mb-6 sm:mb-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="eyebrow mb-2 text-muted-foreground">
              Weekly Intelligence · {data.weekLabel}
            </p>
            <h1 className="max-w-2xl font-serif text-[1.65rem] font-medium leading-[1.2] tracking-tight text-balance sm:text-[1.85rem]">
              {data.headline}
            </h1>
            <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-secondary-foreground">
              {weekSummary}
            </p>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <RefreshButton onClick={refetch} refreshing={refreshing} />
            <Button
              variant="secondary"
              size="md"
              className="gap-1.5"
              onClick={handleRegenerate}
              disabled={regenerate.pending}
              aria-label={regenerate.pending ? "Regenerating digest" : "Regenerate digest"}
            >
              {regenerate.pending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} aria-hidden="true" />
              ) : (
                <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              )}
              Regenerate
            </Button>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border pt-4">
          <Badge variant={curated ? "quiet" : "primary"} className="gap-1.5">
            {curated ? (
              <CalendarRange className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
            ) : (
              <Sparkles className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
            )}
            {curated ? "Curated fallback" : `${data.confidence} confidence · AI`}
          </Badge>
          <span className="text-[12px] text-muted-foreground numeric">
            {data.emailCount} emails · generated {data.generatedLabel}
          </span>
          {data.sources?.map((source) => (
            <SourceChip key={source} source={source} />
          ))}
        </div>

        {coverage.emailNote ? (
          <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">
            {coverage.emailNote}
          </p>
        ) : null}

        <p className="mt-3 text-[12px] text-muted-foreground">
          What happened this week, and what to expect next — not today&apos;s priorities.{" "}
          <Link to="/morning-brief" className="text-foreground underline-offset-2 hover:underline">
            Open Morning Brief
          </Link>{" "}
          for what needs attention today.
        </p>
      </motion.header>

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <section className="mt-2">
        <h2 className="text-[15px] font-semibold tracking-tight">What happened this week</h2>
        <p className="mt-0.5 text-[12px] text-muted-foreground">
          Cross-system memory from synced records
        </p>
      </section>

      <DigestSection
        title="Important conversations"
        description="Threads and decisions that shaped the week"
        items={data.importantConversations}
        emptyHint={
          sourcesWithData.includes("Gmail")
            ? null
            : "No Gmail threads in this window — connect and sync Gmail to fill this section."
        }
      />
      <DigestSection title="Decisions & approvals" items={data.decisionsAndApprovals} />
      <DigestSection title="Follow-ups" items={data.followUps} />
      <DigestSection title="Unresolved" items={data.unresolvedItems} />
      <DigestSection title="Notable activity" items={data.notableActivity} />
      <DigestSection
        title="Carry into next week"
        description="What should not slip"
        items={data.carryIntoNextWeek}
      />

      <section className="mt-10">
        <div className="mb-3">
          <h2 className="text-[15px] font-semibold tracking-tight">Next week outlook</h2>
          <p className="mt-0.5 text-[12px] text-muted-foreground">
            What to expect — facts from your systems, recommendations labelled separately
          </p>
        </div>
        {hasOutlookContent(outlook) ? (
          <Card>
            <div className="divide-y divide-border px-4 py-4 sm:px-5">
              <OutlookGroup title="Upcoming meetings" items={outlook.upcomingMeetings} />
              <OutlookGroup title="Upcoming deadlines" items={outlook.upcomingDeadlines} />
              <OutlookGroup title="Overdue work" items={outlook.overdueWork} />
              <OutlookGroup title="CRM needing attention" items={outlook.crmAttention} />
              <OutlookGroup title="Email follow-ups" items={outlook.emailFollowUps} />
              <OutlookGroup title="Important work items" items={outlook.workItems} />
              <OutlookGroup title="Likely carry-forward" items={outlook.carryForward} />
              <OutlookGroup title="Recommended priorities" items={outlook.recommendedPriorities} />
              <OutlookGroup title="Risks & watchouts" items={outlook.risksAndWatchouts} />
              <OutlookGroup title="Workload signals" items={outlook.workloadSignals} />
            </div>
          </Card>
        ) : (
          <p className="text-[13px] text-muted-foreground">
            No forward-looking items yet. Upcoming meetings, deadlines, and CRM risks appear here
            once those systems have synced rows for your account.
          </p>
        )}
      </section>

      {data.planningNote ? (
        <Card className="mt-8">
          <div className="px-5 py-4 sm:px-6">
            <p className="eyebrow text-muted-foreground">Planning note</p>
            <p className="mt-2 text-[14px] leading-relaxed text-secondary-foreground">
              {data.planningNote}
            </p>
          </div>
        </Card>
      ) : null}

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to="/morning-brief"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-foreground hover:underline"
        >
          <Sun className="h-3.5 w-3.5 text-accent-strong" strokeWidth={1.75} aria-hidden="true" />
          Morning Brief
          <ArrowRight className="h-3.5 w-3.5 text-faint" strokeWidth={1.75} aria-hidden="true" />
        </Link>
        <Link
          to="/inbox"
          className="inline-flex items-center gap-1.5 text-[13px] font-medium text-muted-foreground hover:text-foreground hover:underline"
        >
          <Inbox className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
          Inbox
        </Link>
      </div>
    </div>
  )
}
