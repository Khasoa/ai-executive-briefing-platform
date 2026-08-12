import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ApiError } from "@/api/client"
import { useAuth } from "@/auth/AuthContext"
import { Logo } from "@/components/layout/Logo"
import { Button } from "@/components/ui/button"
import { Field, Input } from "@/components/ui/input"

export function RegisterPage() {
  const { register, beginGoogleOAuth } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [pending, setPending] = useState(false)
  const [googlePending, setGooglePending] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    if (password.length < 8) {
      setError("Password must be at least 8 characters.")
      return
    }
    setPending(true)
    try {
      await register({
        email: email.trim(),
        password,
        fullName: fullName.trim(),
      })
      navigate("/", { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create your account.")
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
      setError(err instanceof ApiError ? err.message : "Google sign-up is unavailable.")
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background px-4 py-10">
      <div
        className="pointer-events-none absolute inset-0 opacity-70"
        style={{
          background:
            "radial-gradient(ellipse 80% 50% at 50% -10%, color-mix(in srgb, var(--color-primary) 12%, transparent), transparent)",
        }}
        aria-hidden="true"
      />

      <div className="relative w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <Logo className="mb-4" />
          <h1 className="text-[22px] font-semibold tracking-tight">Create your Briefly account</h1>
          <p className="mt-1.5 text-[13px] text-muted-foreground">
            One intelligent briefing every morning from the systems you already run.
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
            Continue with Google
          </Button>

          <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-[0.08em] text-faint">
            <span className="h-px flex-1 bg-border" />
            or email
            <span className="h-px flex-1 bg-border" />
          </div>

          <form className="space-y-4" onSubmit={handleSubmit}>
            <Field label="Full name">
              <Input
                required
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Alex Founder"
              />
            </Field>
            <Field label="Work email">
              <Input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
              />
            </Field>
            <Field label="Password" hint="At least 8 characters">
              <Input
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
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
              {pending ? "Creating account…" : "Create account"}
            </Button>
          </form>
        </div>

        <p className="mt-5 text-center text-[13px] text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
