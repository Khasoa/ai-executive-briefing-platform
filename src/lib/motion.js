/** Calm, executive motion presets. Short, no bounce, no drama.

Entrance presets must never start at opacity 0 — that blanks text while
card chrome is still perceptible during route transitions / first paint.
Translate only; keep content readable the entire time.
*/
export const ease = [0.22, 0.61, 0.36, 1]

export const fadeUp = {
  initial: { y: 8 },
  animate: { y: 0 },
  transition: { duration: 0.28, ease },
}

/** Staggered entrance for a card in a grid or column. */
export function enter(index = 0) {
  return {
    initial: { y: 8 },
    animate: { y: 0 },
    transition: { duration: 0.28, delay: Math.min(index, 8) * 0.04, ease },
  }
}
