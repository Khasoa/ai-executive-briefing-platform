"""In-memory dataset backing the Briefly API.

Every value here mirrors the shape a real integration (Gmail, Google Calendar,
GoHighLevel, Notion) would return once wired up, so services can swap the source
without changing response schemas.
"""

BRIEF_DATE = "Tuesday, August 4, 2026"

USER = {
    "name": "Lydia",
    "fullName": "Lydia Reyes",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "email": "lydia@arcadiasystems.com",
    "avatar": "LR",
    "timezone": "Europe/Athens",
}

BRIEF_META = {
    "id": "brief_2026_08_04",
    "date": BRIEF_DATE,
    "generatedAt": "2026-08-04T06:30:00+03:00",
    "generatedLabel": "2 minutes ago",
    "confidence": "high",
    "sources": ["Gmail", "Google Calendar", "GoHighLevel", "Notion"],
    "headline": "Meridian Labs is the day. Everything else can wait until it is resolved.",
}

EXECUTIVE_SUMMARY_TEXT = (
    "Meridian Labs has gone quiet for nine days on a $480K renewal that closes Friday, and their "
    "champion forwarded a competitor's pricing sheet last night. That is the single decision that "
    "moves the quarter. Beyond it, the day is manageable: four meetings, two of which need real "
    "preparation, and six emails that genuinely need you rather than your team."
)

PRIORITIES = [
    {
        "id": "pri_1",
        "rank": 1,
        "title": "Decide the Meridian Labs renewal position before the 11:00 call",
        "detail": (
            "Nine days of silence, a competitor quote in the thread, and a Friday close date. "
            "You need a defended number and a walk-away line before you dial in."
        ),
        "urgency": "critical",
        "owner": "Lydia",
        "source": "GoHighLevel",
    },
    {
        "id": "pri_2",
        "rank": 2,
        "title": "Approve the Q3 hiring plan so recruiting can open two roles",
        "detail": (
            "Marcus has been blocked for four days. Two staff engineering offers expire if the "
            "requisitions are not open by Thursday."
        ),
        "urgency": "high",
        "owner": "Lydia",
        "source": "Notion",
    },
    {
        "id": "pri_3",
        "rank": 3,
        "title": "Send the board the July metrics narrative",
        "detail": (
            "Sarah has the numbers ready in Notion. Only the strategic commentary is missing, and "
            "the board reads on Wednesday evening."
        ),
        "urgency": "high",
        "owner": "Lydia",
        "source": "Notion",
    },
    {
        "id": "pri_4",
        "rank": 4,
        "title": "Answer Pinnacle Health on the security questionnaire scope",
        "detail": (
            "Their procurement team is waiting on one clarification to move to legal review. A "
            "two-line reply unblocks $520K."
        ),
        "urgency": "medium",
        "owner": "Lydia",
        "source": "Gmail",
    },
    {
        "id": "pri_5",
        "rank": 5,
        "title": "Confirm the September customer advisory board date",
        "detail": "Low effort, but three customers have asked twice and the venue holds expire Friday.",
        "urgency": "medium",
        "owner": "Elena Park",
        "source": "Google Calendar",
    },
]

RISKS = [
    {
        "id": "risk_1",
        "title": "Meridian Labs renewal is being competitively shopped",
        "detail": (
            "Their VP of Engineering forwarded a competitor pricing sheet at 22:14 last night, most "
            "likely by accident. The thread shows procurement is modelling a 30% reduction."
        ),
        "severity": "critical",
        "impact": "$480K ARR",
        "mitigation": "Lead with the migration cost analysis, not a discount. Hold price, extend term.",
        "source": "Gmail",
    },
    {
        "id": "risk_2",
        "title": "Engineering hiring is four days behind plan",
        "detail": (
            "Two staff-level candidates have competing offers with Thursday deadlines. The Q3 plan "
            "has been waiting on your approval since Friday."
        ),
        "severity": "high",
        "impact": "Q4 roadmap slip",
        "mitigation": "Approve the plan as written today; adjust headcount split next week if needed.",
        "source": "Notion",
    },
    {
        "id": "risk_3",
        "title": "Cascade Analytics has not responded in eleven days",
        "detail": (
            "A $275K proposal sent on July 24 with no reply. Their evaluation window closes at "
            "month end and two competitors are in the process."
        ),
        "severity": "medium",
        "impact": "$275K pipeline",
        "mitigation": "Have Elena send a decision-deadline email rather than another check-in.",
        "source": "GoHighLevel",
    },
]

KPIS = [
    {
        "id": "inbox",
        "label": "Inbox",
        "value": "6",
        "sublabel": "need your reply",
        "change": "18 handled by rules",
        "trend": "down",
        "icon": "inbox",
        "tone": "primary",
    },
    {
        "id": "meetings",
        "label": "Meetings",
        "value": "4",
        "sublabel": "scheduled today",
        "change": "2 need preparation",
        "trend": "neutral",
        "icon": "meetings",
        "tone": "slate",
    },
    {
        "id": "deals",
        "label": "Open Deals",
        "value": "$2.6M",
        "sublabel": "across 6 opportunities",
        "change": "1 at risk this week",
        "trend": "up",
        "icon": "deals",
        "tone": "primary",
    },
    {
        "id": "tasks",
        "label": "Pending Tasks",
        "value": "9",
        "sublabel": "assigned to you",
        "change": "3 overdue",
        "trend": "down",
        "icon": "tasks",
        "tone": "accent",
    },
]

ACTIVITY = [
    {
        "id": "act_1",
        "type": "email",
        "title": "James Liu forwarded a competitor pricing sheet",
        "detail": "Meridian Labs · renewal thread",
        "time": "22:14 yesterday",
        "source": "Gmail",
    },
    {
        "id": "act_2",
        "type": "deal",
        "title": "Pinnacle Health moved to Security Review",
        "detail": "$520K · probability raised to 65%",
        "time": "07:40",
        "source": "GoHighLevel",
    },
    {
        "id": "act_3",
        "type": "document",
        "title": "Sarah Chen published July metrics",
        "detail": "ARR $3.4M · NRR 118% · burn $410K",
        "time": "06:12",
        "source": "Notion",
    },
    {
        "id": "act_4",
        "type": "meeting",
        "title": "Northwind Digital moved the QBR to 15:30",
        "detail": "Rachel Kim added two attendees",
        "time": "Yesterday, 18:05",
        "source": "Google Calendar",
    },
    {
        "id": "act_5",
        "type": "deal",
        "title": "Vertex Systems requested pricing",
        "detail": "New inbound · 200-seat estimate",
        "time": "Yesterday, 16:20",
        "source": "GoHighLevel",
    },
]

TODAYS_FOCUS = [
    {
        "id": "foc_1",
        "title": "Hold price with Meridian, trade on term length",
        "description": (
            "Their switching cost is roughly seven months of engineering time. A three-year term at "
            "current pricing reads as a win to procurement without touching your rate card."
        ),
        "rationale": "Competitor quote is 30% lower but excludes migration and support.",
        "action": "Open the prep brief",
        "actionTarget": "/meetings",
        "impact": "$480K ARR protected",
        "priority": "critical",
        "sources": ["Gmail", "GoHighLevel"],
    },
    {
        "id": "foc_2",
        "title": "Approve the hiring plan this morning, not this afternoon",
        "description": (
            "Both staff candidates respond to offers on Thursday. Recruiting needs 48 hours to move, "
            "which means the plan has to be signed before noon today."
        ),
        "rationale": "Four days blocked; two offers expire Thursday.",
        "action": "Review in Notion",
        "actionTarget": "/inbox",
        "impact": "2 senior hires",
        "priority": "high",
        "sources": ["Notion", "Gmail"],
    },
    {
        "id": "foc_3",
        "title": "Delegate the board metrics narrative to Sarah",
        "description": (
            "The numbers are already written. Sarah can draft the commentary and you edit it in "
            "fifteen minutes tonight instead of blocking an hour you do not have."
        ),
        "rationale": "Board reads Wednesday evening; drafting is not the constrained skill here.",
        "action": "Draft delegation note",
        "actionTarget": "/ask",
        "impact": "1 hour reclaimed",
        "priority": "medium",
        "sources": ["Notion"],
    },
]

