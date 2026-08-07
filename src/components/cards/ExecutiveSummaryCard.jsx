import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { AlertTriangle, ArrowRight, CalendarClock, CircleCheck, Users } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button-variants"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { cn } from "@/lib/utils"
import { fadeUp } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_DOT, SIGNAL_LABEL, isElevatedSignal } from "@/lib/signals"

function Panel({ icon: Icon, title, count, children, className }) {
  return (
    <section className={cn("min-w-0", className)}>
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-faint" strokeWidth={1.75} aria-hidden="true" />
        <h3 className="text-[12px] font-semibold text-muted-foreground">{title}</h3>
        {typeof count === "number" && count > 0 && (
          <span className="text-[11px] text-faint numeric">{count}</span>
        )}
      </div>
      {children}
    </section>
  )
}

/**
 * The hero of the Overview page: one paragraph of judgement, then the five
 * things an executive needs before deciding what to do first.
 */
export function ExecutiveSummaryCard({ summary, brief }) {
  const {
    summary: narrative,
    priorities,
    risks,
    meetingsToPrepare,
    clientsNeedingAttention,
    recommendedActions,
  } = summary

  return (
    <motion.div {...fadeUp}>
      <Card className="overflow-hidden border-primary/15 ring-1 ring-primary/5">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3.5 sm:px-6">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
              <h2 className="text-[15px] font-semibold tracking-tight">From today&apos;s Morning Brief</h2>
            </div>
            <p className="mt-0.5 pl-3.5 text-[12px] text-muted-foreground">
              Generated {brief.generatedLabel}
            </p>
          </div>
          <Link
            to="/morning-brief"
            className={cn(buttonVariants({ variant: "primary", size: "sm" }), "gap-1.5")}
          >
            Open Morning Brief
            <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
          </Link>
        </div>

        <div className="px-4 py-5 sm:px-6 sm:py-6">
          <p className="max-w-3xl font-serif text-[17px] leading-[1.65] text-foreground text-balance sm:text-[18px]">
            {narrative}
          </p>

          <div className="mt-5">
            <Panel icon={CircleCheck} title="Priorities" count={priorities.length}>
              <ol className="space-y-1">
                {priorities.slice(0, 4).map((priority, index) => (
                  <li
                    key={priority.id}
                    className="flex items-start gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-subtle sm:px-2.5"
                  >
                    <span
                      className={cn(
                        "mt-1 h-4 w-0.5 shrink-0 rounded-full",
                        SIGNAL_ACCENT_BAR[priority.urgency],
                      )}
                      aria-hidden="true"
                    />
                    <span className="w-4 shrink-0 pt-px text-[13px] font-semibold text-faint numeric">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1 text-[13px] font-medium leading-snug text-foreground">
                      {priority.title}
                    </span>
                    {isElevatedSignal(priority.urgency) && (
                      <Badge variant={SIGNAL_BADGE[priority.urgency]}>
                        {SIGNAL_LABEL[priority.urgency]}
                      </Badge>
                    )}
                  </li>
                ))}
              </ol>
            </Panel>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-5 border-t border-border pt-5 md:grid-cols-2 md:gap-x-8 md:gap-y-5">
            <Panel icon={AlertTriangle} title="Risks" count={risks.length}>
              <ul className="space-y-2">
                {risks.map((risk) => (
                  <li key={risk.id} className="flex items-start gap-2.5">
                    <span
                      className={cn(
                        "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                        SIGNAL_DOT[risk.severity],
                      )}
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium leading-snug">{risk.title}</p>
                      <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                        {risk.impact}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel icon={CalendarClock} title="Prep needed" count={meetingsToPrepare.length}>
              <ul className="space-y-2">
                {meetingsToPrepare.map((meeting) => (
                  <li key={meeting.id} className="flex items-start gap-2.5">
                    <span className="mt-0.5 w-10 shrink-0 text-[12px] font-medium text-faint numeric">
                      {meeting.time}
                    </span>
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium leading-snug">{meeting.title}</p>
                      <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                        {meeting.reason}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel icon={Users} title="Clients" count={clientsNeedingAttention.length}>
              <ul className="space-y-2">
                {clientsNeedingAttention.map((client) => (
                  <li key={client.id} className="flex items-start gap-2.5">
                    <span
                      className={cn(
                        "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                        SIGNAL_DOT[client.severity],
                      )}
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium leading-snug">
                        {client.company}
                        <span className="ml-1.5 font-normal text-muted-foreground">
                          {client.value}
                        </span>
                      </p>
                      <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                        {client.reason}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel icon={ArrowRight} title="Actions" count={recommendedActions.length}>
              <ul className="space-y-2">
                {recommendedActions.map((action) => (
                  <li key={action.id} className="flex items-start gap-2.5">
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/40"
                      aria-hidden="true"
                    />
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium leading-snug">{action.label}</p>
                      <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                        {action.rationale}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1 border-t border-border px-4 py-2.5 sm:px-6">
          <span className="mr-1 text-[11px] text-faint">Sources</span>
          {brief.sources.map((source) => (
            <SourceChip key={source} source={source} />
          ))}
        </div>
      </Card>
    </motion.div>
  )
}
