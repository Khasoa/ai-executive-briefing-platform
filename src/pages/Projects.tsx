import { motion } from "framer-motion"
import { FolderKanban, AlertTriangle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { projects } from "@/data/mock"
import { cn } from "@/lib/utils"
import { pageHeader, ease } from "@/lib/motion"

export function ProjectsPage() {
  return (
    <div className="mx-auto max-w-5xl px-8 py-10 lg:px-12">
      <motion.div {...pageHeader} className="mb-10">
        <div className="flex items-center gap-2.5">
          <FolderKanban className="h-5 w-5 text-coral" strokeWidth={1.75} />
          <h1 className="text-3xl font-semibold tracking-tight lg:text-[2rem]">Projects</h1>
        </div>
        <p className="mt-2 text-muted-foreground">7 active initiatives across the company</p>
      </motion.div>

      <div className="space-y-3">
        {projects.map((project, i) => (
          <motion.div
            key={project.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.45, ease }}
          >
            <Card className="hover:card-shadow-hover">
              <CardContent className="flex items-center gap-6 p-6">
                <div className="flex-1 min-w-0">
                  <div className="mb-1.5 flex items-center gap-2">
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
                <div className="w-36 shrink-0">
                  <div className="mb-1.5 flex justify-between text-xs text-muted-foreground">
                    <span>Progress</span>
                    <span className="tabular-nums">{project.progress}%</span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${project.progress}%` }}
                      transition={{ duration: 0.8, delay: 0.2 + i * 0.05, ease: [0.25, 0.1, 0.25, 1] }}
                      className={cn(
                        "h-full rounded-full",
                        project.status === "At Risk" ? "bg-gold/80" : "bg-coral/70"
                      )}
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
