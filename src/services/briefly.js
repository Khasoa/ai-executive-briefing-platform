import { api } from "@/services/client"

/**
 * Every call the frontend makes to the Briefly FastAPI backend.
 *
 * Pages consume these functions through `useApiQuery`; no page builds a URL or
 * holds its own copy of server data.
 */

export const getWorkspace = (options) => api.get("/workspace", options)

export const getOverview = (options) => api.get("/overview", options)

export const getMorningBrief = (options) => api.get("/morning-brief", options)

export const regenerateMorningBrief = () => api.post("/morning-brief/regenerate")

export const setChecklistItem = (itemId, done) =>
  api.patch(`/morning-brief/checklist/${itemId}`, { done })

export const getInbox = (options) => api.get("/inbox", options)

export const getMeetings = (options) => api.get("/meetings", options)

export const getMeeting = (meetingId, options) => api.get(`/meetings/${meetingId}`, options)

export const getPipeline = (options) => api.get("/crm", options)

export const getAskWorkspace = (options) => api.get("/ask", options)

export const askBriefly = (question) => api.post("/ask", { question })

export const getIntegrations = (options) => api.get("/integrations", options)

export const syncIntegration = (integrationId) => api.post(`/integrations/${integrationId}/sync`)

export const getSettings = (options) => api.get("/settings", options)

export const updatePreferences = (patch) => api.patch("/settings/preferences", patch)

export const setNotification = (notificationId, enabled) =>
  api.patch(`/settings/notifications/${notificationId}`, { enabled })
