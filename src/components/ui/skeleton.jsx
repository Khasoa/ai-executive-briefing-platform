import { cn } from "@/lib/utils"

/**
 * Theme-aware loading placeholder.
 * Relies on `.shimmer` + `--color-muted` / `--color-border` so dark mode
 * never falls back to hard-coded light greys.
 */
export function Skeleton({ className, ...props }) {
  return (
    <div
      className={cn("shimmer rounded-lg bg-muted", className)}
      data-testid="skeleton"
      aria-hidden="true"
      {...props}
    />
  )
}
