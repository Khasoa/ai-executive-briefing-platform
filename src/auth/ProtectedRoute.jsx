import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "@/auth/AuthContext"
import { Logo } from "@/components/layout/Logo"

export function AuthLoadingScreen({ label = "Restoring your session…" }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-4">
      <Logo />
      <div className="text-center">
        <p className="text-[14px] font-medium">Briefly</p>
        <p className="mt-1 text-[13px] text-muted-foreground">{label}</p>
      </div>
      <div
        className="h-1.5 w-32 overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label={label}
      >
        <div className="h-full w-1/2 animate-pulse rounded-full bg-primary/70" />
      </div>
    </div>
  )
}

/** Shell routes — require a restored authenticated session. */
export function ProtectedRoute() {
  const { isAuthenticated, restoring } = useAuth()
  const location = useLocation()

  if (restoring) return <AuthLoadingScreen />
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}

/** Login / register — bounce away when already signed in. */
export function PublicOnlyRoute() {
  const { isAuthenticated, restoring } = useAuth()

  if (restoring) return <AuthLoadingScreen />
  if (isAuthenticated) return <Navigate to="/" replace />
  return <Outlet />
}
