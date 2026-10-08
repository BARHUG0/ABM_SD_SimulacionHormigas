import { describe, expect, it } from 'vitest'
import { makeFrame } from '../test/fixtures'
import { reachedMilestones } from './milestones'

function frameWith(workers: number, delivered: number) {
  const frame = makeFrame()
  frame.nest.stocks.workers = workers
  frame.metrics.food_delivered_total = delivered
  return frame
}

describe('reachedMilestones', () => {
  it('reports each newly crossed goal', () => {
    const ids = reachedMilestones(frameWith(260, 120), new Set()).map((item) => item.id)
    expect(ids).toEqual(['first-food', 'workers-150', 'workers-250', 'food-100'])
  })

  it('skips goals already reached', () => {
    const reached = new Set(['first-food', 'workers-150'])
    expect(reachedMilestones(frameWith(200, 50), reached)).toEqual([])
  })
})
