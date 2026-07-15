import { motion } from "framer-motion"
import { Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { executiveSummary } from "@/data/mock"

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
      transition={{ duration: 0.4, delay: 0.1 }}
    >
      <Card className="overflow-hidden border-indigo-100 bg-gradient-to-br from-indigo-50/80 via-white to-violet-50/50">
        <CardContent className="p-6">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold">AI Executive Summary</h3>
              <p className="text-xs text-muted-foreground">Generated at {executiveSummary.generatedAt}</p>
            </div>
          </div>
          <p className="mb-5 text-[15px] leading-relaxed text-foreground/90">
            {executiveSummary.summary}
          </p>
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Top Priorities
            </p>
            {executiveSummary.priorities.map((priority, i) => (
              <motion.div
                key={priority.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.05 }}
                className="flex items-center gap-3 rounded-lg bg-white/60 px-3 py-2.5 transition-colors hover:bg-white/90"
              >
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {i + 1}
                </span>
                <span className="flex-1 text-sm">{priority.text}</span>
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
