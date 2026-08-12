import { api } from "@/api/client"

/** GET /overview — executive dashboard payload. */
export const getOverview = (options) => api.get("/overview", options)
