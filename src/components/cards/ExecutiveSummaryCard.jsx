import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { AlertTriangle, ArrowRight, CalendarClock, CircleCheck, Users } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { buttonVariants } from "@/components/ui/button-variants"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { cn } from "@/lib/utils"
import { fadeUp } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_DOT, SIGNAL_LABEL } from "@/lib/signals"

function Panel({ icon: Icon, title, count, children, className }) {
  return (
    <section className={cn("min-w-0", className)}>
      <div className="mb-2.5 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />
        <h3 className="eyebrow text-muted-foreground">{title}</h3>
        {typeof count === "number" && (
          <span className="rounded bg-muted px-1.5 text-[11px] font-semibold text-muted-foreground numeric">
            {count}
          </span>
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
      <Card className="overflow-hidden">
        <div className="border-b border-border bg-subtle px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              <h2 className="text-[15px] font-semibold tracking-tight">Executive Summary</h2>
              <Badge variant="quiet">Generated {brief.generatedLabel}</Badge>
            </div>
            <Link
              to="/morning-brief"
              className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "gap-1.5")}
            >
              Read full brief
              <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} />
            </Link>
          </div>
        </div>

        <div className="px-6 py-6">
          <p className="max-w-4xl font-serif text-[17px] leading-[1.65] text-foreground text-balance">
            {narrative}
          </p>

          <div className="mt-6">
            <Panel icon={CircleCheck} title="Today's priorities" count={priorities.length}>
              <ol className="space-y-1.5">
                {priorities.slice(0, 4).map((priority, index) => (
                  <li
                    key={priority.id}
                    className="flex items-start gap-3 rounded-lg border border-border bg-card px-3 py-2.5 transition-colors hover:border-border-strong"
                  >
                    <span
                      className={cn(
                        "mt-1 h-4 w-0.5 shrink-0 rounded-full",
                        SIGNAL_ACCENT_BAR[priority.urgency],
                      )}
                    />
                    <span className="w-4 shrink-0 pt-px text-[13px] font-semibold text-faint numeric">
                      {index + 1}
                    </span>
                    <span className="min-w-0 flex-1 text-[13px] leading-snug text-foreground">
                      {priority.title}
                    </span>
                    <Badge variant={SIGNAL_BADGE[priority.urgency]}>
                      {SIGNAL_LABEL[priority.urgency]}
                    </Badge>
                  </li>
                ))}
              </ol>
            </Panel>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 border-t border-border pt-6 md:grid-cols-2">
            <Panel icon={AlertTriangle} title="Business risks" count={risks.length}>
              <ul className="space-y-2.5">
                {risks.map((risk) => (
                  <li key={risk.id} className="flex items-start gap-2.5">
                    <span
                      className={cn(
                        "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                        SIGNAL_DOT[risk.severity],
                      )}
                    />
                    <div className="min-w-0">
                      <p className="text-[13px] font-medium leading-snug">{risk.title}</p>
                      <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                        {risk.impact} at stake
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel
              icon={CalendarClock}
              title="Meetings needing preparation"
              count={meetingsToPrepare.length}
            >
              <ul className="space-y-2.5">
                {meetingsToPrepare.map((meeting) => (
                  <li key={meeting.id} className="flex items-start gap-2.5">
                    <span className="mt-0.5 w-10 shrink-0 text-[12px] font-medium text-muted-foreground numeric">
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

            <Panel icon={Users} title="Clients needing attention" count={clientsNeedingAttention.length}>
              <ul className="space-y-2.5">
                {clientsNeedingAttention.map((client) => (
                  <li key={client.id} className="flex items-start gap-2.5">
                    <span
                      className={cn(
                        "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                        SIGNAL_DOT[client.severity],
                      )}
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

            <Panel icon={ArrowRight} title="Recommended actions" count={recommendedActions.length}>
              <ul className="space-y-2.5">
                {recommendedActions.map((action) => (
                  <li key={action.id} className="flex items-start gap-2.5">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/40" />
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

        <div className="flex flex-wrap items-center gap-2 border-t border-border bg-subtle px-6 py-3">
          <span className="text-[11px] text-muted-foreground">Assembled from</span>
          {brief.sources.map((source) => (
            <SourceChip key={source} source={source} className="bg-card" />
          ))}
        </div>
      </Card>
    </motion.div>
  )
}
