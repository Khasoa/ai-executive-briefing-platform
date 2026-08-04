import { cn } from "@/lib/utils"

const tones = {
  primary: "bg-primary",
  accent: "bg-accent-strong",
  critical: "bg-critical",
  neutral: "bg-neutral",
}

export function Progress({ value, tone = "primary", className, label }) {
  const clamped = Math.max(0, Math.min(100, value))

  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn("h-1 w-full overflow-hidden rounded-full bg-muted", className)}
    >
      <div
        className={cn("h-full rounded-full transition-[width] duration-500", tones[tone])}
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}
