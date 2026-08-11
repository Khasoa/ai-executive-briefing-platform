const ACCESS_KEY = "briefly.accessToken"
const REFRESH_KEY = "briefly.refreshToken"
const USER_KEY = "briefly.user"
const THEME_KEY = "briefly.theme"

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function getCachedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function setSession({ accessToken, refreshToken, user }) {
  if (accessToken) localStorage.setItem(ACCESS_KEY, accessToken)
  if (refreshToken) localStorage.setItem(REFRESH_KEY, refreshToken)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function setCachedUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
  else localStorage.removeItem(USER_KEY)
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getThemePreference() {
  return localStorage.getItem(THEME_KEY) || "System"
}

export function setThemePreference(mode) {
  localStorage.setItem(THEME_KEY, mode)
}
