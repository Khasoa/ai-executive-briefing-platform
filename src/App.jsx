import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { ToastProvider } from "@/components/feedback/ToastProvider"
import { AppLayout } from "@/components/layout/AppLayout"
import { OverviewPage } from "@/pages/Overview"
import { MorningBriefPage } from "@/pages/MorningBrief"
import { InboxPage } from "@/pages/Inbox"
import { MeetingsPage } from "@/pages/Meetings"
import { CRMPage } from "@/pages/CRM"
import { AskBrieflyPage } from "@/pages/AskBriefly"
import { IntegrationsPage } from "@/pages/Integrations"
import { SettingsPage } from "@/pages/Settings"

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<OverviewPage />} />
            <Route path="morning-brief" element={<MorningBriefPage />} />
            <Route path="inbox" element={<InboxPage />} />
            <Route path="meetings" element={<MeetingsPage />} />
            <Route path="crm" element={<CRMPage />} />
            <Route path="ask" element={<AskBrieflyPage />} />
            <Route path="integrations" element={<IntegrationsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </ToastProvider>
    </BrowserRouter>
  )
}
