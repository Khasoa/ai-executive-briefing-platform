import { motion } from "framer-motion"
import { Clock, Video, MapPin, Phone } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { meetings } from "@/data/mock"
import { ease } from "@/lib/motion"

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

export function MeetingsTimeline() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-info/10">
            <Clock className="h-4 w-4 text-info" strokeWidth={1.75} />
          </div>
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
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.22 + i * 0.06, duration: 0.45, ease }}
                className="relative flex gap-4 pb-7 last:pb-0"
              >
                {i < meetings.length - 1 && (
                  <div className="absolute left-[15px] top-9 h-[calc(100%-12px)] w-px bg-border/80" />
                )}
                <div className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border/60 bg-card">
                  <div className="h-2 w-2 rounded-full bg-coral/70" />
                </div>
                <div className="flex-1 pt-0.5">
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className="text-xs font-semibold text-coral">{meeting.time}</span>
                    <span className="text-xs text-muted-foreground">{meeting.duration}</span>
                    <Badge variant={typeColors[meeting.type as keyof typeof typeColors]} className="text-[10px]">
                      {meeting.type}
                    </Badge>
                  </div>
                  <h4 className="text-sm font-medium leading-snug">{meeting.title}</h4>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {meeting.attendees.join(", ")}
                  </p>
                  <div className="mt-2 flex items-center gap-1.5 text-xs text-muted-foreground/80">
                    <LocationIcon className="h-3 w-3" strokeWidth={1.75} />
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
