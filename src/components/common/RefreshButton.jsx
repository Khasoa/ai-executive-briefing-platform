import { Loader2, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

export function RefreshButton({ onClick, refreshing = false, label = "Refresh", className }) {
  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      className={className}
      onClick={onClick}
      disabled={refreshing}
      aria-label={refreshing ? "Refreshing" : label}
    >
      {refreshing ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.75} aria-hidden="true" />
      ) : (
        <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
      )}
      <span className="max-sm:sr-only">{label}</span>
    </Button>
  )
}
