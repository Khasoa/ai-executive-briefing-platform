import { cn } from "@/lib/utils"

export function Card({ className, interactive = false, ...props }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card text-foreground surface",
        interactive &&
          "transition-[box-shadow,border-color] duration-200 hover:border-border-strong hover:surface-raised",
        className,
      )}
      {...props}
    />
  )
}
