import { api } from "@/api/client"

/** GET /morning-brief */
export const getMorningBrief = (options) => api.get("/morning-brief", options)

/** POST /morning-brief/regenerate */
export const regenerateMorningBrief = (options) =>
  api.post("/morning-brief/regenerate", undefined, options)

/** PATCH /morning-brief/checklist/{itemId} */
export const setChecklistItem = (itemId, done, options) =>
  api.patch(`/morning-brief/checklist/${itemId}`, { done }, options)
