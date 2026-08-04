import { cn } from "@/lib/utils"

const sizes = {
  xs: "h-6 w-6 text-[10px]",
  sm: "h-7 w-7 text-[11px]",
  md: "h-8 w-8 text-[11px]",
  lg: "h-10 w-10 text-[13px]",
}

const tones = {
  primary: "bg-primary-soft text-primary",
  neutral: "bg-muted text-secondary-foreground",
  accent: "bg-accent-soft text-accent",
}

export function Avatar({ initials, size = "md", tone = "neutral", className, ...props }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 select-none items-center justify-center rounded-full font-semibold",
        sizes[size],
        tones[tone],
        className,
      )}
      {...props}
    >
      {initials}
    </span>
  )
}

/** Overlapping avatars for attendee lists, collapsing past `max`. */
export function AvatarGroup({ people, max = 4, size = "sm", className }) {
  const shown = people.slice(0, max)
  const overflow = people.length - shown.length

  return (
    <div className={cn("flex items-center", className)}>
      {shown.map((person, index) => (
        <Avatar
          key={`${person.initials}-${index}`}
          initials={person.initials}
          size={size}
          tone={person.tone ?? "neutral"}
          title={person.title}
          className="-ml-1.5 ring-2 ring-card first:ml-0"
        />
      ))}
      {overflow > 0 && (
        <Avatar initials={`+${overflow}`} size={size} tone="neutral" className="-ml-1.5 ring-2 ring-card" />
      )}
    </div>
  )
}
