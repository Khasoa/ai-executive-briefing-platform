import { motion } from "framer-motion"
import { Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { executiveSummary } from "@/data/mock"
import { ease } from "@/lib/motion"

const urgencyColors = {
  critical: "destructive",
  high: "warning",
  medium: "secondary",
} as const

export function ExecutiveSummaryCard() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.55, delay: 0.08, ease }}
    >
      <Card className="overflow-hidden border-peach/40 bg-gradient-to-br from-peach/30 via-card to-champagne/20">
        <CardContent className="p-7">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-coral/10">
              <Sparkles className="h-4 w-4 text-coral" strokeWidth={1.75} />
            </div>
            <div>
              <h3 className="text-[15px] font-semibold tracking-tight">Executive Summary</h3>
              <p className="text-xs text-muted-foreground">Generated at {executiveSummary.generatedAt}</p>
            </div>
          </div>
          <p className="mb-6 max-w-4xl text-[15px] leading-[1.7] text-foreground/85 text-balance">
            {executiveSummary.summary}
          </p>
          <div className="space-y-2.5">
            <p className="text-[11px] font-medium tracking-widest text-muted-foreground uppercase">
              Top Priorities
            </p>
            {executiveSummary.priorities.map((priority, i) => (
              <motion.div
                key={priority.id}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.06, duration: 0.45, ease }}
                className="flex items-center gap-3 rounded-xl border border-border/40 bg-card/70 px-4 py-3 transition-all duration-300 hover:border-border hover:bg-card hover:shadow-sm"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-champagne text-xs font-semibold text-foreground/70">
                  {i + 1}
                </span>
                <span className="flex-1 text-sm leading-snug">{priority.text}</span>
                <Badge variant={urgencyColors[priority.urgency as keyof typeof urgencyColors]}>
                  {priority.urgency}
                </Badge>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
