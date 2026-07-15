import { motion } from "framer-motion"
import { Users, Sparkles, TrendingUp } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { opportunities } from "@/data/mock"
import { formatCurrency } from "@/lib/utils"
import { cn } from "@/lib/utils"
import { pageHeader, ease } from "@/lib/motion"

const stageColors: Record<string, string> = {
  Negotiation: "bg-gold/12 text-[#8a7340]",
  Qualified: "bg-info/10 text-info",
  Proposal: "bg-lavender/12 text-[#7a6e85]",
  Discovery: "bg-coral/10 text-coral",
  "Closed Won": "bg-sage/12 text-sage",
}

export function CRMPage() {
  const totalPipeline = opportunities
    .filter((o) => o.stage !== "Closed Won")
    .reduce((sum, o) => sum + o.value, 0)

  return (
    <div className="mx-auto max-w-7xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="flex items-center gap-2.5">
          <Users className="h-5 w-5 text-coral" strokeWidth={1.75} />
          <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">CRM Pipeline</h1>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-5">
          <div className="flex items-center gap-2 text-muted-foreground">
            <TrendingUp className="h-4 w-4 text-sage" strokeWidth={1.75} />
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
            transition={{ delay: i * 0.06, duration: 0.45, ease }}
          >
            <Card className="group h-full hover:card-shadow-hover">
              <CardContent className="flex h-full flex-col p-6">
                <div className="mb-5 flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-champagne text-sm font-bold text-foreground/80">
                      {opp.logo}
                    </div>
                    <div>
                      <h3 className="font-semibold tracking-tight">{opp.company}</h3>
                      <p className="text-xs text-muted-foreground">{opp.owner}</p>
                    </div>
                  </div>
                  <span
                    className={cn(
                      "rounded-full px-2.5 py-0.5 text-[11px] font-semibold",
                      stageColors[opp.stage] || "bg-muted text-muted-foreground"
                    )}
                  >
                    {opp.stage}
                  </span>
                </div>

                <div className="mb-5 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-muted/50 p-4">
                    <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Value</p>
                    <p className="mt-1 text-lg font-semibold tracking-tight tabular-nums">{formatCurrency(opp.value)}</p>
                  </div>
                  <div className="rounded-xl bg-muted/50 p-4">
                    <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">Probability</p>
                    <div className="mt-1 flex items-center gap-2">
                      <p className="text-lg font-semibold tabular-nums">{opp.probability}%</p>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-border/60">
                        <div
                          className="h-full rounded-full bg-coral/70 transition-all duration-500"
                          style={{ width: `${opp.probability}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mb-4 flex flex-wrap gap-1.5">
                  {opp.tags.map((tag) => (
                    <Badge key={tag} variant="outline" className="text-[10px]">
                      {tag}
                    </Badge>
                  ))}
                </div>

                <div className="mt-auto rounded-xl border border-border/40 bg-champagne/30 p-4">
                  <div className="mb-2 flex items-center gap-1.5">
                    <Sparkles className="h-3 w-3 text-coral" strokeWidth={1.75} />
                    <span className="text-[11px] font-medium tracking-wide text-coral">Deal Summary</span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    {opp.aiSummary}
                  </p>
                </div>

                <p className="mt-4 text-[11px] text-muted-foreground/70">
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
