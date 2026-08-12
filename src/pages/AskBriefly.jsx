import { useCallback, useState } from "react"
import { motion } from "framer-motion"
import {
  Activity,
  ArrowUp,
  CalendarClock,
  Clock,
  Loader2,
  MessagesSquare,
  PenLine,
  Target,
  TrendingUp,
  Users,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Textarea } from "@/components/ui/input"
import { PageHeader, SectionHeading } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import { SourceChip } from "@/components/common/SourceChip"
import { ReportCard } from "@/components/cards/ReportCard"
import {
  AskSkeleton,
  EmptyState,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useToast } from "@/hooks/useToast"
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

function QuestionComposer({ value, onChange, onSubmit, pending }) {
  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSubmit()
    }
  }

  return (
    <Card className="overflow-hidden">
      <label className="sr-only" htmlFor="ask-question">
        Ask Briefly a question
      </label>
      <Textarea
        id="ask-question"
        rows={3}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your priorities, meetings, pipeline or team…"
        className="border-0 px-4 py-4 text-[15px] focus:ring-0 sm:px-5"
      />
      <div className="flex flex-col gap-3 border-t border-border bg-subtle px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <p className="text-[11px] text-muted-foreground">
          Briefly answers from your connected systems and cites every source.
        </p>
        <Button
          variant="primary"
          size="sm"
          className="gap-1.5 self-end sm:self-auto"
          onClick={onSubmit}
          disabled={pending || value.trim().length === 0}
          aria-label={pending ? "Analysing question" : "Ask Briefly"}
        >
          {pending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} aria-hidden="true" />
          ) : (
            <ArrowUp className="h-3.5 w-3.5" strokeWidth={2} aria-hidden="true" />
          )}
          {pending ? "Analysing" : "Ask Briefly"}
        </Button>
      </div>
    </Card>
  )
}

export function AskBrieflyPage() {
  const toast = useToast()
  const { data, loading, refreshing, error, refreshError, refetch, clearRefreshError } =
    useApiQuery(getAskWorkspace)
  const [question, setQuestion] = useState("")
  const [report, setReport] = useState(null)
  const ask = useAsyncAction(askBriefly)

  const submit = useCallback(
    async (text) => {
      const query = (text ?? question).trim()
      if (!query) return
      setQuestion(query)
      const { data: result, error: actionError } = await ask.run(query)
      if (result) {
        setReport(result)
        return
      }
      if (actionError) toast.error(actionError.message)
    },
    [ask, question, toast],
  )

  if (loading) return <AskSkeleton />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { suggestions, recent, connectedSources } = data
  const noSources = connectedSources.length === 0

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow="Ask Briefly"
        title="Executive intelligence workspace"
        description="Ask a question about your business and get a cited report, not a conversation. Briefly reads your systems; you make the call."
        actions={<RefreshButton onClick={refetch} refreshing={refreshing} />}
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      {noSources ? (
        <EmptyState
          icon={MessagesSquare}
          title="Connect a system before asking"
          description="Ask Briefly cites Gmail, Calendar, CRM and Notion. Connect at least one integration so answers have sources you can trust."
          actionLabel="Open Integrations"
          actionTo="/integrations"
          className="mb-8"
        />
      ) : null}

      <QuestionComposer
        value={question}
        onChange={setQuestion}
        onSubmit={() => submit()}
        pending={ask.pending}
      />

      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] text-muted-foreground">Reading from</span>
        {connectedSources.length === 0 ? (
          <span className="text-[11px] text-muted-foreground">no connected systems</span>
        ) : (
          connectedSources.map((source) => <SourceChip key={source} source={source} />)
        )}
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

        {suggestions.length === 0 ? (
          <EmptyState
            icon={Target}
            title="No suggested questions yet"
            description="Once your systems are connected, Briefly proposes high-signal questions based on today's brief."
            actionLabel="Open Integrations"
            actionTo="/integrations"
          />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {suggestions.map((suggestion) => {
              const Icon = SUGGESTION_ICONS[suggestion.icon] ?? Target
              return (
                <button
                  key={suggestion.id}
                  type="button"
                  onClick={() => submit(suggestion.question)}
                  disabled={ask.pending}
                  className="group flex cursor-pointer items-start gap-3 rounded-xl border border-border bg-card p-4 text-left surface transition-[box-shadow,border-color] duration-200 hover:border-border-strong hover:surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40 disabled:opacity-60"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-subtle transition-colors group-hover:bg-primary-soft">
                    <Icon
                      className="h-4 w-4 text-muted-foreground transition-colors group-hover:text-primary"
                      strokeWidth={1.75}
                      aria-hidden="true"
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
        )}
      </motion.div>

      <div className="mt-10">
        <SectionHeading title="Recently asked" />
        {recent.length === 0 ? (
          <EmptyState
            icon={Clock}
            title="No recent questions"
            description="Ask something above — or pick a suggested question — and it will appear here for quick revisit."
            className="py-10"
          />
        ) : (
          <Card>
            <ul className="divide-y divide-border">
              {recent.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => submit(item.question)}
                    disabled={ask.pending}
                    className="flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-subtle focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-ring/40 disabled:opacity-60 sm:px-5"
                  >
                    <Clock
                      className="h-3.5 w-3.5 shrink-0 text-faint"
                      strokeWidth={1.75}
                      aria-hidden="true"
                    />
                    <span className="min-w-0 flex-1 truncate text-[13px] text-secondary-foreground">
                      {item.question}
                    </span>
                    <span className="shrink-0 text-[11px] text-muted-foreground">{item.askedAt}</span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  )
}
