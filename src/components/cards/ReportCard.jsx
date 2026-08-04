import { motion } from "framer-motion"
import { FileText, Quote } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"
import { fadeUp } from "@/lib/motion"

const CONFIDENCE_BADGE = { high: "primary", medium: "accent", low: "quiet" }

function RankedSection({ items }) {
  return (
    <ol className="space-y-2">
      {items.map((item, index) => (
        <li
          key={item.title}
          className="flex items-start gap-3 rounded-lg border border-border bg-subtle px-3.5 py-3"
        >
          <span className="mt-px w-4 shrink-0 text-[13px] font-semibold text-faint numeric">
            {index + 1}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium leading-snug">{item.title}</p>
            {item.detail && (
              <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{item.detail}</p>
            )}
          </div>
          {item.meta && <Badge variant="quiet">{item.meta}</Badge>}
        </li>
      ))}
    </ol>
  )
}

function ListSection({ items }) {
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item.title} className="flex items-start gap-2.5">
          <span className="mt-[0.45rem] h-1 w-1 shrink-0 rounded-full bg-border-strong" />
          <div className="min-w-0">
            <p className="text-[13px] leading-relaxed text-secondary-foreground">{item.title}</p>
            {item.detail && (
              <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">
                {item.detail}
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}

function DraftSection({ body }) {
  return (
    <div className="rounded-lg border border-border bg-subtle">
      <div className="flex items-center gap-2 border-b border-border px-3.5 py-2">
        <FileText className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />
        <span className="eyebrow text-muted-foreground">Draft — not sent</span>
      </div>
      <pre className="whitespace-pre-wrap px-3.5 py-3 font-sans text-[13px] leading-relaxed text-secondary-foreground">
        {body}
      </pre>
      <div className="flex items-center gap-2 border-t border-border px-3.5 py-2.5">
        <Button size="sm" variant="secondary">
          Copy draft
        </Button>
        <span className="text-[11px] text-muted-foreground">
          Briefly never sends anything without your approval.
        </span>
      </div>
    </div>
  )
}

function Section({ section }) {
  return (
    <section>
      <h3 className="eyebrow mb-2.5 text-muted-foreground">{section.title}</h3>
      {section.type === "ranked" && <RankedSection items={section.items} />}
      {section.type === "list" && <ListSection items={section.items} />}
      {section.type === "draft" && <DraftSection body={section.body} />}
      {section.type === "text" && (
        <p className="text-[13px] leading-relaxed text-secondary-foreground">{section.body}</p>
      )}
    </section>
  )
}

/**
 * An answer from Ask Briefly, rendered as a cited report rather than a chat
 * bubble. Every report names the systems it drew from.
 */
export function ReportCard({ report, onFollowUp }) {
  return (
    <motion.article {...fadeUp}>
      <Card className="overflow-hidden">
        <header className="border-b border-border bg-subtle px-6 py-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-start gap-2.5">
              <Quote className="mt-1 h-3.5 w-3.5 shrink-0 text-faint" strokeWidth={1.75} />
              <h2 className="text-[15px] font-semibold leading-snug tracking-tight text-balance">
                {report.question}
              </h2>
            </div>
            <Badge variant={CONFIDENCE_BADGE[report.confidence]}>
              {report.confidence} confidence
            </Badge>
          </div>
        </header>

        <div className="px-6 py-5">
          <p className="font-serif text-[16px] leading-[1.65] text-foreground text-balance">
            {report.summary}
          </p>

          <div className="mt-6 space-y-6">
            {report.sections.map((section) => (
              <Section key={section.id} section={section} />
            ))}
          </div>
        </div>

        <footer className="border-t border-border bg-subtle px-6 py-4">
          <p className="eyebrow mb-2 text-muted-foreground">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {report.citations.map((citation) => (
              <SourceChip
                key={citation.source}
                source={citation.source}
                detail={citation.detail}
                className="bg-card"
              />
            ))}
          </div>

          {report.followUps.length > 0 && (
            <>
              <p className="eyebrow mb-2 mt-4 text-muted-foreground">Follow up</p>
              <div className="flex flex-wrap gap-1.5">
                {report.followUps.map((followUp) => (
                  <Button
                    key={followUp}
                    size="sm"
                    variant="secondary"
                    onClick={() => onFollowUp?.(followUp)}
                  >
                    {followUp}
                  </Button>
                ))}
              </div>
            </>
          )}
        </footer>
      </Card>
    </motion.article>
  )
}
