import { motion } from "framer-motion"
import { ArrowDownRight, ArrowUpRight, CalendarClock, Inbox, ListChecks, Minus, Target } from "lucide-react"
import { Card } from "@/components/ui/card"
import { AnimatedNumber } from "@/components/ui/animated-number"
import { cn } from "@/lib/utils"
import { enter } from "@/lib/motion"

const ICONS = {
  inbox: Inbox,
  meetings: CalendarClock,
  deals: Target,
  tasks: ListChecks,
}

const TONES = {
  primary: "bg-primary-soft text-primary",
  accent: "bg-accent-soft text-accent",
  slate: "bg-muted text-secondary-foreground",
}

const TRENDS = {
  up: { Icon: ArrowUpRight, className: "text-positive" },
  down: { Icon: ArrowDownRight, className: "text-accent" },
  neutral: { Icon: Minus, className: "text-faint" },
}

export function KPIWidget({ kpi, index = 0 }) {
  const Icon = ICONS[kpi.icon] ?? Inbox
  const trend = TRENDS[kpi.trend] ?? TRENDS.neutral

  return (
    <motion.div {...enter(index)}>
      <Card interactive className="h-full">
        <div className="flex h-full flex-col p-5">
          <div className="mb-4 flex items-start justify-between">
            <span
              className={cn(
                "flex h-8 w-8 items-center justify-center rounded-lg",
                TONES[kpi.tone] ?? TONES.slate,
              )}
            >
              <Icon className="h-4 w-4" strokeWidth={1.75} />
            </span>
            <trend.Icon className={cn("h-4 w-4", trend.className)} strokeWidth={1.75} />
          </div>

          <p className="eyebrow text-muted-foreground">{kpi.label}</p>
          <p className="mt-1.5 text-[1.625rem] font-semibold leading-none numeric text-foreground">
            <AnimatedNumber value={kpi.value} />
          </p>
          <p className="mt-1.5 text-[13px] text-secondary-foreground">{kpi.sublabel}</p>
          <p className="mt-auto pt-3 text-xs text-muted-foreground">{kpi.change}</p>
        </div>
      </Card>
    </motion.div>
  )
}

export function KPIGrid({ kpis }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi, index) => (
        <KPIWidget key={kpi.id} kpi={kpi} index={index} />
      ))}
    </div>
  )
}
