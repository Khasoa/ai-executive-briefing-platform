/**
 * Maps Integrations card ids → OAuth start provider.
 *
 * Google Calendar / Gmail are *derived* from Google OAuth and intentionally
 * share the google start flow. Notion, GHL, monday.com, and ClickUp each map
 * to their own provider only — never fall through to another provider.
 */

export const GOOGLE_FAMILY_IDS = Object.freeze(["google", "gmail", "google-calendar"])

/** Independent OAuth providers (card id → authorize path provider). */
export const INDEPENDENT_OAUTH_START = Object.freeze({
  notion: "notion",
  gohighlevel: "gohighlevel",
  monday: "monday",
  clickup: "clickup",
})

/**
 * @param {string} integrationId Catalog / card id from Integrations
 * @returns {string | null} Provider for GET /auth/oauth/{provider}/start, or null if not OAuth
 */
export function resolveOAuthStartProvider(integrationId) {
  if (!integrationId || typeof integrationId !== "string") return null
  const id = integrationId.trim().toLowerCase()
  if (Object.prototype.hasOwnProperty.call(INDEPENDENT_OAUTH_START, id)) {
    return INDEPENDENT_OAUTH_START[id]
  }
  if (GOOGLE_FAMILY_IDS.includes(id)) {
    return "google"
  }
  return null
}

/**
 * Providers whose AuthContext status should refresh after a successful OAuth finish.
 * Google finish refreshes only google (Gmail/Calendar cards derive from catalog).
 */
export function statusRefreshProvidersFor(finishedProvider) {
  const p = (finishedProvider || "").toLowerCase()
  if (p === "google") return ["google"]
  if (p === "notion") return ["notion"]
  if (p === "gohighlevel") return ["gohighlevel"]
  if (p === "monday") return ["monday"]
  if (p === "clickup") return ["clickup"]
  return []
}
