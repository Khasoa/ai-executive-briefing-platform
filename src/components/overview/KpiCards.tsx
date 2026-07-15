import { motion } from "framer-motion"
import { Inbox, Calendar, TrendingUp, FolderKanban, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { AnimatedNumber } from "@/components/ui/animated-number"
import { kpis } from "@/data/mock"
import { cn } from "@/lib/utils"
import { ease } from "@/lib/motion"

const iconMap = {
  inbox: Inbox,
  calendar: Calendar,
  pipeline: TrendingUp,
  projects: FolderKanban,
}

const colorMap = {
  indigo: "bg-coral/10 text-coral",
  blue: "bg-info/10 text-info",
  emerald: "bg-sage/15 text-sage",
  amber: "bg-gold/15 text-[#8a7340]",
}

export function KpiCards() {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi, i) => {
        const Icon = iconMap[kpi.icon]
        return (
          <motion.div
            key={kpi.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.12 + i * 0.06, ease }}
          >
            <Card className="group hover:card-shadow-hover">
              <CardContent className="p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-xl",
                      colorMap[kpi.color as keyof typeof colorMap]
                    )}
                  >
                    <Icon className="h-[18px] w-[18px]" strokeWidth={1.75} />
                  </div>
                  {kpi.trend === "up" && (
                    <ArrowUpRight className="h-4 w-4 text-sage" strokeWidth={1.75} />
                  )}
                  {kpi.trend === "down" && (
                    <ArrowDownRight className="h-4 w-4 text-gold" strokeWidth={1.75} />
                  )}
                  {kpi.trend === "neutral" && (
                    <Minus className="h-4 w-4 text-muted-foreground/50" strokeWidth={1.75} />
                  )}
                </div>
                <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">
                  {kpi.label}
                </p>
                <p className="mt-1 text-[1.75rem] font-semibold tracking-tight text-foreground">
                  <AnimatedNumber value={kpi.value} />
                </p>
                <p className="mt-0.5 text-sm text-muted-foreground">{kpi.sublabel}</p>
                <p className="mt-3 text-xs text-muted-foreground/70">{kpi.change}</p>
              </CardContent>
            </Card>
          </motion.div>
        )
      })}
    </div>
  )
}
