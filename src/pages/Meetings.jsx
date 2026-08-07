import { useMemo, useState } from "react"
import { CalendarClock } from "lucide-react"
import { Card } from "@/components/ui/card"
import { SegmentedControl } from "@/components/ui/toggle"
import { PageHeader } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import { MeetingCard } from "@/components/cards/MeetingCard"
import {
  EmptyState,
  ListSkeleton,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getMeetings } from "@/api/meetings"

const FILTERS = ["All meetings", "Needs preparation"]

export function MeetingsPage() {
  const { data, loading, refreshing, error, refreshError, refetch, clearRefreshError } =
    useApiQuery(getMeetings)
  const [filter, setFilter] = useState(FILTERS[0])

  const visibleMeetings = useMemo(() => {
    if (!data) return []
    return filter === FILTERS[1]
      ? data.meetings.filter((meeting) => meeting.prepStatus === "needs-prep")
      : data.meetings
  }, [data, filter])

  if (loading) return <ListSkeleton rows={4} />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { date, meetingCount, needsPreparation, totalScheduledMinutes, meetings } = data
  const hours = Math.floor(totalScheduledMinutes / 60)
  const minutes = totalScheduledMinutes % 60
  const calendarEmpty = meetings.length === 0

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow={date}
        title="Meeting intelligence"
        description={`${meetingCount} today · ${needsPreparation} need preparation`}
        actions={
          <>
            <RefreshButton onClick={refetch} refreshing={refreshing} />
            {!calendarEmpty && (
              <SegmentedControl
                options={FILTERS}
                value={filter}
                onChange={setFilter}
                aria-label="Filter meetings"
              />
            )}
          </>
        }
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <Card className="mb-6">
        <dl className="grid grid-cols-2 divide-x divide-border sm:grid-cols-4">
          {[
            ["Meetings", meetingCount],
            ["Need preparation", needsPreparation],
            ["Time in meetings", `${hours}h ${minutes}m`],
            ["Client-facing", meetings.filter((m) => m.type === "client").length],
          ].map(([label, value]) => (
            <div key={label} className="px-3 py-3 sm:px-5 sm:py-4">
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[16px] font-semibold numeric sm:text-[18px]">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {calendarEmpty ? (
        <EmptyState
          icon={CalendarClock}
          title="No meetings on today's calendar"
          description="Connect Google Calendar so Briefly can prepare context, talking points and risks before each meeting."
          actionLabel="Open Integrations"
          actionTo="/integrations"
        />
      ) : visibleMeetings.length === 0 ? (
        <EmptyState
          icon={CalendarClock}
          title="Nothing needs preparation"
          description="Every meeting on today's calendar already has enough context. Switch to All meetings to review the full day."
          action={
            <button
              type="button"
              onClick={() => setFilter(FILTERS[0])}
              className="cursor-pointer rounded-lg border border-border bg-card px-3 py-1.5 text-[13px] font-medium surface transition-colors hover:border-border-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40"
            >
              Show all meetings
            </button>
          }
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
