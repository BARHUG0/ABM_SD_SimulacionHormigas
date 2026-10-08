import { describe, expect, it } from 'vitest'
import { makeFrame } from '../test/fixtures'
import { LiveHistory } from './liveHistory'

describe('LiveHistory', () => {
  it('keeps only the most recent window of ticks', () => {
    const history = new LiveHistory(3)
    for (let tick = 1; tick <= 5; tick++) history.push(tick, makeFrame(tick * 10))
    expect(history.ticks).toEqual([3, 4, 5])
    expect(history.series['stocks.workers']).toEqual([30, 40, 50])
  })

  it('replaces a repeated tick and clears when time goes back', () => {
    const history = new LiveHistory()
    history.push(1, makeFrame(10))
    history.push(1, makeFrame(11))
    expect(history.series['stocks.workers']).toEqual([11])
    history.push(0, makeFrame(5))
    expect(history.ticks).toEqual([0])
  })
})
