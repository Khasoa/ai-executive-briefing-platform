import { motion } from "framer-motion"
import { Calendar, Video, MapPin, Phone } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { meetings } from "@/data/mock"

const typeColors = {
  internal: "secondary",
  client: "purple",
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
    <div className="mx-auto max-w-4xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">Calendar</h1>
        </div>
        <p className="mt-1 text-muted-foreground">Wednesday, July 15, 2026 — 4 meetings</p>
      </motion.div>

      <div className="space-y-4">
        {meetings.map((meeting, i) => {
          const LocationIcon = locationIcons[meeting.location as keyof typeof locationIcons] || Video
          return (
            <motion.div
              key={meeting.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card className="transition-all duration-200 hover:card-shadow-hover">
                <CardContent className="flex items-center gap-5 p-5">
                  <div className="w-20 shrink-0 text-center">
                    <p className="text-lg font-semibold text-primary">{meeting.time.split(" ")[0]}</p>
                    <p className="text-xs text-muted-foreground">{meeting.time.split(" ")[1]}</p>
                  </div>
                  <div className="h-12 w-px bg-border" />
                  <div className="flex-1">
                    <div className="mb-1 flex items-center gap-2">
                      <h3 className="font-medium">{meeting.title}</h3>
                      <Badge variant={typeColors[meeting.type as keyof typeof typeColors]}>
                        {meeting.type}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {meeting.attendees.join(" · ")} · {meeting.duration}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                    <LocationIcon className="h-4 w-4" />
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
