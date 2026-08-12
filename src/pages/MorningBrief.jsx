import { useState } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import {
  AlertTriangle,
  CalendarClock,
  CalendarRange,
  Check,
  Inbox,
  Loader2,
  Printer,
  RefreshCw,
  Sparkles,
  Sun,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { MorningBriefCard } from "@/components/cards/MorningBriefCard"
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
import {
  getMorningBrief,
  regenerateMorningBrief,
  setChecklistItem,
} from "@/api/morningBrief"
import { cn } from "@/lib/utils"
import { fadeUp } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_DOT, SIGNAL_LABEL } from "@/lib/signals"

const FOCUS_KIND = {
  "deep-work": { label: "Deep work", className: "border-primary/25 bg-primary-soft text-primary" },
  decision: { label: "Decision", className: "border-accent/25 bg-accent-soft text-accent" },
  "quick-win": { label: "Quick win", className: "border-border bg-subtle text-secondary-foreground" },
  review: { label: "Review", className: "border-border bg-subtle text-secondary-foreground" },
}

function BriefMasthead({ meta, preparedFor, onRegenerate, regenerating, onRefresh, refreshing }) {
  return (
    <motion.header {...fadeUp} className="mb-6 sm:mb-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="eyebrow mb-2 text-muted-foreground">Morning Brief · {meta.date}</p>
          <h1 className="max-w-3xl font-serif text-[1.75rem] font-medium leading-[1.2] tracking-tight text-foreground text-balance sm:text-[2rem]">
            {meta.headline}
          </h1>
          <p className="mt-3 text-[13px] text-muted-foreground">
            Prepared for {preparedFor.fullName}, {preparedFor.role} at {preparedFor.company} ·
            generated {meta.generatedLabel}
          </p>
        </div>

        <div className="flex w-full shrink-0 flex-wrap items-center gap-2 no-print sm:w-auto">
          <RefreshButton onClick={onRefresh} refreshing={refreshing} />
          <Button
            variant="secondary"
            size="md"
            className="gap-1.5"
            onClick={onRegenerate}
            disabled={regenerating}
            aria-label={regenerating ? "Regenerating brief" : "Regenerate brief"}
          >
            {regenerating ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} aria-hidden="true" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            )}
            Regenerate
          </Button>
          <Button
            variant="secondary"
            size="md"
            className="gap-1.5"
            onClick={() => window.print()}
            aria-label="Print morning brief"
          >
            <Printer className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            Print
          </Button>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border pt-4">
        <Badge variant="primary" className="gap-1.5">
          <Sparkles className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
          {meta.confidence} confidence
        </Badge>
        {meta.sources.map((source) => (
          <SourceChip key={source} source={source} />
        ))}
        <Link
          to="/weekly-digest"
          className="ml-auto inline-flex items-center gap-1.5 text-[12px] font-medium text-muted-foreground transition-colors hover:text-foreground no-print"
        >
          <CalendarRange className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
          Review this week&apos;s activity
        </Link>
      </div>
    </motion.header>
  )
}

function ChecklistRow({ item, onToggle, pending }) {
  return (
    <li className="flex items-start gap-3 py-2.5 sm:items-center">
      <button
        type="button"
        role="checkbox"
        aria-checked={item.done}
        aria-label={`${item.done ? "Mark incomplete" : "Mark complete"}: ${item.label}`}
        disabled={pending}
        onClick={() => onToggle(item)}
        className={cn(
          "mt-0.5 flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded border transition-colors sm:mt-0",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40",
          item.done
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border-strong bg-card hover:border-primary/50",
          pending && "opacity-50",
        )}
      >
        {item.done && <Check className="h-3 w-3" strokeWidth={3} aria-hidden="true" />}
      </button>

      <span
        className={cn(
          "min-w-0 flex-1 text-[13px] leading-snug",
          item.done ? "text-muted-foreground line-through" : "text-foreground",
        )}
      >
        {item.label}
      </span>

      <Badge variant="quiet" className="hidden sm:inline-flex">
        {item.category}
      </Badge>
      <span className="hidden w-24 shrink-0 text-right text-[11px] text-muted-foreground sm:block">
        {item.due}
      </span>
    </li>
  )
}

