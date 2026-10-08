import { describe, expect, it } from 'vitest'
import { stackedDeaths } from './series'

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
