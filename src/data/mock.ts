export const user = {
  name: "Lydia",
  role: "CEO & Founder",
  company: "Meridian Labs",
  avatar: "L",
}

export const executiveSummary = {
  generatedAt: "6:30 AM",
  summary:
    "Today is high-stakes. Your Series B term sheet from Horizon Ventures needs a response by EOD, and the Acme Corp deal is at a critical negotiation point. Three investor emails are waiting, and your 2 PM board prep session requires the Q2 metrics deck — which is 80% complete.",
  priorities: [
    { id: "1", text: "Review & respond to Horizon Ventures term sheet", urgency: "critical" },
    { id: "2", text: "Finalize Q2 board deck before 2 PM prep session", urgency: "high" },
    { id: "3", text: "Approve revised Acme Corp enterprise proposal", urgency: "high" },
    { id: "4", text: "Prep talking points for TechCrunch interview", urgency: "medium" },
  ],
}

export const kpis = [
  {
    id: "inbox",
    label: "Inbox",
    value: "12",
    sublabel: "need attention",
    change: "+3 since yesterday",
    trend: "up" as const,
    icon: "inbox" as const,
    color: "indigo",
  },
  {
    id: "calendar",
    label: "Calendar",
    value: "4",
    sublabel: "meetings today",
    change: "2.5 hrs free",
    trend: "neutral" as const,
    icon: "calendar" as const,
    color: "blue",
  },
  {
    id: "crm",
    label: "CRM Pipeline",
    value: "$4.2M",
    sublabel: "active pipeline",
    change: "+$380K this week",
    trend: "up" as const,
    icon: "pipeline" as const,
    color: "emerald",
  },
  {
    id: "projects",
    label: "Projects",
    value: "7",
    sublabel: "active initiatives",
    change: "2 at risk",
    trend: "down" as const,
    icon: "projects" as const,
    color: "amber",
  },
]

export const aiRecommendations = [
  {
    id: "1",
    title: "Respond to Horizon Ventures first",
    description:
      "Their term sheet expires Friday. A prompt response signals confidence and keeps leverage on valuation terms.",
    action: "Draft response",
    priority: "high",
  },
  {
    id: "2",
    title: "Delegate board deck data pulls",
    description:
      "Finance metrics are the bottleneck. Assign to Sarah — she has the latest ARR and churn data ready.",
    action: "Assign to Sarah",
    priority: "medium",
  },
  {
    id: "3",
    title: "Block 30 min before Acme call",
    description:
      "Review their latest redlines and prepare a concession strategy on the SLA terms.",
    action: "Add to calendar",
    priority: "medium",
  },
]

export const meetings = [
  {
    id: "1",
    title: "Daily Leadership Standup",
    time: "9:00 AM",
    duration: "30 min",
    attendees: ["Sarah Chen", "Marcus Webb", "Elena Park"],
    type: "internal",
    location: "Zoom",
  },
  {
    id: "2",
    title: "Acme Corp — Contract Negotiation",
    time: "11:00 AM",
    duration: "45 min",
    attendees: ["James Liu (Acme)", "Marcus Webb"],
    type: "client",
    location: "Google Meet",
  },
  {
    id: "3",
    title: "Board Deck Prep",
    time: "2:00 PM",
    duration: "60 min",
    attendees: ["Sarah Chen", "Elena Park"],
    type: "internal",
    location: "Conference Room A",
  },
  {
    id: "4",
    title: "Horizon Ventures — Partner Call",
    time: "4:30 PM",
    duration: "30 min",
    attendees: ["David Park (Horizon)", "Elena Park"],
    type: "investor",
    location: "Phone",
  },
]

export const activities = [
  {
    id: "1",
    type: "email",
    title: "David Park replied to term sheet thread",
    time: "25 min ago",
    icon: "mail",
  },
  {
    id: "2",
    type: "deal",
    title: "Acme Corp moved to Negotiation stage",
    time: "1 hr ago",
    icon: "trending",
  },
  {
    id: "3",
    type: "project",
    title: "Q2 Board Deck updated by Sarah Chen",
    time: "2 hrs ago",
    icon: "file",
  },
  {
    id: "4",
    type: "meeting",
    title: "Leadership standup notes shared",
    time: "3 hrs ago",
    icon: "calendar",
  },
  {
    id: "5",
    type: "crm",
    title: "New lead: Vertex Systems ($120K)",
    time: "5 hrs ago",
    icon: "user",
  },
]

