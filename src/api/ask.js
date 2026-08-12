import { api } from "@/api/client"

/** GET /ask */
export const getAskWorkspace = (options) => api.get("/ask", options)

/** POST /ask */
export const askBriefly = (question, options) => api.post("/ask", { question }, options)
