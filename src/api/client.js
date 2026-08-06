const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000"
const DEFAULT_TIMEOUT_MS = 30_000

export class ApiError extends Error {
  constructor(message, status, cause) {
    super(message, cause ? { cause } : undefined)
    this.name = "ApiError"
    this.status = status
  }
}

function combineSignals(callerSignal, timeoutMs) {
  const timeoutSignal = AbortSignal.timeout(timeoutMs)
  if (!callerSignal) return timeoutSignal
  if (typeof AbortSignal.any === "function") {
    return AbortSignal.any([callerSignal, timeoutSignal])
  }
  return callerSignal
}

function isTimeoutAbort(error, callerSignal) {
  if (error?.name !== "AbortError" && error?.name !== "TimeoutError") return false
  if (callerSignal?.aborted) return false
  return true
}

async function parseJson(response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch (cause) {
    throw new ApiError("Unexpected response from the Briefly API.", response.status, cause)
  }
}

async function readError(response) {
  try {
    const body = await parseJson(response)
    if (body == null) return `Request failed with status ${response.status}.`
    if (typeof body.detail === "string") return body.detail
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => item?.msg ?? String(item))
        .filter(Boolean)
        .join(", ")
    }
  } catch (error) {
    if (error instanceof ApiError && error.message.startsWith("Unexpected")) {
      return error.message
    }
  }
  return `Request failed with status ${response.status}.`
}

async function request(path, { method = "GET", body, signal, timeout = DEFAULT_TIMEOUT_MS } = {}) {
  let response

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      signal: combineSignals(signal, timeout),
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (error) {
    if (error?.name === "AbortError" && signal?.aborted) throw error
    if (isTimeoutAbort(error, signal)) {
      throw new ApiError(`Request timed out after ${timeout / 1000}s.`, 0, error)
    }
    throw new ApiError(`Cannot reach the Briefly API at ${BASE_URL}.`, 0, error)
  }

  if (!response.ok) {
    throw new ApiError(await readError(response), response.status)
  }

  if (response.status === 204) return null
  return parseJson(response)
}

export const api = {
  get: (path, options) => request(path, options),
  post: (path, body, options) => request(path, { ...options, method: "POST", body }),
  patch: (path, body, options) => request(path, { ...options, method: "PATCH", body }),
}
