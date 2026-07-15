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
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="relative flex h-screen flex-col border-r border-border bg-card/80 glass"
    >
      <div className="flex h-16 items-center gap-3 px-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
          <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none">
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
            <p className="text-sm font-semibold tracking-tight">Atlas</p>
            <p className="text-[11px] text-muted-foreground">AI Executive Partner</p>
          </motion.div>
        )}
      </div>

      <nav className="flex-1 space-y-1 px-3 py-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )
            }
          >
            <item.icon className="h-[18px] w-[18px] shrink-0" />
            {!collapsed && (
              <>
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/10 px-1.5 text-[11px] font-semibold text-primary">
                    {item.badge}
                  </span>
                )}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-border p-3">
        <div className={cn("flex items-center gap-3 rounded-lg p-2", collapsed && "justify-center")}>
          <Avatar className="h-8 w-8">
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
        className="absolute -right-3 top-20 flex h-6 w-6 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm transition-colors hover:text-foreground cursor-pointer"
      >
        {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
      </button>
    </motion.aside>
  )
}
