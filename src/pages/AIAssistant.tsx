import { useState, useRef, useEffect } from "react"
import { motion } from "framer-motion"
import { Sparkles, Send, Paperclip, Mic } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { chatSuggestions, chatHistory as initialHistory } from "@/data/mock"
import { cn } from "@/lib/utils"
import { ease } from "@/lib/motion"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
}

const aiResponses: Record<string, string> = {
  "What needs my attention today?":
    "Based on your calendar, inbox, and pipeline, here are your top 3 priorities today:\n\n1. **Horizon Ventures term sheet** — David Park sent final terms ($18M at $90M pre). Response needed by 6 PM.\n\n2. **Acme Corp negotiation at 11 AM** — SLA terms are the blocker. I've prepared two concession packages for you.\n\n3. **Board deck prep at 2 PM** — Strategic narrative section is empty. Sarah has the metrics ready.\n\nYou also have 3 unread investor emails and 2 engineering attrition issues that need your input.",

  "Summarize my sales pipeline":
    "Your active pipeline totals **$2.1M** across 5 opportunities:\n\n• **Acme Corp** — $850K, Negotiation (85%) — Close expected this week pending SLA resolution\n• **Pinnacle Health** — $520K, Qualified (60%) — Strong demo feedback, EHR integration next\n• **Northwind Digital** — $340K, Proposal (70%) — MSA approved, ready to sign\n• **Vertex Systems** — $120K, Discovery (25%) — New inbound, needs intro call\n• **Cascade Analytics** — $275K, Proposal (45%) — No response in 3 days, follow-up recommended\n\nWeighted pipeline value: **$1.4M**. Acme is your highest-impact deal this week.",

  "Draft a response to Horizon Ventures":
    "Here's a draft response to David Park:\n\n---\n\nHi David,\n\nThank you for sending the final terms. We're excited about partnering with Horizon Ventures.\n\nWe've reviewed the term sheet and are aligned on most points. We'd like to discuss two items on our call at 4:30 PM today:\n\n1. **Valuation** — We'd like to propose $95M pre-money based on our Q2 metrics (118% NRR, 8% MoM growth)\n2. **Board composition** — We'd prefer 5 seats (2 founders, 2 investors, 1 independent)\n\nLooking forward to our conversation.\n\nBest,\nLydia\n\n---\n\nShall I send this or would you like to adjust the tone?",

  "What are the risks in my calendar this week?":
    "I've identified 3 risks in your schedule this week:\n\n⚠️ **Acme Corp call (Today, 11 AM)** — SLA impasse could derail $850K deal. No backup concession strategy documented.\n\n⚠️ **Board deck prep (Today, 2 PM)** — Strategic narrative is incomplete with board meeting in 48 hours.\n\n⚠️ **Engineering attrition** — Two senior engineers resigned. No retention plan scheduled despite Marcus's email 5 hours ago.\n\nRecommendation: Block 30 minutes before the Acme call to review concession options.",

  "Prepare me for the Acme Corp call":
    "Here's your briefing for the **Acme Corp call at 11 AM**:\n\n**Context:** Enterprise deal worth $850K ARR. Currently in final negotiation. James Liu (VP Engineering) is your counterpart.\n\n**The Blocker:** Acme's legal team wants 99.99% uptime SLA with financial penalties. Your standard is 99.9%.\n\n**Your Options:**\n1. **Enhanced Support Tier** — Offer 24/7 dedicated support + 15-min response SLA instead of uptime guarantee\n2. **Partial Credit Model** — 99.9% SLA with service credits (not penalties) for downtime\n\n**Leverage:** Acme has been evaluating for 4 months. Their Q3 budget closes in 2 weeks.\n\n**Talking Points:**\n- Industry benchmark is 99.9% (only 12% of vendors offer 99.99%)\n- Your current uptime is 99.95% — offer to share historical data\n- Enhanced support tier is valued at $50K/year",
}

export function AIAssistantPage() {
  const [messages, setMessages] = useState<Message[]>(initialHistory)
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, isTyping])

  const sendMessage = (text: string) => {
    if (!text.trim()) return

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setIsTyping(true)

    setTimeout(() => {
      const response =
        aiResponses[text] ||
        "I've analyzed your connected tools (email, calendar, CRM, projects) and here's what I found relevant to your question. Would you like me to dig deeper into any specific area?"
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), role: "assistant", content: response },
      ])
      setIsTyping(false)
    }, 1200)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border/50 px-8 py-5 glass">
        <div className="mx-auto flex max-w-3xl items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-coral/10">
            <Sparkles className="h-4 w-4 text-coral" strokeWidth={1.75} />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight">AI Assistant</h1>
            <p className="text-xs text-muted-foreground">
              Connected to email, calendar, CRM & projects
            </p>
          </div>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-8">
        <div className="mx-auto max-w-3xl space-y-6">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease }}
              className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}
            >
              {msg.role === "assistant" && (
                <div className="mr-3 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-coral/10">
                  <Sparkles className="h-4 w-4 text-coral" strokeWidth={1.75} />
                </div>
              )}
              <div
                className={cn(
                  "max-w-[85%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-card border border-border/60 card-shadow"
                )}
              >
                {msg.content.split("\n").map((line, i) => (
                  <p key={i} className={i > 0 ? "mt-2.5" : ""}>
                    {line.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
                      part.startsWith("**") && part.endsWith("**") ? (
                        <strong key={j} className="font-semibold">{part.slice(2, -2)}</strong>
                      ) : (
                        <span key={j}>{part}</span>
                      )
                    )}
                  </p>
                ))}
              </div>
            </motion.div>
          ))}

          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease }}
              className="flex items-center gap-3"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-coral/10">
                <Sparkles className="h-4 w-4 text-coral" strokeWidth={1.75} />
              </div>
              <div className="flex gap-1.5 rounded-2xl border border-border/50 bg-card px-5 py-4">
                <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground" />
                <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground [animation-delay:200ms]" />
                <span className="typing-dot h-1.5 w-1.5 rounded-full bg-muted-foreground [animation-delay:400ms]" />
              </div>
            </motion.div>
          )}

          {messages.length <= 1 && (
            <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {chatSuggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => sendMessage(suggestion)}
                  className="rounded-xl border border-border/60 bg-card px-5 py-3.5 text-left text-sm text-muted-foreground transition-all duration-300 hover:border-coral/20 hover:bg-accent/50 hover:text-foreground hover:shadow-sm cursor-pointer"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-border/50 px-8 py-5 glass">
        <div className="mx-auto flex max-w-3xl items-center gap-2.5">
          <Button variant="ghost" size="icon" className="shrink-0 text-muted-foreground">
            <Paperclip className="h-4 w-4" strokeWidth={1.75} />
          </Button>
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
            placeholder="Ask Atlas anything about your business..."
            className="flex-1"
          />
          <Button variant="ghost" size="icon" className="shrink-0 text-muted-foreground">
            <Mic className="h-4 w-4" strokeWidth={1.75} />
          </Button>
          <Button
            variant="coral"
            size="icon"
            className="shrink-0"
            onClick={() => sendMessage(input)}
            disabled={!input.trim()}
          >
            <Send className="h-4 w-4" strokeWidth={1.75} />
          </Button>
        </div>
      </div>
    </div>
  )
}
