import { describe, expect, it } from "vitest"
import { classifyError } from "@/lib/errors"

describe("classifyError provider messages", () => {
  it("surfaces Google Calendar API-not-enabled (409)", () => {
    const result = classifyError({
      status: 409,
      message:
        "Google Calendar API is not enabled for this Google Cloud project. Enable the Calendar API in Google Cloud Console, wait a few minutes, then Sync again.",
    })
    expect(result.kind).toBe("conflict")
    expect(result.message).toMatch(/not enabled/i)
  })

  it("surfaces provider 502 messages instead of generic server copy", () => {
    const result = classifyError({
      status: 502,
      message: "Google Calendar is temporarily unavailable. Try again shortly.",
    })
    expect(result.message).toMatch(/Google Calendar/i)
    expect(result.message).not.toMatch(/Briefly hit a server error/i)
  })

  it("keeps generic copy for opaque 500s", () => {
    const result = classifyError({
      status: 500,
      message: "Internal Server Error",
    })
    expect(result.message).toMatch(/server error/i)
  })

  it("surfaces Google authorization refresh (401)", () => {
    const result = classifyError({
      status: 401,
      message: "Google Calendar authorization needs to be refreshed. Reconnect Google.",
    })
    expect(result.message).toMatch(/authorization needs to be refreshed/i)
  })
})
