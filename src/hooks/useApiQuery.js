import { useCallback, useEffect, useRef, useState } from "react"
import { classifyError } from "@/lib/errors"

/**
 * Fetches server state for a page.
 *
 * Initial load shows a skeleton (`loading`). Later refreshes keep the current
 * view (`refreshing`) so the page does not flash blank. Failed refreshes keep
 * the last good payload and expose `refreshError` instead of wiping the page.
 */
export function useApiQuery(fetcher) {
  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  })

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [refreshError, setRefreshError] = useState(null)
  const dataRef = useRef(null)
  const controllerRef = useRef(null)

  const refetch = useCallback(async () => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    const hasData = dataRef.current != null
    if (hasData) {
      setRefreshing(true)
      setRefreshError(null)
    } else {
      setLoading(true)
      setError(null)
    }

    try {
      const result = await fetcherRef.current({ signal: controller.signal })
      if (controller.signal.aborted) return
      dataRef.current = result
      setData(result)
      setError(null)
      setRefreshError(null)
    } catch (caught) {
      if (caught?.name === "AbortError") return
      const classified = classifyError(caught)
      if (hasData) {
        setRefreshError(classified)
      } else {
        setError(classified)
        dataRef.current = null
        setData(null)
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
        setRefreshing(false)
      }
    }
  }, [])

  useEffect(() => {
    refetch()
    return () => controllerRef.current?.abort()
  }, [refetch])

  const updateData = useCallback((value) => {
    setData((current) => {
      const next = typeof value === "function" ? value(current) : value
      dataRef.current = next
      return next
    })
  }, [])

  return {
    data,
    loading,
    refreshing,
    error,
    refreshError,
    refetch,
    setData: updateData,
    clearRefreshError: () => setRefreshError(null),
  }
}
