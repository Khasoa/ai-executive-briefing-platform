import { motion } from "framer-motion"
import { BookOpen, Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { researchItems } from "@/data/mock"

export function ResearchPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2">
          <BookOpen className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">Research</h1>
        </div>
        <p className="mt-1 text-muted-foreground">
          AI-curated intelligence relevant to your business
        </p>
      </motion.div>

      <div className="space-y-4">
        {researchItems.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <Card className="cursor-pointer transition-all duration-200 hover:card-shadow-hover">
              <CardContent className="p-5">
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium">{item.title}</h3>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {item.source} · {item.date}
                    </p>
                  </div>
                  <Badge variant={item.relevance === "high" ? "purple" : "secondary"}>
                    {item.relevance} relevance
                  </Badge>
                </div>
                <div className="flex gap-2 rounded-lg bg-muted/50 p-3">
                  <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                  <p className="text-sm leading-relaxed text-muted-foreground">{item.summary}</p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
