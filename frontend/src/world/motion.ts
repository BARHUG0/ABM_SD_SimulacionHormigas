const reducedMotionQuery = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)') ?? null

export function prefersReducedMotion(): boolean {
  return reducedMotionQuery?.matches ?? false
}
