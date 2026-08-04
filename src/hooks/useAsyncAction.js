import { useCallback, useState } from "react"

/**
 * Runs a one-off mutation (sync, regenerate, ask) with pending and error state.
 * Actions are always user-initiated — Briefly never fires one on its own.
 */
export function useAsyncAction(action) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState(null)

  const run = useCallback(
    async (...args) => {
      setPending(true)
      setError(null)
      try {
        return await action(...args)
      } catch (caught) {
        setError(caught.message ?? "That action could not be completed.")
        return null
      } finally {
        setPending(false)
      }
    },
    [action],
  )

  return { run, pending, error }
}
