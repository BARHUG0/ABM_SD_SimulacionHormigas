import { useCatalog } from '../api/queries'
import { useUi } from '../sim/ui'
import { ANT_STATE_COLORS } from './palette'

const hex = (color: number) => `#${color.toString(16).padStart(6, '0')}`

export function AntTooltip() {
  const ant = useUi((state) => state.hoveredAnt)
  const { data: catalog } = useCatalog()
  if (!ant) return null
  const role = catalog?.ant_roles[ant.role]?.label ?? 'Hormiga'
  const state = catalog?.ant_states[ant.state]?.label ?? '—'

  return (
    <div
      className="panel pointer-events-none absolute z-20 min-w-40 px-3 py-2 text-sm"
      style={{ left: ant.screenX + 16, top: ant.screenY + 16 }}
    >
      <div className="font-bold text-sand-100">
        {role} <span className="font-normal text-sand-400">#{ant.id}</span>
      </div>
      <div className="flex items-center gap-2 text-sand-200">
        <span className="size-2 rounded-full" style={{ background: hex(ANT_STATE_COLORS[ant.state] ?? 0xffffff) }} />
        {state}
      </div>
      <div className="mt-1 grid grid-cols-2 gap-x-3 text-xs text-sand-400">
        <span>Edad</span>
        <span className="text-right text-sand-200">{ant.age} ticks</span>
        <span>Energía</span>
        <span className="text-right text-sand-200">{ant.energy.toFixed(0)}</span>
        {ant.carrying && <span className="col-span-2 text-leaf-400">Carga comida</span>}
      </div>
    </div>
  )
}
