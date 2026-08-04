import { useEffect, useRef } from "react"
import { animate, motion, useMotionValue, useTransform } from "framer-motion"
import { ease } from "@/lib/motion"

/**
 * Counts a KPI value up on first paint. Values that are not numeric
 * (or fragments like "$2.6M") keep their prefix and suffix intact.
 */
export function AnimatedNumber({ value, className }) {
  const match = String(value).match(/^(\D*)([\d.]+)(\D*)$/)
  const prefix = match?.[1] ?? ""
  const digits = match?.[2] ?? ""
  const suffix = match?.[3] ?? ""
  const target = match ? Number.parseFloat(digits) : 0
  const decimals = digits.includes(".") ? digits.split(".")[1].length : 0

  const progress = useMotionValue(0)
  const display = useTransform(progress, (current) =>
    match ? `${prefix}${current.toFixed(decimals)}${suffix}` : String(value),
  )
  const hasRun = useRef(false)

  useEffect(() => {
    if (!match || hasRun.current) return
    hasRun.current = true
    const controls = animate(progress, target, { duration: 0.9, ease })
    return () => controls.stop()
  }, [match, progress, target])

  if (!match) return <span className={className}>{value}</span>

  return <motion.span className={className}>{display}</motion.span>
}
