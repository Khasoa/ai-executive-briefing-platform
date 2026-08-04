const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function request(path, { method = "GET", body, signal } = {}) {
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      signal,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (error) {
    if (error.name === "AbortError") throw error
    throw new ApiError(`Cannot reach the Briefly API at ${BASE_URL}.`, 0)
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status)
  }

  return response.status === 204 ? null : response.json()
}

async function readError(response) {
  try {
    const body = await response.json()
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) return body.detail.map((item) => item.msg).join(", ")
  } catch {
    // Response had no JSON body; fall through to the status-based message.
  }
  return `Request failed with status ${response.status}.`
}

export const api = {
  get: (path, options) => request(path, options),
  post: (path, body, options) => request(path, { ...options, method: "POST", body }),
  patch: (path, body, options) => request(path, { ...options, method: "PATCH", body }),
}
