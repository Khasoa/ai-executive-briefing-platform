import { motion } from "framer-motion"
import {
  Target,
  Calendar,
  TrendingUp,
  Clock,
  AlertTriangle,
  Zap,
  Sparkles,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { dailyBrief } from "@/data/mock"
import { formatCurrency } from "@/lib/utils"
import { pageHeader, staggerContainer, staggerItem } from "@/lib/motion"

const sectionIcons = {
  priorities: Target,
  meetings: Calendar,
  pipeline: TrendingUp,
  deadlines: Clock,
  risks: AlertTriangle,
  suggestedActions: Zap,
}

const sectionIconColors = {
  priorities: "bg-coral/10 text-coral",
  meetings: "bg-info/10 text-info",
  pipeline: "bg-sage/12 text-sage",
  deadlines: "bg-gold/12 text-gold",
  risks: "bg-destructive/10 text-destructive",
  suggestedActions: "bg-lavender/12 text-lavender",
}

const severityColors = {
  urgent: "destructive",
  high: "warning",
  medium: "secondary",
} as const

const riskSeverity = {
  high: "destructive",
  medium: "warning",
} as const

export function DailyBriefPage() {
  const { sections } = dailyBrief

  return (
    <div className="mx-auto max-w-4xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-coral" strokeWidth={1.75} />
          <Badge variant="coral">AI Generated</Badge>
        </div>
        <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">Daily Brief</h1>
        <p className="mt-2 text-muted-foreground">{dailyBrief.date}</p>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-foreground/80">{dailyBrief.greeting}</p>
      </motion.div>

      <motion.div variants={staggerContainer} initial="hidden" animate="show" className="space-y-7">
        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${sectionIconColors.priorities}`}>
                  <sectionIcons.priorities className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <CardTitle>Today's Priorities</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ol className="space-y-4">
                {sections.priorities.map((p, i) => (
                  <li key={i} className="flex gap-3.5 text-sm leading-relaxed">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-champagne text-xs font-semibold text-foreground/70">
                      {i + 1}
                    </span>
                    {p}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${sectionIconColors.meetings}`}>
                  <sectionIcons.meetings className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <CardTitle>Meetings</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {sections.meetings.map((m, i) => (
                <div key={i} className="flex gap-5 rounded-xl border border-border/50 p-5 transition-colors duration-300 hover:bg-muted/20">
                  <span className="w-20 shrink-0 text-sm font-semibold text-coral">{m.time}</span>
                  <div>
                    <p className="text-sm font-medium">{m.title}</p>
                    <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{m.note}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={staggerItem}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${sectionIconColors.pipeline}`}>
                  <sectionIcons.pipeline className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <CardTitle>Pipeline Updates</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {sections.pipeline.map((deal, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-xl bg-muted/40 px-5 py-4 transition-colors duration-300 hover:bg-muted/60"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{deal.company}</p>
                      <Badge variant="outline" className="text-[10px]">
                        {deal.stage}
                      </Badge>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{deal.note}</p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold tabular-nums">
                    {formatCurrency(parseInt(deal.value.replace(/[$K]/g, "")) * (deal.value.includes("K") ? 1000 : 1))}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        <div className="grid grid-cols-1 gap-7 md:grid-cols-2">
          <motion.div variants={staggerItem}>
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center gap-2.5">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${sectionIconColors.deadlines}`}>
                    <sectionIcons.deadlines className="h-4 w-4" strokeWidth={1.75} />
                  </div>
                  <CardTitle>Deadlines</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {sections.deadlines.map((d, i) => (
                  <div key={i} className="flex items-start justify-between gap-3 border-b border-border/40 pb-4 last:border-0 last:pb-0">
                    <div>
                      <p className="text-sm font-medium">{d.item}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{d.due}</p>
                    </div>
                    <Badge variant={severityColors[d.status as keyof typeof severityColors]}>
                      {d.status}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={staggerItem}>
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center gap-2.5">
                  <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${sectionIconColors.risks}`}>
                    <sectionIcons.risks className="h-4 w-4" strokeWidth={1.75} />
                  </div>
                  <CardTitle>Risks</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-5">
                {sections.risks.map((r, i) => (
                  <div key={i}>
                    <div className="mb-1.5 flex items-center gap-2">
                      <p className="text-sm font-medium">{r.title}</p>
                      <Badge variant={riskSeverity[r.severity as keyof typeof riskSeverity]}>
                        {r.severity}
                      </Badge>
                    </div>
                    <p className="text-sm leading-relaxed text-muted-foreground">{r.description}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <motion.div variants={staggerItem}>
          <Card className="border-peach/30 bg-gradient-to-br from-peach/20 via-card to-champagne/15">
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${sectionIconColors.suggestedActions}`}>
                  <sectionIcons.suggestedActions className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <CardTitle>Suggested Actions</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-4">
                {sections.suggestedActions.map((action, i) => (
                  <li key={i} className="flex gap-3.5 text-sm leading-relaxed">
                    <Zap className="mt-0.5 h-4 w-4 shrink-0 text-coral" strokeWidth={1.75} />
                    {action}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  )
}
