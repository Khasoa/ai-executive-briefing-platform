import { motion } from "framer-motion"
import { getGreeting } from "@/lib/utils"
import { user } from "@/data/mock"
import { ExecutiveSummaryCard } from "@/components/overview/ExecutiveSummary"
import { KpiCards } from "@/components/overview/KpiCards"
import { AIRecommendations } from "@/components/overview/AIRecommendations"
import { MeetingsTimeline } from "@/components/overview/MeetingsTimeline"
import { ActivityFeed } from "@/components/overview/ActivityFeed"

export function OverviewPage() {
  const greeting = getGreeting()

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">
          {greeting}, {user.name}
        </h1>
        <p className="mt-1 text-muted-foreground">
          Here's what's happening across {user.company} today.
        </p>
      </motion.div>

      <div className="mb-6">
        <ExecutiveSummaryCard />
      </div>

      <div className="mb-8">
        <KpiCards />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <AIRecommendations />
        </div>
        <div className="space-y-6">
          <MeetingsTimeline />
          <ActivityFeed />
        </div>
      </div>
    </div>
  )
}
