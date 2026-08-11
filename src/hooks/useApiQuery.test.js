import { act, renderHook, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { useApiQuery } from "@/hooks/useApiQuery"

describe("useApiQuery", () => {
  it("shows loading on first fetch, then success data", async () => {
    const fetcher = vi.fn().mockResolvedValue({ title: "Overview" })
    const { result } = renderHook(() => useApiQuery(fetcher))

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()

    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.data).toEqual({ title: "Overview" })
    expect(result.current.refreshing).toBe(false)
  })

  it("keeps existing data visible during soft refresh", async () => {
    let resolveSecond
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ title: "First" })
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveSecond = resolve
          }),
      )

    const { result } = renderHook(() => useApiQuery(fetcher))
    await waitFor(() => expect(result.current.data).toEqual({ title: "First" }))

    act(() => {
      void result.current.refetch()
    })

    await waitFor(() => expect(result.current.refreshing).toBe(true))
    expect(result.current.loading).toBe(false)
    expect(result.current.data).toEqual({ title: "First" })

    await act(async () => {
      resolveSecond({ title: "Second" })
    })

    await waitFor(() => expect(result.current.data).toEqual({ title: "Second" }))
    expect(result.current.refreshing).toBe(false)
    expect(result.current.loading).toBe(false)
  })

  it("keeps last good data when a soft refresh fails", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ title: "Good" })
      .mockRejectedValueOnce(Object.assign(new Error("down"), { status: 500 }))

    const { result } = renderHook(() => useApiQuery(fetcher))
    await waitFor(() => expect(result.current.data).toEqual({ title: "Good" }))

    await act(async () => {
      await result.current.refetch()
    })

    expect(result.current.data).toEqual({ title: "Good" })
    expect(result.current.error).toBeNull()
    expect(result.current.refreshError?.kind).toBe("server")
    expect(result.current.loading).toBe(false)
  })
})
