import type { SeriesTable } from '../../sim/liveHistory'

export const DEATH_CAUSES = [
  { key: 'deaths.predator', label: 'Depredador', color: '#e2412f' },
  { key: 'deaths.flood', label: 'Inundación', color: '#5fa8d3' },
  { key: 'deaths.starvation', label: 'Hambre', color: '#e9a23b' },
  { key: 'deaths.old_age', label: 'Vejez', color: '#9a7d60' },
] as const

export const POPULATION_SERIES = [
  { key: 'stocks.workers', label: 'Obreras', color: '#f3e2bf', scale: 'count' },
  { key: 'stocks.larvae', label: 'Larvas', color: '#9cc985', scale: 'count' },
  { key: 'stocks.eggs', label: 'Huevos', color: '#86c1e3', scale: 'count' },
  { key: 'stocks.food', label: 'Comida', color: '#e9a23b', scale: 'food' },
] as const

export const CHART_KEYS = [...POPULATION_SERIES.map((item) => item.key), ...DEATH_CAUSES.map((item) => item.key)]

export function populationData(table: SeriesTable): number[][] {
  return [table.ticks, ...POPULATION_SERIES.map((item) => table.series[item.key] ?? [])]
}

export function stackedDeaths(table: SeriesTable): number[][] {
  const layers: number[][] = []
  let running = table.ticks.map(() => 0)
  for (const cause of DEATH_CAUSES) {
    const values = table.series[cause.key] ?? []
    running = running.map((sum, index) => sum + (values[index] ?? 0))
    layers.push(running)
  }
  return [table.ticks, ...layers.reverse()]
}
