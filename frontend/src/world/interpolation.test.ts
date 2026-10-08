import { describe, expect, it } from 'vitest'
import { blendInto, lerpAngle, TELEPORT_DISTANCE, type Track } from './interpolation'

describe('lerpAngle', () => {
  it('takes the short way across the ±π seam', () => {
    const halfway = lerpAngle(3, -3, 0.5)
    expect(Math.abs(halfway)).toBeGreaterThan(3)
    expect(Math.cos(halfway)).toBeCloseTo(-1, 2)
  })

  it('interpolates plainly when no wrap is needed', () => {
    expect(lerpAngle(0, 1, 0.25)).toBeCloseTo(0.25)
  })
})

describe('blendInto', () => {
  const track = (x: number, y: number): Track => ({ x, y, heading: 0 })

  it('moves part of the way from the previous position', () => {
    const target = track(4, 0)
    blendInto(target, 0, 0, 0, 0.5)
    expect(target.x).toBe(2)
  })

  it('snaps when the jump exceeds the teleport distance', () => {
    const target = track(TELEPORT_DISTANCE + 1, 0)
    blendInto(target, 0, 0, 0, 0.5)
    expect(target.x).toBe(TELEPORT_DISTANCE + 1)
  })

  it('accepts a larger cutoff when frames are spaced further apart', () => {
    const target = track(TELEPORT_DISTANCE + 1, 0)
    blendInto(target, 0, 0, 0, 0.5, TELEPORT_DISTANCE * 2)
    expect(target.x).toBe((TELEPORT_DISTANCE + 1) / 2)
  })
})
