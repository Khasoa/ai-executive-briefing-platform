import { api } from "@/api/client"

/** POST /auth/login */
export const login = (body, options) => api.post("/auth/login", body, options)

/** POST /auth/register */
export const register = (body, options) => api.post("/auth/register", body, options)

/** POST /auth/refresh — also used by the client interceptor via raw fetch */
export const refreshSession = (refreshToken, options) =>
  api.post("/auth/refresh", { refreshToken }, { ...options, skipAuth: true })

/** POST /auth/logout */
export const logout = (refreshToken, options) =>
  api.post("/auth/logout", { refreshToken }, options)

/** GET /auth/me */
export const getMe = (options) => api.get("/auth/me", options)

/** GET /auth/oauth/{provider}/start */
export const startOAuth = (provider, options) =>
  api.get(`/auth/oauth/${provider}/start`, options)

/** POST /auth/oauth/{provider}/exchange */
export const exchangeOAuthTicket = (provider, ticket, options) =>
  api.post(
    `/auth/oauth/${provider}/exchange`,
    { ticket },
    { ...options, skipAuth: true },
  )

/** GET /auth/oauth/{provider}/status */
export const getOAuthStatus = (provider, options) =>
  api.get(`/auth/oauth/${provider}/status`, options)

/** POST /auth/oauth/{provider}/disconnect */
export const disconnectOAuth = (provider, options) =>
  api.post(`/auth/oauth/${provider}/disconnect`, undefined, options)
