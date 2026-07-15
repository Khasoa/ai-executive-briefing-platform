import { motion } from "framer-motion"
import { Inbox, Calendar, TrendingUp, FolderKanban, ArrowUpRight, ArrowDownRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { kpis } from "@/data/mock"
import { cn } from "@/lib/utils"

const iconMap = {
  inbox: Inbox,
  calendar: Calendar,
  pipeline: TrendingUp,
  projects: FolderKanban,
}

const colorMap = {
  indigo: "from-indigo-500/10 to-indigo-500/5 text-indigo-600",
  blue: "from-blue-500/10 to-blue-500/5 text-blue-600",
  emerald: "from-emerald-500/10 to-emerald-500/5 text-emerald-600",
  amber: "from-amber-500/10 to-amber-500/5 text-amber-600",
}

export function KpiCards() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi, i) => {
        const Icon = iconMap[kpi.icon]
        return (
          <motion.div
            key={kpi.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 + i * 0.05 }}
          >
            <Card className="group transition-all duration-300 hover:card-shadow-hover">
              <CardContent className="p-5">
                <div className="mb-3 flex items-center justify-between">
                  <div
                    className={cn(
                      "flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br",
                      colorMap[kpi.color as keyof typeof colorMap]
                    )}
                  >
                    <Icon className="h-4 w-4" />
                  </div>
                  {kpi.trend === "up" && (
                    <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                  )}
                  {kpi.trend === "down" && (
                    <ArrowDownRight className="h-4 w-4 text-amber-500" />
                  )}
                </div>
                <p className="text-2xl font-semibold tracking-tight">{kpi.value}</p>
                <p className="text-sm text-muted-foreground">{kpi.sublabel}</p>
                <p className="mt-2 text-xs text-muted-foreground/80">{kpi.change}</p>
              </CardContent>
            </Card>
          </motion.div>
        )
      })}
    </div>
  )
}
