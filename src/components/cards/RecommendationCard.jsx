import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { ArrowUpRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { cn } from "@/lib/utils"
import { enter } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_LABEL, isElevatedSignal } from "@/lib/signals"

/**
 * A single AI recommendation. It argues for a course of action and names the
 * evidence — it never takes the action itself.
 */
export function RecommendationCard({ recommendation, index = 0 }) {
  const { title, description, rationale, action, actionTarget, impact, priority, sources } =
    recommendation

  return (
    <motion.div {...enter(index)}>
      <Card className="h-full overflow-hidden">
        <div className="flex h-full">
          <span className={cn("w-0.5 shrink-0", SIGNAL_ACCENT_BAR[priority])} aria-hidden="true" />
          <div className="flex min-w-0 flex-1 flex-col px-4 py-4 sm:px-5 sm:py-4">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-[14px] font-semibold leading-snug tracking-tight text-balance">
                {title}
              </h3>
              {isElevatedSignal(priority) && (
                <Badge variant={SIGNAL_BADGE[priority]}>{SIGNAL_LABEL[priority]}</Badge>
              )}
            </div>

            <p className="mt-1.5 text-[13px] leading-relaxed text-secondary-foreground">
              {description}
            </p>

            <p className="mt-2 text-[12px] leading-relaxed text-muted-foreground">{rationale}</p>

            <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-2 pt-3">
              <span className="text-[12px] font-medium text-primary">{impact}</span>
              <Link
                to={actionTarget}
                className="inline-flex items-center gap-1 text-[12px] font-medium text-secondary-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40"
              >
                {action}
                <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              </Link>
            </div>

            {sources?.length > 0 && (
              <div className="mt-2 flex flex-wrap items-center gap-0.5 border-t border-border/70 pt-2">
                {sources.map((source) => (
                  <SourceChip key={source} source={source} />
                ))}
              </div>
            )}
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
