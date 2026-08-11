import { api } from "@/api/client"

/** GET /weekly-digest */
export const getWeeklyDigest = (options) => api.get("/weekly-digest", options)

/** POST /weekly-digest/regenerate */
export const regenerateWeeklyDigest = (options) =>
  api.post("/weekly-digest/regenerate", undefined, options)
