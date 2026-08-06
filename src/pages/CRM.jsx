import { useCallback, useMemo, useState } from "react"
import { Target } from "lucide-react"
import { Card } from "@/components/ui/card"
import { SegmentedControl } from "@/components/ui/toggle"
import { PageHeader } from "@/components/common/PageHeader"
import { DealCard } from "@/components/cards/DealCard"
import { EmptyState, ListSkeleton, PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getCrm } from "@/api/crm"
import { formatCurrency } from "@/lib/utils"
import { bySignal } from "@/lib/signals"

const FILTERS = ["Needs attention", "Full pipeline"]
const ATTENTION_LEVELS = new Set(["critical", "high"])

export function CRMPage() {
  const fetchCrm = useCallback((options) => getCrm(options), [])
  const { data, loading, error, refetch } = useApiQuery(fetchCrm)
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
  if (error) return <PageError message={error} onRetry={refetch} />

  const { summary } = data

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow="Pipeline"
        title="Opportunities needing you"
        description={summary.headline}
        actions={<SegmentedControl options={FILTERS} value={filter} onChange={setFilter} />}
      />

      <Card className="mb-6">
        <dl className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            ["Open pipeline", formatCurrency(summary.pipelineValue)],
            ["Weighted value", formatCurrency(summary.weightedValue)],
            ["Needs attention", summary.needingAttention],
            ["Closing this month", summary.closingThisMonth],
          ].map(([label, value]) => (
            <div key={label} className="px-5 py-4">
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[18px] font-semibold numeric">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {visibleDeals.length === 0 ? (
        <EmptyState
          icon={Target}
          title="No deals need you today"
          description="Every opportunity is progressing without executive intervention."
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
