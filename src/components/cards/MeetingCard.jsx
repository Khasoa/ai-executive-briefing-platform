import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  AlertTriangle,
  Building2,
  ChevronDown,
  ClipboardList,
  ExternalLink,
  HelpCircle,
  Mail,
  MapPin,
  MessageSquareQuote,
  NotebookPen,
  Users,
} from "lucide-react"
import { Avatar, AvatarGroup } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { cn } from "@/lib/utils"
import { ease, enter } from "@/lib/motion"
import { SIGNAL_DOT } from "@/lib/signals"

const TYPE_LABEL = {
  internal: "Internal",
  client: "Client-facing",
  investor: "Investor",
  personal: "Personal",
}

function Block({ icon: Icon, title, children }) {
  return (
    <section className="min-w-0">
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" strokeWidth={1.75} />
        <h4 className="eyebrow text-muted-foreground">{title}</h4>
      </div>
      {children}
    </section>
  )
}

function BulletList({ items, marker = "bg-border-strong" }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-2.5">
          <span className={cn("mt-[0.4rem] h-1 w-1 shrink-0 rounded-full", marker)} />
          <span className="min-w-0 break-words text-[13px] leading-relaxed text-secondary-foreground">
            {item}
          </span>
        </li>
      ))}
    </ul>
  )
}

/**
 * Meeting intelligence card — richer for today, concise for future windows.
 */
