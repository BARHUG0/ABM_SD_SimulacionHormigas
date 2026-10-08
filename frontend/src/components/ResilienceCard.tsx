import * as Dialog from '@radix-ui/react-dialog'
import { useQuery } from '@tanstack/react-query'
import { HeartPulse, Skull, Sprout, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import type { ReactNode } from 'react'
import { endpoints } from '../api/endpoints'
import type { SurvivalSummary } from '../api/types'
import { PERTURBATIONS } from '../sim/perturbations'
import { useSimulation } from '../sim/store'
import { useUi } from '../sim/ui'
import { DEATH_CAUSES } from './charts/series'
import { formatCount, formatValue } from './format'

function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl bg-soil-800/80 px-3 py-2">
      <div className="text-[10px] font-bold tracking-wider text-sand-400 uppercase">{label}</div>
      <div className="text-lg font-extrabold text-sand-100 tabular-nums">{value}</div>
      {hint && <div className="text-[11px] text-sand-500">{hint}</div>}
    </div>
  )
}

type Deaths = SurvivalSummary['deaths']

const causeOf = (key: string) => key.replace('deaths.', '') as keyof Deaths

function DeathBars({ deaths }: { deaths: Deaths }) {
  const total = DEATH_CAUSES.reduce((sum, cause) => sum + deaths[causeOf(cause.key)], 0)
  if (total === 0) return <p className="text-sm text-sand-400">Ninguna hormiga murió.</p>
  return (
    <div className="flex flex-col gap-2">
      <div className="flex h-3 overflow-hidden rounded-full bg-soil-800">
        {DEATH_CAUSES.map((cause) => (
          <div
            key={cause.key}
            style={{ width: `${(deaths[causeOf(cause.key)] / total) * 100}%`, background: cause.color }}
            title={`${cause.label}: ${deaths[causeOf(cause.key)]}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-sand-300">
        {DEATH_CAUSES.map((cause) => (
          <span key={cause.key} className="flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: cause.color }} />
            {cause.label} <b className="text-sand-100">{formatCount(deaths[causeOf(cause.key)])}</b>
          </span>
        ))}
      </div>
    </div>
  )
}

function SummaryBody({ summary }: { summary: SurvivalSummary }) {
  const events = useSimulation((state) => state.events)
  const alive = summary.colony_alive

  return (
    <div className="flex flex-col gap-4">
      <div className={`flex items-center gap-3 rounded-xl px-4 py-3 ${alive ? 'bg-leaf-500/15' : 'bg-ember-500/15'}`}>
        {alive ? <Sprout className="text-leaf-400" size={28} /> : <Skull className="text-ember-400" size={28} />}
        <div>
          <div className={`text-lg font-black ${alive ? 'text-leaf-400' : 'text-ember-400'}`}>
            {alive ? 'La colonia resiste' : 'La colonia colapsó'}
          </div>
          <div className="text-xs text-sand-400">
            {alive
              ? `${formatCount(summary.ticks_elapsed)} ticks de vida`
              : `Colapso en el tick ${formatCount(summary.collapse_tick)}`}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Stat label="Población máxima" value={formatCount(summary.peak_population)} />
        <Stat
          label="Población mínima"
          value={formatCount(summary.min_population)}
          hint={`tick ${formatCount(summary.min_population_tick)}`}
        />
        <Stat label="Comida recolectada" value={formatCount(summary.total_food_delivered)} />
        <Stat
          label="Eficiencia media"
          value={formatValue(summary.mean_foraging_efficiency)}
          hint="comida por hormiga activa y tick"
        />
      </div>

      <section>
        <h3 className="mb-2 text-sm font-extrabold text-sand-200">Muertes por causa</h3>
        <DeathBars deaths={summary.deaths} />
      </section>

      <section>
        <h3 className="mb-2 text-sm font-extrabold text-sand-200">Recuperación tras perturbaciones</h3>
        {summary.recoveries.length === 0 ? (
          <p className="text-sm text-sand-400">Aún no hubo perturbaciones terminadas.</p>
        ) : (
          <ul className="flex flex-col gap-1.5 text-sm">
            {summary.recoveries.map((recovery) => {
              const event = events.find((item) => item.id === recovery.event_id)
              const meta = event ? PERTURBATIONS[event.type] : null
              return (
                <li key={recovery.event_id} className="flex items-center gap-2 rounded-lg bg-soil-800/80 px-3 py-1.5">
                  <span className="font-bold" style={{ color: meta?.color }}>
                    {meta?.label ?? 'Perturbación'}
                  </span>
                  <span className="text-sand-400 tabular-nums">
                    {formatCount(recovery.population_before)} → {formatCount(recovery.min_population_during)}
                  </span>
                  <span className="ml-auto text-xs font-bold">
                    {recovery.recovery_ticks === null ? (
                      <span className="text-ember-400">Sin recuperar</span>
                    ) : (
                      <span className="text-leaf-400">Recuperada en {formatCount(recovery.recovery_ticks)} ticks</span>
                    )}
                  </span>
                </li>
              )
            })}
          </ul>
        )}
      </section>
    </div>
  )
}

export function ResilienceCard() {
  const open = useUi((state) => state.summaryOpen)
  const close = () => useUi.getState().setSummaryOpen(false)
  const simulationId = useSimulation((state) => state.simulationId)
  const status = useSimulation((state) => state.status)
  const generation = useSimulation((state) => state.generation)
  const { data, isError, refetch } = useQuery({
    queryKey: ['summary', simulationId, generation, status],
    queryFn: () => endpoints.summary(simulationId!),
    enabled: open && simulationId !== null,
    staleTime: 0,
  })

  return (
    <Dialog.Root open={open} onOpenChange={(next) => !next && close()}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal key="resilience" forceMount>
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-40 grid place-items-center bg-soil-950/60 p-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Dialog.Content asChild forceMount aria-describedby={undefined}>
                  <motion.section
                    className="panel flex max-h-full w-[min(520px,100%)] flex-col gap-4 overflow-y-auto p-5"
                    initial={{ scale: 0.94, y: 12 }}
                    animate={{ scale: 1, y: 0 }}
                    exit={{ scale: 0.96, opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 320, damping: 26 }}
                  >
                    <header className="flex items-center gap-2">
                      <HeartPulse className="text-amber-500" size={22} />
                      <Dialog.Title className="text-xl font-black text-sand-100">Resiliencia de la colonia</Dialog.Title>
                      <Dialog.Close
                        aria-label="Cerrar resumen"
                        className="ml-auto rounded-lg p-1.5 text-sand-300 hover:bg-soil-700"
                      >
                        <X size={18} />
                      </Dialog.Close>
                    </header>
                    {data ? (
                      <SummaryBody summary={data} />
                    ) : isError ? (
                      <button onClick={() => void refetch()} className="text-sm font-bold text-amber-400 underline">
                        No se pudo cargar el resumen. Reintentar
                      </button>
                    ) : (
                      <p className="text-sm text-sand-400">Calculando resumen…</p>
                    )}
                  </motion.section>
                </Dialog.Content>
              </motion.div>
            </Dialog.Overlay>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}
