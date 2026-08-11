import { useEffect, useId, useRef, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { ChevronUp, LogOut, Settings as SettingsIcon } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { Avatar } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

export function UserMenu({ user, compact = false }) {
  const { logout, googleStatus } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const menuId = useId()

  useEffect(() => {
    if (!open) return undefined

    function onPointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false)
    }
    function onKey(event) {
      if (event.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onPointerDown)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onPointerDown)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  async function handleLogout() {
    setOpen(false)
    await logout()
    navigate("/login", { replace: true })
  }

  const googleAccount =
    googleStatus?.connected && googleStatus?.account
      ? googleStatus.account
      : null

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-lg px-1 py-1 text-left transition-colors",
          "hover:bg-card/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40",
          compact && "justify-center px-0",
        )}
      >
        <Avatar initials={user.avatar} size="md" tone="primary" />
        {!compact && (
          <>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-medium leading-tight">{user.fullName}</p>
              <p className="truncate text-[11px] leading-tight text-muted-foreground">
                {user.role}
              </p>
            </div>
            <ChevronUp
              className={cn(
                "h-3.5 w-3.5 shrink-0 text-faint transition-transform",
                open ? "rotate-0" : "rotate-180",
              )}
              strokeWidth={1.75}
              aria-hidden="true"
            />
          </>
        )}
      </button>

      {open && (
        <div
          id={menuId}
          role="menu"
          className="surface-raised absolute bottom-full left-0 right-0 z-50 mb-2 overflow-hidden rounded-xl border border-border bg-card py-1 max-lg:left-auto max-lg:right-0 max-lg:w-64"
        >
          <div className="border-b border-border px-3 py-2.5">
            <p className="truncate text-[13px] font-medium">{user.fullName}</p>
            <p className="truncate text-[12px] text-muted-foreground">{user.email}</p>
            {googleAccount ? (
              <p className="mt-1 truncate text-[11px] text-faint">
                Google · {googleAccount}
              </p>
            ) : (
              <p className="mt-1 text-[11px] text-faint">Google not connected</p>
            )}
          </div>

          <Link
            role="menuitem"
            to="/settings"
            onClick={() => setOpen(false)}
            className="flex items-center gap-2 px-3 py-2 text-[13px] text-secondary-foreground transition-colors hover:bg-subtle hover:text-foreground"
          >
            <SettingsIcon className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            Settings
          </Link>

          <button
            type="button"
            role="menuitem"
            onClick={handleLogout}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-[13px] text-secondary-foreground transition-colors hover:bg-subtle hover:text-foreground"
          >
            <LogOut className="h-3.5 w-3.5" strokeWidth={1.75} aria-hidden="true" />
            Log out
          </button>
        </div>
      )}
    </div>
  )
}
