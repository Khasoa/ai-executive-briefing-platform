import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { WeeklyDigestPage } from "@/pages/WeeklyDigest"

vi.mock("@/hooks/useToast", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}))

vi.mock("@/api/weeklyDigest", () => ({
  getWeeklyDigest: vi.fn(),
  regenerateWeeklyDigest: vi.fn(),
}))

import { getWeeklyDigest } from "@/api/weeklyDigest"

const populated = {
  id: "wd_1",
  weekStart: "2026-08-02",
  weekEnd: "2026-08-08",
  weekLabel: "Aug 2 – 8, 2026",
  headline: "A focused week around renewals",
  summary: "Three threads dominated the inbox.",
  weekSummary: "Three threads dominated the inbox.",
  importantConversations: [
    {
      id: "i1",
      title: "Meridian renewal",
      detail: "Competitor quote in thread",
      source: "Gmail",
      emailIds: ["em_1"],
      kind: "fact",
    },
  ],
  decisionsAndApprovals: [],
  followUps: [],
  unresolvedItems: [],
  notableActivity: [],
  carryIntoNextWeek: [
    {
      id: "c1",
      title: "Close Meridian",
      detail: "Decide before Friday",
      source: "Gmail",
      emailIds: ["em_1"],
      kind: "fact",
    },
  ],
  nextWeekOutlook: {
    upcomingMeetings: [
      {
        id: "m1",
        title: "Board sync",
        detail: "Tuesday 10:00",
        source: "Google Calendar",
        kind: "fact",
      },
    ],
    upcomingDeadlines: [],
    overdueWork: [],
    crmAttention: [],
    emailFollowUps: [],
    workItems: [],
    carryForward: [],
    recommendedPriorities: [
      {
        id: "r1",
        title: "Protect Monday morning",
        detail: "Clear renewals first",
        source: "OpenAI",
        kind: "recommendation",
      },
    ],
    risksAndWatchouts: [],
    workloadSignals: [],
  },
  dataCoverage: {
    emailCount: 8,
    emailSummariesAvailable: true,
    emailNote: "",
    sourcesWithData: ["Gmail", "Google Calendar"],
  },
  planningNote: "Protect Monday morning.",
  confidence: "high",
  generatedBy: "openai",
  sources: ["Gmail", "OpenAI"],
  emailCount: 8,
  generatedAt: "2026-08-08T10:00:00Z",
  generatedLabel: "just now",
}

function renderPage() {
  return render(
    <MemoryRouter>
      <WeeklyDigestPage />
    </MemoryRouter>,
  )
}

describe("WeeklyDigestPage", () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it("shows a theme-aware loading skeleton", async () => {
    getWeeklyDigest.mockReturnValue(new Promise(() => {}))
    const { container } = renderPage()
    expect(screen.getByLabelText("Loading weekly digest")).toBeInTheDocument()
    expect(container.querySelectorAll("[data-testid='skeleton']").length).toBeGreaterThan(0)
    expect(container.querySelector(".shimmer")).toBeTruthy()
  })

  it("renders a populated digest", async () => {
    getWeeklyDigest.mockResolvedValueOnce(populated)
    renderPage()
    await waitFor(() => expect(screen.getByText(populated.headline)).toBeInTheDocument())
    expect(screen.getByText("What happened this week")).toBeInTheDocument()
    expect(screen.getByText("Important conversations")).toBeInTheDocument()
    expect(screen.getByText("Meridian renewal")).toBeInTheDocument()
    expect(screen.getByText("Next week outlook")).toBeInTheDocument()
    expect(screen.getByText("Board sync")).toBeInTheDocument()
    expect(screen.getByText("Protect Monday morning.")).toBeInTheDocument()
  })

  it("shows empty state when there is no activity", async () => {
    getWeeklyDigest.mockResolvedValueOnce({
      ...populated,
      emailCount: 0,
      importantConversations: [],
      carryIntoNextWeek: [],
      nextWeekOutlook: {},
      dataCoverage: { sourcesWithData: [] },
      sources: [],
      summary: "",
      headline: "Quiet",
    })
    renderPage()
    await waitFor(() =>
      expect(screen.getByText("No weekly activity yet")).toBeInTheDocument(),
    )
  })

  it("shows error state", async () => {
    getWeeklyDigest.mockRejectedValueOnce(Object.assign(new Error("Network down"), { name: "TypeError" }))
    renderPage()
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument(),
    )
  })
})
