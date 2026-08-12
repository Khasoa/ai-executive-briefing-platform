import { useEffect, useRef, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { ApiError } from "@/api/client"
import { AuthLoadingScreen } from "@/auth/ProtectedRoute"
import { useAuth } from "@/auth/AuthContext"
import { Button } from "@/components/ui/button"
import { getRefreshToken } from "@/lib/auth-storage"
import { exchangeOAuthTicketOnce } from "@/lib/oauthTicketExchange"

const PROVIDER_LABELS = {
  notion: "Notion",
  gohighlevel: "GoHighLevel",
  monday: "monday.com",
  clickup: "ClickUp",
  google: "Google",
}

/**
 * Handles `OAUTH_SUCCESS_REDIRECT?ticket=…&provider=…`.
 * Exchanges the one-time ticket for Briefly tokens, then enters the app.
 *
 * StrictMode remounts must not POST the same ticket twice — see
 * `exchangeOAuthTicketOnce`.
 */
export function OAuthCallbackPage() {
  const [params] = useSearchParams()
  const { finishOAuth, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState("")
  const ticket = params.get("ticket")
  const provider = (params.get("provider") || "google").toLowerCase()

  // Keep the latest finishOAuth without re-firing the exchange effect when
  // AuthContext rebuilds callbacks after a successful session.
  const finishOAuthRef = useRef(finishOAuth)
  useEffect(() => {
    finishOAuthRef.current = finishOAuth
  }, [finishOAuth])

  useEffect(() => {
    if (!ticket) {
      setError("Missing OAuth ticket. Start again from Sign in.")
      return
    }

    let cancelled = false

    exchangeOAuthTicketOnce(provider, ticket, (p, t) => finishOAuthRef.current(p, t))
      .then(() => {
        if (cancelled) return
        const toIntegrations = ["notion", "gohighlevel", "monday", "clickup"].includes(
          provider,
        )
        navigate(toIntegrations ? "/integrations" : "/", { replace: true })
      })
      .catch((err) => {
        if (cancelled) return
        // A remount that raced an older code path may see "already used"
        // after the winning exchange stored tokens — only then continue.
        const message = err instanceof ApiError ? err.message : ""
        if (/already used/i.test(message) && getRefreshToken()) {
          navigate("/", { replace: true })
          return
        }
        const label = PROVIDER_LABELS[provider] || "OAuth"
        setError(err instanceof ApiError ? err.message : `${label} sign-in failed.`)
      })

    return () => {
      cancelled = true
    }
  }, [ticket, provider, navigate])

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4">
        <p className="max-w-sm text-center text-[14px] text-critical" role="alert">
          {error}
        </p>
        <Button variant="primary" onClick={() => navigate("/login", { replace: true })}>
          Back to sign in
        </Button>
        <Link to="/login" className="text-[13px] text-muted-foreground hover:underline">
          Or open the login page
        </Link>
      </div>
    )
  }

  if (isAuthenticated) {
    return <AuthLoadingScreen label="Opening your workspace…" />
  }

  const label = PROVIDER_LABELS[provider] || "OAuth"
  return <AuthLoadingScreen label={`Completing ${label} connection…`} />
}
