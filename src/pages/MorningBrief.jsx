import { useCallback, useState } from "react"
import { motion } from "framer-motion"
import {
  AlertTriangle,
  Check,
  Loader2,
  Printer,
  RefreshCw,
  Sparkles,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { MorningBriefCard } from "@/components/cards/MorningBriefCard"
import { SourceChip } from "@/components/common/SourceChip"
import { DocumentSkeleton, PageError } from "@/components/feedback/PageState"
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

function BriefMasthead({ meta, preparedFor, onRegenerate, regenerating }) {
  return (
    <motion.header {...fadeUp} className="mb-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="eyebrow mb-2 text-muted-foreground">Morning Brief · {meta.date}</p>
          <h1 className="max-w-3xl font-serif text-[2rem] font-medium leading-[1.2] tracking-tight text-foreground text-balance">
            {meta.headline}
          </h1>
          <p className="mt-3 text-[13px] text-muted-foreground">
            Prepared for {preparedFor.fullName}, {preparedFor.role} at {preparedFor.company} ·
            generated {meta.generatedLabel}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2 no-print">
          <Button
            variant="secondary"
            size="md"
            className="gap-1.5"
            onClick={onRegenerate}
            disabled={regenerating}
          >
            {regenerating ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} />
            )}
            Regenerate
          </Button>
          <Button variant="secondary" size="md" className="gap-1.5" onClick={() => window.print()}>
            <Printer className="h-3.5 w-3.5" strokeWidth={1.75} />
            Print
          </Button>
        </div>
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-border pt-4">
        <Badge variant="primary" className="gap-1.5">
          <Sparkles className="h-3 w-3" strokeWidth={1.75} />
          {meta.confidence} confidence
        </Badge>
        {meta.sources.map((source) => (
          <SourceChip key={source} source={source} />
        ))}
      </div>
    </motion.header>
  )
}

function ChecklistRow({ item, onToggle, pending }) {
  return (
    <li className="flex items-center gap-3 py-2.5">
      <button
        type="button"
        role="checkbox"
        aria-checked={item.done}
        disabled={pending}
        onClick={() => onToggle(item)}
        className={cn(
          "flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded border transition-colors",
          item.done
            ? "border-primary bg-primary text-primary-foreground"
            : "border-border-strong bg-card hover:border-primary/50",
          pending && "opacity-50",
        )}
      >
        {item.done && <Check className="h-3 w-3" strokeWidth={3} />}
      </button>

      <span
        className={cn(
          "flex-1 text-[13px] leading-snug",
          item.done ? "text-muted-foreground line-through" : "text-foreground",
        )}
      >
        {item.label}
      </span>

      <Badge variant="quiet">{item.category}</Badge>
      <span className="w-24 shrink-0 text-right text-[11px] text-muted-foreground">{item.due}</span>
    </li>
  )
}

export function MorningBriefPage() {
  const fetchBrief = useCallback((options) => getMorningBrief(options), [])
  const { data, loading, error, refetch, setData } = useApiQuery(fetchBrief)
  const [pendingItem, setPendingItem] = useState(null)

  const regenerate = useAsyncAction(regenerateMorningBrief)
  const toggleItem = useAsyncAction(setChecklistItem)

  async function handleRegenerate() {
    const fresh = await regenerate.run()
    if (fresh) setData(fresh)
  }

  async function handleToggle(item) {
    setPendingItem(item.id)
    const updated = await toggleItem.run(item.id, !item.done)
    setPendingItem(null)
    if (!updated) return

    setData((current) => ({
      ...current,
      actionChecklist: current.actionChecklist.map((entry) =>
        entry.id === updated.id ? updated : entry,
      ),
    }))
  }

  if (loading) return <DocumentSkeleton />
  if (error) return <PageError message={error} onRetry={refetch} />

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

  return (
    <div className="print-page mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <BriefMasthead
        meta={meta}
        preparedFor={preparedFor}
        onRegenerate={handleRegenerate}
        regenerating={regenerate.pending}
      />

      {regenerate.error && (
        <p className="mb-4 text-[13px] text-critical no-print">{regenerate.error}</p>
      )}

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
                    <span className="text-[11px] text-muted-foreground">Owner: {priority.owner}</span>
                    <SourceChip source={priority.source} />
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </MorningBriefCard>

        <MorningBriefCard
          number={3}
          title="Critical risks"
          description="What could go wrong today, and what to do about it"
          meta={`${criticalRisks.length} identified`}
          index={2}
          tone="accent"
        >
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
        </MorningBriefCard>

        <MorningBriefCard
          number={4}
          title="Today's meetings"
          meta={`${meetings.length} scheduled`}
          index={3}
        >
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
        </MorningBriefCard>

        <MorningBriefCard
          number={5}
          title="Clients needing attention"
          meta={`${clientsNeedingAttention.length} accounts`}
          index={4}
        >
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
        </MorningBriefCard>

        <MorningBriefCard
          number={6}
          title="Important emails"
          description="Summarised so you can decide without opening Gmail"
          meta={`${importantEmails.length} threads`}
          index={5}
        >
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
                  className="flex items-start gap-4 rounded-lg border border-border bg-card px-3.5 py-3"
                >
                  <span className="w-24 shrink-0 text-[12px] font-medium text-foreground numeric">
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
                      "shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-medium",
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
              <li key={item.id} className="flex items-start gap-4 py-3 first:pt-0 last:pb-0">
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium leading-snug">{item.task}</p>
                  <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                    {item.reason}
                  </p>
                </div>
                <div className="w-40 shrink-0 text-right">
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
          {toggleItem.error && (
            <p className="mt-3 text-[12px] text-critical">{toggleItem.error}</p>
          )}
        </MorningBriefCard>
      </div>

      <motion.section {...fadeUp} className="mt-8">
        <Card className="overflow-hidden border-primary/20">
          <div className="bg-primary px-6 py-5">
            <p className="eyebrow text-primary-foreground/60">The question that matters</p>
            <h2 className="mt-1.5 font-serif text-[22px] font-medium leading-snug text-primary-foreground">
              {closing.question}
            </h2>
          </div>
          <div className="px-6 py-5">
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
