import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Inbox, Sparkles, AlertCircle, ChevronRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { inboxCategories, type EmailCategory } from "@/data/mock"
import { cn } from "@/lib/utils"

const categoryColors: Record<EmailCategory, string> = {
  urgent: "text-red-600 bg-red-50",
  clients: "text-indigo-600 bg-indigo-50",
  investors: "text-emerald-600 bg-emerald-50",
  finance: "text-blue-600 bg-blue-50",
  internal: "text-violet-600 bg-violet-50",
  newsletters: "text-gray-600 bg-gray-50",
}

export function InboxPage() {
  const [activeCategory, setActiveCategory] = useState<EmailCategory>("urgent")
  const active = inboxCategories.find((c) => c.id === activeCategory)!

  return (
    <div className="mx-auto max-w-6xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2">
          <Inbox className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">Inbox</h1>
        </div>
        <p className="mt-1 text-muted-foreground">
          AI-classified emails with executive summaries
        </p>
      </motion.div>

      <div className="flex flex-col gap-6 lg:flex-row">
        <div className="flex gap-2 overflow-x-auto pb-2 lg:w-56 lg:flex-col lg:overflow-visible lg:pb-0">
          {inboxCategories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={cn(
                "flex shrink-0 items-center justify-between rounded-lg px-4 py-2.5 text-sm font-medium transition-all duration-200 cursor-pointer",
                activeCategory === cat.id
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <span>{cat.label}</span>
              <span
                className={cn(
                  "ml-2 flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[11px] font-semibold",
                  categoryColors[cat.id]
                )}
              >
                {cat.count}
              </span>
            </button>
          ))}
        </div>

        <div className="flex-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeCategory}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.2 }}
              className="space-y-3"
            >
              {active.emails.map((email, i) => (
                <motion.div
                  key={email.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card
                    className={cn(
                      "group cursor-pointer transition-all duration-200 hover:card-shadow-hover",
                      email.unread && "border-l-2 border-l-primary"
                    )}
                  >
                    <CardContent className="p-5">
                      <div className="mb-2 flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                            {email.from
                              .split(" ")
                              .map((n) => n[0])
                              .join("")
                              .slice(0, 2)}
                          </div>
                          <div>
                            <p className="text-sm font-medium">{email.from}</p>
                            <p className="text-xs text-muted-foreground">{email.time}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {email.actionRequired && (
                            <Badge variant="destructive" className="gap-1 text-[10px]">
                              <AlertCircle className="h-3 w-3" />
                              Action
                            </Badge>
                          )}
                          <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
                        </div>
                      </div>
                      <h3 className="mb-2 text-sm font-medium">{email.subject}</h3>
                      <div className="flex gap-2 rounded-lg bg-indigo-50/50 p-3">
                        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                        <p className="text-sm leading-relaxed text-muted-foreground">
                          {email.summary}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
