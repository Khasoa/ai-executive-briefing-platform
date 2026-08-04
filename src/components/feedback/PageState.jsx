import { AlertTriangle, Inbox, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export function PageError({ message, onRetry }) {
  return (
    <div className="mx-auto max-w-lg px-6 py-24">
      <Card className="text-center">
        <div className="flex flex-col items-center gap-4 px-8 py-10">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-critical-soft">
            <AlertTriangle className="h-[18px] w-[18px] text-critical" strokeWidth={1.75} />
          </span>
          <div>
            <p className="text-[15px] font-semibold">Briefly could not reach your data</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{message}</p>
          </div>
          <Button onClick={onRetry} size="sm" className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} />
            Try again
          </Button>
        </div>
      </Card>
    </div>
  )
}

export function EmptyState({ title, description, icon: Icon = Inbox, action, className }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-subtle px-8 py-14 text-center",
        className,
      )}
    >
      <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-card surface">
        <Icon className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
      </span>
      <p className="text-[14px] font-medium text-foreground">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-[13px] leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

function HeaderSkeleton() {
  return (
    <div className="mb-8 space-y-3">
      <Skeleton className="h-3 w-40" />
      <Skeleton className="h-8 w-72" />
      <Skeleton className="h-4 w-96" />
    </div>
  )
}

export function OverviewSkeleton() {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <HeaderSkeleton />
      <Skeleton className="mb-6 h-80 w-full" />
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-32" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Skeleton className="h-80 lg:col-span-2" />
        <Skeleton className="h-80" />
      </div>
    </div>
  )
}

export function ListSkeleton({ rows = 5, maxWidth = "max-w-5xl" }) {
  return (
    <div className={cn("mx-auto px-6 py-8 lg:px-10", maxWidth)}>
      <HeaderSkeleton />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
    </div>
  )
}

export function DocumentSkeleton() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <HeaderSkeleton />
      <Skeleton className="mb-6 h-48 w-full" />
      <div className="space-y-6">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="space-y-3">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-24 w-full" />
          </div>
        ))}
      </div>
    </div>
  )
}
