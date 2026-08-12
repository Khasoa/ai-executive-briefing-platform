import { useCallback, useEffect, useMemo, useState } from "react"
import {
  disconnectOAuth,
  exchangeOAuthTicket,
  getMe,
  getOAuthStatus,
  login as loginRequest,
  logout as logoutRequest,
  register as registerRequest,
  startOAuth,
} from "@/api/auth"
import { setAuthFailureHandler } from "@/api/client"
import { AuthContext } from "@/auth/auth-context"
import {
  clearSession,
  getCachedUser,
  getRefreshToken,
  setCachedUser,
  setSession,
} from "@/lib/auth-storage"
import {
  loadAndApplyTheme,
  persistTheme,
  watchSystemTheme,
} from "@/lib/theme"

function applyTokenResponse(data) {
  setSession({
    accessToken: data.accessToken,
    refreshToken: data.refreshToken,
    user: data.user,
  })
  return data.user
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getCachedUser())
  const [googleStatus, setGoogleStatus] = useState(null)
  const [notionStatus, setNotionStatus] = useState(null)
  const [ghlStatus, setGhlStatus] = useState(null)
  const [mondayStatus, setMondayStatus] = useState(null)
  const [clickupStatus, setClickupStatus] = useState(null)
  const [restoring, setRestoring] = useState(true)
  const [theme, setThemeState] = useState(() => loadAndApplyTheme())

  const refreshGoogleStatus = useCallback(async () => {
    try {
      const status = await getOAuthStatus("google")
      setGoogleStatus(status)
      return status
    } catch {
      setGoogleStatus(null)
      return null
    }
  }, [])

  const refreshNotionStatus = useCallback(async () => {
    try {
      const status = await getOAuthStatus("notion")
      setNotionStatus(status)
      return status
    } catch {
      setNotionStatus(null)
      return null
    }
  }, [])

  const refreshGhlStatus = useCallback(async () => {
    try {
      const status = await getOAuthStatus("gohighlevel")
      setGhlStatus(status)
      return status
    } catch {
      setGhlStatus(null)
      return null
    }
  }, [])

  const refreshMondayStatus = useCallback(async () => {
    try {
      const status = await getOAuthStatus("monday")
      setMondayStatus(status)
      return status
    } catch {
      setMondayStatus(null)
      return null
    }
  }, [])

  const refreshClickupStatus = useCallback(async () => {
    try {
      const status = await getOAuthStatus("clickup")
      setClickupStatus(status)
      return status
    } catch {
      setClickupStatus(null)
      return null
    }
  }, [])

  const refreshProviderStatuses = useCallback(async () => {
    await Promise.all([
      refreshGoogleStatus(),
      refreshNotionStatus(),
      refreshGhlStatus(),
      refreshMondayStatus(),
      refreshClickupStatus(),
    ])
  }, [
    refreshGoogleStatus,
    refreshNotionStatus,
    refreshGhlStatus,
    refreshMondayStatus,
    refreshClickupStatus,
  ])

  const completeSession = useCallback(
    async (tokenResponse) => {
      const nextUser = applyTokenResponse(tokenResponse)
      setUser(nextUser)
      await refreshProviderStatuses()
      return nextUser
    },
    [refreshProviderStatuses],
  )

  const clearAuth = useCallback(() => {
    clearSession()
    setUser(null)
    setGoogleStatus(null)
    setNotionStatus(null)
    setGhlStatus(null)
    setMondayStatus(null)
    setClickupStatus(null)
  }, [])

  useEffect(() => {
    setAuthFailureHandler(() => {
      clearAuth()
    })
    return () => setAuthFailureHandler(null)
  }, [clearAuth])

  useEffect(() => {
    let cancelled = false

    async function restore() {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        if (!cancelled) {
          setUser(null)
          setRestoring(false)
        }
        return
      }

      try {
        const me = await getMe()
        if (cancelled) return
        setUser(me)
        setSession({ user: me })
        await refreshProviderStatuses()
      } catch {
        if (!cancelled) clearAuth()
      } finally {
        if (!cancelled) setRestoring(false)
      }
    }

    restore()
    return () => {
      cancelled = true
    }
  }, [clearAuth, refreshProviderStatuses])

  useEffect(() => watchSystemTheme(() => theme), [theme])

  const login = useCallback(
    async ({ email, password }) => {
      const data = await loginRequest({ email, password })
      return completeSession(data)
    },
    [completeSession],
  )

  const register = useCallback(
    async (payload) => {
      const data = await registerRequest(payload)
      return completeSession(data)
    },
    [completeSession],
  )

  const logout = useCallback(async () => {
    const refreshToken = getRefreshToken()
    try {
      if (refreshToken) await logoutRequest(refreshToken)
    } catch {
      // Still clear local session even if the revoke call fails.
    }
    clearAuth()
  }, [clearAuth])

  const beginOAuth = useCallback(async (provider) => {
    const { authorizationUrl } = await startOAuth(provider)
    window.location.assign(authorizationUrl)
  }, [])

  const beginGoogleOAuth = useCallback(async () => beginOAuth("google"), [beginOAuth])
  const beginNotionOAuth = useCallback(async () => beginOAuth("notion"), [beginOAuth])
  const beginGhlOAuth = useCallback(async () => beginOAuth("gohighlevel"), [beginOAuth])
  const beginMondayOAuth = useCallback(async () => beginOAuth("monday"), [beginOAuth])
  const beginClickupOAuth = useCallback(async () => beginOAuth("clickup"), [beginOAuth])

  const finishOAuth = useCallback(
    async (provider, ticket) => {
      const data = await exchangeOAuthTicket(provider, ticket)
      const nextUser = applyTokenResponse(data)
      setUser(nextUser)
      // Refresh only the provider that completed OAuth — never fan out status
      // mutations that could make unrelated cards look freshly connected.
      const p = (provider || "").toLowerCase()
      if (p === "google") await refreshGoogleStatus()
      else if (p === "notion") await refreshNotionStatus()
      else if (p === "gohighlevel") await refreshGhlStatus()
      else if (p === "monday") await refreshMondayStatus()
      else if (p === "clickup") await refreshClickupStatus()
      return nextUser
    },
    [
      refreshGoogleStatus,
      refreshNotionStatus,
      refreshGhlStatus,
      refreshMondayStatus,
      refreshClickupStatus,
    ],
  )

  const finishGoogleOAuth = useCallback(
    async (ticket) => finishOAuth("google", ticket),
    [finishOAuth],
  )

  const disconnectGoogle = useCallback(async () => {
    const status = await disconnectOAuth("google")
    setGoogleStatus(status)
    return status
  }, [])

  const disconnectNotion = useCallback(async () => {
    const status = await disconnectOAuth("notion")
    setNotionStatus(status)
    return status
  }, [])

  const disconnectGhl = useCallback(async () => {
    const status = await disconnectOAuth("gohighlevel")
    setGhlStatus(status)
    return status
  }, [])

  const disconnectMonday = useCallback(async () => {
    const status = await disconnectOAuth("monday")
    setMondayStatus(status)
    return status
  }, [])

  const disconnectClickup = useCallback(async () => {
    const status = await disconnectOAuth("clickup")
    setClickupStatus(status)
    return status
  }, [])

  const setTheme = useCallback((mode) => {
    setThemeState(persistTheme(mode))
  }, [])

  const updateUser = useCallback((nextUser) => {
    if (!nextUser) return null
    setCachedUser(nextUser)
    setUser(nextUser)
    return nextUser
  }, [])

  const value = useMemo(
    () => ({
      user,
      restoring,
      isAuthenticated: Boolean(user),
      googleStatus,
      notionStatus,
      ghlStatus,
      mondayStatus,
      clickupStatus,
      theme,
      setTheme,
      updateUser,
      login,
      register,
      logout,
      beginOAuth,
      beginGoogleOAuth,
      beginNotionOAuth,
      beginGhlOAuth,
      beginMondayOAuth,
      beginClickupOAuth,
      finishOAuth,
      finishGoogleOAuth,
      disconnectGoogle,
      disconnectNotion,
      disconnectGhl,
      disconnectMonday,
      disconnectClickup,
      refreshGoogleStatus,
      refreshNotionStatus,
      refreshGhlStatus,
      refreshMondayStatus,
      refreshClickupStatus,
    }),
    [
      user,
      restoring,
      googleStatus,
      notionStatus,
      ghlStatus,
      mondayStatus,
      clickupStatus,
      theme,
      setTheme,
      updateUser,
      login,
      register,
      logout,
      beginOAuth,
      beginGoogleOAuth,
      beginNotionOAuth,
      beginGhlOAuth,
      beginMondayOAuth,
      beginClickupOAuth,
      finishOAuth,
      finishGoogleOAuth,
      disconnectGoogle,
      disconnectNotion,
      disconnectGhl,
      disconnectMonday,
      disconnectClickup,
      refreshGoogleStatus,
      refreshNotionStatus,
      refreshGhlStatus,
      refreshMondayStatus,
      refreshClickupStatus,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export { useAuth } from "@/auth/useAuth"
