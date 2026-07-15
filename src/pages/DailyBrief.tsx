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

const sectionIcons = {
  priorities: Target,
  meetings: Calendar,
  pipeline: TrendingUp,
  deadlines: Clock,
  risks: AlertTriangle,
  suggestedActions: Zap,
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

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
}

const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0 },
}

export function DailyBriefPage() {
  const { sections } = dailyBrief

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="mb-2 flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <Badge variant="purple">AI Generated</Badge>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">Daily Brief</h1>
        <p className="mt-1 text-muted-foreground">{dailyBrief.date}</p>
        <p className="mt-3 text-[15px] leading-relaxed">{dailyBrief.greeting}</p>
      </motion.div>

      <motion.div variants={container} initial="hidden" animate="show" className="space-y-6">
        <motion.div variants={item}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <sectionIcons.priorities className="h-4 w-4 text-primary" />
                <CardTitle>Today's Priorities</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ol className="space-y-3">
                {sections.priorities.map((p, i) => (
                  <li key={i} className="flex gap-3 text-sm leading-relaxed">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {i + 1}
                    </span>
                    {p}
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <sectionIcons.meetings className="h-4 w-4 text-blue-500" />
                <CardTitle>Meetings</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {sections.meetings.map((m, i) => (
                <div key={i} className="flex gap-4 rounded-lg border border-border/60 p-4">
                  <span className="shrink-0 text-sm font-medium text-primary">{m.time}</span>
                  <div>
                    <p className="text-sm font-medium">{m.title}</p>
                    <p className="mt-1 text-sm text-muted-foreground">{m.note}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={item}>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <sectionIcons.pipeline className="h-4 w-4 text-emerald-500" />
                <CardTitle>Pipeline Updates</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {sections.pipeline.map((deal, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-lg bg-muted/40 px-4 py-3"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{deal.company}</p>
                      <Badge variant="outline" className="text-[10px]">
                        {deal.stage}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{deal.note}</p>
                  </div>
                  <span className="shrink-0 text-sm font-semibold">
                    {formatCurrency(parseInt(deal.value.replace(/[$K]/g, "")) * (deal.value.includes("K") ? 1000 : 1))}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <motion.div variants={item}>
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <sectionIcons.deadlines className="h-4 w-4 text-amber-500" />
                  <CardTitle>Deadlines</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {sections.deadlines.map((d, i) => (
                  <div key={i} className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">{d.item}</p>
                      <p className="text-xs text-muted-foreground">{d.due}</p>
                    </div>
                    <Badge variant={severityColors[d.status as keyof typeof severityColors]}>
                      {d.status}
                    </Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>

          <motion.div variants={item}>
            <Card className="h-full">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <sectionIcons.risks className="h-4 w-4 text-red-500" />
                  <CardTitle>Risks</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {sections.risks.map((r, i) => (
                  <div key={i}>
                    <div className="mb-1 flex items-center gap-2">
                      <p className="text-sm font-medium">{r.title}</p>
                      <Badge variant={riskSeverity[r.severity as keyof typeof riskSeverity]}>
                        {r.severity}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">{r.description}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        <motion.div variants={item}>
          <Card className="border-indigo-100 bg-gradient-to-br from-indigo-50/50 to-white">
            <CardHeader>
              <div className="flex items-center gap-2">
                <sectionIcons.suggestedActions className="h-4 w-4 text-primary" />
                <CardTitle>Suggested Actions</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-3">
                {sections.suggestedActions.map((action, i) => (
                  <li key={i} className="flex gap-3 text-sm leading-relaxed">
                    <Zap className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
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
