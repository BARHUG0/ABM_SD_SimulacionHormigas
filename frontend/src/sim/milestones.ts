import type { FrameData } from '../api/types'
import { formatCount } from '../components/format'

export interface Milestone {
  id: string
  text: string
}

const WORKER_GOALS = [150, 250, 500, 1000, 2000]
const FOOD_GOALS = [100, 500, 1000, 5000]

export function reachedMilestones(frame: FrameData, reached: ReadonlySet<string>): Milestone[] {
  const found: Milestone[] = []
  const delivered = frame.metrics.food_delivered_total
  const workers = frame.nest.stocks.workers

  if (delivered > 0 && !reached.has('first-food')) {
    found.push({ id: 'first-food', text: '¡Llegó la primera comida al nido!' })
  }
  for (const goal of WORKER_GOALS) {
    const id = `workers-${goal}`
    if (workers >= goal && !reached.has(id)) {
      found.push({ id, text: `¡La colonia alcanzó ${formatCount(goal)} obreras!` })
    }
  }
  for (const goal of FOOD_GOALS) {
    const id = `food-${goal}`
    if (delivered >= goal && !reached.has(id)) {
      found.push({ id, text: `${formatCount(goal)} unidades de comida recolectadas` })
    }
  }
  return found
}
