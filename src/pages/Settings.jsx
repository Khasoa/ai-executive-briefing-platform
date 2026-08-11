import { useEffect, useState } from "react"
import { Monitor, ShieldCheck } from "lucide-react"
import { useAuth } from "@/auth/AuthContext"
import { Avatar } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Field, Input } from "@/components/ui/input"
import { SegmentedControl, Toggle } from "@/components/ui/toggle"
import { PageHeader } from "@/components/common/PageHeader"
import { RefreshButton } from "@/components/common/RefreshButton"
import {
  ListSkeleton,
  PageError,
  RefreshBanner,
} from "@/components/feedback/PageState"
import { useToast } from "@/hooks/useToast"
import { useApiQuery } from "@/hooks/useApiQuery"
import { useAsyncAction } from "@/hooks/useAsyncAction"
import {
  changePassword,
  getSettings,
  setNotification,
  updatePreferences,
  updateProfile,
} from "@/api/settings"
import { cn } from "@/lib/utils"

function Section({ title, description, children, footer }) {
  return (
    <Card className="overflow-hidden">
      <header className="border-b border-border bg-subtle px-4 py-4 sm:px-6">
        <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
        {description && <p className="mt-0.5 text-[12px] text-muted-foreground">{description}</p>}
      </header>
      <div className="px-4 py-5 sm:px-6">{children}</div>
      {footer && (
        <div className="flex items-center gap-3 border-t border-border bg-subtle px-4 py-3 sm:px-6">
          {footer}
        </div>
      )}
    </Card>
  )
}

function Row({ label, description, children, className }) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 py-3.5 sm:flex-row sm:items-start sm:justify-between sm:gap-6",
        className,
      )}
    >
      <div className="min-w-0">
        <p className="text-[13px] font-medium">{label}</p>
        {description && (
          <p className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{description}</p>
        )}
      </div>
      <div className="shrink-0 sm:self-center">{children}</div>
    </div>
  )
}

function isGoogleAccount(account) {
  return String(account.provider || "").toLowerCase().includes("google")
}

function initialsFromName(fullName) {
  return (
    String(fullName || "")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || "BR"
  )
}

