import { motion } from "framer-motion"
import { Settings, Bell, Shield, Palette, Link2, User } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { user } from "@/data/mock"

const settingsSections = [
  {
    icon: User,
    title: "Profile",
    description: `${user.name} · ${user.role} at ${user.company}`,
  },
  {
    icon: Bell,
    title: "Notifications",
    description: "Daily brief at 6:30 AM, urgent email alerts, meeting reminders",
  },
  {
    icon: Link2,
    title: "Connected Tools",
    description: "Gmail, Google Calendar, Salesforce, Slack, Notion",
  },
  {
    icon: Shield,
    title: "Privacy & Security",
    description: "Two-factor authentication, data retention, API access",
  },
  {
    icon: Palette,
    title: "Appearance",
    description: "Light mode, compact density, animation preferences",
  },
]

export function SettingsPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">Settings</h1>
        </div>
      </motion.div>

      <div className="space-y-4">
        {settingsSections.map((section, i) => (
          <motion.div
            key={section.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card className="cursor-pointer transition-all duration-200 hover:card-shadow-hover">
              <CardHeader className="pb-0">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                    <section.icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div>
                    <CardTitle className="text-sm">{section.title}</CardTitle>
                    <p className="text-sm text-muted-foreground">{section.description}</p>
                  </div>
                </div>
              </CardHeader>
              <CardContent />
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
