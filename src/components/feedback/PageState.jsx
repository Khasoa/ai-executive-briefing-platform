import { AlertTriangle, Inbox, RefreshCw, WifiOff, X } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { buttonVariants } from "@/components/ui/button-variants"
import { cn } from "@/lib/utils"

export function PageError({ error, message, onRetry }) {
  const title = error?.title ?? "Briefly could not reach your data"
  const body = error?.message ?? message ?? "Something went wrong."
  const Icon = error?.kind === "network" ? WifiOff : AlertTriangle

  return (
    <div className="mx-auto max-w-lg px-4 py-16 sm:px-6 sm:py-24">
      <Card className="text-center">
        <div className="flex flex-col items-center gap-4 px-6 py-10 sm:px-8">
          <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-critical-soft">
            <Icon className="h-[18px] w-[18px] text-critical" strokeWidth={1.75} aria-hidden="true" />
          </span>
          <div>
            <p className="text-[15px] font-semibold">{title}</p>
            <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">{body}</p>
          </div>
          {onRetry && (
            <Button onClick={onRetry} size="sm" className="gap-1.5">
              <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
              Try again
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}

export function RefreshBanner({ error, onRetry, onDismiss }) {
  if (!error) return null

  return (
    <div
      className="mb-5 flex flex-col gap-3 rounded-xl border border-accent/25 bg-accent-soft px-4 py-3 sm:flex-row sm:items-center"
      role="alert"
    >
      <div className="min-w-0 flex-1">
        <p className="text-[13px] font-medium text-foreground">{error.title}</p>
        <p className="mt-0.5 text-[12px] leading-relaxed text-secondary-foreground">
          {error.message} Showing the last successful load.
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {onRetry && (
          <Button size="sm" variant="secondary" onClick={onRetry} className="gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            Retry
          </Button>
        )}
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className="cursor-pointer rounded-md p-1.5 text-faint transition-colors hover:bg-card hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40"
            aria-label="Dismiss"
          >
            <X className="h-3.5 w-3.5" strokeWidth={1.75} />
          </button>
        )}
      </div>
    </div>
  )
}

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  actionLabel,
  actionTo,
  className,
}) {
  const resolvedAction =
    action ??
    (actionLabel && actionTo ? (
      <Link to={actionTo} className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}>
        {actionLabel}
      </Link>
    ) : null)

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-subtle px-6 py-12 text-center sm:px-8 sm:py-14",
        className,
      )}
      role="status"
    >
      <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-card surface">
        <Icon className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} aria-hidden="true" />
      </span>
      <p className="text-[14px] font-medium text-foreground">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-[13px] leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
      {resolvedAction && <div className="mt-4">{resolvedAction}</div>}
    </div>
  )
}

function HeaderSkeleton() {
  return (
    <div className="mb-8 space-y-3">
      <Skeleton className="h-3 w-28 sm:w-40" />
      <Skeleton className="h-8 w-48 sm:w-72" />
      <Skeleton className="h-4 w-full max-w-md sm:max-w-96" />
    </div>
  )
}

export function OverviewSkeleton() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-10" aria-busy="true" aria-label="Loading overview">
      <HeaderSkeleton />
      <Skeleton className="mb-6 h-64 w-full sm:h-80" />
      <div className="mb-8 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-24" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Skeleton className="h-64 lg:col-span-2 sm:h-80" />
        <Skeleton className="h-64 sm:h-80" />
      </div>
    </div>
  )
}

export function ListSkeleton({ rows = 5, maxWidth = "max-w-5xl" }) {
  return (
    <div
      className={cn("mx-auto px-4 py-8 sm:px-6 lg:px-10", maxWidth)}
      aria-busy="true"
      aria-label="Loading"
    >
      <HeaderSkeleton />
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <Skeleton key={index} className="h-24 w-full sm:h-28" />
        ))}
      </div>
    </div>
  )
}

export function DocumentSkeleton() {
  return (
    <div
      className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-10"
      aria-busy="true"
      aria-label="Loading morning brief"
    >
      <HeaderSkeleton />
      <Skeleton className="mb-6 h-40 w-full sm:h-48" />
      <div className="space-y-6">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="space-y-3">
            <Skeleton className="h-4 w-40 sm:w-48" />
            <Skeleton className="h-24 w-full" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function AskSkeleton() {
  return (
    <div
      className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-10"
      aria-busy="true"
      aria-label="Loading Ask Briefly"
    >
      <HeaderSkeleton />
      <Skeleton className="mb-8 h-28 w-full" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-20" />
        ))}
      </div>
    </div>
  )
}
