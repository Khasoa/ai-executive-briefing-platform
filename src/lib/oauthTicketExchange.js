/**
 * Deduplicate one-time OAuth ticket exchanges across React StrictMode
 * remounts and effect re-runs. The backend ticket remains single-use;
 * this only ensures the browser issues a single POST per ticket.
 */

/** @type {Map<string, Promise<unknown>>} */
const inflight = new Map()

/**
 * @param {string} provider
 * @param {string} ticket
 * @param {(provider: string, ticket: string) => Promise<unknown>} exchangeFn
 */
export function exchangeOAuthTicketOnce(provider, ticket, exchangeFn) {
  const key = `${String(provider).toLowerCase()}:${ticket}`
  const existing = inflight.get(key)
  if (existing) return existing

  const promise = Promise.resolve()
    .then(() => exchangeFn(provider, ticket))
    .catch((error) => {
      // Allow a genuine retry (e.g. transient network) while the ticket
      // is still valid server-side. Successful exchanges stay cached so
      // a remount cannot fire a second POST.
      inflight.delete(key)
      throw error
    })

  inflight.set(key, promise)
  return promise
}

/** Test helper — clear the in-flight map between cases. */
export function resetOAuthTicketExchanges() {
  inflight.clear()
}
