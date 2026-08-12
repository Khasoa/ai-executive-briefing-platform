import { api } from "@/api/client"

/** GET /crm */
export const getCrm = (options) => api.get("/crm", options)
