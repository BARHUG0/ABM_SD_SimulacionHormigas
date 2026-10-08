import { describe, expect, it } from 'vitest'
import { pointAlong } from './pipes'

describe('pointAlong', () => {
  const path = [
    [0, 0],
    [10, 0],
    [10, 30],
  ] as const

  it('measures the fraction along the whole path length', () => {
    expect(pointAlong(path, 0)).toEqual([0, 0])
    expect(pointAlong(path, 0.125)).toEqual([5, 0])
    expect(pointAlong(path, 0.5)).toEqual([10, 10])
    expect(pointAlong(path, 1)).toEqual([10, 30])
  })

  it('clamps fractions outside 0..1', () => {
    expect(pointAlong(path, -1)).toEqual([0, 0])
    expect(pointAlong(path, 2)).toEqual([10, 30])
  })
})
