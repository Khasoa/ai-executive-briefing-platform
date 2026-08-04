import { cn } from "@/lib/utils"

export function Skeleton({ className, ...props }) {
  return <div className={cn("shimmer rounded-lg bg-muted", className)} {...props} />
}
