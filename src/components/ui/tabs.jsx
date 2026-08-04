import { cn } from "@/lib/utils"

/**
 * Controlled tab bar. Each tab is `{ id, label, count }`; `count` is optional.
 */
export function Tabs({ tabs, value, onChange, className }) {
  return (
    <div
      role="tablist"
      className={cn("flex flex-wrap items-center gap-1 border-b border-border", className)}
    >
      {tabs.map((tab) => {
        const active = tab.id === value
        return (
          <button
            key={tab.id}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            className={cn(
              "-mb-px cursor-pointer border-b-2 px-3 py-2.5 text-[13px] font-medium transition-colors duration-150",
              active
                ? "border-primary text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
            {typeof tab.count === "number" && (
              <span
                className={cn(
                  "ml-2 rounded px-1.5 py-0.5 text-[11px] numeric",
                  active ? "bg-primary-soft text-primary" : "bg-muted text-muted-foreground",
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
