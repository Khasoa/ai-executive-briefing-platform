import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { IntegrationCard } from "@/components/cards/IntegrationCard"

const base = {
  id: "gohighlevel",
  name: "GoHighLevel",
  category: "CRM",
  description: "Pipeline",
  account: null,
  lastSyncLabel: "Never",
  scopes: ["opportunities.readonly"],
  metrics: [
    { label: "Opportunities", value: "—" },
    { label: "Pipeline", value: "—" },
  ],
  poweredBy: "GoHighLevel API",
}

describe("IntegrationCard work management", () => {
  it("shows Connect for monday.com when disconnected", () => {
    render(
      <IntegrationCard
        integration={{
          id: "monday",
          name: "monday.com",
          category: "Work management",
          description: "Boards",
          status: "not-connected",
          account: null,
          lastSyncLabel: "Never",
          scopes: ["boards:read"],
          metrics: [{ label: "Items", value: "—" }],
          poweredBy: "monday.com API",
        }}
        onConnect={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: /connect monday.com/i })).toBeEnabled()
  })

  it("shows Sync for ClickUp when connected", async () => {
    const user = userEvent.setup()
    const onSync = vi.fn()
    render(
      <IntegrationCard
        integration={{
          id: "clickup",
          name: "ClickUp",
          category: "Work management",
          description: "Tasks",
          status: "connected",
          account: "Team One",
          lastSyncLabel: "1 hour ago",
          scopes: ["tasks.read"],
          metrics: [{ label: "Tasks", value: "12" }],
          poweredBy: "ClickUp API",
        }}
        onSync={onSync}
        onDisconnect={vi.fn()}
      />,
    )
    await user.click(screen.getByRole("button", { name: /sync clickup/i }))
    expect(onSync).toHaveBeenCalledWith("clickup")
  })
})

describe("IntegrationCard GoHighLevel", () => {
  it("shows Connect when disconnected", () => {
    render(
      <IntegrationCard
        integration={{ ...base, status: "not-connected" }}
        onConnect={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: /connect gohighlevel/i })).toBeEnabled()
  })

  it("shows Sync and Disconnect when connected", async () => {
    const user = userEvent.setup()
    const onSync = vi.fn()
    const onDisconnect = vi.fn()
    render(
      <IntegrationCard
        integration={{
          ...base,
          status: "connected",
          account: "Location loc-1",
          lastSyncLabel: "2 minutes ago",
        }}
        onSync={onSync}
        onDisconnect={onDisconnect}
      />,
    )
    expect(screen.getByRole("button", { name: /sync gohighlevel/i })).toBeEnabled()
    await user.click(screen.getByRole("button", { name: /sync gohighlevel/i }))
    expect(onSync).toHaveBeenCalledWith("gohighlevel")
    await user.click(screen.getByRole("button", { name: /disconnect gohighlevel/i }))
    expect(onDisconnect).toHaveBeenCalled()
  })

  it("shows syncing state", () => {
    render(
      <IntegrationCard
        integration={{ ...base, status: "syncing", account: "Location loc-1" }}
        syncing
      />,
    )
    expect(screen.getByText("Syncing")).toBeInTheDocument()
  })

  it("shows error badge", () => {
    render(<IntegrationCard integration={{ ...base, status: "error" }} />)
    expect(screen.getByText("Sync failed")).toBeInTheDocument()
  })

  it("shows Check configuration for OpenAI api_key auth", async () => {
    const user = userEvent.setup()
    const onCheck = vi.fn()
    render(
      <IntegrationCard
        integration={{
          id: "openai",
          name: "OpenAI",
          category: "Intelligence",
          description: "Briefs",
          status: "configured",
          authType: "api_key",
          account: "Server API key",
          lastSyncLabel: "Ready",
          statusDetail: "Model gpt-4.1-mini",
          scopes: ["responses.write"],
          metrics: [{ label: "Model", value: "gpt-4.1-mini" }],
          poweredBy: "OpenAI Platform",
          canSync: false,
          canConnect: false,
          canCheck: true,
        }}
        onCheck={onCheck}
      />,
    )
    expect(screen.getByText("Configured")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /connect openai/i })).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /check openai configuration/i }))
    expect(onCheck).toHaveBeenCalledWith("openai")
  })
})
