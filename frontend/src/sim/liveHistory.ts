import type { FrameData, HistoryKey } from '../api/types'

export const LIVE_KEYS = [
  'stocks.workers',
  'stocks.larvae',
  'stocks.eggs',
  'stocks.food',
  'metrics.alive_ants',
  'deaths.predator',
  'deaths.flood',
  'deaths.starvation',
  'deaths.old_age',
] as const satisfies readonly HistoryKey[]

export type LiveKey = (typeof LIVE_KEYS)[number]

const readers: Record<LiveKey, (frame: FrameData) => number> = {
  'stocks.workers': (frame) => frame.nest.stocks.workers,
  'stocks.larvae': (frame) => frame.nest.stocks.larvae,
  'stocks.eggs': (frame) => frame.nest.stocks.eggs,
  'stocks.food': (frame) => frame.nest.stocks.food,
  'metrics.alive_ants': (frame) => frame.metrics.alive_ants,
  'deaths.predator': (frame) => frame.metrics.deaths.predator,
  'deaths.flood': (frame) => frame.metrics.deaths.flood,
  'deaths.starvation': (frame) => frame.metrics.deaths.starvation,
  'deaths.old_age': (frame) => frame.metrics.deaths.old_age,
}

export interface SeriesTable {
  ticks: number[]
  series: Record<string, number[]>
}

export class LiveHistory implements SeriesTable {
  readonly window: number
  ticks: number[] = []
  series: Record<LiveKey, number[]> = LiveHistory.emptySeries()

  constructor(window = 500) {
    this.window = window
  }

  private static emptySeries(): Record<LiveKey, number[]> {
    return Object.fromEntries(LIVE_KEYS.map((key) => [key, []])) as unknown as Record<LiveKey, number[]>
  }

  clear(): void {
    this.ticks = []
    this.series = LiveHistory.emptySeries()
  }

  push(tick: number, frame: FrameData): void {
    const last = this.ticks.at(-1)
    if (last !== undefined && tick < last) this.clear()
    if (last === tick) this.dropLast()
    this.ticks.push(tick)
    for (const key of LIVE_KEYS) this.series[key].push(readers[key](frame))
    let expired = 0
    while (expired < this.ticks.length && this.ticks[expired] <= tick - this.window) expired++
    if (expired > 0) this.dropFirst(expired)
  }

  private dropLast(): void {
    this.ticks.pop()
    for (const key of LIVE_KEYS) this.series[key].pop()
  }

  private dropFirst(count: number): void {
    this.ticks.splice(0, count)
    for (const key of LIVE_KEYS) this.series[key].splice(0, count)
  }
}
