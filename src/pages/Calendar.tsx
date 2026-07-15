import { motion } from "framer-motion"
import { Calendar, Video, MapPin, Phone } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { meetings } from "@/data/mock"
import { pageHeader, ease } from "@/lib/motion"

const typeColors = {
  internal: "secondary",
  client: "coral",
  investor: "success",
} as const

const locationIcons = {
  Zoom: Video,
  "Google Meet": Video,
  "Conference Room A": MapPin,
  Phone: Phone,
}

export function CalendarPage() {
  return (
    <div className="mx-auto max-w-4xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="flex items-center gap-2.5">
          <Calendar className="h-5 w-5 text-coral" strokeWidth={1.75} />
          <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">Calendar</h1>
        </div>
        <p className="mt-2 text-muted-foreground">Wednesday, July 15, 2026 — 4 meetings</p>
      </motion.div>

      <div className="space-y-4">
        {meetings.map((meeting, i) => {
          const LocationIcon = locationIcons[meeting.location as keyof typeof locationIcons] || Video
          return (
            <motion.div
              key={meeting.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06, duration: 0.45, ease }}
            >
              <Card className="hover:card-shadow-hover">
                <CardContent className="flex items-center gap-6 p-6">
                  <div className="w-[4.5rem] shrink-0 text-center">
                    <p className="text-lg font-semibold tracking-tight text-coral">{meeting.time.split(" ")[0]}</p>
                    <p className="text-[11px] font-medium tracking-wide text-muted-foreground uppercase">{meeting.time.split(" ")[1]}</p>
                  </div>
                  <div className="h-14 w-px bg-border/60" />
                  <div className="flex-1 min-w-0">
                    <div className="mb-1.5 flex flex-wrap items-center gap-2">
                      <h3 className="font-medium">{meeting.title}</h3>
                      <Badge variant={typeColors[meeting.type as keyof typeof typeColors]}>
                        {meeting.type}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {meeting.attendees.join(" · ")} · {meeting.duration}
                    </p>
                  </div>
                  <div className="hidden items-center gap-1.5 text-sm text-muted-foreground sm:flex">
                    <LocationIcon className="h-4 w-4" strokeWidth={1.75} />
                    {meeting.location}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
