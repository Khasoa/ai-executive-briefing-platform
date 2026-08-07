import { Link, NavLink } from "react-router-dom"
import {
  CalendarClock,
  Inbox,
  LayoutGrid,
  MessagesSquare,
  Plug,
  Settings as SettingsIcon,
  Sun,
  Target,
} from "lucide-react"
import { Avatar } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { Logo } from "@/components/layout/Logo"
import { cn } from "@/lib/utils"

/** The whole product. Anything that does not serve the brief is not here. */
const PRIMARY_NAV = [
  { to: "/", label: "Overview", icon: LayoutGrid, end: true },
  { to: "/morning-brief", label: "Morning Brief", icon: Sun, highlight: true },
  { to: "/inbox", label: "Inbox", icon: Inbox, badge: "inbox" },
  { to: "/meetings", label: "Meetings", icon: CalendarClock, badge: "meetings" },
  { to: "/crm", label: "CRM", icon: Target, badge: "crm" },
  { to: "/ask", label: "Ask Briefly", icon: MessagesSquare },
]

const SECONDARY_NAV = [
  { to: "/integrations", label: "Integrations", icon: Plug },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
]

function NavItem({ item, badges }) {
  const count = item.badge ? badges?.[item.badge] : null

  return (
    <NavLink
      to={item.to}
      end={item.end}
      title={item.label}
      aria-label={count > 0 ? `${item.label}, ${count}` : item.label}
      className={({ isActive }) =>
        cn(
          "group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40",
          "max-lg:justify-center max-lg:px-0",
          item.highlight &&
            (isActive
              ? "bg-accent-soft text-foreground surface"
              : "text-foreground hover:bg-accent-soft/70"),
          !item.highlight &&
            (isActive
              ? "bg-card text-foreground surface"
              : "text-muted-foreground hover:bg-card/70 hover:text-foreground"),
        )
      }
    >
      {({ isActive }) => (
        <>
          <item.icon
            className={cn(
              "h-4 w-4 shrink-0 transition-colors",
              item.highlight
                ? "text-accent-strong"
                : isActive
                  ? "text-primary"
                  : "text-faint group-hover:text-muted-foreground",
            )}
            strokeWidth={item.highlight ? 2 : 1.75}
            aria-hidden="true"
          />
          <span className="flex-1 truncate max-lg:hidden">{item.label}</span>
          {count > 0 && (
            <span
              className={cn(
                "rounded px-1.5 py-0.5 text-[11px] font-semibold numeric max-lg:hidden",
                isActive ? "bg-primary-soft text-primary" : "bg-muted text-muted-foreground",
              )}
            >
              {count}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

export function Sidebar({ workspace }) {
  const user = workspace?.user
  const brief = workspace?.brief

  return (
    <aside
      className="flex h-screen w-14 shrink-0 flex-col border-r border-border bg-subtle sm:w-16 lg:w-60"
      aria-label="Primary"
    >
      <div className="flex h-14 items-center gap-2.5 px-4 max-lg:justify-center max-lg:px-0">
        <Logo />
        <div className="min-w-0 max-lg:hidden">
          <p className="text-[14px] font-semibold leading-tight tracking-tight">Briefly</p>
          <p className="text-[11px] leading-tight text-muted-foreground">Executive briefings</p>
        </div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2 max-lg:px-2" aria-label="Product">
        {PRIMARY_NAV.map((item) => (
          <NavItem key={item.to} item={item} badges={workspace?.badges} />
        ))}

        <div className="my-3 h-px bg-border" role="separator" />

        {SECONDARY_NAV.map((item) => (
          <NavItem key={item.to} item={item} badges={workspace?.badges} />
        ))}
      </nav>

      {brief && (
        <Link
          to="/morning-brief"
          className="mx-3 mb-3 rounded-lg border border-accent/20 bg-accent-soft/60 px-3 py-2.5 transition-colors hover:border-accent/35 hover:bg-accent-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40 max-lg:hidden"
        >
          <div className="flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-strong" aria-hidden="true" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-accent">
              Brief ready
            </p>
          </div>
          <p className="mt-1 text-[12px] leading-snug text-secondary-foreground">
            Generated {brief.generatedLabel}
          </p>
        </Link>
      )}

      <div className="border-t border-border p-3">
        {user ? (
          <div className="flex items-center gap-2.5 px-1 max-lg:justify-center max-lg:px-0">
            <Avatar initials={user.avatar} size="md" tone="primary" />
            <div className="min-w-0 flex-1 max-lg:hidden">
              <p className="truncate text-[13px] font-medium leading-tight">{user.fullName}</p>
              <p className="truncate text-[11px] leading-tight text-muted-foreground">
                {user.role}
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2.5 px-1">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="flex-1 space-y-1.5 max-lg:hidden">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-2.5 w-20" />
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
