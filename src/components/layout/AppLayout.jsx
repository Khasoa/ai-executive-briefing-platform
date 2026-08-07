import { Outlet } from "react-router-dom"
import { Sidebar } from "@/components/layout/Sidebar"
import { useApiQuery } from "@/hooks/useApiQuery"
import { getWorkspace } from "@/api/workspace"

/**
 * Application shell. The workspace payload (identity, brief freshness, nav
 * counts) is fetched once here rather than by every page.
 */
export function AppLayout() {
  const { data: workspace } = useApiQuery(getWorkspace)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2 focus:text-[13px] focus:font-medium focus:shadow-md focus:outline-none focus:ring-2 focus:ring-primary-ring/40"
      >
        Skip to content
      </a>
      <Sidebar workspace={workspace} />
      <main id="main-content" className="min-w-0 flex-1 overflow-y-auto" tabIndex={-1}>
        <Outlet context={{ workspace }} />
      </main>
    </div>
  )
}
