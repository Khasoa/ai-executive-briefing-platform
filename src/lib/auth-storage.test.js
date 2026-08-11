import { beforeEach, describe, expect, it } from "vitest"
import {
  clearSession,
  getAccessToken,
  getCachedUser,
  getRefreshToken,
  getThemePreference,
  setSession,
  setThemePreference,
} from "@/lib/auth-storage"

describe("auth-storage", () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it("stores and clears session tokens and user", () => {
    setSession({
      accessToken: "access",
      refreshToken: "refresh",
      user: { email: "a@b.com", fullName: "A" },
    })
    expect(getAccessToken()).toBe("access")
    expect(getRefreshToken()).toBe("refresh")
    expect(getCachedUser()).toEqual({ email: "a@b.com", fullName: "A" })

    clearSession()
    expect(getAccessToken()).toBeNull()
    expect(getRefreshToken()).toBeNull()
    expect(getCachedUser()).toBeNull()
  })

  it("persists theme preference", () => {
    expect(getThemePreference()).toBe("System")
    setThemePreference("Dark")
    expect(getThemePreference()).toBe("Dark")
  })
})
