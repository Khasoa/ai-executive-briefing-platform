import { motion } from "framer-motion"
import { ArrowRight, Sparkles } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { SourceChip } from "@/components/common/SourceChip"
import { cn, formatCurrency } from "@/lib/utils"
import { enter } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_LABEL } from "@/lib/signals"

function Metric({ label, value, className }) {
  return (
    <div className={className}>
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
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
      <Card interactive className="overflow-hidden">
        <div className="flex">
          <span className={cn("w-0.5 shrink-0", SIGNAL_ACCENT_BAR[riskLevel])} />

          <div className="min-w-0 flex-1 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-subtle text-[12px] font-semibold text-secondary-foreground">
                  {logo}
                </span>
                <div className="min-w-0">
                  <h3 className="text-[15px] font-semibold leading-tight tracking-tight">
                    {company}
                  </h3>
                  <p className="mt-0.5 text-[12px] text-muted-foreground">
                    {industry} · owned by {owner}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="outline">{stage}</Badge>
                <Badge variant={SIGNAL_BADGE[riskLevel]}>{SIGNAL_LABEL[riskLevel]} risk</Badge>
              </div>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <Metric label="Value" value={formatCurrency(value)} />
              <Metric label="Probability" value={`${probability}%`} />
              <Metric label="Expected close" value={closeDate} />
              <Metric label="Last interaction" value={lastInteraction.time} />
            </dl>

            <Progress
              value={probability}
              tone={riskLevel === "critical" ? "critical" : riskLevel === "high" ? "accent" : "primary"}
              label={`${company} probability`}
              className="mt-3"
            />

            <p className="mt-3 text-[12px] leading-relaxed text-muted-foreground">
              Most recent: {lastInteraction.summary}
            </p>

            <div className="mt-3.5 rounded-lg bg-subtle px-3.5 py-3">
              <div className="mb-1.5 flex items-center gap-1.5">
                <Sparkles className="h-3 w-3 text-primary" strokeWidth={1.75} />
                <span className="eyebrow text-muted-foreground">Summary</span>
              </div>
              <p className="text-[13px] leading-relaxed text-secondary-foreground">{aiSummary}</p>
            </div>

            <div className="mt-2.5 flex items-start gap-2.5 rounded-lg border border-primary/15 bg-primary-soft px-3.5 py-3">
              <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" strokeWidth={1.75} />
              <div>
                <p className="eyebrow text-primary">Recommended next action</p>
                <p className="mt-1 text-[13px] leading-relaxed text-secondary-foreground">
                  {recommendedAction}
                </p>
              </div>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-1.5">
              {signals.map((signal) => (
                <Badge key={signal} variant="quiet">
                  {signal}
                </Badge>
              ))}
              <span className="ml-auto flex items-center gap-1.5">
                {sources.map((source) => (
                  <SourceChip key={source} source={source} />
                ))}
              </span>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
