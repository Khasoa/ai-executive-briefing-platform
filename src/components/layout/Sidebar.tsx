import { NavLink } from "react-router-dom"
import { motion } from "framer-motion"
import {
  LayoutDashboard,
  Newspaper,
  Inbox,
  Calendar,
  Users,
  FolderKanban,
  BookOpen,
  Sparkles,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { user } from "@/data/mock"
import { useState } from "react"
import { ease } from "@/lib/motion"

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Overview" },
  { to: "/daily-brief", icon: Newspaper, label: "Daily Brief" },
  { to: "/inbox", icon: Inbox, label: "Inbox", badge: 12 },
  { to: "/calendar", icon: Calendar, label: "Calendar" },
  { to: "/crm", icon: Users, label: "CRM" },
  { to: "/projects", icon: FolderKanban, label: "Projects" },
  { to: "/research", icon: BookOpen, label: "Research" },
  { to: "/assistant", icon: Sparkles, label: "AI Assistant" },
  { to: "/settings", icon: Settings, label: "Settings" },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 260 }}
      transition={{ duration: 0.35, ease }}
      className="relative z-10 flex h-screen flex-col border-r border-border/60 glass-sidebar"
    >
      <div className="flex h-[4.5rem] items-center gap-3 px-5">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary shadow-sm">
          <svg viewBox="0 0 24 24" className="h-4 w-4 text-primary-foreground" fill="none">
            <path d="M6 18L12 6L18 18H6Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
            <circle cx="12" cy="15" r="1.5" fill="currentColor" />
          </svg>
        </div>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="overflow-hidden"
          >
            <p className="text-sm font-semibold tracking-tight text-foreground">Atlas</p>
            <p className="text-[11px] tracking-wide text-muted-foreground">Executive Partner</p>
          </motion.div>
        )}
      </div>

      <nav className="flex-1 space-y-0.5 px-3 py-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition-all duration-300",
                isActive
                  ? "bg-accent text-foreground shadow-sm [&_svg]:text-coral"
                  : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
              )
            }
          >
            <item.icon className="h-[17px] w-[17px] shrink-0" />
            {!collapsed && (
              <>
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-coral/10 px-1.5 text-[10px] font-semibold text-coral">
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border/50 p-3">
        <div className={cn("flex items-center gap-3 rounded-xl p-2.5", collapsed && "justify-center")}>
          <Avatar className="h-8 w-8 ring-2 ring-border/40">
            <AvatarFallback className="text-xs">{user.avatar}</AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium">{user.name}</p>
              <p className="truncate text-[11px] text-muted-foreground">{user.role}</p>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-[5.5rem] flex h-6 w-6 items-center justify-center rounded-full border border-border/80 bg-card text-muted-foreground shadow-sm transition-all duration-300 hover:text-foreground hover:shadow-md cursor-pointer"
      >
        {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
      </button>
    </motion.aside>
  )
}
