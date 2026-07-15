import { motion } from "framer-motion"
import { BookOpen, Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { researchItems } from "@/data/mock"
import { pageHeader, ease } from "@/lib/motion"

export function ResearchPage() {
  return (
    <div className="mx-auto max-w-4xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="flex items-center gap-2.5">
          <BookOpen className="h-5 w-5 text-coral" strokeWidth={1.75} />
          <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">Research</h1>
        </div>
        <p className="mt-2 text-muted-foreground">
          AI-curated intelligence relevant to your business
        </p>
      </motion.div>

      <div className="space-y-4">
        {researchItems.map((item, i) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06, duration: 0.45, ease }}
          >
            <Card className="cursor-pointer hover:card-shadow-hover">
              <CardContent className="p-6">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium leading-snug">{item.title}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.source} · {item.date}
                    </p>
                  </div>
                  <Badge variant={item.relevance === "high" ? "lavender" : "secondary"}>
                    {item.relevance} relevance
                  </Badge>
                </div>
                <div className="flex gap-2.5 rounded-xl bg-muted/40 p-4">
                  <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-coral" strokeWidth={1.75} />
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
