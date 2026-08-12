import { beforeEach, describe, expect, it, vi } from "vitest"
import { StrictMode } from "react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { render, screen, waitFor } from "@testing-library/react"
import { OAuthCallbackPage } from "@/pages/OAuthCallback"
import { resetOAuthTicketExchanges } from "@/lib/oauthTicketExchange"

const finishOAuth = vi.fn()
const navigate = vi.fn()

vi.mock("@/auth/AuthContext", () => ({
  useAuth: () => ({
    finishOAuth,
    isAuthenticated: false,
  }),
}))

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom")
  return {
    ...actual,
    useNavigate: () => navigate,
  }
})

function renderCallback(search) {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={[`/oauth/callback${search}`]}>
        <Routes>
          <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>,
  )
}

describe("OAuthCallbackPage", () => {
  beforeEach(() => {
    resetOAuthTicketExchanges()
    finishOAuth.mockReset()
    navigate.mockReset()
    finishOAuth.mockResolvedValue({ email: "user@example.com" })
  })

  it("does not exchange the same ticket twice under StrictMode", async () => {
    const ticket = "fresh-ticket-value-1234567890"
    renderCallback(`?ticket=${ticket}&provider=google`)

    await waitFor(() => {
      expect(finishOAuth).toHaveBeenCalledTimes(1)
    })
    expect(finishOAuth).toHaveBeenCalledWith("google", ticket)
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/", { replace: true })
    })
  })

  it("shows an error when the ticket is missing", async () => {
    renderCallback("?provider=google")
    expect(await screen.findByRole("alert")).toHaveTextContent(/missing oauth ticket/i)
    expect(finishOAuth).not.toHaveBeenCalled()
  })

  it("leaves the user on a successful Google OAuth path (navigates home)", async () => {
    renderCallback("?ticket=success-ticket-abcdefghij&provider=google")
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/", { replace: true })
    })
  })
})
