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
      <Card className="h-full">
        <div className="flex h-full flex-col px-4 py-3.5 sm:px-4 sm:py-4">
          <div className="mb-2.5 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className={cn(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-md",
                  TONES[kpi.tone] ?? TONES.slate,
                )}
              >
                <Icon className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <p className="truncate text-[12px] font-medium text-muted-foreground">{kpi.label}</p>
            </div>
            <trend.Icon
              className={cn("h-3.5 w-3.5 shrink-0", trend.className)}
              strokeWidth={1.75}
              aria-hidden="true"
            />
          </div>

          <p className="text-[1.375rem] font-semibold leading-none numeric text-foreground">
            <AnimatedNumber value={kpi.value} />
          </p>
          <p className="mt-1 text-[12px] leading-snug text-secondary-foreground">{kpi.sublabel}</p>
          <p className="mt-1.5 text-[11px] text-faint">{kpi.change}</p>
        </div>
      </Card>
    </motion.div>
  )
}

export function KPIGrid({ kpis }) {
  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {kpis.map((kpi, index) => (
        <KPIWidget key={kpi.id} kpi={kpi} index={index} />
      ))}
    </div>
  )
}
