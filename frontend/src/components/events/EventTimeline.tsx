import { CloudRain, Skull, Sun, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import { useMemo, useState, type ReactNode } from 'react'
import { endpoints } from '../../api/endpoints'
import type { EventInfo, PerturbationType } from '../../api/types'
import { attempt, currentSimulationId } from '../../sim/actions'
import {
  DEFAULT_LAUNCH,
  eventRequest,
  PERTURBATION_ORDER,
  PERTURBATIONS,
  timelineDomain,
  visibleEvents,
  type LaunchOptions,
} from '../../sim/perturbations'
import { useSimulation } from '../../sim/store'
import { useUi } from '../../sim/ui'
import { formatCount, formatValue, pluralize } from '../format'
import { IconButton } from '../ui/IconButton'
import { Slider } from '../ui/Slider'

const ICONS: Record<PerturbationType, ReactNode> = {
  drought: <Sun size={20} />,
  flood: <CloudRain size={20} />,
  predator_wave: <Skull size={20} />,
}

const STATUS_LABELS: Record<EventInfo['status'], string> = {
  scheduled: 'Programada',
  active: 'En curso',
  finished: 'Terminada',
  cancelled: 'Cancelada',
}

async function launch(type: PerturbationType, options: LaunchOptions) {
  const simulationId = currentSimulationId()
  if (!simulationId) return
  const event = await attempt(() =>
    endpoints.createEvent(simulationId, eventRequest(type, options, useSimulation.getState().world)),
  )
  if (event && currentSimulationId() === simulationId) useSimulation.getState().upsertEvent(event)
}

async function cancel(eventId: string) {
  const simulationId = currentSimulationId()
  if (!simulationId) return
  const event = await attempt(() => endpoints.cancelEvent(simulationId, eventId))
  if (event && currentSimulationId() === simulationId) useSimulation.getState().upsertEvent(event)
}

function LaunchCard({ type, onClose }: { type: PerturbationType; onClose: () => void }) {
  const [options, setOptions] = useState(DEFAULT_LAUNCH)
  const meta = PERTURBATIONS[type]
  const set = (patch: Partial<LaunchOptions>) => setOptions((current) => ({ ...current, ...patch }))

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.15 }}
      className="panel absolute bottom-full left-0 mb-2 flex w-72 flex-col gap-3 p-4"
    >
      <div className="flex items-start gap-2">
        <div>
          <div className="font-extrabold" style={{ color: meta.color }}>
            {meta.label}
          </div>
          <p className="text-xs text-sand-400">{meta.description}</p>
        </div>
        <button onClick={onClose} aria-label="Cerrar" className="ml-auto rounded p-1 text-sand-400 hover:bg-soil-700">
          <X size={16} />
        </button>
      </div>
      <label className="flex flex-col gap-1.5 text-xs font-bold text-sand-300">
        <span className="flex justify-between">
          Intensidad <span className="text-amber-400">{Math.round(options.intensity * 100)}%</span>
        </span>
        <Slider
          label="Intensidad"
          value={options.intensity}
          min={0.1}
          max={1}
          step={0.05}
          onChange={(intensity) => set({ intensity })}
        />
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-bold text-sand-300">
        <span className="flex justify-between">
          Duración <span className="text-amber-400">{formatCount(options.duration)} ticks</span>
        </span>
        <Slider
          label="Duración"
          value={options.duration}
          min={50}
          max={3000}
          step={50}
          onChange={(duration) => set({ duration })}
        />
      </label>
      {type === 'predator_wave' && (
        <label className="flex flex-col gap-1.5 text-xs font-bold text-sand-300">
          <span className="flex justify-between">
            Depredadores <span className="text-amber-400">{options.predatorCount}</span>
          </span>
          <Slider
            label="Depredadores"
            value={options.predatorCount}
            min={1}
            max={20}
            step={1}
            onChange={(predatorCount) => set({ predatorCount })}
          />
        </label>
      )}
      <button
        onClick={() => {
          void launch(type, options)
          onClose()
        }}
        className="rounded-xl py-2 text-sm font-extrabold text-soil-950 transition-transform duration-150 hover:scale-[1.02] active:scale-95"
        style={{ background: meta.color }}
      >
        Lanzar ahora
      </button>
    </motion.div>
  )
}

