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

export function blendInto(
  track: Track,
  fromX: number,
  fromY: number,
  fromHeading: number,
  t: number,
  maxDistance = TELEPORT_DISTANCE,
): void {
  const dx = track.x - fromX
  const dy = track.y - fromY
  if (dx * dx + dy * dy > maxDistance * maxDistance) return
  track.x = fromX + dx * t
  track.y = fromY + dy * t
  track.heading = lerpAngle(fromHeading, track.heading, t)
}
