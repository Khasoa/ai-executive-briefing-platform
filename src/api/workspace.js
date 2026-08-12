import { api } from "@/api/client"

/** GET /workspace — shell identity, brief freshness, nav badges. */
export const getWorkspace = (options) => api.get("/workspace", options)
