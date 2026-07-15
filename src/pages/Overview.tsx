import { motion } from "framer-motion"
import { getGreeting } from "@/lib/utils"
import { user } from "@/data/mock"
import { ExecutiveSummaryCard } from "@/components/overview/ExecutiveSummary"
import { KpiCards } from "@/components/overview/KpiCards"
import { AIRecommendations } from "@/components/overview/AIRecommendations"
import { MeetingsTimeline } from "@/components/overview/MeetingsTimeline"
import { ActivityFeed } from "@/components/overview/ActivityFeed"
import { pageHeader } from "@/lib/motion"

export function OverviewPage() {
  const greeting = getGreeting()

  return (
    <div className="mx-auto max-w-7xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <p className="mb-2 text-[13px] font-medium tracking-wide text-muted-foreground uppercase">
          {new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" })}
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground lg:text-[2rem]">
          {greeting}, {user.name}
        </h1>
        <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-muted-foreground">
          Here's what's happening across {user.company} today.
        </p>
      </motion.div>

      <div className="mb-8">
        <ExecutiveSummaryCard />
      </div>

      <div className="mb-10">
        <KpiCards />
      </div>

      <div className="grid grid-cols-1 gap-7 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-7">
          <AIRecommendations />
        </div>
        <div className="space-y-7">
          <MeetingsTimeline />
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