MEETINGS = [
    {
        "id": "mtg_1",
        "title": "Leadership Standup",
        "startTime": "09:00",
        "endTime": "09:30",
        "duration": "30 min",
        "type": "internal",
        "location": "Google Meet",
        "prepStatus": "ready",
        "prepReason": "Recurring internal sync. No preparation required.",
        "attendees": [
            {"name": "Sarah Chen", "role": "CFO", "company": "Arcadia Systems", "avatar": "SC"},
            {"name": "Marcus Webb", "role": "VP Engineering", "company": "Arcadia Systems", "avatar": "MW"},
            {"name": "Elena Park", "role": "VP Revenue", "company": "Arcadia Systems", "avatar": "EP"},
        ],
        "agenda": [
            "Weekly metrics review",
            "Meridian Labs renewal status",
            "Q3 hiring plan blockers",
        ],
        "company": {
            "name": "Arcadia Systems",
            "industry": "Internal",
            "size": "64 employees",
            "relationship": "Leadership team",
            "background": (
                "Standing Tuesday sync. The only open item carried from last week is the Q3 hiring "
                "plan, which is waiting on your approval."
            ),
        },
        "relatedEmails": [
            {
                "id": "rel_1",
                "subject": "Q3 hiring plan — needs your sign-off",
                "sender": "Marcus Webb",
                "summary": "Two staff engineering offers expire Thursday. Plan unchanged since Friday.",
                "time": "4 days ago",
            }
        ],
        "preparationNotes": [
            "Marcus will raise the hiring plan again. Come with a yes or a specific objection.",
            "Sarah published July metrics at 06:12; skim ARR and burn before the call.",
        ],
        "talkingPoints": [
            "Meridian is the company priority this week — everyone should route blockers to you.",
            "July NRR came in at 118%, the third consecutive month above 115%.",
            "Hiring plan decision lands today, before noon.",
        ],
        "recommendedQuestions": [
            "What would we cut from the Q4 roadmap if both staff hires fall through?",
            "Which customers besides Meridian have gone quiet for more than a week?",
        ],
        "risks": [
            {
                "title": "Hiring plan stalls a fifth day",
                "detail": "Recruiting cannot open requisitions without the approved plan.",
                "severity": "high",
            }
        ],
        "sources": ["Google Calendar", "Notion"],
    },
    {
        "id": "mtg_2",
        "title": "Meridian Labs — Renewal Negotiation",
        "startTime": "11:00",
        "endTime": "11:45",
        "duration": "45 min",
        "type": "client",
        "location": "Zoom",
        "prepStatus": "needs-prep",
        "prepReason": "Competitive threat surfaced last night. No agreed position yet.",
        "attendees": [
            {"name": "James Liu", "role": "VP Engineering", "company": "Meridian Labs", "avatar": "JL"},
            {"name": "Dana Whitfield", "role": "Head of Procurement", "company": "Meridian Labs", "avatar": "DW"},
            {"name": "Elena Park", "role": "VP Revenue", "company": "Arcadia Systems", "avatar": "EP"},
        ],
        "agenda": [
            "Renewal term and pricing",
            "Support tier and response commitments",
            "Migration timeline for the analytics module",
        ],
        "company": {
            "name": "Meridian Labs",
            "industry": "Industrial R&D software",
            "size": "1,200 employees",
            "relationship": "Customer since March 2023",
            "arr": "$480K",
            "background": (
                "Three-year customer, 94% seat utilisation, two successful expansions. Dana joined "
                "procurement in May and has been re-tendering every contract above $250K. James has "
                "been your champion since the original deal and has not changed his position."
            ),
        },
        "relatedEmails": [
            {
                "id": "rel_2",
                "subject": "Fwd: Vantage Cloud — commercial proposal",
                "sender": "James Liu",
                "summary": (
                    "Competitor quote at roughly 30% below current pricing. Excludes migration, "
                    "professional services and their premium support tier."
                ),
                "time": "22:14 yesterday",
            },
            {
                "id": "rel_3",
                "subject": "Re: Renewal timeline",
                "sender": "Dana Whitfield",
                "summary": "Confirms Friday as the internal decision deadline. Asks for best and final.",
                "time": "6 days ago",
            },
        ],
        "preparationNotes": [
            "The competitor quote omits migration. Your analytics module holds 3 years of their calibration data.",
            "Utilisation is 94% — this is not a shelfware conversation, it is a price conversation.",
            "Dana is measured on savings. Give her a number she can report that is not your unit price.",
        ],
        "talkingPoints": [
            "Migration cost estimate: roughly seven months of two engineers, before any downtime risk.",
            "Offer a 36-month term at current pricing with a fixed uplift cap — savings without discounting.",
            "Reference the 118% net revenue retention across their peer accounts as validation.",
        ],
        "recommendedQuestions": [
            "What does the evaluation look like if we take price off the table entirely?",
            "Which of your teams would own the migration if you switched vendors?",
            "Is Friday a hard deadline, or the date your board packet is due?",
        ],
        "risks": [
            {
                "title": "Discounting sets the floor for two other renewals",
                "detail": "Globex and Northwind renew in Q4 and benchmark against Meridian pricing.",
                "severity": "critical",
            },
            {
                "title": "Dana may not have full migration context",
                "detail": "The competitor proposal she is modelling excludes professional services entirely.",
                "severity": "high",
            },
        ],
        "sources": ["Gmail", "Google Calendar", "GoHighLevel"],
    },
    {
        "id": "mtg_3",
        "title": "Pinnacle Health — Security Review",
        "startTime": "14:00",
        "endTime": "14:45",
        "duration": "45 min",
        "type": "client",
        "location": "Microsoft Teams",
        "prepStatus": "needs-prep",
        "prepReason": "One open questionnaire item is blocking legal review.",
        "attendees": [
            {"name": "Tom Bradley", "role": "CTO", "company": "Pinnacle Health", "avatar": "TB"},
            {"name": "Priya Raman", "role": "CISO", "company": "Pinnacle Health", "avatar": "PR"},
            {"name": "Marcus Webb", "role": "VP Engineering", "company": "Arcadia Systems", "avatar": "MW"},
        ],
        "agenda": [
            "SOC 2 Type II report walkthrough",
            "Data residency for protected health information",
            "Sub-processor list and breach notification terms",
        ],
        "company": {
            "name": "Pinnacle Health",
            "industry": "Healthcare provider network",
            "size": "8,400 employees",
            "relationship": "New business · 4 months in cycle",
            "arr": "$520K potential",
            "background": (
                "Regional provider network with 22 facilities. Tom championed the platform after a "
                "strong March demo. Priya's security team is the last gate before legal review."
            ),
        },
        "relatedEmails": [
            {
                "id": "rel_4",
                "subject": "Security questionnaire — item 4.7 clarification",
                "sender": "Priya Raman",
                "summary": (
                    "Asks whether PHI can be pinned to a single region. Everything else in the "
                    "questionnaire is already accepted."
                ),
                "time": "Yesterday",
            }
        ],
        "preparationNotes": [
            "Item 4.7 is the only blocker. Marcus confirmed single-region pinning is already supported.",
            "Bring the SOC 2 Type II report dated June 2026 — Priya has not seen the current version.",
        ],
        "talkingPoints": [
            "Single-region data residency is configurable per tenant and is available at no extra cost.",
            "Breach notification is contractually 24 hours, ahead of their 72-hour requirement.",
            "Three comparable provider networks are running the same configuration today.",
        ],
        "recommendedQuestions": [
            "If 4.7 is resolved on this call, can legal review start this week?",
            "Does your team need a penetration test summary before signature?",
        ],
        "risks": [
            {
                "title": "Legal review slips past the fiscal year boundary",
                "detail": "Their procurement year closes September 30; slipping costs a full quarter.",
                "severity": "medium",
            }
        ],
        "sources": ["Gmail", "Google Calendar", "GoHighLevel"],
    },
    {
        "id": "mtg_4",
        "title": "Northwind Digital — Quarterly Business Review",
        "startTime": "15:30",
        "endTime": "16:15",
        "duration": "45 min",
        "type": "client",
        "location": "Google Meet",
        "prepStatus": "ready",
        "prepReason": "Elena has prepared the deck. Review the usage summary before joining.",
        "attendees": [
            {"name": "Rachel Kim", "role": "COO", "company": "Northwind Digital", "avatar": "RK"},
            {"name": "Elena Park", "role": "VP Revenue", "company": "Arcadia Systems", "avatar": "EP"},
        ],
        "agenda": [
            "H1 adoption and outcomes",
            "Expansion into their EMEA business unit",
            "Q4 renewal timing",
        ],
        "company": {
            "name": "Northwind Digital",
            "industry": "Digital agency network",
            "size": "600 employees",
            "relationship": "Customer since November 2024",
            "arr": "$340K",
            "background": (
                "Steady account with 71% seat utilisation. Rachel has raised EMEA expansion twice, "
                "which would add roughly 140 seats."
            ),
        },
        "relatedEmails": [
            {
                "id": "rel_5",
                "subject": "QBR moved to 15:30 + two additions",
                "sender": "Rachel Kim",
                "summary": "Added their EMEA operations lead and finance business partner to the invite.",
                "time": "Yesterday, 18:05",
            }
        ],
        "preparationNotes": [
            "Two finance-adjacent attendees were added yesterday — expect commercial questions.",
            "Utilisation is 71%; lead with outcomes rather than usage numbers.",
        ],
        "talkingPoints": [
            "Their reporting cycle dropped from nine days to two since onboarding.",
            "EMEA expansion at 140 seats would land near $110K incremental ARR.",
            "Q4 renewal is clean — no open support escalations in six months.",
        ],
        "recommendedQuestions": [
            "What would need to be true to approve EMEA before your Q4 planning locks?",
            "Who owns the budget for the EMEA business unit?",
        ],
        "risks": [
            {
                "title": "Late finance attendees may reopen pricing",
                "detail": "Adding a finance business partner the day before often signals a budget review.",
                "severity": "medium",
            }
        ],
        "sources": ["Google Calendar", "GoHighLevel", "Notion"],
    },
]

