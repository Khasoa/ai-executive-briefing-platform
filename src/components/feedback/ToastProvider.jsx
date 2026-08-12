import { useCallback, useMemo, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { CheckCircle2, CircleAlert, X } from "lucide-react"
import { ToastContext } from "@/components/feedback/toast-context"
import { cn } from "@/lib/utils"

const ICONS = {
  success: CheckCircle2,
  error: CircleAlert,
}

let toastId = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef(new Map())

  const dismiss = useCallback((id) => {
    const timer = timers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const push = useCallback(
    (tone, message, options = {}) => {
      if (!message) return
      const id = ++toastId
      const duration = options.duration ?? (tone === "error" ? 6000 : 3500)
      setToasts((current) => [...current.slice(-3), { id, tone, message }])
      if (duration > 0) {
        timers.current.set(
          id,
          setTimeout(() => dismiss(id), duration),
        )
      }
    },
    [dismiss],
  )

  const api = useMemo(
    () => ({
      success: (message, options) => push("success", message, options),
      error: (message, options) => push("error", message, options),
      dismiss,
    }),
    [dismiss, push],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 px-4 pb-6 sm:items-end sm:pr-6"
        aria-live="polite"
        aria-relevant="additions"
      >
        <AnimatePresence initial={false}>
          {toasts.map((toast) => {
            const Icon = ICONS[toast.tone] ?? CheckCircle2
            return (
              <motion.div
                key={toast.id}
                initial={{ opacity: 0, y: 12, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.98 }}
                transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                className={cn(
                  "pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border bg-card px-3.5 py-3 surface-raised",
                  toast.tone === "error" ? "border-critical/20" : "border-border",
                )}
                role="status"
              >
                <Icon
                  className={cn(
                    "mt-0.5 h-4 w-4 shrink-0",
                    toast.tone === "error" ? "text-critical" : "text-primary",
                  )}
                  strokeWidth={1.75}
                  aria-hidden="true"
                />
                <p className="min-w-0 flex-1 text-[13px] leading-snug text-foreground">
                  {toast.message}
                </p>
                <button
                  type="button"
                  onClick={() => dismiss(toast.id)}
                  className="cursor-pointer rounded-md p-0.5 text-faint transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-ring/40"
                  aria-label="Dismiss notification"
                >
                  <X className="h-3.5 w-3.5" strokeWidth={1.75} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}
