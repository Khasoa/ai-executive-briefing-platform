import { Link } from "react-router-dom"
import { ArrowRight, Sun } from "lucide-react"
import { buttonVariants } from "@/components/ui/button-variants"
import { PageHeader, SectionHeading } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import { ActivityFeed } from "@/components/common/ActivityFeed"
import { ExecutiveSummaryCard } from "@/components/cards/ExecutiveSummaryCard"
import { KPIGrid } from "@/components/cards/KPIWidget"
import { RecommendationCard } from "@/components/cards/RecommendationCard"
import {
  EmptyState,
  OverviewSkeleton,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getOverview } from "@/api/overview"
import { cn, getGreeting } from "@/lib/utils"

export function OverviewPage() {
  const { data, loading, refreshing, error, refreshError, refetch, clearRefreshError } =
    useApiQuery(getOverview)

  if (loading) return <OverviewSkeleton />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { user, brief, executiveSummary, kpis, activity, focus } = data

  return (
    <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6 sm:py-7 lg:px-10">
      <PageHeader
        eyebrow={brief.date}
        title={`${getGreeting()}, ${user.name}`}
        description="Start with the Morning Brief — everything else on this page supports it."
        actions={
          <>
            <RefreshButton onClick={refetch} refreshing={refreshing} />
            <Link
              to="/morning-brief"
              className={cn(buttonVariants({ variant: "primary", size: "md" }), "gap-1.5")}
            >
              <Sun className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
              Morning Brief
            </Link>
          </>
        }
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <ExecutiveSummaryCard summary={executiveSummary} brief={brief} />

      <div className="mt-6">
        <KPIGrid kpis={kpis} />
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-3 lg:gap-7">
        <section className="lg:col-span-2">
          <SectionHeading title="Today's focus" />
          {focus.length === 0 ? (
            <EmptyState
              title="No focus items yet"
              description="Once your Morning Brief is generated, Briefly ranks the recommendations that protect revenue or unblock the day."
              actionLabel="Open Morning Brief"
              actionTo="/morning-brief"
            />
          ) : (
            <div className="space-y-2.5">
              {focus.map((recommendation, index) => (
                <RecommendationCard
                  key={recommendation.id}
                  recommendation={recommendation}
                  index={index}
                />
              ))}
            </div>
          )}
        </section>

        <section>
          <SectionHeading
            title="Overnight"
            action={
              <Link
                to="/inbox"
                className="inline-flex items-center gap-1 text-[12px] font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40"
              >
                Inbox
                <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              </Link>
            }
          />
          {activity.length === 0 ? (
            <EmptyState
              title="No overnight activity"
              description="When Gmail, Calendar and CRM are connected, changes appear here each morning."
              actionLabel="Check integrations"
              actionTo="/integrations"
              className="py-8"
            />
          ) : (
            <ActivityFeed items={activity} />
          )}
        </section>
      </div>
    </div>
  )
}
