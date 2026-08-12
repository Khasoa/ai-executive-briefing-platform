import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { AuthProvider } from "@/auth/AuthContext"
import { useAuth } from "@/auth/useAuth"
import { clearSession, setSession } from "@/lib/auth-storage"

vi.mock("@/api/auth", () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(async () => null),
  getMe: vi.fn(),
  getOAuthStatus: vi.fn(async () => ({ connected: false, configured: true, provider: "google" })),
  startOAuth: vi.fn(),
  exchangeOAuthTicket: vi.fn(),
  disconnectOAuth: vi.fn(),
}))

import { getMe, login, logout, startOAuth } from "@/api/auth"

function Probe() {
  const { user, restoring, logout: signOut, isAuthenticated } = useAuth()
  if (restoring) return <p>restoring</p>
  return (
    <div>
      <p>{isAuthenticated ? user.email : "signed-out"}</p>
      <button type="button" onClick={() => signOut()}>
        logout
      </button>
    </div>
  )
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it("restores session via /auth/me when refresh token exists", async () => {
    setSession({
      accessToken: "a",
      refreshToken: "r",
      user: { email: "cached@example.com", fullName: "Cached" },
    })
    getMe.mockResolvedValueOnce({
      email: "live@example.com",
      fullName: "Live",
      avatar: "L",
      role: "CEO",
      company: "Co",
      name: "Live",
      timezone: "UTC",
    })

    render(
      <MemoryRouter>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </MemoryRouter>,
    )

    expect(screen.getByText("restoring")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText("live@example.com")).toBeInTheDocument())
  })

  it("logs out and clears session", async () => {
    const user = userEvent.setup()
    setSession({
      accessToken: "a",
      refreshToken: "r",
      user: { email: "a@example.com", fullName: "A" },
    })
    getMe.mockResolvedValueOnce({
      email: "a@example.com",
      fullName: "A",
      avatar: "A",
      role: "CEO",
      company: "Co",
      name: "A",
      timezone: "UTC",
    })

    render(
      <MemoryRouter>
        <AuthProvider>
          <Probe />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText("a@example.com")).toBeInTheDocument())
    await user.click(screen.getByRole("button", { name: "logout" }))
    await waitFor(() => expect(screen.getByText("signed-out")).toBeInTheDocument())
    expect(logout).toHaveBeenCalled()
    expect(localStorage.getItem("briefly.refreshToken")).toBeNull()
  })

  it("login stores tokens through auth API", async () => {
    login.mockResolvedValueOnce({
      accessToken: "acc",
      refreshToken: "ref",
      user: {
        email: "new@example.com",
        fullName: "New",
        avatar: "N",
        role: "CEO",
        company: "Co",
        name: "New",
        timezone: "UTC",
      },
    })
    getMe.mockRejectedValueOnce(new Error("no session"))

    function LoginProbe() {
      const { login: doLogin, user, restoring } = useAuth()
      if (restoring) return <p>restoring</p>
      return (
        <div>
          <button
            type="button"
            onClick={() => doLogin({ email: "new@example.com", password: "password1" })}
          >
            sign-in
          </button>
          <p>{user?.email ?? "none"}</p>
        </div>
      )
    }

    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginProbe />
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText("none")).toBeInTheDocument())
    await user.click(screen.getByRole("button", { name: "sign-in" }))
    await waitFor(() => expect(screen.getByText("new@example.com")).toBeInTheDocument())
    expect(localStorage.getItem("briefly.accessToken")).toBe("acc")
  })
})

describe("Protected routing smoke", () => {
  it("shows login route when unauthenticated", async () => {
    clearSession()
    getMe.mockRejectedValue(new Error("nope"))

    function Login() {
      return <p>login-page</p>
    }
    function Home() {
      return <p>home-page</p>
    }

    const { ProtectedRoute, PublicOnlyRoute } = await import("@/auth/ProtectedRoute")

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AuthProvider>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="login" element={<Login />} />
            </Route>
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Home />} />
            </Route>
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    )

    await waitFor(() => expect(screen.getByText("login-page")).toBeInTheDocument())
  })
})

function OAuthStartProbe() {
  const { beginOAuth, beginNotionOAuth, beginClickupOAuth, restoring } = useAuth()
  if (restoring) return <p>restoring</p>
  return (
    <div>
      <button type="button" onClick={() => beginNotionOAuth()}>
        start-notion
      </button>
      <button type="button" onClick={() => beginClickupOAuth()}>
        start-clickup
      </button>
      <button type="button" onClick={() => beginOAuth("monday")}>
        start-monday
      </button>
      <button type="button" onClick={() => beginOAuth("gohighlevel")}>
        start-ghl
      </button>
    </div>
  )
}

describe("AuthProvider OAuth start isolation", () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    startOAuth.mockResolvedValue({ authorizationUrl: "https://example.com/oauth" })
    // Avoid navigation during tests
    vi.stubGlobal("location", { ...window.location, assign: vi.fn() })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it("beginNotionOAuth only calls startOAuth('notion')", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AuthProvider>
          <OAuthStartProbe />
        </AuthProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText("start-notion")).toBeInTheDocument())
    await user.click(screen.getByText("start-notion"))
    expect(startOAuth).toHaveBeenCalledTimes(1)
    expect(startOAuth).toHaveBeenCalledWith("notion")
  })

  it("beginClickupOAuth only calls startOAuth('clickup')", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AuthProvider>
          <OAuthStartProbe />
        </AuthProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText("start-clickup")).toBeInTheDocument())
    await user.click(screen.getByText("start-clickup"))
    expect(startOAuth).toHaveBeenCalledTimes(1)
    expect(startOAuth).toHaveBeenCalledWith("clickup")
  })

  it("monday and GHL starts stay isolated", async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <AuthProvider>
          <OAuthStartProbe />
        </AuthProvider>
      </MemoryRouter>,
    )
    await waitFor(() => expect(screen.getByText("start-monday")).toBeInTheDocument())
    await user.click(screen.getByText("start-monday"))
    expect(startOAuth).toHaveBeenLastCalledWith("monday")
    await user.click(screen.getByText("start-ghl"))
    expect(startOAuth).toHaveBeenLastCalledWith("gohighlevel")
    expect(startOAuth.mock.calls.map((c) => c[0])).toEqual(["monday", "gohighlevel"])
  })
})
