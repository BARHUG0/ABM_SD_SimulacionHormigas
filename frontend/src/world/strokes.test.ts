import { describe, expect, it } from 'vitest'
import { cellsBetween, foodRadius } from './strokes'

describe('cellsBetween', () => {
  it('fills every cell of a diagonal stroke without the start cell', () => {
    expect(cellsBetween([0, 0], [3, 3])).toEqual([
      [1, 1],
      [2, 2],
      [3, 3],
    ])
  })

  it('follows the longer axis', () => {
    const cells = cellsBetween([0, 0], [4, 1])
    expect(cells).toHaveLength(4)
    expect(cells.at(-1)).toEqual([4, 1])
  })

  it('returns nothing for the same cell', () => {
    expect(cellsBetween([2, 2], [2, 2])).toEqual([])
  })
})

describe('foodRadius', () => {
  it('grows with the brush and caps at 20', () => {
    expect(foodRadius(2)).toBe(4)
    expect(foodRadius(40)).toBe(20)
  })
})
