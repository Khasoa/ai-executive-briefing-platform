import { motion } from "framer-motion"
import { Settings, Bell, Shield, Palette, Link2, User } from "lucide-react"
import { Card, CardHeader, CardTitle } from "@/components/ui/card"
import { user } from "@/data/mock"
import { pageHeader, ease } from "@/lib/motion"

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
    <div className="mx-auto max-w-3xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="flex items-center gap-2.5">
          <Settings className="h-5 w-5 text-coral" strokeWidth={1.75} />
          <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">Settings</h1>
        </div>
      </motion.div>

      <div className="space-y-3">
        {settingsSections.map((section, i) => (
          <motion.div
            key={section.title}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.45, ease }}
          >
            <Card className="cursor-pointer hover:card-shadow-hover">
              <CardHeader>
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-muted/80">
                    <section.icon className="h-4 w-4 text-muted-foreground" strokeWidth={1.75} />
                  </div>
                  <div>
                    <CardTitle className="text-sm">{section.title}</CardTitle>
                    <p className="mt-0.5 text-sm text-muted-foreground">{section.description}</p>
                  </div>
                </div>
              </CardHeader>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
