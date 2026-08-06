import { useCallback, useState } from "react"
import { motion } from "framer-motion"
import {
  Activity,
  ArrowUp,
  CalendarClock,
  Clock,
  Loader2,
  PenLine,
  Target,
  TrendingUp,
  Users,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { PageHeader, SectionHeading } from "@/components/common/PageHeader"
import { SourceChip } from "@/components/common/SourceChip"
import { ReportCard } from "@/components/cards/ReportCard"
import { PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { useAsyncAction } from "@/hooks/useAsyncAction"
import { askBriefly, getAskWorkspace } from "@/api/ask"
import { fadeUp } from "@/lib/motion"

const SUGGESTION_ICONS = {
  target: Target,
  calendar: CalendarClock,
  trending: TrendingUp,
  activity: Activity,
  pen: PenLine,
  users: Users,
}

function WorkspaceSkeleton() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <div className="mb-8 space-y-3">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-8 w-80" />
        <Skeleton className="h-4 w-96" />
      </div>
      <Skeleton className="mb-8 h-28 w-full" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-20" />
        ))}
      </div>
    </div>
  )
}

function QuestionComposer({ value, onChange, onSubmit, pending }) {
  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <Card className="overflow-hidden">
      <Textarea
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your priorities, meetings, pipeline or team…"
        className="border-0 px-5 py-4 text-[15px] focus:ring-0"
      />
      <div className="flex items-center justify-between gap-3 border-t border-border bg-subtle px-5 py-3">
        <p className="text-[11px] text-muted-foreground">
          Briefly answers from your connected systems and cites every source.
        </p>
        <Button
          variant="primary"
          size="sm"
          className="gap-1.5"
          onClick={onSubmit}
          disabled={pending || value.trim().length === 0}
        >
          {pending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} />
          ) : (
            <ArrowUp className="h-3.5 w-3.5" strokeWidth={2} />
          )}
          {pending ? "Analysing" : "Ask Briefly"}
        </Button>
      </div>
    </Card>
  )
}

export function AskBrieflyPage() {
  const fetchWorkspace = useCallback((options) => getAskWorkspace(options), [])
  const { data, loading, error, refetch } = useApiQuery(fetchWorkspace)
  const [question, setQuestion] = useState("")
  const [report, setReport] = useState(null)
  const ask = useAsyncAction(askBriefly)

  const submit = useCallback(
    async (text) => {
      const query = (text ?? question).trim()
      if (!query) return
      setQuestion(query)
      const result = await ask.run(query)
      if (result) setReport(result)
    },
    [ask, question],
  )

  if (loading) return <WorkspaceSkeleton />
  if (error) return <PageError message={error} onRetry={refetch} />

  const { suggestions, recent, connectedSources } = data

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow="Ask Briefly"
        title="Executive intelligence workspace"
        description="Ask a question about your business and get a cited report, not a conversation. Briefly reads your systems; you make the call."
      />

      <QuestionComposer
        value={question}
        onChange={setQuestion}
        onSubmit={() => submit()}
        pending={ask.pending}
      />

      {ask.error && <p className="mt-3 text-[13px] text-critical">{ask.error}</p>}

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] text-muted-foreground">Reading from</span>
        {connectedSources.map((source) => (
          <SourceChip key={source} source={source} />
        ))}
      </div>

      {report && (
        <div className="mt-8">
          <ReportCard report={report} onFollowUp={submit} />
        </div>
      )}

      <motion.div {...fadeUp} className="mt-10">
        <SectionHeading
          title={report ? "Ask something else" : "Start here"}
          description="Questions executives ask Briefly most often."
        />

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {suggestions.map((suggestion) => {
            const Icon = SUGGESTION_ICONS[suggestion.icon] ?? Target
            return (
              <button
                key={suggestion.id}
                type="button"
                onClick={() => submit(suggestion.question)}
                disabled={ask.pending}
                className="group flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-card p-4 text-left surface transition-[box-shadow,border-color] duration-200 hover:border-border-strong hover:surface-raised disabled:opacity-60"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-subtle transition-colors group-hover:bg-primary-soft">
                  <Icon
                    className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary"
                    strokeWidth={1.75}
                  />
                </span>
                <span className="min-w-0">
                  <span className="block text-[13px] font-medium leading-snug text-foreground">
                    {suggestion.question}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-muted-foreground">
                    {suggestion.category}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      </motion.div>

      <div className="mt-10">
        <SectionHeading title="Recently asked" />
        <Card>
          <ul className="divide-y divide-border">
            {recent.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => submit(item.question)}
                  disabled={ask.pending}
                  className="flex w-full cursor-pointer items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-subtle disabled:opacity-60"
                >
                  <Clock className="h-3.5 w-3.5 shrink-0 text-faint" strokeWidth={1.75} />
                  <span className="min-w-0 flex-1 truncate text-[13px] text-secondary-foreground">
                    {item.question}
                  </span>
                  <span className="shrink-0 text-[11px] text-muted-foreground">{item.askedAt}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}
