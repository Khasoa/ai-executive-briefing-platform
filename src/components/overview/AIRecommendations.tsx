import { motion } from "framer-motion"
import { Lightbulb, ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { aiRecommendations } from "@/data/mock"
import { ease } from "@/lib/motion"

export function AIRecommendations() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gold/12">
            <Lightbulb className="h-4 w-4 text-gold" strokeWidth={1.75} />
          </div>
          <CardTitle>Recommendations</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {aiRecommendations.map((rec, i) => (
          <motion.div
            key={rec.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.28 + i * 0.07, duration: 0.45, ease }}
            className="group rounded-xl border border-border/50 p-5 transition-all duration-300 hover:border-border hover:bg-muted/30 hover:shadow-sm"
          >
            <div className="mb-2 flex items-start justify-between gap-3">
              <h4 className="text-sm font-medium leading-snug">{rec.title}</h4>
              {rec.priority === "high" && (
                <span className="shrink-0 rounded-full bg-coral/10 px-2.5 py-0.5 text-[10px] font-semibold tracking-wide text-coral uppercase">
                  Priority
                </span>
              )}
            </div>
            <p className="mb-4 text-sm leading-relaxed text-muted-foreground">
              {rec.description}
            </p>
            <Button variant="ghost" size="sm" className="h-8 gap-1.5 px-2 text-xs text-coral hover:text-coral hover:bg-coral/8">
              {rec.action}
              <ArrowRight className="h-3 w-3 transition-transform duration-300 group-hover:translate-x-0.5" />
            </Button>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  )
}
