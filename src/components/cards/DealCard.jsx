import { motion } from "framer-motion"
import { ArrowRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { SourceChip } from "@/components/common/SourceChip"
import { cn, formatCurrency } from "@/lib/utils"
import { enter } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_LABEL, isElevatedSignal } from "@/lib/signals"

function Metric({ label, value, className }) {
  return (
    <div className={className}>
      <dt className="text-[11px] text-faint">{label}</dt>
      <dd className="mt-0.5 text-[13px] font-medium text-foreground numeric">{value}</dd>
    </div>
  )
}

/** An opportunity that needs an executive decision, with the reasoning attached. */
export function DealCard({ opportunity, index = 0 }) {
  const {
    company,
    logo,
    industry,
    stage,
    value,
    probability,
    owner,
    closeDate,
    riskLevel,
    lastInteraction,
    aiSummary,
    recommendedAction,
    signals,
    sources,
  } = opportunity

  return (
    <motion.div {...enter(index)}>
      <Card className="overflow-hidden">
        <div className="flex">
          <span className={cn("w-0.5 shrink-0", SIGNAL_ACCENT_BAR[riskLevel])} aria-hidden="true" />

          <div className="min-w-0 flex-1 p-4 sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3 min-w-0">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-subtle text-[12px] font-semibold text-secondary-foreground">
                  {logo}
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-[15px] font-semibold leading-tight tracking-tight">
                      {company}
                    </h3>
                    <span className="text-[12px] text-muted-foreground">{stage}</span>
                    {isElevatedSignal(riskLevel) && (
                      <Badge variant={SIGNAL_BADGE[riskLevel]}>
                        {SIGNAL_LABEL[riskLevel]}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-0.5 text-[12px] text-faint">
                    {industry} · {owner}
                  </p>
                </div>
              </div>

              <p className="text-[15px] font-semibold numeric text-foreground">
                {formatCurrency(value)}
              </p>
            </div>

            <dl className="mt-3.5 grid grid-cols-3 gap-x-4 gap-y-2">
              <Metric label="Probability" value={`${probability}%`} />
              <Metric label="Close" value={closeDate} />
              <Metric label="Last touch" value={lastInteraction.time} />
            </dl>

            <Progress
              value={probability}
              tone={
                riskLevel === "critical" ? "critical" : riskLevel === "high" ? "accent" : "primary"
              }
              label={`${company} probability`}
              className="mt-2.5"
            />

            <p className="mt-3 text-[13px] leading-relaxed text-secondary-foreground">{aiSummary}</p>

            <div className="mt-3 flex items-start gap-2.5 rounded-lg bg-primary-soft/80 px-3.5 py-3">
              <ArrowRight
                className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              <p className="text-[13px] leading-relaxed text-secondary-foreground">
                <span className="font-medium text-foreground">Next. </span>
                {recommendedAction}
              </p>
            </div>

            {(signals.length > 0 || sources.length > 0) && (
              <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-border/70 pt-2.5">
                {signals.slice(0, 3).map((signal) => (
                  <span key={signal} className="text-[11px] text-muted-foreground">
                    {signal}
                  </span>
                ))}
                <span className="ml-auto flex items-center gap-0.5">
                  {sources.map((source) => (
                    <SourceChip key={source} source={source} />
                  ))}
                </span>
              </div>
            )}
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
