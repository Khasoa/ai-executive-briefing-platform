import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { api, ApiError } from "@/api/client"
import { clearSession, setSession } from "@/lib/auth-storage"

describe("api client auth", () => {
  beforeEach(() => {
    localStorage.clear()
    vi.stubGlobal("fetch", vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    clearSession()
  })

  it("attaches Bearer access token", async () => {
    setSession({ accessToken: "tok-123", refreshToken: "ref", user: { email: "a@b.com" } })
    fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ ok: true }),
    })

    await api.get("/auth/me")
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/auth/me"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer tok-123" }),
      }),
    )
  })

  it("refreshes on 401 and retries", async () => {
    setSession({ accessToken: "old", refreshToken: "ref-1", user: { email: "a@b.com" } })

    fetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "expired" }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          accessToken: "new-access",
          refreshToken: "new-refresh",
          user: { email: "a@b.com", fullName: "A" },
        }),
        text: async () =>
          JSON.stringify({
            accessToken: "new-access",
            refreshToken: "new-refresh",
            user: { email: "a@b.com", fullName: "A" },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ email: "a@b.com" }),
      })

    const me = await api.get("/auth/me")
    expect(me).toEqual({ email: "a@b.com" })
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(localStorage.getItem("briefly.accessToken")).toBe("new-access")
  })

  it("throws ApiError when refresh fails", async () => {
    setSession({ accessToken: "old", refreshToken: "ref-1", user: { email: "a@b.com" } })

    fetch
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "expired" }),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "invalid refresh" }),
      })

    await expect(api.get("/workspace")).rejects.toBeInstanceOf(ApiError)
    expect(localStorage.getItem("briefly.accessToken")).toBeNull()
  })
})
