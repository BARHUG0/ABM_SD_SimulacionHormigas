import { describe, expect, it } from 'vitest'
import { historyEvery, stackedDeaths } from './series'

describe('historyEvery', () => {
  it('counts stored samples, not ticks, when the history is thinned', () => {
    expect(historyEvery(0, 1, 800)).toBe(1)
    expect(historyEvery(8000, 1, 800)).toBe(10)
    expect(historyEvery(32000, 2, 800)).toBe(20)
    expect(historyEvery(32000, 64, 800)).toBe(1)
  })
})

describe('stackedDeaths', () => {
  it('stacks causes so the first band holds the total', () => {
    const table = {
      ticks: [1, 2],
      series: {
        'deaths.predator': [1, 2],
        'deaths.flood': [0, 3],
        'deaths.starvation': [4, 4],
        'deaths.old_age': [1, 1],
      },
    }
    expect(stackedDeaths(table)).toEqual([
      [1, 2],
      [6, 10],
      [5, 9],
      [1, 5],
      [1, 2],
    ])
  })
})
