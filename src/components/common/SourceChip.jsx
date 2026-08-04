import { Calendar, Database, FileText, Mail, Sparkles, Workflow } from "lucide-react"
import { cn } from "@/lib/utils"

const SOURCE_ICONS = {
  Gmail: Mail,
  "Google Calendar": Calendar,
  GoHighLevel: Database,
  Notion: FileText,
  OpenAI: Sparkles,
  n8n: Workflow,
}

/**
 * Shows which connected system a piece of intelligence came from. Every AI
 * statement in Briefly is attributable, so this appears throughout.
 */
export function SourceChip({ source, detail, count, className }) {
  const Icon = SOURCE_ICONS[source] ?? Database

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-border bg-subtle px-2 py-1 text-[11px] text-secondary-foreground",
        className,
      )}
    >
      <Icon className="h-3 w-3 text-muted-foreground" strokeWidth={1.75} />
      <span className="font-medium">{source}</span>
      {detail && <span className="text-muted-foreground">· {detail}</span>}
      {typeof count === "number" && !detail && (
        <span className="text-muted-foreground numeric">· {count}</span>
      )}
    </span>
  )
}

export function SourceChipList({ sources, className }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-1.5", className)}>
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
