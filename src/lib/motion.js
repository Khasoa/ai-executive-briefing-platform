/** Calm, executive motion presets. Short, no bounce, no drama. */
export const ease = [0.22, 0.61, 0.36, 1]

export const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35, ease },
}

/** Staggered entrance for a card in a grid or column. */
export function enter(index = 0) {
  return {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.35, delay: Math.min(index, 8) * 0.045, ease },
  }
}
