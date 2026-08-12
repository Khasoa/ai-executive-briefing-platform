import { getThemePreference, setThemePreference } from "@/lib/auth-storage"

function systemPrefersDark() {
  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false
}

/** Resolve Light | Dark | System → whether dark class should apply. */
export function resolveDark(mode) {
  if (mode === "Dark") return true
  if (mode === "Light") return false
  return systemPrefersDark()
}

export function applyTheme(mode) {
  const dark = resolveDark(mode)
  document.documentElement.classList.toggle("dark", dark)
  document.documentElement.dataset.theme = mode
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute("content", dark ? "#141618" : "#FAFAF9")
}

export function loadAndApplyTheme() {
  const mode = getThemePreference()
  applyTheme(mode)
  return mode
}

export function persistTheme(mode) {
  setThemePreference(mode)
  applyTheme(mode)
  return mode
}

/** Watch OS preference when mode is System. Returns cleanup. */
export function watchSystemTheme(getMode) {
  const mq = window.matchMedia?.("(prefers-color-scheme: dark)")
  if (!mq) return () => {}

  const onChange = () => {
    if (getMode() === "System") applyTheme("System")
  }
  mq.addEventListener?.("change", onChange)
  return () => mq.removeEventListener?.("change", onChange)
}
