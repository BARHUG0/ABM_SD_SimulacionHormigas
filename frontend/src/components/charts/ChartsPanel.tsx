import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import type uPlot from 'uplot'
import { endpoints } from '../../api/endpoints'
import type { HistoryKey } from '../../api/types'
import type { SeriesTable } from '../../sim/liveHistory'
import { useSimulation } from '../../sim/store'
import { AXIS_STYLE } from './theme'
import { UPlotChart } from './UPlotChart'
import { CHART_KEYS, DEATH_CAUSES, POPULATION_SERIES, populationData, stackedDeaths } from './series'

type Range = 'recent' | 'full'

const CHART_HEIGHT = 190
const LIVE_REFRESH_MS = 250
const FULL_REFRESH_MS = 2000
const TARGET_POINTS = 800
const EMPTY_TABLE: SeriesTable = { ticks: [], series: {} }

const formatTick = (_: uPlot, values: number[]) => values.map((value) => `${Math.round(value)}`)

const populationOptions: Omit<uPlot.Options, 'width'> = {
  height: CHART_HEIGHT,
  cursor: { drag: { x: false, y: false } },
  scales: { x: { time: false }, count: { auto: true }, food: { auto: true } },
  axes: [
    { ...AXIS_STYLE, values: formatTick },
    { ...AXIS_STYLE, scale: 'count', size: 42 },
    { ...AXIS_STYLE, scale: 'food', side: 1, size: 42, grid: { show: false } },
  ],
  series: [
    { label: 'Tick' },
    ...POPULATION_SERIES.map((item) => ({
      label: item.label,
      stroke: item.color,
      width: 2,
      scale: item.scale,
      value: (_: uPlot, value: number | null) => (value === null ? '—' : value.toFixed(0)),
    })),
  ],
  legend: { live: true },
}

const deathsOptions: Omit<uPlot.Options, 'width'> = {
  height: CHART_HEIGHT,
  cursor: { drag: { x: false, y: false } },
  scales: { x: { time: false } },
  axes: [
    { ...AXIS_STYLE, values: formatTick },
    { ...AXIS_STYLE, size: 42 },
  ],
  series: [
    { label: 'Tick' },
    ...[...DEATH_CAUSES].reverse().map((cause) => ({
      label: cause.label,
      stroke: cause.color,
      fill: cause.color + 'cc',
      width: 1,
      value: (plot: uPlot, value: number | null, seriesIndex: number, index: number | null) => {
        if (value === null || index === null) return '—'
        const below = plot.data[seriesIndex + 1]?.[index] ?? 0
        return `${Math.round(value - (below ?? 0))}`
      },
    })),
  ],
}

function useLiveTable(enabled: boolean): SeriesTable | null {
  const [table, setTable] = useState<SeriesTable | null>(null)

  useEffect(() => {
    if (!enabled) return
    let version = -1
    const refresh = () => {
      const { live, liveVersion } = useSimulation.getState()
      if (liveVersion === version) return
      version = liveVersion
      const series = Object.fromEntries(Object.entries(live.series).map(([key, values]) => [key, values.slice()]))
      setTable({ ticks: live.ticks.slice(), series })
    }
    refresh()
    const timer = setInterval(refresh, LIVE_REFRESH_MS)
    return () => clearInterval(timer)
  }, [enabled])

  return enabled ? table : null
}

function useFullTable(enabled: boolean): SeriesTable | null {
  const simulationId = useSimulation((state) => state.simulationId)
  const running = useSimulation((state) => state.status === 'running')
  const every = useSimulation((state) => Math.max(1, Math.ceil(state.tick / TARGET_POINTS)))
  const pausedTick = useSimulation((state) => (state.status === 'running' ? null : state.tick))
  const { data } = useQuery({
    queryKey: ['history', simulationId, every, pausedTick],
    queryFn: () => endpoints.history(simulationId!, CHART_KEYS as HistoryKey[], every),
    enabled: enabled && simulationId !== null,
    refetchInterval: running ? FULL_REFRESH_MS : false,
    placeholderData: (previous) => previous,
  })
  return enabled && data ? { ticks: data.ticks, series: data.series } : null
}

export function ChartsPanel() {
  const [range, setRange] = useState<Range>('recent')
  const live = useLiveTable(range === 'recent')
  const full = useFullTable(range === 'full')
  const table = (range === 'recent' ? live : full) ?? EMPTY_TABLE
  const population = useMemo(() => populationData(table), [table])
  const deaths = useMemo(() => stackedDeaths(table), [table])

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-1 self-start rounded-xl bg-soil-800 p-1 text-xs font-bold">
        {(['recent', 'full'] as Range[]).map((option) => (
          <button
            key={option}
            onClick={() => setRange(option)}
            aria-pressed={range === option}
            className={`rounded-lg px-3 py-1.5 transition-colors duration-150 ${
              range === option ? 'bg-sand-200 text-soil-950' : 'text-sand-300 hover:bg-soil-700'
            }`}
          >
            {option === 'recent' ? 'Últimos 500 ticks' : 'Corrida completa'}
          </button>
        ))}
      </div>

      <section>
        <h3 className="mb-1 text-sm font-extrabold text-sand-200">Población y reservas</h3>
        <UPlotChart options={populationOptions} data={population} />
      </section>

      <section>
        <h3 className="mb-1 text-sm font-extrabold text-sand-200">Muertes acumuladas por causa</h3>
        <UPlotChart options={deathsOptions} data={deaths} />
      </section>
    </div>
  )
}
