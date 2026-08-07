import { cn } from "@/lib/utils"

export function Logo({ className }) {
  return (
    <span
      role="img"
      aria-label="Briefly"
      className={cn(
        "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary",
        className,
      )}
    >
      <svg viewBox="0 0 32 32" className="h-8 w-8" fill="none" aria-hidden="true">
        <rect x="8" y="9" width="16" height="2" rx="1" fill="#FFFFFF" fillOpacity="0.92" />
        <rect x="8" y="15" width="11" height="2" rx="1" fill="#FFFFFF" fillOpacity="0.55" />
        <rect x="8" y="21" width="7" height="2" rx="1" fill="#D97706" />
      </svg>
    </span>
  )
}