export const dailyBrief = {
  date: "Wednesday, July 15, 2026",
  greeting: "Here's your executive briefing for today.",
  sections: {
    priorities: [
      "Close Horizon Ventures term sheet negotiation — response needed by 6 PM",
      "Finalize and approve Q2 board presentation (80% complete)",
      "Navigate Acme Corp SLA concessions in today's 11 AM call",
      "Prepare key messages for tomorrow's TechCrunch interview",
    ],
    meetings: [
      { time: "9:00 AM", title: "Leadership Standup", note: "Discuss hiring plan delays" },
      { time: "11:00 AM", title: "Acme Corp Negotiation", note: "SLA terms are the blocker — prepare 2 concession options" },
      { time: "2:00 PM", title: "Board Deck Prep", note: "Sarah has metrics; you need to add strategic narrative" },
      { time: "4:30 PM", title: "Horizon Ventures Call", note: "Confirm valuation range before signing" },
    ],
    pipeline: [
      { company: "Acme Corp", stage: "Negotiation", value: "$850K", note: "85% probability — close expected this week" },
      { company: "Vertex Systems", stage: "Discovery", value: "$120K", note: "New inbound — schedule intro call" },
      { company: "Northwind Digital", stage: "Proposal", value: "$340K", note: "Awaiting legal review on MSA" },
      { company: "Pinnacle Health", stage: "Qualified", value: "$520K", note: "Champion identified — demo scheduled Friday" },
    ],
    deadlines: [
      { item: "Horizon Ventures term sheet response", due: "Today, 6:00 PM", status: "urgent" },
      { item: "Q2 Board presentation final", due: "Thursday, 9:00 AM", status: "high" },
      { item: "Acme Corp contract signature", due: "Friday, EOD", status: "high" },
      { item: "Engineering hiring plan", due: "Next Monday", status: "medium" },
    ],
    risks: [
      {
        title: "Acme Corp SLA impasse",
        description: "Their legal team is pushing for 99.99% uptime SLA. Our standard is 99.9%. Risk of losing $850K deal.",
        severity: "high",
      },
      {
        title: "Board deck incomplete",
        description: "Strategic narrative section is empty. Board meeting is in 48 hours.",
        severity: "high",
      },
      {
        title: "Engineering attrition",
        description: "Two senior engineers gave notice this week. Hiring plan needs acceleration.",
        severity: "medium",
      },
    ],
    suggestedActions: [
      "Send Horizon Ventures a counter-proposal with 15% higher valuation and standard protective provisions",
      "Block 1 hour this afternoon to write the board deck strategic narrative",
      "Prepare two SLA concession packages for Acme: enhanced support tier vs. partial uptime credit",
      "Schedule 1:1 with departing engineers to understand root causes",
    ],
  },
}

export type EmailCategory = "urgent" | "clients" | "investors" | "finance" | "internal" | "newsletters"

export interface Email {
  id: string
  from: string
  subject: string
  summary: string
  time: string
  unread: boolean
  actionRequired?: boolean
}

