import { useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import {
  AlertTriangle,
  Building2,
  ChevronDown,
  ClipboardList,
  HelpCircle,
  Mail,
  MapPin,
  MessageSquareQuote,
  NotebookPen,
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
  client: "Client",
  investor: "Investor",
  personal: "Personal",
}

function Block({ icon: Icon, title, children }) {
  return (
    <section>
      <div className="mb-2 flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />
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
          <span className="text-[13px] leading-relaxed text-secondary-foreground">{item}</span>
        </li>
      ))}
    </ul>
  )
}

/**
 * Meeting intelligence, not a calendar entry: who is in the room, what they
 * care about, what to say, what to ask and what could go wrong.
 */
export function MeetingCard({ meeting, index = 0, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const needsPrep = meeting.prepStatus === "needs-prep"

  return (
    <motion.div {...enter(index)}>
      <Card className="overflow-hidden">
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          className="flex w-full cursor-pointer items-start gap-4 p-5 text-left transition-colors hover:bg-subtle"
        >
          <div className="w-14 shrink-0">
            <p className="text-[15px] font-semibold leading-none numeric">{meeting.startTime}</p>
            <p className="mt-1 text-[11px] text-muted-foreground numeric">{meeting.duration}</p>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-[15px] font-semibold leading-snug tracking-tight">
                {meeting.title}
              </h3>
              <Badge variant={needsPrep ? "accent" : "quiet"}>
                {needsPrep ? "Needs preparation" : "Ready"}
              </Badge>
              <Badge variant="quiet">{TYPE_LABEL[meeting.type]}</Badge>
            </div>

            <p className="mt-1.5 text-[12px] text-muted-foreground">{meeting.prepReason}</p>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2">
              <AvatarGroup
                people={meeting.attendees.map((attendee) => ({
                  initials: attendee.avatar,
                  title: `${attendee.name} · ${attendee.role}`,
                }))}
              />
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <MapPin className="h-3 w-3" strokeWidth={1.75} />
                {meeting.location}
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
                <Building2 className="h-3 w-3" strokeWidth={1.75} />
                {meeting.company.name}
              </span>
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
              <div className="border-t border-border px-5 py-5">
                <div className="grid grid-cols-1 gap-x-8 gap-y-6 lg:grid-cols-2">
                  <Block icon={Building2} title={`About ${meeting.company.name}`}>
                    <p className="text-[13px] leading-relaxed text-secondary-foreground">
                      {meeting.company.background}
                    </p>
                    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
                      {[
                        ["Industry", meeting.company.industry],
                        ["Size", meeting.company.size],
                        ["Relationship", meeting.company.relationship],
                        ["Annual value", meeting.company.arr],
                      ]
                        .filter(([, value]) => Boolean(value))
                        .map(([label, value]) => (
                          <div key={label}>
                            <dt className="text-[11px] text-muted-foreground">{label}</dt>
                            <dd className="text-[12px] font-medium text-secondary-foreground">
                              {value}
                            </dd>
                          </div>
                        ))}
                    </dl>
                  </Block>

                  <Block icon={ClipboardList} title="Agenda">
                    <ol className="space-y-1.5">
                      {meeting.agenda.map((item, agendaIndex) => (
                        <li key={item} className="flex items-start gap-2.5">
                          <span className="w-3 shrink-0 text-[12px] font-semibold text-faint numeric">
                            {agendaIndex + 1}
                          </span>
                          <span className="text-[13px] leading-relaxed text-secondary-foreground">
                            {item}
                          </span>
                        </li>
                      ))}
                    </ol>

                    <div className="mt-4">
                      <h4 className="eyebrow mb-2 text-muted-foreground">In the room</h4>
                      <ul className="space-y-1.5">
                        {meeting.attendees.map((attendee) => (
                          <li key={attendee.name} className="flex items-center gap-2.5">
                            <Avatar initials={attendee.avatar} size="xs" />
                            <span className="text-[12px] text-secondary-foreground">
                              <span className="font-medium text-foreground">{attendee.name}</span>
                              {" · "}
                              {attendee.role}, {attendee.company}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </Block>

                  <Block icon={NotebookPen} title="Preparation notes">
                    <BulletList items={meeting.preparationNotes} marker="bg-primary/40" />
                  </Block>

                  <Block icon={MessageSquareQuote} title="Talking points">
                    <BulletList items={meeting.talkingPoints} marker="bg-primary/40" />
                  </Block>

                  <Block icon={HelpCircle} title="Questions worth asking">
                    <ul className="space-y-2">
                      {meeting.recommendedQuestions.map((question) => (
                        <li
                          key={question}
                          className="rounded-lg border border-border bg-subtle px-3 py-2 text-[13px] leading-relaxed text-secondary-foreground"
                        >
                          {question}
                        </li>
                      ))}
                    </ul>
                  </Block>

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
                          <div>
                            <p className="text-[13px] font-medium leading-snug">{risk.title}</p>
                            <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                              {risk.detail}
                            </p>
                          </div>
                        </li>
                      ))}
                    </ul>
                  </Block>

                  <Block icon={Mail} title="Relevant emails">
                    <ul className="space-y-2">
                      {meeting.relatedEmails.map((email) => (
                        <li
                          key={email.id}
                          className="rounded-lg border border-border bg-card px-3 py-2.5"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-[13px] font-medium leading-snug">{email.subject}</p>
                            <span className="shrink-0 text-[11px] text-muted-foreground">
                              {email.time}
                            </span>
                          </div>
                          <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">
                            {email.sender} — {email.summary}
                          </p>
                        </li>
                      ))}
                    </ul>
                  </Block>
                </div>

                <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-border pt-4">
                  <span className="text-[11px] text-muted-foreground">Prepared from</span>
                  {meeting.sources.map((source) => (
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
