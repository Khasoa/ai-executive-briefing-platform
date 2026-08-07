import { useCallback, useEffect, useRef, useState } from "react"
import { classifyError } from "@/lib/errors"

/**
 * Runs a one-off mutation (sync, regenerate, ask) with pending and error state.
 * Actions are always user-initiated — Briefly never fires one on its own.
 *
 * `run` resolves to `{ data, error }` so callers can toast without waiting for
 * a re-render to observe the error state.
 */
export function useAsyncAction(action) {
  const actionRef = useRef(action)
  useEffect(() => {
    actionRef.current = action
  })

  const [pending, setPending] = useState(false)
  const [error, setError] = useState(null)

  const run = useCallback(async (...args) => {
    setPending(true)
    setError(null)
    try {
      const data = await actionRef.current(...args)
      return { data, error: null }
    } catch (caught) {
      if (caught?.name === "AbortError") return { data: null, error: null, aborted: true }
      const classified = classifyError(caught)
      setError(classified)
      return { data: null, error: classified }
    } finally {
      setPending(false)
    }
  }, [])

  return { run, pending, error, clearError: () => setError(null) }
}
