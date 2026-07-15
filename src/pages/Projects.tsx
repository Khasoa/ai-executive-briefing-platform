import { motion } from "framer-motion"
import { FolderKanban, AlertTriangle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { projects } from "@/data/mock"
import { cn } from "@/lib/utils"

export function ProjectsPage() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-8 lg:px-10">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-center gap-2">
          <FolderKanban className="h-5 w-5 text-primary" />
          <h1 className="text-2xl font-semibold tracking-tight lg:text-3xl">Projects</h1>
        </div>
        <p className="mt-1 text-muted-foreground">7 active initiatives across the company</p>
      </motion.div>

      <div className="space-y-3">
        {projects.map((project, i) => (
          <motion.div
            key={project.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card className="transition-all duration-200 hover:card-shadow-hover">
              <CardContent className="flex items-center gap-5 p-5">
                <div className="flex-1 min-w-0">
                  <div className="mb-1 flex items-center gap-2">
                    <h3 className="font-medium">{project.name}</h3>
                    <Badge
                      variant={project.status === "At Risk" ? "warning" : "success"}
                      className="gap-1"
                    >
                      {project.status === "At Risk" && <AlertTriangle className="h-3 w-3" />}
                      {project.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {project.owner} · Due {project.dueDate}
                  </p>
                </div>
                <div className="w-32 shrink-0">
                  <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                    <span>Progress</span>
                    <span>{project.progress}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        project.status === "At Risk" ? "bg-amber-500" : "bg-primary"
                      )}
                      style={{ width: `${project.progress}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
