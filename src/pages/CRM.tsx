import { motion } from "framer-motion"
import { Users, Sparkles, TrendingUp } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { opportunities } from "@/data/mock"
import { formatCurrency } from "@/lib/utils"
import { cn } from "@/lib/utils"

const stageColors: Record<string, string> = {
  Negotiation: "bg-amber-50 text-amber-700",
  Qualified: "bg-blue-50 text-blue-700",
  Proposal: "bg-indigo-50 text-indigo-700",
  Discovery: "bg-violet-50 text-violet-700",
  "Closed Won": "bg-emerald-50 text-emerald-700",
}

export function CRMPage() {
  const totalPipeline = opportunities
    .filter((o) => o.stage !== "Closed Won")
    .reduce((sum, o) => sum + o.value, 0)

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">CRM Pipeline</h1>
        </div>
        <div className="mt-2 flex items-center gap-4">
          <div className="flex items-center gap-2 text-muted-foreground">
            <TrendingUp className="h-4 w-4" />
            <span className="text-sm">
              Active pipeline: <strong className="text-foreground">{formatCurrency(totalPipeline)}</strong>
            </span>
          </div>
          <span className="text-sm text-muted-foreground">
            {opportunities.filter((o) => o.stage !== "Closed Won").length} opportunities
          </span>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
        {opportunities.map((opp, i) => (
          <motion.div
            key={opp.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <Card className="group h-full transition-all duration-300 hover:card-shadow-hover">
              <CardContent className="flex h-full flex-col p-5">
                <div className="mb-4 flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-100 to-violet-50 text-sm font-bold text-indigo-700">
                      {opp.logo}
                    </div>
                    <div>
                      <h3 className="font-semibold">{opp.company}</h3>
                      <p className="text-xs text-muted-foreground">{opp.owner}</p>
                    </div>
                  </div>
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                      stageColors[opp.stage] || "bg-gray-50 text-gray-700"
                    )}
                  >
                    {opp.stage}
                  </span>
                </div>

                <div className="mb-4 grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-xs text-muted-foreground">Value</p>
                    <p className="text-lg font-semibold">{formatCurrency(opp.value)}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-xs text-muted-foreground">Probability</p>
                    <div className="flex items-center gap-2">
                      <p className="text-lg font-semibold">{opp.probability}%</p>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${opp.probability}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mb-3 flex flex-wrap gap-1.5">
                  {opp.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-[10px]">
                      {tag}
                    </Badge>
                  ))}
                </div>

                <div className="mt-auto rounded-lg border border-indigo-100 bg-indigo-50/30 p-3">
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3 text-primary" />
                    <span className="text-[11px] font-medium text-primary">AI Deal Summary</span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {opp.aiSummary}
                  </p>
                </div>

                <p className="mt-3 text-[11px] text-muted-foreground">
                  Last activity: {opp.lastActivity}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
