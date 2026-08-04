import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { ArrowUpRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { cn } from "@/lib/utils"
import { enter } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_LABEL } from "@/lib/signals"

/**
 * A single AI recommendation. It argues for a course of action and names the
 * evidence — it never takes the action itself.
 */
export function RecommendationCard({ recommendation, index = 0 }) {
  const { title, description, rationale, action, actionTarget, impact, priority, sources } =
    recommendation

  return (
    <motion.div {...enter(index)}>
      <Card interactive className="h-full overflow-hidden">
        <div className="flex h-full">
          <span className={cn("w-0.5 shrink-0", SIGNAL_ACCENT_BAR[priority])} />
          <div className="flex min-w-0 flex-1 flex-col p-5">
            <div className="mb-2 flex items-start justify-between gap-3">
              <h3 className="text-[14px] font-semibold leading-snug tracking-tight text-balance">
                {title}
              </h3>
              <Badge variant={SIGNAL_BADGE[priority]}>{SIGNAL_LABEL[priority]}</Badge>
            </div>

            <p className="text-[13px] leading-relaxed text-secondary-foreground">{description}</p>

            <p className="mt-3 border-l-2 border-border pl-3 text-[12px] leading-relaxed text-muted-foreground">
              {rationale}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-2 pt-1">
              {sources.map((source) => (
                <SourceChip key={source} source={source} />
              ))}
            </div>

            <div className="mt-4 flex items-center justify-between gap-3 border-t border-border pt-3">
              <span className="text-[12px] font-medium text-primary">{impact}</span>
              <Link
                to={actionTarget}
                className="inline-flex items-center gap-1 text-[12px] font-medium text-secondary-foreground transition-colors hover:text-foreground"
              >
                {action}
                <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={1.75} />
              </Link>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
