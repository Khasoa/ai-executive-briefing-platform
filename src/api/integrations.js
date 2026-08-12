import { api } from "@/api/client"

/** GET /integrations */
export const getIntegrations = (options) => api.get("/integrations", options)

/** POST /integrations/{integrationId}/sync */
export const syncIntegration = (integrationId, options) =>
  api.post(`/integrations/${integrationId}/sync`, undefined, options)

/** POST /integrations/{integrationId}/check — OpenAI / n8n configuration probe */
export const checkIntegration = (integrationId, options) =>
  api.post(`/integrations/${integrationId}/check`, undefined, options)
