import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Inbox, Sparkles, AlertCircle, ChevronRight } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { inboxCategories, type EmailCategory } from "@/data/mock"
import { cn } from "@/lib/utils"
import { pageHeader, ease } from "@/lib/motion"

const categoryColors: Record<EmailCategory, string> = {
  urgent: "text-destructive bg-destructive/8",
  clients: "text-coral bg-coral/10",
  investors: "text-sage bg-sage/12",
  finance: "text-gold bg-gold/12",
  internal: "text-lavender bg-lavender/12",
  newsletters: "text-muted-foreground bg-muted",
}

export function InboxPage() {
  const [activeCategory, setActiveCategory] = useState<EmailCategory>("urgent")
  const active = inboxCategories.find((c) => c.id === activeCategory)!

  return (
    <div className="mx-auto max-w-6xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="flex items-center gap-2.5">
          <Inbox className="h-5 w-5 text-coral" strokeWidth={1.75} />
          <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">Inbox</h1>
        </div>
        <p className="mt-2 text-[15px] text-muted-foreground">
          AI-classified emails with executive summaries
        </p>
      </motion.div>

      <div className="flex flex-col gap-7 lg:flex-row">
        <div className="flex gap-2 overflow-x-auto pb-2 lg:w-60 lg:flex-col lg:overflow-visible lg:pb-0">
          {inboxCategories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={cn(
                "flex shrink-0 items-center justify-between rounded-xl px-4 py-3 text-[13px] font-medium transition-all duration-300 cursor-pointer",
                activeCategory === cat.id
                  ? "bg-accent text-foreground shadow-sm"
                  : "text-muted-foreground hover:bg-muted/70 hover:text-foreground"
              )}
            >
              <span>{cat.label}</span>
              <span
                className={cn(
                  "ml-2 flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-semibold",
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
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.35, ease }}
              className="space-y-4"
            >
              {active.emails.map((email, i) => (
                <motion.div
                  key={email.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05, duration: 0.4, ease }}
                >
                  <Card
                    className={cn(
                      "group cursor-pointer hover:card-shadow-hover",
                      email.unread && "border-l-[3px] border-l-coral"
                    )}
                  >
                    <CardContent className="p-6">
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-peach text-xs font-semibold text-coral">
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
                          <ChevronRight className="h-4 w-4 text-muted-foreground/50 opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:translate-x-0.5" />
                        </div>
                      </div>
                      <h3 className="mb-3 text-sm font-medium leading-snug">{email.subject}</h3>
                      <div className="flex gap-2.5 rounded-xl bg-champagne/50 p-4">
                        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-coral" strokeWidth={1.75} />
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
