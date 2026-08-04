import { useCallback } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Sun } from "lucide-react"
import { buttonVariants } from "@/components/ui/button-variants"
import { PageHeader, SectionHeading } from "@/components/common/PageHeader"
import { ActivityFeed } from "@/components/common/ActivityFeed"
import { ExecutiveSummaryCard } from "@/components/cards/ExecutiveSummaryCard"
import { KPIGrid } from "@/components/cards/KPIWidget"
import { RecommendationCard } from "@/components/cards/RecommendationCard"
import { OverviewSkeleton, PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getOverview } from "@/services/briefly"
import { cn, getGreeting } from "@/lib/utils"

export function OverviewPage() {
  const fetchOverview = useCallback((options) => getOverview(options), [])
  const { data, loading, error, refetch } = useApiQuery(fetchOverview)

  if (loading) return <OverviewSkeleton />
  if (error) return <PageError message={error} onRetry={refetch} />

  const { user, brief, executiveSummary, kpis, activity, focus } = data

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow={brief.date}
        title={`${getGreeting()}, ${user.name}`}
        description={`Today's Morning Brief · generated ${brief.generatedLabel} from ${brief.sources.length} connected systems.`}
        actions={
          <Link
            to="/morning-brief"
            className={cn(buttonVariants({ variant: "primary", size: "md" }), "gap-1.5")}
          >
            <Sun className="h-4 w-4" strokeWidth={1.75} />
            Open Morning Brief
          </Link>
        }
      />

      <ExecutiveSummaryCard summary={executiveSummary} brief={brief} />

      <div className="mt-8">
        <KPIGrid kpis={kpis} />
      </div>

      <div className="mt-10 grid grid-cols-1 gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <SectionHeading
            title="Today's focus"
            description="Three recommendations, ranked by what they protect or unblock."
          />
          <div className="space-y-3">
            {focus.map((recommendation, index) => (
              <RecommendationCard
                key={recommendation.id}
                recommendation={recommendation}
                index={index}
              />
            ))}
          </div>
        </section>

        <section>
          <SectionHeading
            title="Recent activity"
            description="What changed across your systems overnight."
            action={
              <Link
                to="/inbox"
                className="inline-flex items-center gap-1 text-[12px] font-medium text-muted-foreground transition-colors hover:text-foreground"
              >
                Inbox
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} />
              </Link>
            }
          />
          <ActivityFeed items={activity} />
        </section>
      </div>
    </div>
  )
}
