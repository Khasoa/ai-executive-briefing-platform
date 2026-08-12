import { describe, expect, it, vi, afterEach } from "vitest"
import { cleanup, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { IntegrationCard } from "@/components/cards/IntegrationCard"
import { resolveOAuthStartProvider } from "@/lib/oauthConnect"

const oauthCards = [
  {
    id: "notion",
    name: "Notion",
    category: "Knowledge",
    description: "Docs",
    status: "not-connected",
    authType: "oauth",
    account: null,
    lastSyncLabel: "Never",
    scopes: ["read_content"],
    metrics: [{ label: "Pages", value: "—" }],
    poweredBy: "Notion API",
    canConnect: true,
    canSync: false,
  },
  {
    id: "gohighlevel",
    name: "GoHighLevel",
    category: "CRM",
    description: "Pipeline",
    status: "not-connected",
    authType: "oauth",
    account: null,
    lastSyncLabel: "Never",
    scopes: ["opportunities.readonly"],
    metrics: [{ label: "Opportunities", value: "—" }],
    poweredBy: "GoHighLevel API",
    canConnect: true,
    canSync: false,
  },
  {
    id: "monday",
    name: "monday.com",
    category: "Work management",
    description: "Boards",
    status: "not-connected",
    authType: "oauth",
    account: null,
    lastSyncLabel: "Never",
    scopes: ["boards:read"],
    metrics: [{ label: "Items", value: "—" }],
    poweredBy: "monday.com API",
    canConnect: true,
    canSync: false,
  },
  {
    id: "clickup",
    name: "ClickUp",
    category: "Work management",
    description: "Tasks",
    status: "not-connected",
    authType: "oauth",
    account: null,
    lastSyncLabel: "Never",
    scopes: ["tasks.read"],
    metrics: [{ label: "Tasks", value: "—" }],
    poweredBy: "ClickUp API",
    canConnect: true,
    canSync: false,
  },
]

describe("Integration OAuth connect isolation", () => {
  afterEach(() => {
    cleanup()
  })

  it("only the clicked card enters connecting state", async () => {
    const user = userEvent.setup()
    const onConnect = vi.fn()
    const connectingId = "notion"

    render(
      <div>
        {oauthCards.map((integration) => (
          <IntegrationCard
            key={integration.id}
            integration={integration}
            onConnect={onConnect}
            connecting={connectingId === integration.id}
          />
        ))}
      </div>,
    )

    const notionBtn = screen.getByRole("button", { name: /connect notion/i })
    expect(notionBtn).toBeDisabled()
    expect(notionBtn).toHaveTextContent(/redirecting/i)
    expect(screen.getByRole("button", { name: /connect gohighlevel/i })).toBeEnabled()
    expect(screen.getByRole("button", { name: /connect monday.com/i })).toBeEnabled()
    expect(screen.getByRole("button", { name: /connect clickup/i })).toBeEnabled()

    await user.click(screen.getByRole("button", { name: /connect gohighlevel/i }))
    expect(onConnect).toHaveBeenCalledTimes(1)
    expect(onConnect).toHaveBeenCalledWith("gohighlevel")
    expect(resolveOAuthStartProvider("gohighlevel")).toBe("gohighlevel")
  })

  it.each([
    ["notion", "notion"],
    ["gohighlevel", "gohighlevel"],
    ["monday", "monday"],
    ["clickup", "clickup"],
  ])("Connect %s routes to %s OAuth only", async (cardId, provider) => {
    const user = userEvent.setup()
    const onConnect = vi.fn()
    const card = oauthCards.find((c) => c.id === cardId)
    render(<IntegrationCard integration={card} onConnect={onConnect} />)
    await user.click(screen.getByRole("button", { name: new RegExp(`connect ${card.name}`, "i") }))
    expect(onConnect).toHaveBeenCalledWith(cardId)
    expect(resolveOAuthStartProvider(cardId)).toBe(provider)
  })

  it("does not show Redirecting on sibling cards when one is connecting", () => {
    render(
      <div>
        <IntegrationCard integration={oauthCards[0]} connecting onConnect={vi.fn()} />
        <IntegrationCard integration={oauthCards[1]} connecting={false} onConnect={vi.fn()} />
      </div>,
    )
    const notionBtn = screen.getByRole("button", { name: /connect notion/i })
    expect(notionBtn).toBeDisabled()
    expect(notionBtn).toHaveTextContent(/redirecting/i)
    const ghlBtn = screen.getByRole("button", { name: /connect gohighlevel/i })
    expect(ghlBtn).toBeEnabled()
    expect(ghlBtn).toHaveTextContent(/connect gohighlevel/i)
  })
})
