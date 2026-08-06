import { useCallback, useState } from "react"
import { KeyRound, Monitor, ShieldCheck } from "lucide-react"
import { Avatar } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Field, Input } from "@/components/ui/input"
import { SegmentedControl, Toggle } from "@/components/ui/toggle"
import { PageHeader } from "@/components/common/PageHeader"
import { ListSkeleton, PageError } from "@/components/feedback/PageState"
import { useApiQuery } from "@/hooks/useApiQuery"
import { useAsyncAction } from "@/hooks/useAsyncAction"
import { getSettings, setNotification, updatePreferences } from "@/api/settings"
import { cn } from "@/lib/utils"

function Section({ title, description, children, footer }) {
  return (
    <Card className="overflow-hidden">
      <header className="border-b border-border bg-subtle px-6 py-4">
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {description && <p className="mt-0.5 text-[12px] text-muted-foreground">{description}</p>}
      </header>
      <div className="px-6 py-5">{children}</div>
      {footer && (
        <div className="flex items-center gap-3 border-t border-border bg-subtle px-6 py-3">
          {footer}
        </div>
      )}
    </Card>
  )
}

function Row({ label, description, children, className }) {
  return (
    <div className={cn("flex items-start justify-between gap-6 py-3.5", className)}>
      <div className="min-w-0">
        <p className="text-[13px] font-medium">{label}</p>
        {description && (
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

export function SettingsPage() {
  const fetchSettings = useCallback((options) => getSettings(options), [])
  const { data, loading, error, refetch, setData } = useApiQuery(fetchSettings)
  const [savedAt, setSavedAt] = useState(null)

  const savePreferences = useAsyncAction(updatePreferences)
  const toggleNotification = useAsyncAction(setNotification)

  async function patchPreferences(patch) {
    const updated = await savePreferences.run(patch)
    if (!updated) return
    setData((current) => ({ ...current, preferences: updated }))
    setSavedAt(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }))
  }

  async function patchNotification(notification, enabled) {
    const updated = await toggleNotification.run(notification.id, enabled)
    if (!updated) return
    setData((current) => ({
      ...current,
      notifications: current.notifications.map((entry) =>
        entry.id === updated.id ? updated : entry,
      ),
    }))
  }

  if (loading) return <ListSkeleton rows={4} />
  if (error) return <PageError message={error} onRetry={refetch} />

  const { profile, preferences, notifications, security, theme, connectedAccounts } = data

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-6 py-8 lg:px-10">
      <PageHeader
        eyebrow="Settings"
        title="Account and briefing preferences"
        description="Control how Briefly reads your systems, what it puts in your morning brief, and how it reaches you."
      />

      <Section title="Profile" description="How you appear across Briefly">
        <div className="mb-5 flex items-center gap-4">
          <Avatar initials={profile.avatar} size="lg" tone="primary" className="h-12 w-12 text-[15px]" />
          <div>
            <p className="text-[15px] font-semibold">{profile.fullName}</p>
            <p className="text-[13px] text-muted-foreground">
              {profile.role} · {profile.company}
            </p>
          </div>
          <Button variant="secondary" size="sm" className="ml-auto">
            Change photo
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Full name">
            <Input defaultValue={profile.fullName} />
          </Field>
          <Field label="Role">
            <Input defaultValue={profile.role} />
          </Field>
          <Field label="Work email">
            <Input defaultValue={profile.email} type="email" />
          </Field>
          <Field label="Phone">
            <Input defaultValue={profile.phone} />
          </Field>
          <Field label="Company" className="sm:col-span-2">
            <Input defaultValue={profile.company} />
          </Field>
        </div>
      </Section>

      <Section
        title="Preferences"
        description="When your brief arrives and what it emphasises"
        footer={
          <span className="text-[11px] text-muted-foreground">
            {savePreferences.pending
              ? "Saving…"
              : savedAt
                ? `Saved at ${savedAt}`
                : "Changes save automatically"}
          </span>
        }
      >
        <div className="divide-y divide-border">
          <Row label="Delivery time" description="Your brief is generated and waiting by this time.">
            <Input
              type="time"
              className="w-32"
              defaultValue={preferences.briefTime}
              onBlur={(event) => patchPreferences({ briefTime: event.target.value })}
            />
          </Row>

          <Row label="Tone" description="How directly Briefly states its recommendations.">
            <SegmentedControl
              options={preferences.toneOptions}
              value={preferences.tone}
              onChange={(tone) => patchPreferences({ tone })}
            />
          </Row>

          <Row label="Brief length" description="How much detail each section carries.">
            <SegmentedControl
              options={preferences.briefLengthOptions}
              value={preferences.briefLength}
              onChange={(briefLength) => patchPreferences({ briefLength })}
            />
          </Row>

          <Row
            label="Automatic actions"
            description="Briefly never sends email or changes a deal without your approval. This stays off by design."
          >
            <Toggle
              checked={preferences.autoApproveActions}
              onChange={() => {}}
              disabled
              label="Automatic actions"
            />
          </Row>
        </div>

        <div className="mt-4 border-t border-border pt-4">
          <p className="mb-2 text-[13px] font-medium">Focus areas</p>
          <div className="flex flex-wrap gap-1.5">
            {preferences.focusAreaOptions.map((area) => {
              const active = preferences.focusAreas.includes(area)
              return (
                <button
                  key={area}
                  type="button"
                  onClick={() =>
                    patchPreferences({
                      focusAreas: active
                        ? preferences.focusAreas.filter((entry) => entry !== area)
                        : [...preferences.focusAreas, area],
                    })
                  }
                  className={cn(
                    "cursor-pointer rounded-md border px-2.5 py-1 text-[12px] font-medium transition-colors",
                    active
                      ? "border-primary/20 bg-primary-soft text-primary"
                      : "border-border bg-card text-muted-foreground hover:border-border-strong hover:text-foreground",
                  )}
                >
                  {area}
                </button>
              )
            })}
          </div>
        </div>
      </Section>

      <Section title="Notifications" description="What Briefly interrupts you for">
        <div className="divide-y divide-border">
          {notifications.map((notification) => (
            <Row
              key={notification.id}
              label={notification.label}
              description={`${notification.description} · ${notification.channel}`}
            >
              <Toggle
                checked={notification.enabled}
                onChange={(enabled) => patchNotification(notification, enabled)}
                label={notification.label}
              />
            </Row>
          ))}
        </div>
        {toggleNotification.error && (
          <p className="mt-3 text-[12px] text-critical">{toggleNotification.error}</p>
        )}
      </Section>

      <Section title="Security" description="Access to your business intelligence">
        <div className="divide-y divide-border">
          <Row
            label="Two-factor authentication"
            description={`Enabled via ${security.twoFactorMethod}`}
          >
            <Badge variant="primary" className="gap-1.5">
              <ShieldCheck className="h-3 w-3" strokeWidth={1.75} />
              Active
            </Badge>
          </Row>
          <Row label="Password" description={`Last changed ${security.lastPasswordChange}`}>
            <Button variant="secondary" size="sm">
              Change password
            </Button>
          </Row>
        </div>

        <div className="mt-5">
          <p className="eyebrow mb-2 text-muted-foreground">Active sessions</p>
          <ul className="divide-y divide-border rounded-lg border border-border">
            {security.sessions.map((session) => (
              <li key={session.id} className="flex items-center gap-3 px-3.5 py-3">
                <Monitor className="h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium leading-snug">{session.device}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {session.location} · {session.lastActive}
                  </p>
                </div>
                {session.current ? (
                  <Badge variant="primary">This device</Badge>
                ) : (
                  <Button variant="ghost" size="sm">
                    Revoke
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-5">
          <p className="eyebrow mb-2 text-muted-foreground">API keys</p>
          <ul className="divide-y divide-border rounded-lg border border-border">
            {security.apiKeys.map((key) => (
              <li key={key.id} className="flex items-center gap-3 px-3.5 py-3">
                <KeyRound className="h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium leading-snug">{key.label}</p>
                  <p className="text-[11px] text-muted-foreground numeric">
                    {key.prefix}··· · created {key.createdAt} · last used {key.lastUsed}
                  </p>
                </div>
                <Button variant="ghost" size="sm">
                  Revoke
                </Button>
              </li>
            ))}
          </ul>
        </div>
      </Section>

      <Section title="Theme" description="Briefly is tuned for long reading sessions">
        <div className="divide-y divide-border">
          <Row label="Appearance">
            <SegmentedControl options={theme.modeOptions} value={theme.mode} onChange={() => {}} />
          </Row>
          <Row label="Density">
            <SegmentedControl
              options={theme.densityOptions}
              value={theme.density}
              onChange={() => {}}
            />
          </Row>
          <Row label="Accent">
            <SegmentedControl
              options={theme.accentOptions}
              value={theme.accent}
              onChange={() => {}}
            />
          </Row>
          <Row label="Reduce motion" description="Removes card transitions and counters.">
            <Toggle checked={theme.reducedMotion} onChange={() => {}} label="Reduce motion" />
          </Row>
        </div>
      </Section>

      <Section
        title="Connected accounts"
        description="Manage individual connections on the Integrations page"
      >
        <ul className="divide-y divide-border">
          {connectedAccounts.map((account) => (
            <li key={account.id} className="flex items-center gap-3 py-3">
              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-medium leading-snug">{account.provider}</p>
                <p className="text-[11px] text-muted-foreground">{account.detail}</p>
              </div>
              {account.status === "connected" ? (
                <>
                  <span className="text-[11px] text-muted-foreground">
                    Since {account.connectedAt}
                  </span>
                  <Button variant="ghost" size="sm">
                    Disconnect
                  </Button>
                </>
              ) : (
                <Button variant="secondary" size="sm">
                  Connect
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}
