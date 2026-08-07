/**
 * Classify API failures into UX-friendly recovery copy.
 * Status 0 = network / timeout / unreachable (see api/client.js).
 */

export function classifyError(error) {
  const message = error?.message ?? String(error ?? "Something went wrong.")
  const status = typeof error?.status === "number" ? error.status : undefined
  const lower = message.toLowerCase()

  if (status === 0 || lower.includes("cannot reach") || lower.includes("failed to fetch")) {
    return {
      kind: "network",
      title: "You appear to be offline",
      message: "Briefly could not reach the server. Check your connection, then try again.",
      detail: message,
    }
  }

  if (lower.includes("timed out") || lower.includes("timeout")) {
    return {
      kind: "timeout",
      title: "That took too long",
      message: "The server did not respond in time. Your data may still be loading — try again.",
      detail: message,
    }
  }

  if (status != null && status >= 500) {
    return {
      kind: "server",
      title: "Something went wrong on our side",
      message: "Briefly hit a server error. Wait a moment, then try again.",
      detail: message,
    }
  }

  if (status === 404) {
    return {
      kind: "not-found",
      title: "Nothing was found",
      message: message || "That item is no longer available.",
      detail: message,
    }
  }

  if (status === 409) {
    return {
      kind: "conflict",
      title: "That action is not available yet",
      message: message || "The system is not ready for this action.",
      detail: message,
    }
  }

  return {
    kind: "request",
    title: "Briefly could not load this page",
    message: message || "Something went wrong. Try again in a moment.",
    detail: message,
  }
}