export function MeetingCard({ meeting, index = 0, defaultOpen = false, emphasize = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const [seriesOpen, setSeriesOpen] = useState(false)
  const isToday = meeting.window === "today"
  const prepToday = Boolean(meeting.prepRecommended)
  const attendees = meeting.attendees || []
  const company = meeting.company || {}
  const relatedEmails = meeting.relatedEmails || []
  const suggested = meeting.suggestedPrepActions || []
  const highlights = meeting.prepHighlights || []
  const organizer = meeting.organizer
  const timing =
    meeting.timingLabel ||
    [meeting.relativeLabel, meeting.dateLabel].filter(Boolean).join(" · ")
  const timeRange =
    meeting.startTime && meeting.endTime
      ? `${meeting.startTime}–${meeting.endTime}`
      : meeting.startTime || ""

  return (
    <motion.div {...enter(index)} className="min-w-0">
      <Card
        className={cn(
          "overflow-hidden",
          emphasize && "border-border-strong/70 shadow-sm",
          isToday && prepToday && "ring-1 ring-primary/25",
        )}
      >
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-label={`${open ? "Collapse" : "Expand"} details for ${meeting.title}`}
          className="flex w-full min-w-0 cursor-pointer items-start gap-3 p-4 text-left transition-colors hover:bg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-ring/40 sm:gap-4 sm:p-5"
        >
          <div className="w-[4.5rem] shrink-0 sm:w-20">
            {!isToday && meeting.weekdayDateLabel ? (
              <p className="text-[11px] leading-snug text-muted-foreground">
                {meeting.weekdayDateLabel}
              </p>
            ) : null}
            <p className="text-[14px] font-semibold leading-snug numeric sm:text-[15px]">
              {timeRange || meeting.startTime}
            </p>
            <p className="mt-1 text-[11px] text-muted-foreground numeric">{meeting.duration}</p>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3
                className={cn(
                  "min-w-0 break-words font-semibold leading-snug tracking-tight",
                  emphasize ? "text-[16px] sm:text-[17px]" : "text-[14px] sm:text-[15px]",
                )}
              >
                {meeting.title}
              </h3>
              {prepToday ? (
                <Badge variant="accent">Prepare today</Badge>
              ) : isToday ? (
                <span className="text-[11px] text-faint">Ready</span>
              ) : (
                <span className="text-[11px] text-faint">Upcoming</span>
              )}
            </div>

            <p className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12px] leading-snug text-muted-foreground">
              <span>{timing}</span>
              {meeting.duration ? <span aria-hidden="true">·</span> : null}
              {meeting.duration ? <span>{meeting.duration}</span> : null}
              <span aria-hidden="true">·</span>
              <span>{TYPE_LABEL[meeting.type] || meeting.type}</span>
              {meeting.isRecurring ? (
                <>
                  <span aria-hidden="true">·</span>
                  <span>{meeting.recurringLabel || "Recurring"}</span>
                </>
              ) : null}
            </p>

            {isToday && meeting.whyItMatters ? (
              <p className="mt-2 line-clamp-2 text-[12px] leading-snug text-secondary-foreground sm:line-clamp-3">
                {meeting.whyItMatters}
              </p>
            ) : null}

            {!isToday ? (
              <p className="mt-1.5 text-[12px] text-muted-foreground">
                {meeting.prepStatusLabel || "Preparation not yet needed — review closer to the meeting."}
              </p>
            ) : null}

            {highlights.length > 0 && isToday ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {highlights.slice(0, 4).map((item) => (
                  <span
                    key={item}
                    className="rounded-md bg-subtle px-2 py-0.5 text-[11px] text-secondary-foreground"
                  >
                    {item}
                  </span>
                ))}
              </div>
            ) : null}

            <div className="mt-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
              {attendees.length > 0 ? (
                <AvatarGroup
                  people={attendees.slice(0, 5).map((attendee) => ({
                    initials: attendee.avatar,
                    title: `${attendee.name} · ${attendee.role || ""}`,
                  }))}
                />
              ) : null}
              {organizer?.name ? (
                <span className="inline-flex min-w-0 max-w-full items-center gap-1 text-[11px] text-faint">
                  <Users className="h-3 w-3 shrink-0" strokeWidth={1.75} aria-hidden="true" />
                  <span className="truncate">Organizer · {organizer.name}</span>
                </span>
              ) : null}
              {meeting.location && !String(meeting.location).startsWith("http") ? (
                <span className="inline-flex min-w-0 max-w-full items-center gap-1 text-[11px] text-faint">
                  <MapPin className="h-3 w-3 shrink-0" strokeWidth={1.75} aria-hidden="true" />
                  <span className="truncate">{meeting.location}</span>
                </span>
              ) : null}
              {company.name ? (
                <span className="inline-flex min-w-0 max-w-full items-center gap-1 text-[11px] text-faint">
                  <Building2 className="h-3 w-3 shrink-0" strokeWidth={1.75} aria-hidden="true" />
                  <span className="truncate">{company.name}</span>
                </span>
              ) : null}
            </div>
          </div>

          <ChevronDown
            className={cn(
              "mt-1 h-4 w-4 shrink-0 text-faint transition-transform duration-200",
              open && "rotate-180",
            )}
            strokeWidth={1.75}
          />
        </button>

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.28, ease }}
              className="overflow-hidden"
            >
              <div className="border-t border-border px-4 py-5 sm:px-5">
                <div className="grid grid-cols-1 gap-x-8 gap-y-6 lg:grid-cols-2">
                  {meeting.contextNote ? (
                    <div className="rounded-lg border border-border bg-subtle px-3 py-2.5 text-[12px] leading-relaxed text-muted-foreground lg:col-span-2">
                      {meeting.contextNote}
                    </div>
                  ) : null}

                  {suggested.length > 0 ? (
                    <Block icon={ClipboardList} title={isToday ? "Prepare" : "Later"}>
                      <BulletList items={suggested} marker="bg-primary/40" />
                    </Block>
                  ) : null}

                  {isToday && meeting.whyItMatters ? (
                    <Block icon={NotebookPen} title="Why it matters">
                      <p className="break-words text-[13px] leading-relaxed text-secondary-foreground">
                        {meeting.whyItMatters}
                      </p>
                    </Block>
                  ) : null}

                  {attendees.length > 0 ? (
                    <Block icon={Users} title="Who is attending">
                      <ul className="space-y-1.5">
                        {attendees.map((attendee) => (
                          <li key={`${attendee.name}-${attendee.email || ""}`} className="flex items-center gap-2.5">
                            <Avatar initials={attendee.avatar} size="xs" />
                            <span className="min-w-0 break-words text-[12px] text-secondary-foreground">
                              <span className="font-medium text-foreground">{attendee.name}</span>
                              {attendee.role || attendee.company
                                ? ` · ${[attendee.role, attendee.company].filter(Boolean).join(", ")}`
                                : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </Block>
                  ) : null}

                  {company.name && isToday ? (
                    <Block icon={Building2} title={`About ${company.name}`}>
                      <p className="break-words text-[13px] leading-relaxed text-secondary-foreground">
                        {company.background || "No company background stored for this meeting."}
                      </p>
                    </Block>
                  ) : null}

                  {(meeting.agenda || []).length > 0 ? (
                    <Block icon={ClipboardList} title="Agenda">
                      <ol className="space-y-1.5">
                        {meeting.agenda.map((item, agendaIndex) => (
                          <li key={`${agendaIndex}-${item.slice(0, 24)}`} className="flex items-start gap-2.5">
                            <span className="w-3 shrink-0 text-[12px] font-semibold text-faint numeric">
                              {agendaIndex + 1}
                            </span>
                            <span className="min-w-0 break-words text-[13px] leading-relaxed text-secondary-foreground">
                              {item}
                            </span>
                          </li>
                        ))}
                      </ol>
                      {meeting.isRecurring ? (
                        <div className="mt-3">
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation()
                              setSeriesOpen((value) => !value)
                            }}
                            className="cursor-pointer text-[12px] font-medium text-muted-foreground hover:text-foreground"
                          >
                            {seriesOpen ? "Hide recurring note" : "View recurring series"}
                          </button>
                          {seriesOpen ? (
                            <p className="mt-1.5 text-[12px] leading-relaxed text-muted-foreground">
                              This is one occurrence of a recurring series. Full series dates are
                              kept in Google Calendar — Briefly shows only this occurrence.
                            </p>
                          ) : null}
                        </div>
                      ) : null}
                    </Block>
                  ) : meeting.isRecurring ? (
                    <Block icon={ClipboardList} title="Recurring">
                      <p className="text-[13px] text-muted-foreground">
                        {meeting.recurringLabel || "Recurring meeting"} — this card shows the
                        current occurrence only.
                      </p>
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          setSeriesOpen((value) => !value)
                        }}
                        className="mt-2 cursor-pointer text-[12px] font-medium text-muted-foreground hover:text-foreground"
                      >
                        {seriesOpen ? "Hide" : "View recurring series"}
                      </button>
                      {seriesOpen ? (
                        <p className="mt-1.5 text-[12px] text-muted-foreground">
                          Open Google Calendar for the full series schedule.
                        </p>
                      ) : null}
                    </Block>
                  ) : null}

                  {isToday && (meeting.preparationNotes || []).length > 0 ? (
                    <Block icon={NotebookPen} title="Preparation notes">
                      <BulletList items={meeting.preparationNotes} marker="bg-primary/40" />
                    </Block>
                  ) : null}

                  {isToday && (meeting.talkingPoints || []).length > 0 ? (
                    <Block icon={MessageSquareQuote} title="Talking points">
                      <BulletList items={meeting.talkingPoints} marker="bg-primary/40" />
                    </Block>
                  ) : null}

                  {isToday && (meeting.recommendedQuestions || []).length > 0 ? (
                    <Block icon={HelpCircle} title="Questions worth asking">
                      <ul className="space-y-2">
                        {meeting.recommendedQuestions.map((question) => (
                          <li
                            key={question}
                            className="break-words rounded-lg border border-border bg-subtle px-3 py-2 text-[13px] leading-relaxed text-secondary-foreground"
                          >
                            {question}
                          </li>
                        ))}
                      </ul>
                    </Block>
                  ) : null}

                  {isToday && (meeting.risks || []).length > 0 ? (
                    <Block icon={AlertTriangle} title="Potential risks">
                      <ul className="space-y-2.5">
                        {meeting.risks.map((risk) => (
                          <li key={risk.title} className="flex items-start gap-2.5">
                            <span
                              className={cn(
                                "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                                SIGNAL_DOT[risk.severity],
                              )}
                            />
                            <div className="min-w-0">
                              <p className="break-words text-[13px] font-medium leading-snug">
                                {risk.title}
                              </p>
                              <p className="mt-0.5 break-words text-[12px] leading-relaxed text-muted-foreground">
                                {risk.detail}
                              </p>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </Block>
                  ) : null}

                  {isToday ? (
                    <Block icon={Mail} title="Relevant emails">
                      {relatedEmails.length > 0 ? (
                        <ul className="space-y-2">
                          {relatedEmails.map((email) => (
                            <li
                              key={email.id}
                              className="rounded-lg border border-border bg-card px-3 py-2.5"
                            >
                              <div className="flex items-start justify-between gap-3">
                                <p className="min-w-0 break-words text-[13px] font-medium leading-snug">
                                  {email.subject}
                                </p>
                                <span className="shrink-0 text-[11px] text-muted-foreground">
                                  {email.time}
                                </span>
                              </div>
                              <p className="mt-1 break-words text-[12px] leading-relaxed text-muted-foreground">
                                {email.sender} — {email.summary}
                              </p>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[13px] leading-relaxed text-muted-foreground">
                          No related emails matched from subject, attendee, or company metadata.
                        </p>
                      )}
                    </Block>
                  ) : null}

                  {meeting.meetingLink ? (
                    <div className="lg:col-span-2">
                      <a
                        href={meeting.meetingLink}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex max-w-full items-center gap-1.5 text-[12px] font-medium text-primary hover:underline"
                        onClick={(event) => event.stopPropagation()}
                      >
                        <ExternalLink className="h-3.5 w-3.5 shrink-0" strokeWidth={1.75} />
                        <span className="truncate">{meeting.meetingLink}</span>
                      </a>
                    </div>
                  ) : null}
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                  <span className="text-[11px] text-muted-foreground">Prepared from</span>
                  {(meeting.sources || []).map((source) => (
                    <SourceChip key={source} source={source} />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  )
}
