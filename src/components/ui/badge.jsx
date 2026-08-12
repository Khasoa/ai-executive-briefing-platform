import { cva } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-[11px] font-medium leading-5",
  {
    variants: {
      variant: {
        neutral: "border-border bg-subtle text-secondary-foreground",
        quiet: "border-transparent bg-muted text-secondary-foreground",
        primary: "border-primary/15 bg-primary-soft text-primary",
        accent: "border-accent/25 bg-accent-soft text-accent",
        critical: "border-critical/25 bg-critical-soft text-critical",
        outline: "border-border-strong bg-card text-secondary-foreground",
        solid: "border-transparent bg-primary text-primary-foreground",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
)

export function Badge({ className, variant, ...props }) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