INBOX_CATEGORIES = [
    {
        "id": "needs-reply",
        "label": "Needs Reply",
        "description": "Waiting on a response from you",
    },
    {
        "id": "high-priority",
        "label": "High Priority",
        "description": "Time-sensitive or commercially significant",
    },
    {
        "id": "waiting",
        "label": "Waiting On Others",
        "description": "You have replied; the ball is with someone else",
    },
    {
        "id": "delegated",
        "label": "Delegated",
        "description": "Assigned to your team, tracked for follow-up",
    },
    {
        "id": "informational",
        "label": "Information Only",
        "description": "No action required, read when convenient",
    },
]

EMAILS = [
    {
        "id": "em_1",
        "category": "high-priority",
        "subject": "Fwd: Vantage Cloud — commercial proposal",
        "sender": {"name": "James Liu", "email": "james.liu@meridianlabs.com", "company": "Meridian Labs", "avatar": "JL"},
        "timeLabel": "22:14 yesterday",
        "receivedAt": "2026-08-03T22:14:00+03:00",
        "aiSummary": (
            "Appears to be an accidental forward. Contains a competitor proposal roughly 30% below "
            "your current pricing, excluding migration and premium support. Procurement is modelling "
            "it as a like-for-like replacement, which it is not."
        ),
        "priority": "critical",
        "suggestedResponse": (
            "Acknowledge receipt without commenting on the competitor's numbers, and offer to bring "
            "a migration cost analysis to the 11:00 call so both sides compare the same scope."
        ),
        "readingTime": "3 min",
        "threadCount": 7,
        "unread": True,
        "labels": ["Renewal", "Meridian Labs"],
    },
    {
        "id": "em_2",
        "category": "needs-reply",
        "subject": "Q3 hiring plan — needs your sign-off",
        "sender": {"name": "Marcus Webb", "email": "marcus@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "MW"},
        "timeLabel": "4 days ago",
        "receivedAt": "2026-07-31T09:05:00+03:00",
        "aiSummary": (
            "Fourth follow-up on the same request. Two staff engineering candidates hold competing "
            "offers with Thursday deadlines. The plan is unchanged from the version you reviewed."
        ),
        "priority": "high",
        "suggestedResponse": (
            "Approve as written and note that the headcount split between platform and product can "
            "be revisited at the September planning session."
        ),
        "readingTime": "2 min",
        "threadCount": 4,
        "unread": True,
        "labels": ["Hiring", "Blocked"],
    },
    {
        "id": "em_3",
        "category": "needs-reply",
        "subject": "Security questionnaire — item 4.7 clarification",
        "sender": {"name": "Priya Raman", "email": "p.raman@pinnaclehealth.org", "company": "Pinnacle Health", "avatar": "PR"},
        "timeLabel": "Yesterday, 16:40",
        "receivedAt": "2026-08-03T16:40:00+03:00",
        "aiSummary": (
            "Single open question on whether protected health information can be pinned to one "
            "region. Every other questionnaire item is already accepted. Answering unblocks legal review."
        ),
        "priority": "high",
        "suggestedResponse": (
            "Confirm that per-tenant single-region residency is supported at no additional cost, and "
            "attach the June 2026 SOC 2 Type II report ahead of the 14:00 call."
        ),
        "readingTime": "1 min",
        "threadCount": 3,
        "unread": True,
        "labels": ["Security", "Pinnacle Health"],
    },
    {
        "id": "em_4",
        "category": "needs-reply",
        "subject": "September advisory board — venue holds expire Friday",
        "sender": {"name": "Elena Park", "email": "elena@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "EP"},
        "timeLabel": "Yesterday, 11:20",
        "receivedAt": "2026-08-03T11:20:00+03:00",
        "aiSummary": (
            "Three customers have asked for confirmed dates twice. Elena needs a yes on September "
            "17–18 before the venue releases the hold on Friday."
        ),
        "priority": "medium",
        "suggestedResponse": "Confirm September 17–18 and let Elena own the agenda and invitations.",
        "readingTime": "1 min",
        "threadCount": 2,
        "unread": False,
        "labels": ["Customers"],
    },
    {
        "id": "em_5",
        "category": "high-priority",
        "subject": "July metrics are published",
        "sender": {"name": "Sarah Chen", "email": "sarah@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "SC"},
        "timeLabel": "06:12",
        "receivedAt": "2026-08-04T06:12:00+03:00",
        "aiSummary": (
            "ARR $3.4M, net revenue retention 118%, burn $410K per month, 26 months of runway. Third "
            "consecutive month above 115% retention. Only the board narrative is outstanding."
        ),
        "priority": "high",
        "suggestedResponse": (
            "Ask Sarah to draft the strategic narrative section so you review rather than write it."
        ),
        "readingTime": "4 min",
        "threadCount": 1,
        "unread": True,
        "labels": ["Board", "Finance"],
    },
    {
        "id": "em_6",
        "category": "waiting",
        "subject": "Re: Cascade Analytics proposal",
        "sender": {"name": "Daniel Osei", "email": "d.osei@cascadeanalytics.io", "company": "Cascade Analytics", "avatar": "DO"},
        "timeLabel": "11 days ago",
        "receivedAt": "2026-07-24T14:02:00+03:00",
        "aiSummary": (
            "Confirmed receipt of the $275K proposal and promised feedback within a week. Eleven "
            "days of silence since. Two competitors are known to be in the evaluation."
        ),
        "priority": "medium",
        "suggestedResponse": (
            "Rather than another check-in, ask Elena to send a decision-deadline note tied to your "
            "Q3 implementation capacity."
        ),
        "readingTime": "1 min",
        "threadCount": 5,
        "unread": False,
        "labels": ["Pipeline", "Stalled"],
    },
    {
        "id": "em_7",
        "category": "waiting",
        "subject": "Re: Master services agreement redlines",
        "sender": {"name": "Nadia Fischer", "email": "nadia@hollandlegal.com", "company": "Holland Legal", "avatar": "NF"},
        "timeLabel": "2 days ago",
        "receivedAt": "2026-08-02T10:15:00+03:00",
        "aiSummary": (
            "Outside counsel is reviewing the data residency clause for Pinnacle Health and expects "
            "to return comments Wednesday. No input needed from you."
        ),
        "priority": "low",
        "suggestedResponse": "No response required. Briefly will flag it if Wednesday passes without comments.",
        "readingTime": "1 min",
        "threadCount": 6,
        "unread": False,
        "labels": ["Legal"],
    },
    {
        "id": "em_8",
        "category": "delegated",
        "subject": "Vertex Systems — pricing request",
        "sender": {"name": "Elena Park", "email": "elena@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "EP"},
        "timeLabel": "Yesterday, 16:20",
        "receivedAt": "2026-08-03T16:20:00+03:00",
        "aiSummary": (
            "Inbound request for a 200-seat quote. Elena has taken it and will qualify budget and "
            "timeline before it reaches you. Assigned yesterday, no update yet."
        ),
        "priority": "low",
        "suggestedResponse": "No action. Briefly will resurface this if there is no movement by Thursday.",
        "readingTime": "1 min",
        "threadCount": 2,
        "unread": False,
        "labels": ["Inbound", "Delegated to Elena"],
    },
    {
        "id": "em_9",
        "category": "delegated",
        "subject": "Support escalation — Globex reporting latency",
        "sender": {"name": "Tomas Vidal", "email": "tomas@arcadiasystems.com", "company": "Arcadia Systems", "avatar": "TV"},
        "timeLabel": "2 days ago",
        "receivedAt": "2026-08-02T08:44:00+03:00",
        "aiSummary": (
            "Reporting latency on the Globex tenant was traced to a scheduled index rebuild. "
            "Resolved and communicated. Marcus owns the permanent fix in the next release."
        ),
        "priority": "low",
        "suggestedResponse": "No action. Marcus is tracking the permanent fix.",
        "readingTime": "2 min",
        "threadCount": 9,
        "unread": False,
        "labels": ["Support", "Resolved"],
    },
    {
        "id": "em_10",
        "category": "informational",
        "subject": "Your August 6 podcast recording is confirmed",
        "sender": {"name": "Operators Weekly", "email": "studio@operatorsweekly.fm", "company": "Operators Weekly", "avatar": "OW"},
        "timeLabel": "Yesterday",
        "receivedAt": "2026-08-03T09:00:00+03:00",
        "aiSummary": (
            "Recording confirmed for Thursday at 10:00. Prep questions arrive Wednesday. Already on "
            "your calendar with a 30-minute preparation block."
        ),
        "priority": "low",
        "suggestedResponse": "No response required.",
        "readingTime": "1 min",
        "threadCount": 1,
        "unread": False,
        "labels": ["Press"],
    },
    {
        "id": "em_11",
        "category": "informational",
        "subject": "Enterprise SaaS renewal benchmarks, H1 2026",
        "sender": {"name": "Bridgepoint Research", "email": "insights@bridgepoint.co", "company": "Bridgepoint Research", "avatar": "BR"},
        "timeLabel": "Yesterday",
        "receivedAt": "2026-08-03T07:30:00+03:00",
        "aiSummary": (
            "Median enterprise renewal discount held at 7% in H1. Relevant to today's Meridian "
            "conversation: competitive displacement attempts succeeded in only 18% of cases where "
            "utilisation exceeded 85%."
        ),
        "priority": "low",
        "suggestedResponse": "No response required. The 18% figure is useful ammunition at 11:00.",
        "readingTime": "6 min",
        "threadCount": 1,
        "unread": False,
        "labels": ["Research"],
    },
]

INBOX_SUMMARY = {
    "headline": "Six emails genuinely need you. The other eighteen do not.",
    "totalUnread": 24,
    "estimatedClearTime": "34 min",
    "handledAutomatically": 18,
}

OPPORTUNITIES = [
    {
        "id": "opp_1",
        "company": "Meridian Labs",
        "logo": "ML",
        "industry": "Industrial R&D software",
        "stage": "Renewal",
        "value": 480000,
        "probability": 55,
        "owner": "Elena Park",
        "closeDate": "Aug 7, 2026",
        "riskLevel": "critical",
        "lastInteraction": {
            "type": "email",
            "summary": "Competitor pricing sheet forwarded by their champion",
            "time": "22:14 yesterday",
        },
        "aiSummary": (
            "A three-year customer at 94% utilisation is being competitively re-tendered by a new "
            "procurement lead. Probability dropped 25 points overnight when a competitor quote "
            "entered the thread. The champion relationship is intact; the risk is entirely commercial."
        ),
        "recommendedAction": (
            "Hold price and offer a 36-month term with a capped uplift. Bring the migration cost "
            "analysis to the 11:00 call."
        ),
        "signals": ["Champion still engaged", "94% utilisation", "New procurement lead", "Competitor in thread"],
        "sources": ["GoHighLevel", "Gmail"],
    },
    {
        "id": "opp_2",
        "company": "Pinnacle Health",
        "logo": "PH",
        "industry": "Healthcare provider network",
        "stage": "Security Review",
        "value": 520000,
        "probability": 65,
        "owner": "Elena Park",
        "closeDate": "Sep 12, 2026",
        "riskLevel": "low",
        "lastInteraction": {
            "type": "email",
            "summary": "One open questionnaire item before legal review",
            "time": "Yesterday, 16:40",
        },
        "aiSummary": (
            "Largest open opportunity and the cleanest. Security is the final gate and only one "
            "questionnaire item remains open, which engineering has already confirmed is supported."
        ),
        "recommendedAction": "Answer item 4.7 in writing before the 14:00 call so legal can start this week.",
        "signals": ["Executive champion", "Budget confirmed", "Single open blocker"],
        "sources": ["GoHighLevel", "Gmail"],
    },
    {
        "id": "opp_3",
        "company": "Cascade Analytics",
        "logo": "CA",
        "industry": "Data analytics",
        "stage": "Proposal",
        "value": 275000,
        "probability": 30,
        "owner": "Elena Park",
        "closeDate": "Aug 31, 2026",
        "riskLevel": "high",
        "lastInteraction": {
            "type": "email",
            "summary": "Acknowledged the proposal, then went silent",
            "time": "11 days ago",
        },
        "aiSummary": (
            "Eleven days of silence after a promise of feedback within a week. Two competitors are "
            "in the evaluation and their decision window closes at month end. Silence this long "
            "after an acknowledgement usually signals internal disagreement rather than disinterest."
        ),
        "recommendedAction": "Send a decision-deadline note tied to Q3 implementation capacity, not another check-in.",
        "signals": ["No response in 11 days", "Competitive evaluation", "Month-end decision"],
        "sources": ["GoHighLevel"],
    },
    {
        "id": "opp_4",
        "company": "Northwind Digital",
        "logo": "ND",
        "industry": "Digital agency network",
        "stage": "Expansion",
        "value": 110000,
        "probability": 60,
        "owner": "Elena Park",
        "closeDate": "Oct 1, 2026",
        "riskLevel": "medium",
        "lastInteraction": {
            "type": "meeting",
            "summary": "QBR moved to 15:30 with two finance attendees added",
            "time": "Yesterday, 18:05",
        },
        "aiSummary": (
            "EMEA expansion worth roughly 140 seats. Rachel has raised it twice unprompted, which is "
            "a strong signal. Two finance-adjacent attendees were added to today's QBR yesterday, "
            "which often precedes a budget conversation."
        ),
        "recommendedAction": "Ask directly at the QBR who owns the EMEA budget and what approval requires.",
        "signals": ["Customer-initiated", "71% utilisation", "Finance joined late"],
        "sources": ["GoHighLevel", "Google Calendar"],
    },
    {
        "id": "opp_5",
        "company": "Vertex Systems",
        "logo": "VS",
        "industry": "B2B SaaS",
        "stage": "Discovery",
        "value": 190000,
        "probability": 20,
        "owner": "Elena Park",
        "closeDate": "Nov 15, 2026",
        "riskLevel": "low",
        "lastInteraction": {
            "type": "email",
            "summary": "Inbound pricing request for 200 seats",
            "time": "Yesterday, 16:20",
        },
        "aiSummary": (
            "New inbound with a specific seat count, which suggests real internal planning rather "
            "than casual research. Elena is qualifying budget and timeline. No executive involvement "
            "needed yet."
        ),
        "recommendedAction": "None this week. Reassess once Elena reports on budget authority.",
        "signals": ["Inbound", "Specific seat count", "Unqualified"],
        "sources": ["GoHighLevel"],
    },
    {
        "id": "opp_6",
        "company": "Globex Inc",
        "logo": "GI",
        "industry": "Logistics",
        "stage": "Renewal",
        "value": 1020000,
        "probability": 80,
        "owner": "Marcus Webb",
        "closeDate": "Dec 1, 2026",
        "riskLevel": "medium",
        "lastInteraction": {
            "type": "support",
            "summary": "Reporting latency escalation, resolved in two days",
            "time": "2 days ago",
        },
        "aiSummary": (
            "Your largest account, renewing in Q4. A latency escalation was resolved quickly, but it "
            "is the second performance issue this quarter. Renewal pricing will be benchmarked "
            "against whatever you agree with Meridian this week."
        ),
        "recommendedAction": "No action today. Keep Meridian pricing intact to protect this benchmark.",
        "signals": ["Largest account", "Two performance escalations", "Benchmarks against Meridian"],
        "sources": ["GoHighLevel", "Gmail"],
    },
]

CLIENTS_NEEDING_ATTENTION = [
    {
        "id": "cli_1",
        "company": "Meridian Labs",
        "stage": "Renewal",
        "value": "$480K",
        "lastContact": "9 days of silence, broken last night",
        "reason": "Competitively re-tendered by a new procurement lead with a Friday decision date.",
        "recommendedAction": "Hold price, trade on term length, and lead with migration cost.",
        "severity": "critical",
    },
    {
        "id": "cli_2",
        "company": "Cascade Analytics",
        "stage": "Proposal",
        "value": "$275K",
        "lastContact": "11 days ago",
        "reason": "Promised feedback within a week and has not replied since.",
        "recommendedAction": "Have Elena send a decision-deadline note rather than another check-in.",
        "severity": "high",
    },
    {
        "id": "cli_3",
        "company": "Northwind Digital",
        "stage": "Expansion",
        "value": "$110K",
        "lastContact": "Yesterday, 18:05",
        "reason": "Two finance attendees added to today's QBR at short notice.",
        "recommendedAction": "Surface the EMEA budget owner during the 15:30 call.",
        "severity": "medium",
    },
]

SUGGESTED_FOCUS = {
    "headline": "Protect the morning. Meridian needs your full attention before 11:00.",
    "rationale": (
        "You have 90 minutes of uninterrupted time before the renewal call and no other commitment "
        "that cannot move. Everything after 16:15 is discretionary."
    ),
    "blocks": [
        {
            "id": "blk_1",
            "start": "09:30",
            "end": "10:45",
            "label": "Meridian renewal preparation",
            "reason": "Build the migration cost case and set your walk-away line.",
            "kind": "deep-work",
        },
        {
            "id": "blk_2",
            "start": "10:45",
            "end": "11:00",
            "label": "Approve the Q3 hiring plan",
            "reason": "Fifteen minutes clears a four-day block for the whole engineering org.",
            "kind": "decision",
        },
        {
            "id": "blk_3",
            "start": "13:15",
            "end": "13:45",
            "label": "Pinnacle security answer",
            "reason": "Send item 4.7 in writing before the 14:00 call so legal can start.",
            "kind": "quick-win",
        },
        {
            "id": "blk_4",
            "start": "16:30",
            "end": "17:00",
            "label": "Review the board narrative from Sarah",
            "reason": "Edit rather than write. The board reads tomorrow evening.",
            "kind": "review",
        },
    ],
}

RECOMMENDED_DELEGATION = [
    {
        "id": "del_1",
        "task": "Draft the July board metrics narrative",
        "assignee": "Sarah Chen",
        "assigneeRole": "CFO",
        "reason": "She wrote the underlying analysis. You add judgement in fifteen minutes, not an hour.",
        "effort": "60 min saved",
    },
    {
        "id": "del_2",
        "task": "Send the Cascade Analytics decision-deadline note",
        "assignee": "Elena Park",
        "assigneeRole": "VP Revenue",
        "reason": "Deal owner, and a founder follow-up would signal more urgency than you want to show.",
        "effort": "25 min saved",
    },
    {
        "id": "del_3",
        "task": "Confirm the September advisory board logistics",
        "assignee": "Elena Park",
        "assigneeRole": "VP Revenue",
        "reason": "Only the date needs your decision. Venue, agenda and invitations do not.",
        "effort": "40 min saved",
    },
    {
        "id": "del_4",
        "task": "Compile the SOC 2 Type II packet for Pinnacle",
        "assignee": "Marcus Webb",
        "assigneeRole": "VP Engineering",
        "reason": "He owns the control evidence and can attach it before the 14:00 call.",
        "effort": "20 min saved",
    },
]

ACTION_CHECKLIST = [
    {
        "id": "chk_1",
        "label": "Set the Meridian walk-away price and term",
        "category": "Decision",
        "due": "Before 11:00",
        "done": False,
    },
    {
        "id": "chk_2",
        "label": "Approve the Q3 hiring plan in Notion",
        "category": "Decision",
        "due": "Before noon",
        "done": False,
    },
    {
        "id": "chk_3",
        "label": "Reply to Priya on questionnaire item 4.7",
        "category": "Reply",
        "due": "Before 14:00",
        "done": False,
    },
    {
        "id": "chk_4",
        "label": "Ask Sarah to draft the board narrative",
        "category": "Delegate",
        "due": "This morning",
        "done": True,
    },
    {
        "id": "chk_5",
        "label": "Confirm September 17–18 for the advisory board",
        "category": "Reply",
        "due": "Today",
        "done": False,
    },
    {
        "id": "chk_6",
        "label": "Review the Northwind QBR deck",
        "category": "Review",
        "due": "Before 15:30",
        "done": True,
    },
]

CLOSING_ANSWER = {
    "question": "What should I accomplish today?",
    "answer": (
        "Three things. Protect the Meridian renewal with a defended position rather than a discount, "
        "unblock engineering by approving the hiring plan before noon, and remove the last obstacle "
        "in the Pinnacle security review with a two-line reply. Everything else on today's list can "
        "move to Wednesday without cost."
    ),
    "bullets": [
        "Hold Meridian pricing and trade term length instead — $480K ARR and the Q4 renewal benchmark.",
        "Approve the Q3 hiring plan before noon — two staff offers expire Thursday.",
        "Answer Pinnacle questionnaire item 4.7 in writing — unblocks $520K in legal review.",
    ],
}

ASK_SUGGESTIONS = [
    {
        "id": "sug_1",
        "question": "What should I prioritize today?",
        "category": "Prioritisation",
        "icon": "target",
    },
    {
        "id": "sug_2",
        "question": "Prepare me for today's meetings.",
        "category": "Preparation",
        "icon": "calendar",
    },
    {
        "id": "sug_3",
        "question": "Which deals are most at risk?",
        "category": "Pipeline",
        "icon": "trending",
    },
    {
        "id": "sug_4",
        "question": "What changed since yesterday?",
        "category": "Situational",
        "icon": "activity",
    },
    {
        "id": "sug_5",
        "question": "Draft a follow-up email for Meridian Labs.",
        "category": "Drafting",
        "icon": "pen",
    },
    {
        "id": "sug_6",
        "question": "Where is my team blocked on me?",
        "category": "Team",
        "icon": "users",
    },
]

ASK_RECENT = [
    {"id": "rec_1", "question": "Which deals are most at risk?", "askedAt": "Yesterday, 17:40"},
    {"id": "rec_2", "question": "Summarise the Globex support escalation.", "askedAt": "Monday, 09:15"},
    {"id": "rec_3", "question": "What changed since yesterday?", "askedAt": "Monday, 06:35"},
]

ASK_REPORTS = {
    "What should I prioritize today?": {
        "summary": (
            "One decision dominates today. The Meridian Labs renewal is worth $480K and sets the "
            "pricing benchmark for two Q4 renewals, and it is being competitively re-tendered with a "
            "Friday deadline. Two smaller items are worth doing because they unblock other people."
        ),
        "confidence": "high",
        "sections": [
            {
                "id": "sec_1",
                "title": "Do first",
                "type": "ranked",
                "items": [
                    {
                        "title": "Set your Meridian position before 11:00",
                        "detail": "Hold price, trade term length, lead with the migration cost analysis.",
                        "meta": "$480K ARR",
                    },
                    {
                        "title": "Approve the Q3 hiring plan",
                        "detail": "Four days blocked. Two staff engineering offers expire Thursday.",
                        "meta": "2 senior hires",
                    },
                    {
                        "title": "Answer Pinnacle questionnaire item 4.7",
                        "detail": "A two-line reply moves $520K into legal review this week.",
                        "meta": "$520K pipeline",
                    },
                ],
            },
            {
                "id": "sec_2",
                "title": "Safe to defer",
                "type": "list",
                "items": [
                    {"title": "The board metrics narrative — delegate the draft to Sarah and edit tonight."},
                    {"title": "Cascade Analytics follow-up — Elena should own the decision-deadline note."},
                    {"title": "Advisory board logistics — only the date needs you."},
                ],
            },
        ],
        "citations": [
            {"source": "Gmail", "detail": "6 threads reviewed", "count": 6},
            {"source": "Google Calendar", "detail": "4 meetings today", "count": 4},
            {"source": "GoHighLevel", "detail": "6 open opportunities", "count": 6},
            {"source": "Notion", "detail": "Q3 hiring plan, July metrics", "count": 2},
        ],
        "followUps": [
            "What is my walk-away price for Meridian?",
            "Draft the hiring plan approval note.",
            "What happens if I defer the board narrative to Thursday?",
        ],
    },
    "Prepare me for today's meetings.": {
        "summary": (
            "Four meetings, two of which need real preparation. The 11:00 Meridian renewal is the one "
            "that matters; the 14:00 Pinnacle security review needs a single written answer beforehand."
        ),
        "confidence": "high",
        "sections": [
            {
                "id": "sec_1",
                "title": "11:00 — Meridian Labs renewal",
                "type": "list",
                "items": [
                    {"title": "Their competitor quote excludes migration, services and premium support."},
                    {"title": "Migration would cost them roughly seven months of two engineers."},
                    {"title": "Offer 36 months at current pricing with a capped uplift — savings without discounting."},
                    {"title": "Dana is measured on savings; give her a reportable number that is not your unit price."},
                ],
            },
            {
                "id": "sec_2",
                "title": "14:00 — Pinnacle Health security review",
                "type": "list",
                "items": [
                    {"title": "Item 4.7 is the only open blocker; single-region residency is already supported."},
                    {"title": "Bring the June 2026 SOC 2 Type II report — Priya has not seen the current version."},
                    {"title": "Ask directly whether legal review can start this week."},
                ],
            },
            {
                "id": "sec_3",
                "title": "Lower preparation",
                "type": "list",
                "items": [
                    {"title": "09:00 Leadership standup — come with a decision on the hiring plan."},
                    {"title": "15:30 Northwind QBR — two finance attendees added yesterday; expect budget questions."},
                ],
            },
        ],
        "citations": [
            {"source": "Google Calendar", "detail": "4 meetings", "count": 4},
            {"source": "Gmail", "detail": "5 related threads", "count": 5},
            {"source": "GoHighLevel", "detail": "3 linked accounts", "count": 3},
        ],
        "followUps": [
            "What questions should I ask Dana Whitfield?",
            "Summarise the Meridian account history.",
            "Who owns the EMEA budget at Northwind?",
        ],
    },
    "Which deals are most at risk?": {
        "summary": (
            "Two of six opportunities are genuinely at risk, together worth $755K. Meridian is the "
            "urgent one because the decision date is Friday and it anchors your Q4 renewal pricing."
        ),
        "confidence": "high",
        "sections": [
            {
                "id": "sec_1",
                "title": "At risk",
                "type": "ranked",
                "items": [
                    {
                        "title": "Meridian Labs — $480K renewal",
                        "detail": "Competitively re-tendered. Probability fell 25 points overnight. Closes Friday.",
                        "meta": "Critical",
                    },
                    {
                        "title": "Cascade Analytics — $275K proposal",
                        "detail": "Eleven days of silence after promising feedback within a week.",
                        "meta": "High",
                    },
                ],
            },
            {
                "id": "sec_2",
                "title": "Watch, do not act",
                "type": "list",
                "items": [
                    {"title": "Globex Inc — two performance escalations this quarter ahead of a Q4 renewal."},
                    {"title": "Northwind Digital — finance attendees added to today's QBR at short notice."},
                ],
            },
        ],
        "citations": [
            {"source": "GoHighLevel", "detail": "6 opportunities, $2.6M", "count": 6},
            {"source": "Gmail", "detail": "Engagement history across 4 accounts", "count": 4},
        ],
        "followUps": [
            "Draft a follow-up email for Meridian Labs.",
            "What is the weighted value of my pipeline?",
            "How should Elena approach Cascade?",
        ],
    },
    "What changed since yesterday?": {
        "summary": (
            "One change matters. A competitor's pricing proposal entered the Meridian renewal thread "
            "at 22:14 last night, which reframes today's 11:00 call from a routine renewal into a "
            "competitive defence."
        ),
        "confidence": "high",
        "sections": [
            {
                "id": "sec_1",
                "title": "Material changes",
                "type": "list",
                "items": [
                    {"title": "Meridian Labs probability dropped from 80% to 55% after the competitor quote surfaced."},
                    {"title": "Pinnacle Health moved to Security Review; probability rose to 65%."},
                    {"title": "Northwind QBR moved to 15:30 with two finance attendees added."},
                ],
            },
            {
                "id": "sec_2",
                "title": "Routine",
                "type": "list",
                "items": [
                    {"title": "July metrics published: ARR $3.4M, NRR 118%, burn $410K."},
                    {"title": "Globex reporting latency escalation closed after two days."},
                ],
            },
        ],
        "citations": [
            {"source": "Gmail", "detail": "11 new threads overnight", "count": 11},
            {"source": "GoHighLevel", "detail": "3 stage changes", "count": 3},
            {"source": "Google Calendar", "detail": "1 rescheduled meeting", "count": 1},
            {"source": "Notion", "detail": "July metrics published", "count": 1},
        ],
        "followUps": [
            "How does the competitor quote compare on total cost?",
            "What should I prioritize today?",
        ],
    },
    "Draft a follow-up email for Meridian Labs.": {
        "summary": (
            "A draft that acknowledges the forward without commenting on the competitor's numbers, "
            "and reframes the comparison around total cost. Nothing is sent until you approve it."
        ),
        "confidence": "medium",
        "sections": [
            {
                "id": "sec_1",
                "title": "Draft — to James Liu and Dana Whitfield",
                "type": "draft",
                "body": (
                    "Subject: Ahead of today's call — total cost view\n\n"
                    "James, Dana,\n\n"
                    "Thanks for keeping the renewal moving on a tight timeline. Ahead of our 11:00, I "
                    "want to make sure we are comparing the same scope rather than the same line item.\n\n"
                    "I will bring a short analysis covering three things: the engineering effort to "
                    "migrate three years of calibration data, the support commitments included in your "
                    "current agreement, and a 36-month structure that gives procurement a defensible "
                    "saving without changing your unit economics.\n\n"
                    "If Friday is a hard internal deadline, tell me now and we will work to it.\n\n"
                    "Lydia"
                ),
            },
            {
                "id": "sec_2",
                "title": "Why this framing",
                "type": "list",
                "items": [
                    {"title": "Does not acknowledge the competitor quote, which was likely forwarded by mistake."},
                    {"title": "Gives Dana a saving she can report without discounting your rate card."},
                    {"title": "Tests whether Friday is a real deadline or a board packet date."},
                ],
            },
        ],
        "citations": [
            {"source": "Gmail", "detail": "7-message renewal thread", "count": 7},
            {"source": "GoHighLevel", "detail": "Meridian Labs account history", "count": 1},
        ],
        "followUps": [
            "Make the tone firmer.",
            "What is my walk-away price?",
            "Prepare me for today's meetings.",
        ],
    },
    "Where is my team blocked on me?": {
        "summary": (
            "Three people are waiting on decisions only you can make. Together they represent about "
            "nine days of accumulated delay across engineering, finance and revenue."
        ),
        "confidence": "high",
        "sections": [
            {
                "id": "sec_1",
                "title": "Blocked on you",
                "type": "ranked",
                "items": [
                    {
                        "title": "Marcus Webb — Q3 hiring plan",
                        "detail": "Waiting four days. Two staff offers expire Thursday.",
                        "meta": "4 days",
                    },
                    {
                        "title": "Elena Park — advisory board dates",
                        "detail": "Venue holds expire Friday; three customers have asked twice.",
                        "meta": "2 days",
                    },
                    {
                        "title": "Sarah Chen — board narrative scope",
                        "detail": "Needs to know whether she drafts it or you write it.",
                        "meta": "1 day",
                    },
                ],
            }
        ],
        "citations": [
            {"source": "Gmail", "detail": "4 follow-up threads", "count": 4},
            {"source": "Notion", "detail": "2 documents awaiting approval", "count": 2},
        ],
        "followUps": [
            "Draft the hiring plan approval note.",
            "What should I prioritize today?",
        ],
    },
}

DEFAULT_ASK_REPORT = {
    "summary": (
        "Briefly reviewed your connected systems for this question. Here is what is currently known, "
        "along with the specific sources behind it."
    ),
    "confidence": "medium",
    "sections": [
        {
            "id": "sec_1",
            "title": "What Briefly found",
            "type": "list",
            "items": [
                {"title": "Meridian Labs is the highest-stakes open item, with a Friday decision date."},
                {"title": "Two decisions are blocking your team: the Q3 hiring plan and the advisory board date."},
                {"title": "Four meetings are scheduled today; two need preparation."},
            ],
        },
        {
            "id": "sec_2",
            "title": "Suggested next step",
            "type": "text",
            "body": (
                "Ask a narrower question and Briefly will pull the specific thread, meeting or "
                "opportunity behind it. Nothing is actioned without your approval."
            ),
        },
    ],
    "citations": [
        {"source": "Gmail", "detail": "24 threads indexed", "count": 24},
        {"source": "Google Calendar", "detail": "4 meetings today", "count": 4},
        {"source": "GoHighLevel", "detail": "6 open opportunities", "count": 6},
        {"source": "Notion", "detail": "12 documents indexed", "count": 12},
    ],
    "followUps": [
        "What should I prioritize today?",
        "Which deals are most at risk?",
        "Prepare me for today's meetings.",
    ],
}

INTEGRATIONS = [
    {
        "id": "google-calendar",
        "name": "Google Calendar",
        "category": "Calendar",
        "description": "Meetings, attendees and scheduling context for meeting intelligence.",
        "status": "connected",
        "account": "lydia@arcadiasystems.com",
        "lastSync": "2026-08-04T06:28:00+03:00",
        "lastSyncLabel": "4 minutes ago",
        "scopes": ["calendar.readonly", "calendar.events.readonly"],
        "metrics": [
            {"label": "Meetings today", "value": "4"},
            {"label": "Calendars", "value": "2"},
        ],
        "poweredBy": "Google Workspace API",
    },
    {
        "id": "gmail",
        "name": "Gmail",
        "category": "Email",
        "description": "Thread summarisation, prioritisation and suggested responses.",
        "status": "connected",
        "account": "lydia@arcadiasystems.com",
        "lastSync": "2026-08-04T06:29:00+03:00",
        "lastSyncLabel": "3 minutes ago",
        "scopes": ["gmail.readonly", "gmail.metadata"],
        "metrics": [
            {"label": "Threads indexed", "value": "24"},
            {"label": "Needs reply", "value": "6"},
        ],
        "poweredBy": "Google Workspace API",
    },
    {
        "id": "notion",
        "name": "Notion",
        "category": "Knowledge",
        "description": "Plans, metrics and documents that give the brief its internal context.",
        "status": "connected",
        "account": "Arcadia Systems workspace",
        "lastSync": "2026-08-04T05:50:00+03:00",
        "lastSyncLabel": "42 minutes ago",
        "scopes": ["read_content"],
        "metrics": [
            {"label": "Pages indexed", "value": "12"},
            {"label": "Databases", "value": "3"},
        ],
        "poweredBy": "Notion API",
    },
    {
        "id": "gohighlevel",
        "name": "GoHighLevel",
        "category": "CRM",
        "description": "Opportunities, stages and interaction history behind pipeline intelligence.",
        "status": "syncing",
        "account": "Arcadia Systems · Location 4821",
        "lastSync": "2026-08-04T06:31:00+03:00",
        "lastSyncLabel": "syncing now",
        "scopes": ["opportunities.readonly", "contacts.readonly"],
        "metrics": [
            {"label": "Opportunities", "value": "6"},
            {"label": "Pipeline", "value": "$2.6M"},
        ],
        "poweredBy": "GoHighLevel API v2",
    },
    {
        "id": "openai",
        "name": "OpenAI",
        "category": "Intelligence",
        "description": "Summarisation, prioritisation and drafting for every generated brief.",
        "status": "connected",
        "account": "Organisation · arcadia-systems",
        "lastSync": "2026-08-04T06:30:00+03:00",
        "lastSyncLabel": "2 minutes ago",
        "scopes": ["responses.write"],
        "metrics": [
            {"label": "Model", "value": "gpt-5.1"},
            {"label": "Briefs generated", "value": "128"},
        ],
        "poweredBy": "OpenAI Platform",
    },
    {
        "id": "n8n",
        "name": "n8n",
        "category": "Automation",
        "description": "Scheduled brief generation and downstream workflow triggers.",
        "status": "not-connected",
        "account": None,
        "lastSync": None,
        "lastSyncLabel": "Never",
        "scopes": ["workflow.execute"],
        "metrics": [
            {"label": "Workflows", "value": "0"},
            {"label": "Runs this month", "value": "0"},
        ],
        "poweredBy": "n8n Cloud",
    },
]

SYNC_HISTORY = [
    {
        "id": "sync_1",
        "integrationId": "gohighlevel",
        "integration": "GoHighLevel",
        "event": "Incremental sync started",
        "status": "running",
        "time": "06:31",
        "detail": "Pulling opportunity stage changes since 05:31",
    },
    {
        "id": "sync_2",
        "integrationId": "openai",
        "integration": "OpenAI",
        "event": "Morning brief generated",
        "status": "success",
        "time": "06:30",
        "detail": "4 sources, 18.4s, 2,140 tokens",
    },
    {
        "id": "sync_3",
        "integrationId": "gmail",
        "integration": "Gmail",
        "event": "Thread sync completed",
        "status": "success",
        "time": "06:29",
        "detail": "24 threads, 11 new since yesterday",
    },
    {
        "id": "sync_4",
        "integrationId": "google-calendar",
        "integration": "Google Calendar",
        "event": "Event sync completed",
        "status": "success",
        "time": "06:28",
        "detail": "4 events today, 1 reschedule detected",
    },
    {
        "id": "sync_5",
        "integrationId": "notion",
        "integration": "Notion",
        "event": "Page index refreshed",
        "status": "success",
        "time": "05:50",
        "detail": "12 pages, 2 updated overnight",
    },
    {
        "id": "sync_6",
        "integrationId": "gmail",
        "integration": "Gmail",
        "event": "Rate limit backoff",
        "status": "warning",
        "time": "Yesterday, 22:16",
        "detail": "Retried after 30s, no data loss",
    },
]

SETTINGS_PROFILE = {
    "fullName": "Lydia Reyes",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "email": "lydia@arcadiasystems.com",
    "phone": "+30 210 555 0148",
    "timezone": "Europe/Athens (GMT+3)",
    "avatar": "LR",
}

SETTINGS_PREFERENCES = {
    "briefTime": "06:30",
    "briefDays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "tone": "Direct",
    "toneOptions": ["Direct", "Balanced", "Detailed"],
    "briefLength": "Standard",
    "briefLengthOptions": ["Concise", "Standard", "Comprehensive"],
    "focusAreas": ["Revenue", "Client risk", "Team blockers"],
    "focusAreaOptions": ["Revenue", "Client risk", "Team blockers", "Product", "Hiring", "Finance"],
    "autoApproveActions": False,
}

SETTINGS_NOTIFICATIONS = [
    {
        "id": "ntf_1",
        "label": "Morning brief ready",
        "description": "Sent when your brief finishes generating.",
        "channel": "Email",
        "enabled": True,
    },
    {
        "id": "ntf_2",
        "label": "Critical client risk",
        "description": "A key account goes quiet or a competitor appears in a thread.",
        "channel": "Email · Push",
        "enabled": True,
    },
    {
        "id": "ntf_3",
        "label": "Meeting preparation reminder",
        "description": "Thirty minutes before a meeting that needs preparation.",
        "channel": "Push",
        "enabled": True,
    },
    {
        "id": "ntf_4",
        "label": "Deal stage changes",
        "description": "An opportunity moves forward or backward in the pipeline.",
        "channel": "Email",
        "enabled": False,
    },
    {
        "id": "ntf_5",
        "label": "Weekly retrospective",
        "description": "A Friday summary of decisions made and deferred.",
        "channel": "Email",
        "enabled": True,
    },
]

SETTINGS_SECURITY = {
    "twoFactorEnabled": True,
    "twoFactorMethod": "Authenticator app",
    "lastPasswordChange": "March 12, 2026",
    "sessions": [
        {"id": "ses_1", "device": "MacBook Pro · Chrome", "location": "Athens, GR", "lastActive": "Active now", "current": True},
        {"id": "ses_2", "device": "iPhone 17 · Briefly iOS", "location": "Athens, GR", "lastActive": "2 hours ago", "current": False},
        {"id": "ses_3", "device": "iPad Air · Safari", "location": "Thessaloniki, GR", "lastActive": "4 days ago", "current": False},
    ],
    "apiKeys": [
        {"id": "key_1", "label": "n8n automation", "prefix": "brf_live_9f2c", "createdAt": "June 2, 2026", "lastUsed": "Never"},
        {"id": "key_2", "label": "Internal reporting", "prefix": "brf_live_41ad", "createdAt": "April 18, 2026", "lastUsed": "Yesterday"},
    ],
}

SETTINGS_THEME = {
    "mode": "Light",
    "modeOptions": ["Light", "Dark", "System"],
    "density": "Comfortable",
    "densityOptions": ["Compact", "Comfortable"],
    "accent": "Emerald",
    "accentOptions": ["Emerald", "Slate", "Amber"],
    "reducedMotion": False,
}

CONNECTED_ACCOUNTS = [
    {"id": "acc_1", "provider": "Google", "detail": "lydia@arcadiasystems.com", "status": "connected", "connectedAt": "January 8, 2026"},
    {"id": "acc_2", "provider": "Notion", "detail": "Arcadia Systems workspace", "status": "connected", "connectedAt": "February 21, 2026"},
    {"id": "acc_3", "provider": "GoHighLevel", "detail": "Location 4821", "status": "connected", "connectedAt": "March 3, 2026"},
    {"id": "acc_4", "provider": "n8n", "detail": "Not connected", "status": "not-connected", "connectedAt": None},
]