export function MorningBriefPage() {
  const toast = useToast()
  const { data, loading, refreshing, error, refreshError, refetch, setData, clearRefreshError } =
    useApiQuery(getMorningBrief)
  const [pendingItem, setPendingItem] = useState(null)

  const regenerate = useAsyncAction(regenerateMorningBrief)
  const toggleItem = useAsyncAction(setChecklistItem)

  async function handleRegenerate() {
    const { data: fresh, error: actionError } = await regenerate.run()
    if (fresh) {
      setData(fresh)
      toast.success("Morning Brief regenerated")
      return
    }
    if (actionError) toast.error(actionError.message)
  }

  async function handleToggle(item) {
    setPendingItem(item.id)
    const { data: updated, error: actionError } = await toggleItem.run(item.id, !item.done)
    setPendingItem(null)
    if (!updated) {
      if (actionError) toast.error(actionError.message)
      return
    }

    setData((current) => ({
      ...current,
      actionChecklist: current.actionChecklist.map((entry) =>
        entry.id === updated.id ? updated : entry,
      ),
    }))
    toast.success(updated.done ? "Checklist item completed" : "Checklist item reopened")
  }

  if (loading) return <DocumentSkeleton />
  if (error) return <PageError error={error} onRetry={refetch} />

  const {
    meta,
    preparedFor,
    executiveSummary,
    topPriorities,
    criticalRisks,
    meetings,
    clientsNeedingAttention,
    importantEmails,
    suggestedFocus,
    recommendedDelegation,
    actionChecklist,
    closing,
  } = data

  const completed = actionChecklist.filter((item) => item.done).length
  const briefShellEmpty =
    !executiveSummary && topPriorities.length === 0 && criticalRisks.length === 0

  if (briefShellEmpty) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <EmptyState
          icon={Sun}
          title="No Morning Brief for today"
          description="Briefly generates your brief from connected systems each morning. Connect your tools, then regenerate — or wait for the scheduled run."
          actionLabel="Open Integrations"
          actionTo="/integrations"
        />
      </div>
    )
  }

  return (
    <div className="print-page mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <BriefMasthead
        meta={meta}
        preparedFor={preparedFor}
        onRegenerate={handleRegenerate}
        regenerating={regenerate.pending}
        onRefresh={refetch}
        refreshing={refreshing}
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <div className="space-y-5">
        <MorningBriefCard number={1} title="Executive summary" index={0}>
          <p className="font-serif text-[17px] leading-[1.7] text-foreground text-balance">
            {executiveSummary}
          </p>
        </MorningBriefCard>

        <MorningBriefCard
          number={2}
          title="Top priorities"
          description="Ranked by consequence, not by deadline"
          meta={`${topPriorities.length} items`}
          index={1}
        >
          {topPriorities.length === 0 ? (
            <EmptyState
              title="No priorities flagged"
              description="When your systems surface consequential work, it appears here ranked by impact."
              className="border-0 bg-transparent py-8"
            />
          ) : (
            <ol className="divide-y divide-border">
              {topPriorities.map((priority) => (
                <li key={priority.id} className="flex items-start gap-4 py-3.5 first:pt-0 last:pb-0">
                  <span className="w-5 shrink-0 pt-0.5 text-[15px] font-semibold text-faint numeric">
                    {priority.rank}
                  </span>
                  <span
                    className={cn(
                      "mt-1 h-full w-0.5 shrink-0 self-stretch rounded-full",
                      SIGNAL_ACCENT_BAR[priority.urgency],
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <h3 className="text-[14px] font-semibold leading-snug">{priority.title}</h3>
                      <Badge variant={SIGNAL_BADGE[priority.urgency]}>
                        {SIGNAL_LABEL[priority.urgency]}
                      </Badge>
                    </div>
                    <p className="mt-1 text-[13px] leading-relaxed text-secondary-foreground">
                      {priority.detail}
                    </p>
                    <div className="mt-2 flex items-center gap-2">
                      <span className="text-[11px] text-muted-foreground">
                        Owner: {priority.owner}
                      </span>
                      <SourceChip source={priority.source} />
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </MorningBriefCard>

        <MorningBriefCard
          number={3}
          title="Critical risks"
          description="What could go wrong today, and what to do about it"
          meta={`${criticalRisks.length} identified`}
          index={2}
          tone="accent"
        >
          {criticalRisks.length === 0 ? (
            <EmptyState
              title="No critical risks today"
              description="Briefly only surfaces risks that need an executive decision before the day ends."
              className="border-0 bg-transparent py-8"
            />
          ) : (
            <div className="space-y-4">
              {criticalRisks.map((risk) => (
                <article key={risk.id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle
                      className={cn(
                        "mt-0.5 h-4 w-4 shrink-0",
                        risk.severity === "critical" ? "text-critical" : "text-accent",
                      )}
                      strokeWidth={1.75}
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <h3 className="text-[14px] font-semibold leading-snug">{risk.title}</h3>
                        <Badge variant={SIGNAL_BADGE[risk.severity]}>{risk.impact}</Badge>
                      </div>
                      <p className="mt-1 text-[13px] leading-relaxed text-secondary-foreground">
                        {risk.detail}
                      </p>
                      <p className="mt-2.5 border-l-2 border-primary/30 pl-3 text-[13px] leading-relaxed text-secondary-foreground">
                        <span className="font-medium text-foreground">Mitigation. </span>
                        {risk.mitigation}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </MorningBriefCard>

        <MorningBriefCard
          number={4}
          title="Today's meetings"
          meta={`${meetings.length} scheduled`}
          index={3}
        >
          {meetings.length === 0 ? (
            <EmptyState
              icon={CalendarClock}
              title="No meetings in today's brief"
              description="Connect Google Calendar so meeting prep appears here alongside the rest of your briefing."
              actionLabel="Open Integrations"
              actionTo="/integrations"
              className="border-0 bg-transparent py-8"
            />
          ) : (
            <ul className="divide-y divide-border">
              {meetings.map((meeting) => (
                <li key={meeting.id} className="flex items-start gap-4 py-3 first:pt-0 last:pb-0">
                  <span className="w-12 shrink-0 text-[13px] font-semibold text-foreground numeric">
                    {meeting.time}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-[13px] font-semibold leading-snug">{meeting.title}</h3>
                      {meeting.prepStatus === "needs-prep" && (
                        <Badge variant="accent">Needs preparation</Badge>
                      )}
                    </div>
                    <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                      {meeting.note}
                    </p>
                    <p className="mt-1 text-[11px] text-faint">{meeting.attendees.join(", ")}</p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </MorningBriefCard>

        <MorningBriefCard
          number={5}
          title="Clients needing attention"
          meta={`${clientsNeedingAttention.length} accounts`}
          index={4}
        >
          {clientsNeedingAttention.length === 0 ? (
            <EmptyState
              title="No accounts need you today"
              description="Pipeline risk that needs an executive touch will surface here."
              className="border-0 bg-transparent py-8"
            />
          ) : (
            <div className="space-y-3">
              {clientsNeedingAttention.map((client) => (
                <article
                  key={client.id}
                  className="flex items-start gap-3 rounded-lg border border-border bg-subtle p-3.5"
                >
                  <span
                    className={cn(
                      "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                      SIGNAL_DOT[client.severity],
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <h3 className="text-[13px] font-semibold">{client.company}</h3>
                      <span className="text-[12px] text-muted-foreground">
                        {client.stage} · {client.value} · {client.lastContact}
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] leading-relaxed text-secondary-foreground">
                      {client.reason}
                    </p>
                    <p className="mt-1.5 text-[13px] leading-relaxed text-primary">
                      {client.recommendedAction}
                    </p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </MorningBriefCard>

        <MorningBriefCard
          number={6}
          title="Important emails"
          description="Summarised so you can decide without opening Gmail"
          meta={`${importantEmails.length} threads`}
          index={5}
        >
          {importantEmails.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="No important threads flagged"
              description="Connect Gmail so high-priority threads appear in the brief without opening your inbox."
              actionLabel="Open Integrations"
              actionTo="/integrations"
              className="border-0 bg-transparent py-8"
            />
          ) : (
            <ul className="divide-y divide-border">
              {importantEmails.map((email) => (
                <li key={email.id} className="py-3.5 first:pt-0 last:pb-0">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <h3 className="text-[13px] font-semibold leading-snug">{email.subject}</h3>
                    <Badge variant={SIGNAL_BADGE[email.priority]}>
                      {SIGNAL_LABEL[email.priority]}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-[11px] text-muted-foreground">
                    {email.sender} · {email.waitingSince}
                  </p>
                  <p className="mt-1.5 text-[13px] leading-relaxed text-secondary-foreground">
                    {email.summary}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </MorningBriefCard>

        <MorningBriefCard
          number={7}
          title="Suggested focus"
          description={suggestedFocus.headline}
          index={6}
        >
          <p className="mb-4 text-[13px] leading-relaxed text-muted-foreground">
            {suggestedFocus.rationale}
          </p>
          <ul className="space-y-2">
            {suggestedFocus.blocks.map((block) => {
              const kind = FOCUS_KIND[block.kind]
              return (
                <li
                  key={block.id}
                  className="flex flex-col gap-2 rounded-lg border border-border bg-card px-3.5 py-3 sm:flex-row sm:items-start sm:gap-4"
                >
                  <span className="w-auto shrink-0 text-[12px] font-medium text-foreground numeric sm:w-24">
                    {block.start}–{block.end}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium leading-snug">{block.label}</p>
                    <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                      {block.reason}
                    </p>
                  </div>
                  <span
                    className={cn(
                      "self-start rounded-md border px-2 py-0.5 text-[11px] font-medium",
                      kind.className,
                    )}
                  >
                    {kind.label}
                  </span>
                </li>
              )
            })}
          </ul>
        </MorningBriefCard>

        <MorningBriefCard
          number={8}
          title="Recommended delegation"
          description="Work that does not need you, and who should own it"
          index={7}
        >
          <ul className="divide-y divide-border">
            {recommendedDelegation.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:gap-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium leading-snug">{item.task}</p>
                  <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                    {item.reason}
                  </p>
                </div>
                <div className="w-full shrink-0 text-left sm:w-40 sm:text-right">
                  <p className="text-[13px] font-medium">{item.assignee}</p>
                  <p className="text-[11px] text-muted-foreground">{item.assigneeRole}</p>
                  <p className="mt-0.5 text-[11px] font-medium text-primary">{item.effort}</p>
                </div>
              </li>
            ))}
          </ul>
        </MorningBriefCard>

        <MorningBriefCard
          number={9}
          title="Action checklist"
          meta={`${completed} of ${actionChecklist.length} complete`}
          index={8}
        >
          {actionChecklist.length === 0 ? (
            <EmptyState
              title="No checklist items"
              description="Regenerate the brief after connecting your systems to get today's action list."
              className="border-0 bg-transparent py-8"
            />
          ) : (
            <>
              <Progress
                value={(completed / actionChecklist.length) * 100}
                label="Checklist progress"
                className="mb-3"
              />
              <ul className="divide-y divide-border">
                {actionChecklist.map((item) => (
                  <ChecklistRow
                    key={item.id}
                    item={item}
                    onToggle={handleToggle}
                    pending={pendingItem === item.id}
                  />
                ))}
              </ul>
            </>
          )}
        </MorningBriefCard>
      </div>

      <motion.section {...fadeUp} className="mt-8">
        <Card className="overflow-hidden border-primary/20">
          <div className="bg-primary px-5 py-5 sm:px-6">
            <p className="eyebrow text-primary-foreground/60">The question that matters</p>
            <h2 className="mt-1.5 font-serif text-[20px] font-medium leading-snug text-primary-foreground sm:text-[22px]">
              {closing.question}
            </h2>
          </div>
          <div className="px-5 py-5 sm:px-6">
            <p className="font-serif text-[16px] leading-[1.7] text-foreground text-balance">
              {closing.answer}
            </p>
            <ul className="mt-4 space-y-2">
              {closing.bullets.map((bullet) => (
                <li key={bullet} className="flex items-start gap-2.5">
                  <span className="mt-[0.45rem] h-1 w-1 shrink-0 rounded-full bg-primary" />
                  <span className="text-[13px] leading-relaxed text-secondary-foreground">
                    {bullet}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </Card>
      </motion.section>

      <p className="mt-6 text-center text-[11px] text-faint">
        Briefly summarises and recommends. Every decision, reply and action stays yours.
      </p>
    </div>
  )
}
