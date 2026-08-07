import { CalendarClock, FileText, Mail, Target } from "lucide-react"
import { Card } from "@/components/ui/card"

const ICONS = {
  email: Mail,
  deal: Target,
  document: FileText,
  meeting: CalendarClock,
}

export function ActivityFeed({ items }) {
  return (
    <Card>
      <ul className="divide-y divide-border">
        {items.map((item) => {
          const Icon = ICONS[item.type] ?? Mail
          return (
            <li key={item.id} className="flex items-start gap-2.5 px-3.5 py-3 sm:px-4">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted">
                <Icon className="h-3 w-3 text-faint" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium leading-snug">{item.title}</p>
                <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                  {item.detail}
                </p>
                <p className="mt-1 text-[11px] text-faint">
                  <span className="numeric">{item.time}</span>
                  <span className="mx-1.5 text-border-strong">·</span>
                  {item.source}
                </p>
              </div>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
