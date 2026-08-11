import { useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { ApiError } from "@/api/client"
import { useAuth } from "@/auth/AuthContext"
import { Logo } from "@/components/layout/Logo"
import { Button } from "@/components/ui/button"
import { Field, Input } from "@/components/ui/input"

export function LoginPage() {
  const { login, beginGoogleOAuth } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from || "/"

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [pending, setPending] = useState(false)
  const [googlePending, setGooglePending] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setPending(true)
    try {
      await login({ email: email.trim(), password })
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in.")
    } finally {
      setPending(false)
    }
  }

  async function handleGoogle() {
    setError("")
    setGooglePending(true)
    try {
      await beginGoogleOAuth()
    } catch (err) {
      setGooglePending(false)
      setError(err instanceof ApiError ? err.message : "Google sign-in is unavailable.")
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -10%, color-mix(in srgb, var(--color-primary) 12%, transparent), transparent), radial-gradient(ellipse 40% 30% at 90% 80%, color-mix(in srgb, var(--color-accent) 10%, transparent), transparent)",
        }}
        aria-hidden="true"
      />

      <div className="relative w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo className="mb-4" />
          <h1 className="text-[22px] font-semibold tracking-tight">Sign in to Briefly</h1>
          <p className="mt-1.5 text-[13px] text-muted-foreground">
            Your morning brief is waiting — open it with your account.
          </p>
        </div>

        <div className="surface-raised rounded-2xl border border-border bg-card p-6 sm:p-7">
          <Button
            type="button"
            variant="secondary"
            className="w-full gap-2"
            disabled={pending || googlePending}
            onClick={handleGoogle}
          >
            <GoogleMark />
            {googlePending ? "Redirecting to Google…" : "Continue with Google"}
          </Button>

          <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.08em] text-faint">
            <span className="h-px flex-1 bg-border" />
            or email
            <span className="h-px flex-1 bg-border" />
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <Field label="Work email">
              <Input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
              />
            </Field>
            <Field label="Password">
              <Input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </Field>

            {error && (
              <p className="rounded-lg bg-critical-soft px-3 py-2 text-[12px] text-critical" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" variant="primary" className="w-full" disabled={pending || googlePending}>
              {pending ? "Signing in…" : "Sign in"}
            </Button>
          </form>
        </div>

        <p className="mt-5 text-center text-[13px] text-muted-foreground">
          New to Briefly?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  )
}

function GoogleMark() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  )
}
