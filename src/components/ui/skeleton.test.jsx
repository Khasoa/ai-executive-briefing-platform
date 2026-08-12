import { describe, expect, it } from "vitest"
import { render } from "@testing-library/react"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { dirname, resolve } from "node:path"
import { Skeleton } from "@/components/ui/skeleton"
import { OverviewSkeleton, ListSkeleton, DocumentSkeleton, AskSkeleton } from "@/components/feedback/PageState"

const cssPath = resolve(dirname(fileURLToPath(import.meta.url)), "../../index.css")

describe("Skeleton theme awareness", () => {
  it("uses theme tokens rather than hard-coded light backgrounds", () => {
    const { container } = render(<Skeleton className="h-8 w-24" />)
    const node = container.querySelector("[data-testid='skeleton']")
    expect(node).toBeTruthy()
    expect(node.className).toContain("shimmer")
    expect(node.className).toContain("bg-muted")
    expect(node.className).not.toMatch(/bg-white|bg-#|text-white/)
  })

  it("shimmer utility is defined with CSS variables for dark mode", () => {
    const css = readFileSync(cssPath, "utf8")
    const match = css.match(/\.shimmer\s*\{([^}]+)\}/)
    expect(match).toBeTruthy()
    const block = match[1]
    expect(block).toContain("var(--color-muted)")
    expect(block).not.toMatch(/#f1f1ef|#f7f7f5|#ffffff|\b#fff\b/)
  })

  it("page skeletons render intentional placeholders with aria-busy", () => {
    const cases = [
      [<OverviewSkeleton key="o" />, "Loading overview"],
      [<ListSkeleton key="l" rows={2} />, "Loading"],
      [<DocumentSkeleton key="d" />, "Loading morning brief"],
      [<AskSkeleton key="a" />, "Loading Ask Briefly"],
    ]
    for (const [ui, label] of cases) {
      const { container, unmount } = render(ui)
      const root = container.firstChild
      expect(root.getAttribute("aria-busy")).toBe("true")
      expect(root.getAttribute("aria-label")).toBe(label)
      expect(container.querySelectorAll("[data-testid='skeleton']").length).toBeGreaterThan(0)
      unmount()
    }
  })
})
