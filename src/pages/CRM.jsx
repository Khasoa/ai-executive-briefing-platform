import { useMemo, useState } from "react"
import { Target } from "lucide-react"
import { Card } from "@/components/ui/card"
import { SegmentedControl } from "@/components/ui/toggle"
import { PageHeader } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import { DealCard } from "@/components/cards/DealCard"
import {
  EmptyState,
  ListSkeleton,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getCrm } from "@/api/crm"
import { formatCurrency } from "@/lib/utils"
import { bySignal } from "@/lib/signals"

const FILTERS = ["Needs attention", "Full pipeline"]
const ATTENTION_LEVELS = new Set(["critical", "high"])

export function CRMPage() {
  const { data, loading, refreshing, error, refreshError, refetch, clearRefreshError } =
    useApiQuery(getCrm)
  const [filter, setFilter] = useState(FILTERS[0])

  const visibleDeals = useMemo(() => {
    if (!data) return []
    const filtered =
      filter === FILTERS[0]
        ? data.opportunities.filter((deal) => ATTENTION_LEVELS.has(deal.riskLevel))
        : data.opportunities
    return [...filtered].sort(bySignal("riskLevel"))
  }, [data, filter])

  if (loading) return <ListSkeleton rows={3} />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { summary, opportunities } = data
  const pipelineEmpty = opportunities.length === 0

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow="Pipeline"
        title="Pipeline"
        description={summary.headline}
        actions={
          <>
            <RefreshButton onClick={refetch} refreshing={refreshing} />
            {!pipelineEmpty && (
              <SegmentedControl
                options={FILTERS}
                value={filter}
                onChange={setFilter}
                aria-label="Filter opportunities"
              />
            )}
          </>
        }
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <Card className="mb-6">
        <dl className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            ["Open pipeline", formatCurrency(summary.pipelineValue)],
            ["Weighted value", formatCurrency(summary.weightedValue)],
            ["Needs attention", summary.needingAttention],
            ["Closing this month", summary.closingThisMonth],
          ].map(([label, value]) => (
            <div key={label} className="px-3 py-3 sm:px-5 sm:py-4">
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[16px] font-semibold numeric sm:text-[18px]">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {pipelineEmpty ? (
        <EmptyState
          icon={Target}
          title="No opportunities in the pipeline"
          description="Connect GoHighLevel so Briefly can surface deals that need an executive decision — and keep quiet on the ones that do not."
          actionLabel="Open Integrations"
          actionTo="/integrations"
        />
      ) : visibleDeals.length === 0 ? (
        <EmptyState
          icon={Target}
          title="No deals need you today"
          description="Every opportunity is progressing without executive intervention. Switch to Full pipeline to review the rest."
          action={
            <button
              type="button"
              onClick={() => setFilter(FILTERS[1])}
              className="cursor-pointer rounded-lg border border-border bg-card px-3 py-1.5 text-[13px] font-medium surface transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40"
            >
              Show full pipeline
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {visibleDeals.map((opportunity, index) => (
            <DealCard key={opportunity.id} opportunity={opportunity} index={index} />
          ))}
        </div>
      )}
    </div>
  )
}
