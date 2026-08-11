import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  exchangeOAuthTicketOnce,
  resetOAuthTicketExchanges,
} from "@/lib/oauthTicketExchange"

describe("exchangeOAuthTicketOnce", () => {
  beforeEach(() => {
    resetOAuthTicketExchanges()
  })

  it("calls the exchange function only once for the same ticket", async () => {
    const exchangeFn = vi.fn().mockResolvedValue({ ok: true })

    const [a, b] = await Promise.all([
      exchangeOAuthTicketOnce("google", "ticket-abc-1234567890", exchangeFn),
      exchangeOAuthTicketOnce("google", "ticket-abc-1234567890", exchangeFn),
    ])

    expect(exchangeFn).toHaveBeenCalledTimes(1)
    expect(a).toEqual({ ok: true })
    expect(b).toEqual({ ok: true })
  })

  it("allows a retry after a failed exchange", async () => {
    const exchangeFn = vi
      .fn()
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({ ok: true })

    await expect(
      exchangeOAuthTicketOnce("google", "ticket-retry-1234567890", exchangeFn),
    ).rejects.toThrow("network")

    await expect(
      exchangeOAuthTicketOnce("google", "ticket-retry-1234567890", exchangeFn),
    ).resolves.toEqual({ ok: true })

    expect(exchangeFn).toHaveBeenCalledTimes(2)
  })
})
