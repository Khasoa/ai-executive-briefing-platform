import { describe, expect, it } from "vitest"
import {
  GOOGLE_FAMILY_IDS,
  resolveOAuthStartProvider,
  statusRefreshProvidersFor,
} from "@/lib/oauthConnect"

describe("resolveOAuthStartProvider", () => {
  it("starts only Notion OAuth for the Notion card", () => {
    expect(resolveOAuthStartProvider("notion")).toBe("notion")
  })

  it("starts only GHL OAuth for the GoHighLevel card", () => {
    expect(resolveOAuthStartProvider("gohighlevel")).toBe("gohighlevel")
  })

  it("starts only ClickUp OAuth for the ClickUp card", () => {
    expect(resolveOAuthStartProvider("clickup")).toBe("clickup")
  })

  it("starts only monday OAuth for the monday.com card", () => {
    expect(resolveOAuthStartProvider("monday")).toBe("monday")
  })

  it("projects Gmail and Google Calendar Connect to Google OAuth only", () => {
    for (const id of GOOGLE_FAMILY_IDS) {
      expect(resolveOAuthStartProvider(id)).toBe("google")
    }
  })

  it("does not start OAuth for env-config or unknown cards", () => {
    expect(resolveOAuthStartProvider("openai")).toBeNull()
    expect(resolveOAuthStartProvider("n8n")).toBeNull()
    expect(resolveOAuthStartProvider("unknown")).toBeNull()
    expect(resolveOAuthStartProvider("")).toBeNull()
  })

  it("never maps Notion to another independent provider", () => {
    expect(resolveOAuthStartProvider("notion")).not.toBe("clickup")
    expect(resolveOAuthStartProvider("notion")).not.toBe("gohighlevel")
    expect(resolveOAuthStartProvider("notion")).not.toBe("monday")
    expect(resolveOAuthStartProvider("notion")).not.toBe("google")
  })
})

describe("statusRefreshProvidersFor", () => {
  it("refreshes only the finished provider", () => {
    expect(statusRefreshProvidersFor("notion")).toEqual(["notion"])
    expect(statusRefreshProvidersFor("clickup")).toEqual(["clickup"])
    expect(statusRefreshProvidersFor("gohighlevel")).toEqual(["gohighlevel"])
    expect(statusRefreshProvidersFor("monday")).toEqual(["monday"])
    expect(statusRefreshProvidersFor("google")).toEqual(["google"])
  })
})
