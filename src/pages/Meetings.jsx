import { useCallback, useMemo, useState } from "react"
import { CalendarClock } from "lucide-react"
import { Card } from "@/components/ui/card"
import { SegmentedControl } from "@/components/ui/toggle"
import { PageHeader } from "@/components/common/PageHeader"
import { MeetingCard } from "@/components/cards/MeetingCard"
import { EmptyState, ListSkeleton, PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getMeetings } from "@/api/meetings"

const FILTERS = ["All meetings", "Needs preparation"]

export function MeetingsPage() {
  const fetchMeetings = useCallback((options) => getMeetings(options), [])
  const { data, loading, error, refetch } = useApiQuery(fetchMeetings)
  const [filter, setFilter] = useState(FILTERS[0])

  const visibleMeetings = useMemo(() => {
    if (!data) return []
    return filter === FILTERS[1]
      ? data.meetings.filter((meeting) => meeting.prepStatus === "needs-prep")
      : data.meetings
  }, [data, filter])

  if (loading) return <ListSkeleton rows={4} />
  if (error) return <PageError message={error} onRetry={refetch} />

  const { date, meetingCount, needsPreparation, totalScheduledMinutes } = data
  const hours = Math.floor(totalScheduledMinutes / 60)
  const minutes = totalScheduledMinutes % 60

  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow={date}
        title="Meeting intelligence"
        description={`${meetingCount} meetings today. ${needsPreparation} need real preparation — Briefly has assembled the context, talking points and risks for each.`}
        actions={
          <SegmentedControl options={FILTERS} value={filter} onChange={setFilter} />
        }
      />

      <Card className="mb-6">
        <dl className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            ["Meetings", meetingCount],
            ["Need preparation", needsPreparation],
            ["Time in meetings", `${hours}h ${minutes}m`],
            ["Client-facing", data.meetings.filter((m) => m.type === "client").length],
          ].map(([label, value]) => (
            <div key={label} className="px-5 py-4">
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[18px] font-semibold numeric">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {visibleMeetings.length === 0 ? (
        <EmptyState
          icon={CalendarClock}
          title="Nothing needs preparation"
          description="Every meeting on today's calendar is already covered."
        />
      ) : (
        <div className="space-y-3">
          {visibleMeetings.map((meeting, index) => (
            <MeetingCard
              key={meeting.id}
              meeting={meeting}
              index={index}
              defaultOpen={meeting.prepStatus === "needs-prep" && index === 0}
            />
          ))}
        </div>
      )}
    </div>
  )
}
