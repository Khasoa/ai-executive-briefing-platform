import { describe, expect, it } from "vitest"
import { enter, fadeUp } from "@/lib/motion"

describe("motion entrance presets", () => {
  it("never blanks content with an invisible initial opacity", () => {
    expect(fadeUp.initial.opacity ?? 1).toBe(1)
    expect(enter(0).initial.opacity ?? 1).toBe(1)
    expect(enter(3).initial.opacity ?? 1).toBe(1)
  })

  it("still provides a short translate entrance", () => {
    expect(fadeUp.initial.y).toBeGreaterThan(0)
    expect(fadeUp.animate.y).toBe(0)
    expect(enter(2).transition.delay).toBeGreaterThan(0)
  })
})
