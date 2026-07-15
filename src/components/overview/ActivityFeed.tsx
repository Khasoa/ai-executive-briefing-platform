import { motion } from "framer-motion"
import { Mail, TrendingUp, FileText, Calendar, UserPlus, Activity } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { activities } from "@/data/mock"
import { ease } from "@/lib/motion"

const iconMap = {
  mail: Mail,
  trending: TrendingUp,
  file: FileText,
  calendar: Calendar,
  user: UserPlus,
}

export function ActivityFeed() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sage/12">
            <Activity className="h-4 w-4 text-sage" strokeWidth={1.75} />
          </div>
          <CardTitle>Recent Activity</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-0.5">
          {activities.map((activity, i) => {
            const Icon = iconMap[activity.icon as keyof typeof iconMap] || Activity
            return (
              <motion.div
                key={activity.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.28 + i * 0.05, duration: 0.4, ease }}
                className="flex items-center gap-3 rounded-xl px-2.5 py-3 transition-all duration-300 hover:bg-muted/50"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted/80">
                  <Icon className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm leading-snug">{activity.title}</p>
                  <p className="text-xs text-muted-foreground">{activity.time}</p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
