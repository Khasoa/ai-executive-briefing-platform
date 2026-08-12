/**
 * Shared vocabulary for urgency, severity and priority.
 *
 * The API speaks in four levels everywhere (critical / high / medium / low), so
 * every card renders them through this single mapping rather than inventing its
 * own colours.
 */

export const SIGNAL_LABEL = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
}

export const SIGNAL_BADGE = {
  critical: "critical",
  high: "accent",
  medium: "neutral",
  low: "quiet",
}

export const SIGNAL_ACCENT_BAR = {
  critical: "bg-critical",
  high: "bg-accent-strong",
  medium: "bg-neutral/50",
  low: "bg-border-strong",
}

export const SIGNAL_DOT = {
  critical: "bg-critical",
  high: "bg-accent-strong",
  medium: "bg-neutral",
  low: "bg-faint",
}

/** Ordered so lists can sort by "what matters most" without duplicating logic. */
export const SIGNAL_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

/** Badges only for levels that need executive attention — colour bars cover the rest. */
export function isElevatedSignal(level) {
  return level === "critical" || level === "high"
}

export function bySignal(key = "priority") {
  return (a, b) => (SIGNAL_ORDER[a[key]] ?? 9) - (SIGNAL_ORDER[b[key]] ?? 9)
}