function EventDetails({ event, onClose }: { event: EventInfo; onClose: () => void }) {
  const meta = PERTURBATIONS[event.type]
  const cancellable = event.status === 'scheduled' || event.status === 'active'
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.15 }}
      className="panel absolute right-0 bottom-full mb-2 flex w-64 flex-col gap-2 p-4 text-sm"
    >
      <div className="flex items-center gap-2">
        <span className="font-extrabold" style={{ color: meta.color }}>
          {meta.label}
        </span>
        <span className="rounded-full bg-soil-700 px-2 py-0.5 text-[11px] font-bold text-sand-300">
          {STATUS_LABELS[event.status]}
        </span>
        <button onClick={onClose} aria-label="Cerrar" className="ml-auto rounded p-1 text-sand-400 hover:bg-soil-700">
          <X size={16} />
        </button>
      </div>
      <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <dt className="text-sand-400">Ticks</dt>
        <dd className="text-sand-100 tabular-nums">
          {formatCount(event.start_tick)} – {formatCount(event.end_tick)}
        </dd>
        <dt className="text-sand-400">Intensidad</dt>
        <dd className="text-sand-100">{formatValue(event.intensity * 100)}%</dd>
        {event.predator_count !== null && (
          <>
            <dt className="text-sand-400">Depredadores</dt>
            <dd className="text-sand-100">{event.predator_count}</dd>
          </>
        )}
        <dt className="text-sand-400">Zona</dt>
        <dd className="text-sand-100">{event.region ? `${event.region.width}×${event.region.height} celdas` : 'Todo el mundo'}</dd>
      </dl>
      {cancellable && (
        <button
          onClick={() => {
            void cancel(event.id)
            onClose()
          }}
          className="mt-1 rounded-xl bg-ember-500/20 py-1.5 text-xs font-extrabold text-ember-400 hover:bg-ember-500/30"
        >
          Cancelar perturbación
        </button>
      )}
    </motion.div>
  )
}

export function EventTimeline() {
  const tick = useSimulation((state) => Math.floor(state.tick / 10) * 10)
  const events = useSimulation((state) => state.events)
  const finished = useSimulation((state) => state.status === 'finished')
  const popover = useUi((state) => state.popover)
  const setPopover = useUi((state) => state.setPopover)
  const launching = popover?.kind === 'launch' ? popover.type : null
  const selectedId = popover?.kind === 'event' ? popover.id : null
  const coarseTick = Math.floor(tick / 50) * 50
  const domain = useMemo(() => timelineDomain(coarseTick, events), [coarseTick, events])
  const shown = useMemo(() => visibleEvents(events, domain), [events, domain])
  const selected = events.find((event) => event.id === selectedId) ?? null
  const span = domain.end - domain.start
  const position = (value: number) => `${(Math.min(Math.max(value - domain.start, 0), span) / span) * 100}%`

  return (
    <div className="panel pointer-events-auto absolute bottom-3 left-3 z-10 flex w-[min(820px,calc(100%-5.5rem))] items-center gap-3 px-3 py-2">
      <div className="relative flex items-center gap-1 rounded-xl bg-soil-800/80 p-1" role="group" aria-label="Perturbaciones">
        {PERTURBATION_ORDER.map((type) => (
          <IconButton
            key={type}
            label={PERTURBATIONS[type].label}
            active={launching === type}
            disabled={finished}
            onClick={() => setPopover(launching === type ? null : { kind: 'launch', type })}
          >
            {ICONS[type]}
          </IconButton>
        ))}
        <AnimatePresence>
          {launching && <LaunchCard key={launching} type={launching} onClose={() => setPopover(null)} />}
        </AnimatePresence>
      </div>

      <div className="relative flex-1">
        <div
          className="relative h-9 rounded-lg bg-soil-800/80"
          role="group"
          aria-label="Línea de tiempo de perturbaciones"
        >
          {shown.map((event) => (
            <button
              key={event.id}
              onClick={() => setPopover(selectedId === event.id ? null : { kind: 'event', id: event.id })}
              aria-label={`${PERTURBATIONS[event.type].label}, ${STATUS_LABELS[event.status]}`}
              className={`absolute h-2 min-w-2 rounded-sm transition-opacity duration-150 hover:opacity-100 ${
                event.status === 'active' ? 'animate-pulse opacity-100' : event.status === 'finished' ? 'opacity-40' : 'opacity-80'
              } ${selectedId === event.id ? 'ring-2 ring-sand-100' : ''}`}
              style={{
                top: 4 + PERTURBATION_ORDER.indexOf(event.type) * 10,
                left: position(event.start_tick),
                width: `calc(${position(event.end_tick)} - ${position(event.start_tick)})`,
                background: PERTURBATIONS[event.type].color,
              }}
            />
          ))}
          <div
            className="pointer-events-none absolute -top-1 -bottom-1 w-0.5 rounded bg-sand-100 transition-[left] duration-300"
            style={{ left: position(tick) }}
          />
        </div>
        <div className="mt-0.5 flex justify-between text-[10px] text-sand-500 tabular-nums">
          <span>{formatCount(domain.start)}</span>
          <span>{shown.length === 0 ? 'Sin perturbaciones' : pluralize(shown.length, 'perturbación', 'perturbaciones')}</span>
          <span>{formatCount(domain.end)}</span>
        </div>
        <AnimatePresence>
          {selected && <EventDetails key={selected.id} event={selected} onClose={() => setPopover(null)} />}
        </AnimatePresence>
      </div>
    </div>
  )
}
