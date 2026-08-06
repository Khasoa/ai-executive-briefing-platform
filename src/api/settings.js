import { api } from "@/api/client"

/** GET /settings */
export const getSettings = (options) => api.get("/settings", options)

/** PATCH /settings/preferences */
export const updatePreferences = (patch, options) =>
  api.patch("/settings/preferences", patch, options)

/** PATCH /settings/notifications/{notificationId} */
export const setNotification = (notificationId, enabled, options) =>
  api.patch(`/settings/notifications/${notificationId}`, { enabled }, options)
