import { beforeEach, describe, expect, it } from "vitest"
import { applyTheme, resolveDark } from "@/lib/theme"

describe("theme", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark")
  })

  it("resolves Light and Dark explicitly", () => {
    expect(resolveDark("Light")).toBe(false)
    expect(resolveDark("Dark")).toBe(true)
  })

  it("applies dark class for Dark mode", () => {
    applyTheme("Dark")
    expect(document.documentElement.classList.contains("dark")).toBe(true)
    applyTheme("Light")
    expect(document.documentElement.classList.contains("dark")).toBe(false)
  })
})