export const inboxCategories: { id: EmailCategory; label: string; count: number; emails: Email[] }[] = [
  {
    id: "urgent",
    label: "Urgent",
    count: 2,
    emails: [
      {
        id: "e1",
        from: "David Park",
        subject: "Re: Series B Term Sheet — Final Terms",
        summary:
          "Horizon Ventures has sent final terms: $18M at $90M pre-money. They need your signature by Friday. Key change: 1x liquidation preference (non-participating).",
        time: "25 min ago",
        unread: true,
        actionRequired: true,
      },
      {
        id: "e2",
        from: "James Liu",
        subject: "Acme Corp — Revised SLA Requirements",
        summary:
          "Acme's legal team is insisting on 99.99% uptime SLA with financial penalties. James suggests a call today to find middle ground before the 11 AM meeting.",
        time: "1 hr ago",
        unread: true,
        actionRequired: true,
      },
    ],
  },
  {
    id: "clients",
    label: "Clients",
    count: 3,
    emails: [
      {
        id: "e3",
        from: "Rachel Kim",
        subject: "Northwind Digital — MSA Review Complete",
        summary:
          "Legal has approved the MSA with minor redlines on data residency. Rachel is ready to move to signature pending your approval.",
        time: "2 hrs ago",
        unread: true,
      },
      {
        id: "e4",
        from: "Tom Bradley",
        subject: "Pinnacle Health — Demo Feedback",
        summary:
          "Pinnacle's CTO loved the platform demo. They're requesting a custom integration proposal for their EHR system. High intent signal.",
        time: "4 hrs ago",
        unread: false,
      },
      {
        id: "e5",
        from: "Lisa Wong",
        subject: "Globex Inc — Renewal Discussion",
        summary:
          "Globex wants to discuss expanding their license from 50 to 200 seats. Potential upsell of $180K ARR.",
        time: "Yesterday",
        unread: false,
      },
    ],
  },
  {
    id: "investors",
    label: "Investors",
    count: 2,
    emails: [
      {
        id: "e6",
        from: "David Park",
        subject: "Horizon Ventures — Partner Introduction",
        summary:
          "David wants to introduce you to their portfolio ops team for GTM scaling support post-close. Positive signal for deal momentum.",
        time: "3 hrs ago",
        unread: true,
      },
      {
        id: "e7",
        from: "Maria Santos",
        subject: "Summit Capital — Q2 Portfolio Update Request",
        summary:
          "Your existing investor Summit Capital is requesting a brief Q2 update ahead of their LP meeting next week.",
        time: "Yesterday",
        unread: false,
      },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    count: 2,
    emails: [
      {
        id: "e8",
        from: "Sarah Chen",
        subject: "June Financial Close — Final Numbers",
        summary:
          "June ARR: $3.2M (+8% MoM). Net revenue retention: 118%. Burn rate: $420K/month. Runway: 22 months post-Series B.",
        time: "6 hrs ago",
        unread: false,
      },
      {
        id: "e9",
        from: "QuickBooks",
        subject: "Invoice #4821 — Payment Received",
        summary: "Globex Inc paid invoice #4821 ($24,500) for Q2 license renewal. Payment processed successfully.",
        time: "Yesterday",
        unread: false,
      },
    ],
  },
  {
    id: "internal",
    label: "Internal",
    count: 2,
    emails: [
      {
        id: "e10",
        from: "Marcus Webb",
        subject: "Engineering — Attrition Update",
        summary:
          "Two senior engineers (Alex and Priya) submitted resignations. Marcus recommends immediate retention conversations and accelerated hiring.",
        time: "5 hrs ago",
        unread: true,
        actionRequired: true,
      },
      {
        id: "e11",
        from: "Elena Park",
        subject: "All-Hands Agenda — July 18",
        summary:
          "Elena drafted the July all-hands agenda: Series B announcement, product roadmap, and team recognition. Needs your review.",
        time: "Yesterday",
        unread: false,
      },
    ],
  },
  {
    id: "newsletters",
    label: "Newsletters",
    count: 3,
    emails: [
      {
        id: "e12",
        from: "a16z",
        subject: "The State of AI Infrastructure 2026",
        summary: "a16z's annual report on AI infra trends. Relevant section on enterprise AI adoption patterns and pricing models.",
        time: "Today",
        unread: false,
      },
      {
        id: "e13",
        from: "TechCrunch",
        subject: "Your interview is confirmed for Thursday",
        summary: "TechCrunch confirmed your founder spotlight interview for Thursday at 10 AM. They'll send prep questions today.",
        time: "Yesterday",
        unread: false,
      },
      {
        id: "e14",
        from: "First Round Review",
        subject: "How Top Founders Run Their Week",
        summary: "Case study on executive time management from three unicorn founders. Includes a framework for 'CEO mode' vs 'manager mode'.",
        time: "2 days ago",
        unread: false,
      },
    ],
  },
]

export interface Opportunity {
  id: string
  company: string
  logo: string
  stage: string
  probability: number
  value: number
  owner: string
  lastActivity: string
  aiSummary: string
  tags: string[]
}

export const opportunities: Opportunity[] = [
  {
    id: "1",
    company: "Acme Corp",
    logo: "AC",
    stage: "Negotiation",
    probability: 85,
    value: 850000,
    owner: "Marcus Webb",
    lastActivity: "2 hours ago",
    aiSummary:
      "Deal is at the finish line. SLA terms are the only blocker — Acme wants 99.99% uptime. Recommend offering enhanced support tier as alternative to uptime guarantee. Close likely this week if resolved today.",
    tags: ["Enterprise", "Strategic"],
  },
  {
    id: "2",
    company: "Pinnacle Health",
    logo: "PH",
    stage: "Qualified",
    probability: 60,
    value: 520000,
    owner: "Elena Park",
    lastActivity: "4 hours ago",
    aiSummary:
      "Strong champion in CTO Tom Bradley. Demo went exceptionally well. Next step: custom EHR integration proposal. Healthcare vertical expansion opportunity.",
    tags: ["Healthcare", "Expansion"],
  },
  {
    id: "3",
    company: "Northwind Digital",
    logo: "ND",
    stage: "Proposal",
    probability: 70,
    value: 340000,
    owner: "Marcus Webb",
    lastActivity: "2 hours ago",
    aiSummary:
      "MSA legal review complete with minor data residency redlines. Rachel Kim is ready to sign. Low friction close — approve and send for signature.",
    tags: ["Mid-Market"],
  },
  {
    id: "4",
    company: "Vertex Systems",
    logo: "VS",
    stage: "Discovery",
    probability: 25,
    value: 120000,
    owner: "Elena Park",
    lastActivity: "5 hours ago",
    aiSummary:
      "New inbound lead from website demo request. Company is a 200-person SaaS firm. Schedule intro call this week to qualify budget and timeline.",
    tags: ["Inbound", "New"],
  },
  {
    id: "5",
    company: "Globex Inc",
    logo: "GI",
    stage: "Closed Won",
    probability: 100,
    value: 180000,
    owner: "Marcus Webb",
    lastActivity: "Yesterday",
    aiSummary:
      "Existing customer requesting license expansion from 50 to 200 seats. Upsell opportunity worth $180K additional ARR. Lisa Wong is driving the conversation.",
    tags: ["Upsell", "Existing"],
  },
  {
    id: "6",
    company: "Cascade Analytics",
    logo: "CA",
    stage: "Proposal",
    probability: 45,
    value: 275000,
    owner: "Elena Park",
    lastActivity: "3 days ago",
    aiSummary:
      "Proposal sent 3 days ago with no response. Follow-up recommended — Cascade is evaluating two competitors. Decision expected by month end.",
    tags: ["Competitive"],
  },
]

export const chatSuggestions = [
  "What needs my attention today?",
  "Summarize my sales pipeline",
  "Draft a response to Horizon Ventures",
  "What are the risks in my calendar this week?",
  "Prepare me for the Acme Corp call",
]

export const chatHistory = [
  {
    id: "1",
    role: "assistant" as const,
    content:
      "Good morning, Lydia. I'm Atlas, your AI executive partner. I'm connected to your email, calendar, CRM, and project tools. What would you like to focus on today?",
  },
]

export const projects = [
  { id: "1", name: "Series B Fundraise", status: "On Track", progress: 85, owner: "Lydia", dueDate: "Jul 18" },
  { id: "2", name: "Q2 Board Presentation", status: "At Risk", progress: 80, owner: "Sarah Chen", dueDate: "Jul 17" },
  { id: "3", name: "Enterprise Platform v2.0", status: "On Track", progress: 62, owner: "Marcus Webb", dueDate: "Aug 15" },
  { id: "4", name: "Engineering Hiring Plan", status: "At Risk", progress: 40, owner: "Marcus Webb", dueDate: "Jul 21" },
  { id: "5", name: "Healthcare Vertical Launch", status: "On Track", progress: 55, owner: "Elena Park", dueDate: "Sep 1" },
  { id: "6", name: "TechCrunch PR Campaign", status: "On Track", progress: 70, owner: "Elena Park", dueDate: "Jul 16" },
  { id: "7", name: "SOC 2 Type II Audit", status: "On Track", progress: 90, owner: "Sarah Chen", dueDate: "Jul 30" },
]

export const researchItems = [
  {
    id: "1",
    title: "AI Infrastructure Market Landscape 2026",
    source: "a16z",
    summary: "Enterprise AI adoption growing 3x YoY. Key trend: vertical-specific AI agents replacing generic chatbots.",
    relevance: "high",
    date: "Today",
  },
  {
    id: "2",
    title: "Competitor Analysis: DataForge AI",
    source: "Atlas Research",
    summary: "DataForge raised $40M Series B last month. They're targeting healthcare — direct overlap with Pinnacle Health deal.",
    relevance: "high",
    date: "Yesterday",
  },
  {
    id: "3",
    title: "Enterprise SLA Benchmarks",
    source: "Gartner",
    summary: "Industry standard for SaaS uptime SLAs is 99.9%. Only 12% of vendors offer 99.99%. Premium pricing justified.",
    relevance: "high",
    date: "2 days ago",
  },
  {
    id: "4",
    title: "Founder Time Management Frameworks",
    source: "First Round Review",
    summary: "Top founders spend 60% of time on external (sales, fundraising) and 40% on internal (team, product) activities.",
    relevance: "medium",
    date: "2 days ago",
  },
]
