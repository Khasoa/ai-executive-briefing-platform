import { api } from "@/api/client"

/** GET /inbox */
export const getInbox = (options) => api.get("/inbox", options)
