import { useMemo, useState } from "react"
import { CalendarClock, ChevronDown } from "lucide-react"
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
import { cn } from "@/lib/utils"

const FILTERS = ["All meetings", "Needs preparation"]

/** Product sections: tomorrow folds into This week; later stays Later. */
const SECTION_META = [
  {
    key: "today",
    title: "Today",
    description: "Highest relevance — prepare only for these",
    emphasize: true,
    defaultCollapsed: false,
  },
  {
    key: "thisWeek",
    title: "This week",
    description: "Upcoming — not today's preparation queue",
    emphasize: false,
    defaultCollapsed: false,
  },
  {
    key: "thisMonth",
    title: "This month",
    description: "Planning view — review closer to the date",
    emphasize: false,
    defaultCollapsed: true,
  },
  {
    key: "later",
    title: "Later",
    description: "Beyond this month — synced for planning",
    emphasize: false,
    defaultCollapsed: true,
  },
]

function meetingsFromWindows(data, filterNeedsPrep) {
  if (!data) return []

  if (data.windows) {
    const bundled = {
      today: data.windows.today || [],
      thisWeek: [...(data.windows.tomorrow || []), ...(data.windows.thisWeek || [])],
      thisMonth: data.windows.thisMonth || [],
      later: data.windows.later || [],
    }
    return SECTION_META.map((section) => {
      let items = bundled[section.key] || []
      if (filterNeedsPrep) {
        items = items.filter((m) => m.prepRecommended)
      }
      return { ...section, meetings: items }
    }).filter((section) => section.meetings.length > 0 || section.key === "today")
  }

  const meetings = filterNeedsPrep
    ? (data.meetings || []).filter((m) => m.prepRecommended)
    : data.meetings || []
  return meetings.length
    ? [{ key: "all", title: "Meetings", description: "", emphasize: true, meetings, defaultCollapsed: false }]
    : []
}

export function MeetingsPage() {
  const { data, loading, refreshing, error, refreshError, refetch, clearRefreshError } =
    useApiQuery(getMeetings)
  const [filter, setFilter] = useState(FILTERS[0])
  const [collapsed, setCollapsed] = useState(() => ({ thisMonth: true, later: true }))

  const filterNeedsPrep = filter === FILTERS[1]
  const sections = useMemo(
    () => meetingsFromWindows(data, filterNeedsPrep),
    [data, filterNeedsPrep],
  )

  if (loading) return <ListSkeleton rows={4} />
  if (error) return <PageError error={error} onRetry={refetch} />

  const {
    date,
    meetingCount,
    needsPreparation,
    totalScheduledMinutes,
    meetings,
    todayCount,
    needsPreparationToday,
  } = data
  const todayN = todayCount ?? meetingCount
  const prepN = needsPreparationToday ?? needsPreparation
  const hours = Math.floor(totalScheduledMinutes / 60)
  const minutes = totalScheduledMinutes % 60
  const calendarEmpty = (meetings || []).length === 0
  const visibleEmpty =
    filterNeedsPrep &&
    sections.every((s) => s.meetings.length === 0)

  return (
    <div className="mx-auto max-w-5xl overflow-x-hidden px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow={date}
        title="Meeting intelligence"
        description={`${todayN} today · ${prepN} need preparation today`}
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

      <Card className="mb-6 overflow-hidden">
        <dl className="grid grid-cols-2 sm:grid-cols-4">
          {[
            ["Today", todayN],
            ["Need prep today", prepN],
            ["Time today", `${hours}h ${minutes}m`],
            [
              "Client-facing today",
              (
                data.windows?.today ??
                meetings.filter((m) => m.window === "today")
              ).filter((m) => m.type === "client").length,
            ],
          ].map(([label, value], index) => (
            <div
              key={label}
              className={cn(
                "px-3 py-3 sm:px-5 sm:py-4",
                index % 2 === 1 && "border-l border-border",
                index >= 2 && "border-t border-border sm:border-t-0 sm:border-l",
              )}
            >
              <dt className="text-[11px] text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-[16px] font-semibold numeric sm:text-[18px]">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      {calendarEmpty ? (
        <EmptyState
          icon={CalendarClock}
          title="No meetings on the calendar"
          description="Connect Google Calendar so Briefly can separate today from later planning and prepare context before each meeting."
          actionLabel="Open Integrations"
          actionTo="/integrations"
        />
      ) : visibleEmpty ? (
        <EmptyState
          icon={CalendarClock}
          title="Nothing needs preparation today"
          description="Only today's meetings appear in the preparation queue. Switch to All meetings to review this week and later."
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
        <div className="space-y-10">
          {sections.map((section) => {
            const isCollapsed = Boolean(collapsed[section.key])
            const emptyToday = section.key === "today" && section.meetings.length === 0
            return (
              <section key={section.key} className="min-w-0">
                <button
                  type="button"
                  onClick={() =>
                    setCollapsed((prev) => ({
                      ...prev,
                      [section.key]: !prev[section.key],
                    }))
                  }
                  className={cn(
                    "mb-4 flex w-full min-w-0 cursor-pointer items-end justify-between gap-3 border-b pb-2.5 text-left",
                    section.emphasize ? "border-foreground/20" : "border-border",
                  )}
                  aria-expanded={!isCollapsed}
                >
                  <div className="min-w-0">
                    <h2
                      className={cn(
                        "tracking-tight",
                        section.emphasize
                          ? "text-[20px] font-semibold sm:text-[22px]"
                          : "text-[15px] font-semibold text-secondary-foreground sm:text-[16px]",
                      )}
                    >
                      {section.title}
                      <span className="ml-2 text-[13px] font-normal text-muted-foreground numeric">
                        {section.meetings.length}
                      </span>
                    </h2>
                    {section.description ? (
                      <p className="mt-0.5 text-[12px] text-muted-foreground">{section.description}</p>
                    ) : null}
                  </div>
                  <ChevronDown
                    className={cn(
                      "mb-0.5 h-4 w-4 shrink-0 text-faint transition-transform",
                      !isCollapsed && "rotate-180",
                    )}
                    strokeWidth={1.75}
                    aria-hidden="true"
                  />
                </button>

                {!isCollapsed &&
                  (emptyToday ? (
                    <p className="text-[13px] text-muted-foreground">
                      No meetings on today&apos;s calendar.
                    </p>
                  ) : (
                    <div className={cn("space-y-3", section.emphasize && "space-y-4")}>
                      {section.meetings.map((meeting, index) => (
                        <MeetingCard
                          key={meeting.id}
                          meeting={meeting}
                          index={index}
                          emphasize={section.emphasize}
                          defaultOpen={
                            section.key === "today" &&
                            meeting.prepRecommended &&
                            index === 0
                          }
                        />
                      ))}
                    </div>
                  ))}
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
