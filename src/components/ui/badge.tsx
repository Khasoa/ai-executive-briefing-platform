import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-border/60 bg-muted text-muted-foreground",
        success: "border-transparent bg-sage/15 text-sage",
        warning: "border-transparent bg-gold/15 text-[#8a7340]",
        destructive: "border-transparent bg-destructive/10 text-destructive",
        outline: "border-border/80 text-foreground bg-card",
        coral: "border-transparent bg-coral/12 text-coral",
        lavender: "border-transparent bg-lavender/15 text-[#7a6e85]",
        info: "border-transparent bg-info/12 text-info",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
