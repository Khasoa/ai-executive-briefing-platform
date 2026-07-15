import { motion } from "framer-motion"
import { Lightbulb, ArrowRight } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { aiRecommendations } from "@/data/mock"

export function AIRecommendations() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          <CardTitle>AI Recommendations</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {aiRecommendations.map((rec, i) => (
          <motion.div
            key={rec.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.08 }}
            className="group rounded-lg border border-border/60 p-4 transition-all duration-200 hover:border-primary/20 hover:bg-accent/30"
          >
            <div className="mb-1.5 flex items-start justify-between gap-2">
              <h4 className="text-sm font-medium">{rec.title}</h4>
              {rec.priority === "high" && (
                <span className="shrink-0 rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-semibold uppercase text-red-600">
                  High
                </span>
              )}
            </div>
            <p className="mb-3 text-sm leading-relaxed text-muted-foreground">
              {rec.description}
            </p>
            <Button variant="ghost" size="sm" className="h-7 gap-1 px-2 text-xs text-primary">
              {rec.action}
              <ArrowRight className="h-3 w-3" />
            </Button>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  )
}
