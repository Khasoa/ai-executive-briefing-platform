import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { AuthProvider } from "@/auth/AuthContext"
import { ProtectedRoute, PublicOnlyRoute } from "@/auth/ProtectedRoute"
import { ToastProvider } from "@/components/feedback/ToastProvider"
import { AppLayout } from "@/components/layout/AppLayout"
import { OverviewPage } from "@/pages/Overview"
import { MorningBriefPage } from "@/pages/MorningBrief"
import { WeeklyDigestPage } from "@/pages/WeeklyDigest"
import { InboxPage } from "@/pages/Inbox"
import { MeetingsPage } from "@/pages/Meetings"
import { CRMPage } from "@/pages/CRM"
import { AskBrieflyPage } from "@/pages/AskBriefly"
import { IntegrationsPage } from "@/pages/Integrations"
import { SettingsPage } from "@/pages/Settings"
import { LoginPage } from "@/pages/Login"
import { RegisterPage } from "@/pages/Register"
import { OAuthCallbackPage } from "@/pages/OAuthCallback"

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            <Route element={<PublicOnlyRoute />}>
              <Route path="login" element={<LoginPage />} />
              <Route path="register" element={<RegisterPage />} />
            </Route>

            <Route path="oauth/callback" element={<OAuthCallbackPage />} />

            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route index element={<OverviewPage />} />
                <Route path="morning-brief" element={<MorningBriefPage />} />
                <Route path="weekly-digest" element={<WeeklyDigestPage />} />
                <Route path="inbox" element={<InboxPage />} />
                <Route path="meetings" element={<MeetingsPage />} />
                <Route path="crm" element={<CRMPage />} />
                <Route path="ask" element={<AskBrieflyPage />} />
                <Route path="integrations" element={<IntegrationsPage />} />
                <Route path="settings" element={<SettingsPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
