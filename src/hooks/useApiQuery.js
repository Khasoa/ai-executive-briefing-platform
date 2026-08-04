import { useCallback, useEffect, useRef, useState } from "react"

/**
 * Fetches server state for a page.
 *
 * `fetcher` receives `{ signal }`, so an in-flight request is aborted when the
 * page unmounts or refetches. `setData` lets a page apply the result of a
 * mutation without a full round trip.
 */
export function useApiQuery(fetcher) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const controllerRef = useRef(null)

  const refetch = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setLoading(true)
    setError(null)

    try {
      const result = await fetcher({ signal: controller.signal })
      if (controller.signal.aborted) return
      setData(result)
    } catch (caught) {
      if (caught.name === "AbortError") return
      setError(caught.message ?? "Something went wrong.")
      setData(null)
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [fetcher])

  useEffect(() => {
    refetch()
    return () => controllerRef.current?.abort()
  }, [refetch])

  return { data, loading, error, refetch, setData }
}
