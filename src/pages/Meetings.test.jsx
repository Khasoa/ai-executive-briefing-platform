import { afterEach, describe, expect, it, vi } from "vitest"
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { MeetingsPage } from "@/pages/Meetings"

vi.mock("@/api/meetings", () => ({
  getMeetings: vi.fn(),
}))

import { getMeetings } from "@/api/meetings"

const payload = {
  date: "Tuesday, August 11, 2026",
  meetingCount: 1,
  needsPreparation: 1,
  totalScheduledMinutes: 45,
  todayCount: 1,
  needsPreparationToday: 1,
  meetings: [
    {
      id: "m_today",
      title: "Client Success Review",
      startTime: "10:00",
      endTime: "10:45",
      duration: "45 min",
      type: "client",
      location: "Zoom",
      prepStatus: "needs-prep",
      prepReason: "Imported",
      prepRecommended: true,
      prepStatusLabel: "Prepare today",
      window: "today",
      timingLabel: "Today · Aug 11",
      relativeLabel: "in 2h",
      dateLabel: "Aug 11",
      whyItMatters: "Customer relationship review with Globex Corp.",
      suggestedPrepActions: ["Review recent customer emails"],
      prepHighlights: ["Prepare today", "1 related email(s)"],
      attendees: [{ name: "Alex", role: "CSM", company: "Globex", avatar: "A" }],
      agenda: ["Status"],
      company: { name: "Globex Corp", industry: "", size: "", relationship: "", background: "" },
      relatedEmails: [],
      preparationNotes: [],
      talkingPoints: [],
      recommendedQuestions: [],
      risks: [],
      sources: ["Google Calendar"],
    },
    {
      id: "m_week",
      title: "Team Planning",
      startTime: "14:00",
      endTime: "14:45",
      duration: "45 min",
      type: "internal",
      location: "",
      prepStatus: "needs-prep",
      prepReason: "",
      prepRecommended: false,
      prepStatusLabel: "Preparation not yet needed",
      window: "this_week",
      timingLabel: "In 3 days · Aug 14",
      weekdayDateLabel: "Friday, Aug 14",
      relativeLabel: "In 3 days",
      dateLabel: "Aug 14",
      attendees: [],
      agenda: [],
      company: { name: "", industry: "", size: "", relationship: "", background: "" },
      relatedEmails: [],
      preparationNotes: [],
      talkingPoints: [],
      recommendedQuestions: [],
      risks: [],
      sources: ["Google Calendar"],
    },
    {
      id: "m_month",
      title: "Monthly GHMe Content Writers Call",
      startTime: "14:00",
      endTime: "14:45",
      duration: "45 min",
      type: "internal",
      location: "",
      prepStatus: "needs-prep",
      prepReason: "",
      prepRecommended: false,
      prepStatusLabel: "Preparation not yet needed",
      window: "this_month",
      timingLabel: "In 19 days · Aug 30",
      weekdayDateLabel: "Sunday, Aug 30",
      isRecurring: true,
      recurringLabel: "Recurring monthly",
      attendees: [],
      agenda: ["Recurring series — agenda details omitted for this occurrence."],
      company: { name: "", industry: "", size: "", relationship: "", background: "" },
      relatedEmails: [],
      preparationNotes: [],
      talkingPoints: [],
      recommendedQuestions: [],
      risks: [],
      sources: ["Google Calendar"],
    },
    {
      id: "m_later",
      title: "Q4 Planning Offsite",
      startTime: "09:00",
      endTime: "17:00",
      duration: "8h",
      type: "internal",
      location: "",
      prepStatus: "needs-prep",
      prepReason: "",
      prepRecommended: false,
      prepStatusLabel: "Preparation not yet needed",
      window: "later",
      timingLabel: "In 45 days · Sep 28",
      weekdayDateLabel: "Monday, Sep 28",
      isRecurring: false,
      attendees: [],
      agenda: [],
      company: { name: "", industry: "", size: "", relationship: "", background: "" },
      relatedEmails: [],
      preparationNotes: [],
      talkingPoints: [],
      recommendedQuestions: [],
      risks: [],
      sources: ["Google Calendar"],
    },
  ],
  windows: {
    today: null,
    tomorrow: [],
    thisWeek: [],
    thisMonth: [],
    later: [],
    past: [],
  },
}

// Fill windows from meetings for the page helper.
payload.windows.today = [payload.meetings[0]]
payload.windows.thisWeek = [payload.meetings[1]]
payload.windows.thisMonth = [payload.meetings[2]]
payload.windows.later = [payload.meetings[3]]

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe("MeetingsPage hierarchy", () => {
  it("renders Today / This week / This month sections with timing labels", async () => {
    getMeetings.mockResolvedValue(payload)
    const { container } = render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>,
    )

    expect(await screen.findByRole("heading", { name: /Today/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /This week/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /This month/i })).toBeInTheDocument()
    expect(screen.getByText("Client Success Review")).toBeInTheDocument()
    expect(screen.getByText(/Today · Aug 11/)).toBeInTheDocument()
    expect(screen.getByText("Team Planning")).toBeInTheDocument()
    expect(screen.getAllByText(/Prepare today/i).length).toBeGreaterThan(0)

    // Future meeting should not claim prepare-today as its primary badge.
    const weekTitle = screen.getByText("Team Planning")
    const weekCardRoot = weekTitle.closest(".overflow-hidden") || weekTitle.closest("div")
    expect(weekCardRoot).toBeTruthy()
    expect(within(weekCardRoot).queryByText("Prepare today")).toBeNull()

    // No horizontal overflow utilities missing: page root clips overflow.
    expect(container.querySelector(".overflow-x-hidden")).toBeTruthy()
  })

  it("does not merge later meetings into This month", async () => {
    getMeetings.mockResolvedValue(payload)
    render(
      <MemoryRouter>
        <MeetingsPage />
      </MemoryRouter>,
    )

    const laterHeading = await screen.findByRole("heading", { name: /Later/i })
    fireEvent.click(laterHeading.closest("button"))
    const monthHeading = screen.getByRole("heading", { name: /This month/i })
    fireEvent.click(monthHeading.closest("button"))

    expect(screen.getByText("Q4 Planning Offsite")).toBeInTheDocument()

    const monthSection = monthHeading.closest("section")
    expect(within(monthSection).queryByText("Q4 Planning Offsite")).toBeNull()
    expect(within(monthSection).getByText("Monthly GHMe Content Writers Call")).toBeInTheDocument()

    const laterSection = laterHeading.closest("section")
    expect(within(laterSection).getByText("Q4 Planning Offsite")).toBeInTheDocument()
  })
})
