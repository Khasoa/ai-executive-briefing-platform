import { cn } from "@/lib/utils"

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        "h-9 w-full rounded-lg border border-border bg-card px-3 text-[13px] text-foreground transition-colors placeholder:text-faint focus:border-primary-ring/40 focus:outline-none focus:ring-2 focus:ring-primary-ring/15 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground",
        className,
      )}
      {...props}
    />
  )
}

export function Textarea({ className, ...props }) {
  return (
    <textarea
      className={cn(
        "w-full resize-none rounded-lg border border-border bg-card px-3 py-2.5 text-sm leading-relaxed text-foreground transition-colors placeholder:text-faint focus:border-primary-ring/40 focus:outline-none focus:ring-2 focus:ring-primary-ring/15",
        className,
      )}
      {...props}
    />
  )
}

export function Field({ label, hint, children, className }) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1.5 block text-[13px] font-medium text-secondary-foreground">{label}</span>
      {children}
      {hint && <span className="mt-1.5 block text-xs text-muted-foreground">{hint}</span>}
    </label>
  )
}
