export const TELEPORT_DISTANCE = 5

export function indexById(ids: readonly number[]): Map<number, number> {
  const index = new Map<number, number>()
  for (let position = 0; position < ids.length; position++) index.set(ids[position], position)
  return index
}

export function lerpAngle(from: number, to: number, t: number): number {
  let delta = (to - from) % (Math.PI * 2)
  if (delta > Math.PI) delta -= Math.PI * 2
  if (delta < -Math.PI) delta += Math.PI * 2
  return from + delta * t
}

export interface Track {
  x: number
  y: number
  heading: number
}

export function blend(fromX: number, fromY: number, fromHeading: number, to: Track, t: number): Track {
  const dx = to.x - fromX
  const dy = to.y - fromY
  if (dx * dx + dy * dy > TELEPORT_DISTANCE * TELEPORT_DISTANCE) return to
  return { x: fromX + dx * t, y: fromY + dy * t, heading: lerpAngle(fromHeading, to.heading, t) }
}
