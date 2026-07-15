import { useEffect, useRef } from "react"
import { animate, useMotionValue, useTransform, motion } from "framer-motion"

interface AnimatedNumberProps {
  value: string
  className?: string
}

/** Animates numeric portions of KPI values (e.g. "12", "$4.2M"). */
export function AnimatedNumber({ value, className }: AnimatedNumberProps) {
  const match = value.match(/^(\D*)([\d.]+)(\D*)$/)
  const prefix = match?.[1] ?? ""
  const numStr = match?.[2] ?? value
  const suffix = match?.[3] ?? ""
  const target = parseFloat(numStr)

  const motionVal = useMotionValue(0)
  const display = useTransform(motionVal, (v) => {
    if (!match) return value
    const decimals = numStr.includes(".") ? 1 : 0
    return `${prefix}${v.toFixed(decimals)}${suffix}`
  })

  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!match || hasAnimated.current) return
    hasAnimated.current = true
    animate(motionVal, target, { duration: 1.1, ease: [0.25, 0.1, 0.25, 1] })
  }, [match, motionVal, target])

  if (!match) {
    return <span className={className}>{value}</span>
  }

  return <motion.span className={className}>{display}</motion.span>
}
