import { api } from "@/api/client"

/** GET /meetings */
export const getMeetings = (options) => api.get("/meetings", options)

/** GET /meetings/{meetingId} */
export const getMeeting = (meetingId, options) => api.get(`/meetings/${meetingId}`, options)
