import { api } from "@/api/client"

/** GET /meetings */
export const getMeetings = (options) => api.get("/meetings", options)
