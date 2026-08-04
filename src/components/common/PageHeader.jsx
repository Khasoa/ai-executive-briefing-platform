import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { fadeUp } from "@/lib/motion"

/**
 * Consistent page masthead: eyebrow, title, one line of context, optional actions.
 */
export function PageHeader({ eyebrow, title, description, actions, className }) {
  return (
    <motion.header {...fadeUp} className={cn("mb-8", className)}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          {eyebrow && <p className="eyebrow mb-2 text-muted-foreground">{eyebrow}</p>}
          <h1 className="text-[1.75rem] font-semibold leading-tight tracking-tight text-foreground">
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-muted-foreground text-balance">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2 no-print">{actions}</div>}
      </div>
    </motion.header>
  )
}

export function SectionHeading({ title, description, action, className }) {
  return (
    <div className={cn("mb-4 flex items-end justify-between gap-4", className)}>
      <div>
        <h2 className="text-[15px] font-semibold tracking-tight text-foreground">{title}</h2>
        {description && <p className="mt-1 text-[13px] text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  )
}
