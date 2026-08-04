import { CalendarClock, FileText, Mail, Target } from "lucide-react"
import { Card } from "@/components/ui/card"
import { SourceChip } from "@/components/common/SourceChip"

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
            <li key={item.id} className="flex items-start gap-3 px-5 py-3.5">
              <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-muted">
                <Icon className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium leading-snug">{item.title}</p>
                <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">
                  {item.detail}
                </p>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="text-[11px] text-faint numeric">{item.time}</span>
                  <SourceChip source={item.source} className="border-transparent bg-transparent px-0" />
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
