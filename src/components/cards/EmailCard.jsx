import { useState } from "react"
import { motion } from "framer-motion"
import { Clock, CornerUpLeft, MessageSquare, Sparkles } from "lucide-react"
import { Avatar } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { enter } from "@/lib/motion"
import { SIGNAL_ACCENT_BAR, SIGNAL_BADGE, SIGNAL_LABEL } from "@/lib/signals"

/**
 * An intelligent summary of a thread rather than the thread itself. The
 * suggested response is a draft for the executive to approve, never sent.
 */
export function EmailCard({ email, index = 0 }) {
  const [showResponse, setShowResponse] = useState(false)
  const { subject, sender, aiSummary, priority, suggestedResponse, readingTime } = email

  return (
    <motion.div {...enter(index)}>
      <Card interactive className="overflow-hidden">
        <div className="flex">
          <span className={cn("w-0.5 shrink-0", SIGNAL_ACCENT_BAR[priority])} />

          <div className="min-w-0 flex-1 p-5">
            <div className="flex items-start gap-3">
              <Avatar
                initials={sender.avatar}
                size="lg"
                tone={priority === "critical" ? "accent" : "neutral"}
              />

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
                  <h3 className="text-[14px] font-semibold leading-snug tracking-tight text-balance">
                    {subject}
                    {email.unread && (
                      <span className="ml-2 inline-block h-1.5 w-1.5 translate-y-[-1px] rounded-full bg-primary align-middle" />
                    )}
                  </h3>
                  <Badge variant={SIGNAL_BADGE[priority]}>{SIGNAL_LABEL[priority]}</Badge>
                </div>

                <p className="mt-1 text-[12px] text-muted-foreground">
                  <span className="font-medium text-secondary-foreground">{sender.name}</span>
                  {" · "}
                  {sender.company}
                  {" · "}
                  {email.timeLabel}
                </p>
              </div>
            </div>

            <div className="mt-3.5 rounded-lg bg-subtle px-3.5 py-3">
              <div className="mb-1.5 flex items-center gap-1.5">
                <Sparkles className="h-3 w-3 text-primary" strokeWidth={1.75} />
                <span className="eyebrow text-muted-foreground">Summary</span>
              </div>
              <p className="text-[13px] leading-relaxed text-secondary-foreground">{aiSummary}</p>
            </div>

            {showResponse && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="overflow-hidden"
              >
                <div className="mt-2.5 rounded-lg border border-primary/15 bg-primary-soft px-3.5 py-3">
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <CornerUpLeft className="h-3 w-3 text-primary" strokeWidth={1.75} />
                    <span className="eyebrow text-primary">Suggested response</span>
                  </div>
                  <p className="text-[13px] leading-relaxed text-secondary-foreground">
                    {suggestedResponse}
                  </p>
                  <p className="mt-2.5 text-[11px] text-muted-foreground">
                    Briefly drafts. You decide whether it is sent.
                  </p>
                </div>
              </motion.div>
            )}

            <div className="mt-3.5 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Clock className="h-3 w-3" strokeWidth={1.75} />
                  {readingTime} read
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageSquare className="h-3 w-3" strokeWidth={1.75} />
                  {email.threadCount} in thread
                </span>
                {email.labels.map((label) => (
                  <Badge key={label} variant="quiet">
                    {label}
                  </Badge>
                ))}
              </div>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowResponse((open) => !open)}
                aria-expanded={showResponse}
              >
                {showResponse ? "Hide draft" : "View suggested response"}
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
