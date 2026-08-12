import { motion } from "framer-motion"
import { cn } from "@/lib/utils"
import { fadeUp } from "@/lib/motion"

/**
 * Consistent page masthead: eyebrow, title, one line of context, optional actions.
 */
export function PageHeader({ eyebrow, title, description, actions, className }) {
  return (
    <motion.header {...fadeUp} className={cn("mb-5 sm:mb-7", className)}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
        <div className="min-w-0">
          {eyebrow && <p className="eyebrow mb-1.5 text-faint">{eyebrow}</p>}
          <h1 className="text-[1.5rem] font-semibold leading-tight tracking-tight text-foreground sm:text-[1.75rem]">
            {title}
          </h1>
          {description && (
            <p className="mt-1.5 max-w-xl text-[13px] leading-relaxed text-muted-foreground text-balance sm:text-[14px]">
              {description}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex w-full shrink-0 flex-wrap items-center gap-2 no-print sm:w-auto sm:justify-end">
            {actions}
          </div>
        )}
      </div>
    </motion.header>
  )
}

export function SectionHeading({ title, description, action, className }) {
  return (
    <div
      className={cn(
        "mb-3 flex flex-col gap-1.5 sm:mb-3.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4",
        className,
      )}
    >
      <div className="min-w-0">
        <h2 className="text-[14px] font-semibold tracking-tight text-foreground sm:text-[15px]">
          {title}
        </h2>
        {description && (
          <p className="mt-0.5 text-[12px] leading-snug text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}
