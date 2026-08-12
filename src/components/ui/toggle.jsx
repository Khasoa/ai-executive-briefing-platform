import { cn } from "@/lib/utils"

export function Toggle({ checked, onChange, label, disabled = false, className }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:cursor-not-allowed disabled:opacity-50",
        checked ? "bg-primary" : "bg-border-strong",
        className,
      )}
    >
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform duration-200",
          checked ? "translate-x-[1.125rem]" : "translate-x-0.5",
        )}
      />
    </button>
  )
}

/** Segmented control for small, mutually exclusive option sets. */
export function SegmentedControl({
  options,
  value,
  onChange,
  className,
  disabled = false,
  "aria-label": ariaLabel,
}) {
  return (
    <div
      role="radiogroup"
      aria-label={ariaLabel}
      aria-disabled={disabled || undefined}
      className={cn(
        "inline-flex max-w-full flex-wrap rounded-lg border border-border bg-muted p-0.5",
        disabled && "opacity-50",
        className,
      )}
    >
      {options.map((option) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={value === option}
          disabled={disabled}
          onClick={() => onChange(option)}
          className={cn(
            "cursor-pointer rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors duration-150 sm:px-3 sm:text-[13px]",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40",
            "disabled:cursor-not-allowed",
            value === option
              ? "bg-card text-foreground surface"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option}
        </button>
      ))}
    </div>
  )
}
