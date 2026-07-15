import { BrowserRouter, Routes, Route } from "react-router-dom"
import { AppLayout } from "@/components/layout/AppLayout"
import { OverviewPage } from "@/pages/Overview"
import { DailyBriefPage } from "@/pages/DailyBrief"
import { InboxPage } from "@/pages/Inbox"
import { CalendarPage } from "@/pages/Calendar"
import { CRMPage } from "@/pages/CRM"
import { ProjectsPage } from "@/pages/Projects"
import { ResearchPage } from "@/pages/Research"
import { AIAssistantPage } from "@/pages/AIAssistant"
import { SettingsPage } from "@/pages/Settings"

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="daily-brief" element={<DailyBriefPage />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="calendar" element={<CalendarPage />} />
          <Route path="crm" element={<CRMPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="research" element={<ResearchPage />} />
          <Route path="assistant" element={<AIAssistantPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