export function SettingsPage() {
  const toast = useToast()
  const {
    user,
    theme,
    setTheme,
    updateUser,
    googleStatus,
    beginGoogleOAuth,
    disconnectGoogle,
    refreshGoogleStatus,
  } = useAuth()
  const { data, loading, refreshing, error, refreshError, refetch, setData, clearRefreshError } =
    useApiQuery(getSettings)

  const savePreferences = useAsyncAction(updatePreferences)
  const toggleNotification = useAsyncAction(setNotification)
  const saveProfile = useAsyncAction(updateProfile)
  const savePassword = useAsyncAction(changePassword)

  const [profileDraft, setProfileDraft] = useState(null)
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  })

  useEffect(() => {
    if (!data?.profile) return
    setProfileDraft({
      fullName: data.profile.fullName || "",
      role: data.profile.role || "",
      company: data.profile.company || "",
      timezone: data.profile.timezone || "",
      avatar: data.profile.avatar || initialsFromName(data.profile.fullName),
    })
  }, [data?.profile])

  async function patchPreferences(patch) {
    const previous = data?.preferences
    setData((current) =>
      current ? { ...current, preferences: { ...current.preferences, ...patch } } : current,
    )
    const { data: updated, error: actionError } = await savePreferences.run(patch)
    if (!updated) {
      if (previous) setData((current) => (current ? { ...current, preferences: previous } : current))
      if (actionError) toast.error(actionError.message)
      return
    }
    setData((current) => ({ ...current, preferences: updated }))
    toast.success("Preferences saved")
  }

  async function patchNotification(notification, enabled) {
    const previous = data?.notifications
    setData((current) => ({
      ...current,
      notifications: current.notifications.map((entry) =>
        entry.id === notification.id ? { ...entry, enabled } : entry,
      ),
    }))
    const { data: updated, error: actionError } = await toggleNotification.run(
      notification.id,
      enabled,
    )
    if (!updated) {
      if (previous) setData((current) => (current ? { ...current, notifications: previous } : current))
      if (actionError) toast.error(actionError.message)
      return
    }
    setData((current) => ({
      ...current,
      notifications: current.notifications.map((entry) =>
        entry.id === updated.id ? updated : entry,
      ),
    }))
    toast.success(updated.enabled ? `${updated.label} enabled` : `${updated.label} disabled`)
  }

  async function handleGoogleConnect() {
    try {
      await beginGoogleOAuth()
    } catch (err) {
      toast.error(err?.message || "Could not start Google connection.")
    }
  }

  async function handleGoogleDisconnect() {
    try {
      await disconnectGoogle()
      await refreshGoogleStatus()
      refetch()
      toast.success("Google disconnected")
    } catch (err) {
      toast.error(err?.message || "Could not disconnect Google.")
    }
  }

  async function handleSaveProfile(event) {
    event.preventDefault()
    if (!profileDraft) return
    const payload = {
      fullName: profileDraft.fullName.trim(),
      role: profileDraft.role.trim(),
      company: profileDraft.company.trim(),
      timezone: profileDraft.timezone.trim(),
      avatar: (profileDraft.avatar || initialsFromName(profileDraft.fullName)).trim().toUpperCase(),
    }
    const { data: updated, error: actionError } = await saveProfile.run(payload)
    if (!updated) {
      if (actionError) toast.error(actionError.message)
      return
    }
    updateUser(updated)
    setData((current) =>
      current
        ? {
            ...current,
            profile: {
              ...current.profile,
              fullName: updated.fullName,
              role: updated.role,
              company: updated.company,
              timezone: updated.timezone,
              avatar: updated.avatar,
            },
          }
        : current,
    )
    setProfileDraft({
      fullName: updated.fullName,
      role: updated.role,
      company: updated.company,
      timezone: updated.timezone,
      avatar: updated.avatar,
    })
    toast.success("Profile saved")
  }

  async function handleChangePassword(event) {
    event.preventDefault()
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      toast.error("New password and confirmation do not match")
      return
    }
    const { data: result, error: actionError } = await savePassword.run({
      currentPassword: passwordForm.currentPassword,
      newPassword: passwordForm.newPassword,
    })
    if (!result) {
      if (actionError) toast.error(actionError.message)
      return
    }
    setPasswordForm({ currentPassword: "", newPassword: "", confirmPassword: "" })
    toast.success(result.message || "Password updated")
  }

  if (loading) return <ListSkeleton rows={4} maxWidth="max-w-3xl" />
  if (error) return <PageError error={error} onRetry={refetch} />

  const { profile, preferences, notifications, security } = data
  const providerLabel = googleStatus?.connected ? "Google" : "Email / password"
  const googleConnected = Boolean(googleStatus?.connected)
  const hasPassword = Boolean(security?.hasPassword ?? profile?.hasPassword)
  const draft = profileDraft || {
    fullName: profile.fullName || "",
    role: profile.role || "",
    company: profile.company || "",
    timezone: profile.timezone || "",
    avatar: profile.avatar || initialsFromName(profile.fullName),
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
      <PageHeader
        eyebrow="Settings"
        title="Account and briefing preferences"
        description="Control how Briefly reads your systems, what it puts in your morning brief, and how it reaches you."
        actions={<RefreshButton onClick={refetch} refreshing={refreshing} />}
      />

      <RefreshBanner error={refreshError} onRetry={refetch} onDismiss={clearRefreshError} />

      <Section
        title="Profile"
        description="How you appear across Briefly"
        footer={
          <div className="flex w-full items-center justify-between gap-3">
            <span className="text-[11px] text-muted-foreground">
              {saveProfile.pending ? "Saving…" : "Changes persist to your account"}
            </span>
            <Button
              type="submit"
              form="profile-form"
              size="sm"
              disabled={saveProfile.pending}
            >
              Save profile
            </Button>
          </div>
        }
      >
        <form id="profile-form" onSubmit={handleSaveProfile}>
          <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-center">
            <Avatar
              initials={draft.avatar || user?.avatar}
              size="lg"
              tone="primary"
              className="h-12 w-12 text-[15px]"
            />
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-semibold">{draft.fullName || profile.fullName}</p>
              <p className="text-[13px] text-muted-foreground">
                {draft.role || profile.role} · {draft.company || profile.company}
              </p>
              <p className="mt-1 text-[12px] text-muted-foreground">
                Sign-in · {providerLabel}
                {googleStatus?.account ? ` · ${googleStatus.account}` : ""}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Full name">
              <Input
                value={draft.fullName}
                onChange={(event) =>
                  setProfileDraft((current) => ({
                    ...(current || draft),
                    fullName: event.target.value,
                  }))
                }
                required
                autoComplete="name"
              />
            </Field>
            <Field label="Role">
              <Input
                value={draft.role}
                onChange={(event) =>
                  setProfileDraft((current) => ({
                    ...(current || draft),
                    role: event.target.value,
                  }))
                }
                required
              />
            </Field>
            <Field label="Work email" hint="Email cannot be changed here">
              <Input value={profile.email} type="email" readOnly disabled />
            </Field>
            <Field label="Timezone" hint="IANA timezone, e.g. Europe/Athens">
              <Input
                value={draft.timezone}
                onChange={(event) =>
                  setProfileDraft((current) => ({
                    ...(current || draft),
                    timezone: event.target.value,
                  }))
                }
                required
              />
            </Field>
            <Field label="Company" className="sm:col-span-2">
              <Input
                value={draft.company}
                onChange={(event) =>
                  setProfileDraft((current) => ({
                    ...(current || draft),
                    company: event.target.value,
                  }))
                }
              />
            </Field>
            <Field
              label="Avatar initials"
              hint="Photo upload is not available yet. Briefly shows these initials."
              className="sm:col-span-2"
            >
              <Input
                value={draft.avatar}
                maxLength={10}
                onChange={(event) =>
                  setProfileDraft((current) => ({
                    ...(current || draft),
                    avatar: event.target.value.toUpperCase(),
                  }))
                }
                className="max-w-[8rem] uppercase"
              />
            </Field>
          </div>
        </form>
      </Section>

      <Section
        title="Preferences"
        description="When your brief arrives and what it emphasises"
        footer={
          <span className="text-[11px] text-muted-foreground">
            {savePreferences.pending ? "Saving…" : "Changes save automatically"}
          </span>
        }
      >
        <div className="divide-y divide-border">
          <Row label="Delivery time" description="Your brief is generated and waiting by this time.">
            <Input
              type="time"
              className="w-32"
              value={preferences.briefTime}
              onChange={(event) =>
                setData((current) => ({
                  ...current,
                  preferences: { ...current.preferences, briefTime: event.target.value },
                }))
              }
              onBlur={(event) => patchPreferences({ briefTime: event.target.value })}
            />
          </Row>

          <Row
            label="Delivery days"
            description="Days of the week your morning brief should generate."
          >
            <div className="flex flex-wrap justify-end gap-1">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => {
                const active = preferences.briefDays?.includes(day)
                return (
                  <button
                    key={day}
                    type="button"
                    aria-pressed={active}
                    onClick={() => {
                      const next = active
                        ? preferences.briefDays.filter((entry) => entry !== day)
                        : [...(preferences.briefDays || []), day]
                      patchPreferences({ briefDays: next })
                    }}
                    className={cn(
                      "min-w-9 rounded-md border px-2 py-1 text-[12px] font-medium transition-colors",
                      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40",
                      active
                        ? "border-primary/20 bg-primary-soft text-primary"
                        : "border-border bg-card text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {day}
                  </button>
                )
              })}
            </div>
          </Row>

          <Row label="Tone" description="How directly Briefly states its recommendations.">
            <SegmentedControl
              options={preferences.toneOptions}
              value={preferences.tone}
              onChange={(tone) => patchPreferences({ tone })}
              aria-label="Brief tone"
            />
          </Row>

          <Row label="Brief length" description="How much detail each section carries.">
            <SegmentedControl
              options={preferences.briefLengthOptions}
              value={preferences.briefLength}
              onChange={(briefLength) => patchPreferences({ briefLength })}
              aria-label="Brief length"
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
                  aria-pressed={active}
                  onClick={() =>
                    patchPreferences({
                      focusAreas: active
                        ? preferences.focusAreas.filter((entry) => entry !== area)
                        : [...preferences.focusAreas, area],
                    })
                  }
                  className={cn(
                    "cursor-pointer rounded-md border px-2.5 py-1 text-[12px] font-medium transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40",
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
        {notifications.length === 0 ? (
          <p className="text-[13px] text-muted-foreground">
            Notification preferences are available for the demo workspace. Your account does not
            have configurable channels yet.
          </p>
        ) : (
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
        )}
      </Section>

      <Section title="Security" description="Access to your business intelligence">
        <div className="divide-y divide-border">
          <Row
            label="Two-factor authentication"
            description={
              security.twoFactorEnabled
                ? `Enabled via ${security.twoFactorMethod}`
                : "Two-factor authentication is not available yet."
            }
          >
            {security.twoFactorEnabled ? (
              <Badge variant="primary" className="gap-1.5">
                <ShieldCheck className="h-3 w-3" strokeWidth={1.75} />
                Active
              </Badge>
            ) : (
              <Badge variant="quiet">Unavailable</Badge>
            )}
          </Row>
          <Row
            label="Password"
            description={
              hasPassword
                ? "Change your password. Other sessions will need to sign in again."
                : "This account signs in with Google and has no password. You can edit your profile without creating one."
            }
          >
            {hasPassword ? (
              <Badge variant="quiet">Password login</Badge>
            ) : (
              <Badge variant="quiet">OAuth only</Badge>
            )}
          </Row>
        </div>

        {hasPassword ? (
          <form
            className="mt-5 grid grid-cols-1 gap-3 rounded-lg border border-border p-4 sm:grid-cols-2"
            onSubmit={handleChangePassword}
          >
            <Field label="Current password" className="sm:col-span-2">
              <Input
                type="password"
                autoComplete="current-password"
                value={passwordForm.currentPassword}
                onChange={(event) =>
                  setPasswordForm((current) => ({
                    ...current,
                    currentPassword: event.target.value,
                  }))
                }
                required
              />
            </Field>
            <Field label="New password">
              <Input
                type="password"
                autoComplete="new-password"
                value={passwordForm.newPassword}
                onChange={(event) =>
                  setPasswordForm((current) => ({
                    ...current,
                    newPassword: event.target.value,
                  }))
                }
                minLength={8}
                required
              />
            </Field>
            <Field label="Confirm new password">
              <Input
                type="password"
                autoComplete="new-password"
                value={passwordForm.confirmPassword}
                onChange={(event) =>
                  setPasswordForm((current) => ({
                    ...current,
                    confirmPassword: event.target.value,
                  }))
                }
                minLength={8}
                required
              />
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit" size="sm" disabled={savePassword.pending}>
                {savePassword.pending ? "Updating…" : "Update password"}
              </Button>
            </div>
          </form>
        ) : null}

        <div className="mt-5">
          <p className="eyebrow mb-2 text-muted-foreground">Sessions & API keys</p>
          <p className="rounded-lg border border-border px-3.5 py-3 text-[12px] text-muted-foreground">
            Device session lists and personal API keys are not available yet. Use Log out in the
            account menu to end this device. Changing your password revokes other refresh sessions.
          </p>
          {security.sessions?.length ? (
            <ul className="mt-3 divide-y divide-border rounded-lg border border-border">
              {security.sessions.map((session) => (
                <li key={session.id} className="flex items-center gap-3 px-3.5 py-3">
                  <Monitor className="h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={1.75} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-medium leading-snug">{session.device}</p>
                    <p className="text-[11px] text-muted-foreground">
                      {session.location} · {session.lastActive}
                    </p>
                  </div>
                  {session.current ? <Badge variant="primary">This device</Badge> : null}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </Section>

      <Section title="Theme" description="Appearance for this browser">
        <div className="divide-y divide-border">
          <Row
            label="Appearance"
            description="Saved on this device. Light, Dark, or match your system preference."
          >
            <SegmentedControl
              options={["Light", "Dark", "System"]}
              value={theme}
              onChange={setTheme}
              aria-label="Appearance"
            />
          </Row>
          <Row
            label="Density"
            description="Density controls are not persisted by the API yet."
          >
            <SegmentedControl
              options={["Compact", "Comfortable"]}
              value="Comfortable"
              onChange={() => {}}
              aria-label="Density"
              disabled
            />
          </Row>
          <Row label="Accent" description="Accent themes are not available yet.">
            <SegmentedControl
              options={["Emerald"]}
              value="Emerald"
              onChange={() => {}}
              aria-label="Accent colour"
              disabled
            />
          </Row>
          <Row
            label="Reduce motion"
            description="Use your operating system’s reduce-motion setting. In-app override is not available yet."
          >
            <Toggle checked={false} onChange={() => {}} disabled label="Reduce motion" />
          </Row>
        </div>
      </Section>

      <Section
        title="Connected accounts"
        description="Google connects via OAuth. Other providers are coming later."
      >
        <ul className="divide-y divide-border">
          <li className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center">
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-medium leading-snug">Google</p>
              <p className="text-[11px] text-muted-foreground">
                {googleConnected
                  ? googleStatus.account || "Connected"
                  : googleStatus?.configured === false
                    ? "Google OAuth is not configured on the server"
                    : "Calendar and Gmail sync"}
              </p>
            </div>
            {googleConnected ? (
              <>
                <Badge variant="primary">Connected</Badge>
                <Button variant="ghost" size="sm" onClick={handleGoogleDisconnect}>
                  Disconnect
                </Button>
              </>
            ) : (
              <Button
                variant="secondary"
                size="sm"
                onClick={handleGoogleConnect}
                disabled={googleStatus?.configured === false}
                title={
                  googleStatus?.configured === false
                    ? "Set GOOGLE_CLIENT_ID on the API first"
                    : "Connect Google"
                }
              >
                Connect
              </Button>
            )}
          </li>

          {(data.connectedAccounts || [])
            .filter((account) => !isGoogleAccount(account))
            .map((account) => (
              <li key={account.id} className="flex items-center gap-3 py-3">
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-medium leading-snug">{account.provider}</p>
                  <p className="text-[11px] text-muted-foreground">
                    Connection for this provider is not available in the API yet.
                  </p>
                </div>
                <Button variant="secondary" size="sm" disabled title="Not available yet">
                  {account.status === "connected" ? "Disconnect" : "Connect"}
                </Button>
              </li>
            ))}
        </ul>
      </Section>
    </div>
  )
}
