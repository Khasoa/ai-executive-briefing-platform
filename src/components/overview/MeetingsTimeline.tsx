import { motion } from "framer-motion"
import { Clock, Video, MapPin, Phone } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
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

export function MeetingsTimeline() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4 text-blue-500" />
          <CardTitle>Upcoming Meetings</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="relative space-y-0">
          {meetings.map((meeting, i) => {
            const LocationIcon = locationIcons[meeting.location as keyof typeof locationIcons] || Video
            return (
              <motion.div
                key={meeting.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.25 + i * 0.06 }}
                className="relative flex gap-4 pb-6 last:pb-0"
              >
                {i < meetings.length - 1 && (
                  <div className="absolute left-[15px] top-8 h-full w-px bg-border" />
                )}
                <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 border-background bg-accent">
                  <div className="h-2 w-2 rounded-full bg-primary" />
                </div>
                <div className="flex-1 pt-0.5">
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-xs font-medium text-primary">{meeting.time}</span>
                    <span className="text-xs text-muted-foreground">{meeting.duration}</span>
                    <Badge variant={typeColors[meeting.type as keyof typeof typeColors]} className="text-[10px]">
                      {meeting.type}
                    </Badge>
                  </div>
                  <h4 className="text-sm font-medium">{meeting.title}</h4>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {meeting.attendees.join(", ")}
                  </p>
                  <div className="mt-1.5 flex items-center gap-1 text-xs text-muted-foreground">
                    <LocationIcon className="h-3 w-3" />
                    {meeting.location}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}
