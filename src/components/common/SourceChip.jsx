import { Calendar, Database, FileText, Mail, Sparkles, Workflow } from "lucide-react"
import { cn } from "@/lib/utils"

const SOURCE_ICONS = {
  Gmail: Mail,
  "Google Calendar": Calendar,
  GoHighLevel: Database,
  Notion: FileText,
  "monday.com": Workflow,
  ClickUp: Workflow,
  OpenAI: Sparkles,
  n8n: Workflow,
}

/**
 * Shows which connected system a piece of intelligence came from. Kept quiet so
 * attribution never competes with the recommendation itself.
 */
export function SourceChip({ source, detail, count, className }) {
  const Icon = SOURCE_ICONS[source] ?? Database

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] text-faint",
        className,
      )}
    >
      <Icon className="h-3 w-3 shrink-0" strokeWidth={1.75} aria-hidden="true" />
      <span>{source}</span>
      {detail && <span>· {detail}</span>}
      {typeof count === "number" && !detail && (
        <span className="numeric">· {count}</span>
      )}
    </span>
  )
}

export function SourceChipList({ sources, className }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-1", className)}>
      {sources.map((source) =>
        typeof source === "string" ? (
          <SourceChip key={source} source={source} />
        ) : (
          <SourceChip
            key={`${source.source}-${source.detail}`}
            source={source.source}
            detail={source.detail}
            count={source.count}
          />
        ),
      )}
    </div>
  )
}
