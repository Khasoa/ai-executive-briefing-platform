import { motion } from "framer-motion"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { enter } from "@/lib/motion"

/**
 * One numbered section of the Morning Brief.
 *
 * The brief reads as a document rather than a dashboard, so sections share a
 * fixed rhythm: rule, number, title, one line of context, then content.
 */
export function MorningBriefCard({
  number,
  title,
  description,
  meta,
  index = 0,
  tone = "default",
  className,
  children,
}) {
  return (
    <motion.section {...enter(index)} className={cn("scroll-mt-24", className)}>
      <Card className={cn("overflow-hidden", tone === "accent" && "border-accent/25")}>
        <header
          className={cn(
            "flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border px-6 py-4",
            tone === "accent" ? "bg-accent-soft" : "bg-subtle",
          )}
        >
          <div className="flex items-baseline gap-3">
            {number && (
              <span
                className={cn(
                  "text-[11px] font-semibold numeric",
                  tone === "accent" ? "text-accent" : "text-faint",
                )}
              >
                {String(number).padStart(2, "0")}
              </span>
            )}
            <div>
              <h2 className="text-[15px] font-semibold tracking-tight text-foreground">{title}</h2>
              {description && (
                <p className="mt-0.5 text-[12px] text-muted-foreground">{description}</p>
              )}
            </div>
          </div>
          {meta && <span className="text-[12px] text-muted-foreground numeric">{meta}</span>}
        </header>

        <div className="px-6 py-5">{children}</div>
      </Card>
    </motion.section>
  )
}
