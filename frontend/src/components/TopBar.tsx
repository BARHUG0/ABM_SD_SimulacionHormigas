import { Bug, Egg, HeartPulse, LogOut, Pause, Play, RotateCcw, StepForward, Wheat } from 'lucide-react'
import type { ReactNode } from 'react'
import { useScenarios } from '../api/queries'
import { control, leaveSimulation, step, togglePlay } from '../sim/actions'
import { useSimulation } from '../sim/store'
import { useUi } from '../sim/ui'
import { formatCount } from './format'
import { IconButton } from './ui/IconButton'

const SPEEDS = [10, 30, 60, 120]

function Counter({ icon, label, value, tone }: { icon: ReactNode; label: string; value: string; tone: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl bg-soil-800/80 px-3 py-1.5">
      <span className={tone}>{icon}</span>
      <div className="leading-tight">
        <div className="text-[10px] font-bold tracking-wider text-sand-400 uppercase">{label}</div>
        <div className="text-lg font-extrabold text-sand-100 tabular-nums">{value}</div>
      </div>
    </div>
  )
}

function ConnectionBadge() {
  const connection = useSimulation((state) => state.connection)
  if (connection === 'open') return null
  if (connection !== 'closed') {
    return <span className="rounded-full bg-ember-500/20 px-3 py-1 text-xs font-bold text-ember-400">Conectando…</span>
  }
  return (
    <span className="flex items-center gap-2 rounded-full bg-ember-500/20 px-3 py-1 text-xs font-bold text-ember-400">
      Sin conexión
      <button onClick={leaveSimulation} className="text-sand-100 underline">
        Volver al inicio
      </button>
    </span>
  )
}

export function TopBar() {
  const status = useSimulation((state) => state.status)
  const speed = useSimulation((state) => state.speed)
  const tick = useSimulation((state) => state.tick)
  const scenarioId = useSimulation((state) => state.info?.scenario_id)
  const workers = useSimulation((state) => state.frame?.nest.stocks.workers)
  const food = useSimulation((state) => state.frame?.nest.stocks.food)
  const larvae = useSimulation((state) => state.frame?.nest.stocks.larvae)
  const { data: scenarios } = useScenarios()
  const scenarioName = scenarios?.find((scenario) => scenario.id === scenarioId)?.name
  const running = status === 'running'
  const finished = status === 'finished'
  const collapsed = useSimulation((state) => state.finishReason === 'colony_collapsed')

  return (
    <header className="panel pointer-events-auto absolute top-3 right-3 left-3 z-10 flex items-center gap-3 px-3 py-2">
      <div className="mr-1 leading-tight">
        <div className="text-base font-extrabold text-amber-500">Hormiguero Vivo</div>
        <div className="text-xs text-sand-400">{scenarioName ?? 'Simulación'}</div>
      </div>

      <div className="flex items-center gap-1 rounded-xl bg-soil-800/80 p-1">
        <IconButton
          label={running ? 'Pausar' : status === 'created' ? 'Iniciar' : 'Reanudar'}
          shortcut="Espacio"
          disabled={collapsed}
          onClick={() => void togglePlay()}
          active={running}
        >
          {running ? <Pause size={20} /> : <Play size={20} />}
        </IconButton>
        <IconButton label="Avanzar un tick" shortcut="→" disabled={running || finished} onClick={() => void step()}>
          <StepForward size={20} />
        </IconButton>
        <IconButton
          label="Reiniciar conservando obstáculos"
          onClick={() => void control({ action: 'reset', keep_obstacles: true })}
        >
          <RotateCcw size={20} />
        </IconButton>
      </div>

      <div className="flex items-center gap-1 rounded-xl bg-soil-800/80 p-1" role="group" aria-label="Velocidad">
        {SPEEDS.map((option) => (
          <button
            key={option}
            onClick={() => void control({ action: 'set_speed', speed: option })}
            aria-pressed={speed === option}
            className={`rounded-lg px-2.5 py-1.5 text-xs font-bold transition-colors duration-150 ${
              speed === option ? 'bg-sand-200 text-soil-950' : 'text-sand-300 hover:bg-soil-700'
            }`}
          >
            {option}/s
          </button>
        ))}
      </div>

      <div className="min-w-24 text-center leading-tight">
        <div className="text-[10px] font-bold tracking-wider text-sand-400 uppercase">Tick</div>
        <div className="font-extrabold text-sand-100 tabular-nums">{formatCount(tick)}</div>
      </div>

      <ConnectionBadge />

      <div className="ml-auto flex items-center gap-2">
        <Counter icon={<Bug size={20} />} label="Obreras" value={formatCount(workers)} tone="text-sand-200" />
        <Counter icon={<Wheat size={20} />} label="Comida" value={formatCount(food)} tone="text-amber-500" />
        <Counter icon={<Egg size={20} />} label="Larvas" value={formatCount(larvae)} tone="text-leaf-400" />
        <IconButton label="Resiliencia de la colonia" onClick={() => useUi.getState().setSummaryOpen(true)}>
          <HeartPulse size={20} />
        </IconButton>
        <IconButton label="Volver al inicio" onClick={leaveSimulation}>
          <LogOut size={20} />
        </IconButton>
      </div>
    </header>
  )
}
