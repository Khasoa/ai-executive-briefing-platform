import { useCallback } from "react"
import { Outlet } from "react-router-dom"
import { Sidebar } from "@/components/layout/Sidebar"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getWorkspace } from "@/api/workspace"

/**
 * Application shell. The workspace payload (identity, brief freshness, nav
 * counts) is fetched once here rather than by every page.
 */
export function AppLayout() {
  const fetchWorkspace = useCallback((options) => getWorkspace(options), [])
  const { data: workspace } = useApiQuery(fetchWorkspace)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar workspace={workspace} />
      <main className="flex-1 overflow-y-auto">
        <Outlet context={{ workspace }} />
      </main>
    </div>
  )
}
