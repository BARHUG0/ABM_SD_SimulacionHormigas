import * as Accordion from '@radix-ui/react-accordion'
import { ChevronDown, Lock, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { endpoints } from '../../api/endpoints'
import { useParameterSchema } from '../../api/queries'
import type { ParameterSpec } from '../../api/types'
import { attempt, currentSimulationId } from '../../sim/actions'
import { basicSpecs, groupSpecs, GROUP_LABELS, isEditable, normalizeValue, readParameter } from '../../sim/parameters'
import { useSimulation } from '../../sim/store'
import { formatValue } from '../format'
import { Slider } from '../ui/Slider'

async function updateParameter(spec: ParameterSpec, value: number) {
  const simulationId = currentSimulationId()
  if (!simulationId) return
  const config = await attempt(() => endpoints.updateParameters(simulationId, { [spec.key]: value }))
  if (config) useSimulation.setState({ config })
}

function ParameterRow({ spec }: { spec: ParameterSpec }) {
  const value = useSimulation((state) => readParameter(state.config, spec))
  const editable = useSimulation((state) => isEditable(spec, state.status))
  const [draft, setDraft] = useState<number | null>(null)
  const shown = draft ?? value
  const changed = Math.abs(value - spec.default) > spec.step / 2

  const commit = async (next: number) => {
    const normalized = normalizeValue(spec, next)
    if (normalized !== value) await updateParameter(spec, normalized)
    setDraft(null)
  }

  return (
    <div className="flex flex-col gap-1.5 py-2">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold text-sand-200" title={spec.key}>
          {spec.description}
        </span>
        {!editable && (
          <span title="Solo editable antes de iniciar o tras reiniciar" className="text-sand-500">
            <Lock size={13} aria-label="Bloqueado durante la corrida" />
          </span>
        )}
        <span className="ml-auto font-bold text-amber-400 tabular-nums">{formatValue(shown)}</span>
        <span className="text-xs text-sand-500">{spec.unit}</span>
        <button
          onClick={() => void commit(spec.default)}
          disabled={!editable || !changed}
          aria-label={`Restablecer ${spec.description}`}
          title="Restablecer valor por defecto"
          className="rounded p-0.5 text-sand-400 hover:text-sand-100 disabled:invisible"
        >
          <RotateCcw size={13} />
        </button>
      </div>
      <Slider
        value={shown}
        min={spec.minimum}
        max={spec.maximum}
        step={spec.step}
        label={spec.description}
        disabled={!editable}
        onChange={(next) => setDraft(normalizeValue(spec, next))}
        onCommit={(next) => void commit(next)}
      />
      {spec.constraints.length > 0 && <p className="text-[11px] text-sand-500">{spec.constraints.join(' · ')}</p>}
    </div>
  )
}

export function ParametersPanel() {
  const { data: specs, isError, refetch } = useParameterSchema()
  const [advanced, setAdvanced] = useState(false)

  if (isError) {
    return (
      <button onClick={() => void refetch()} className="text-sm font-bold text-amber-400 underline">
        No se pudieron cargar los parámetros. Reintentar
      </button>
    )
  }
  if (!specs) return <p className="text-sm text-sand-400">Cargando parámetros…</p>

  return (
    <div className="flex flex-col gap-3">
      <div className="divide-y divide-soil-700/60">
        {basicSpecs(specs).map((spec) => (
          <ParameterRow key={spec.key} spec={spec} />
        ))}
      </div>

      <button
        onClick={() => setAdvanced((open) => !open)}
        aria-expanded={advanced}
        className="flex items-center gap-2 self-start rounded-lg px-2 py-1 text-sm font-bold text-sand-300 hover:bg-soil-700"
      >
        <ChevronDown size={16} className={`transition-transform duration-200 ${advanced ? 'rotate-180' : ''}`} />
        {advanced ? 'Ocultar parámetros avanzados' : 'Mostrar todos los parámetros'}
      </button>

      {advanced && (
        <Accordion.Root type="multiple" className="flex flex-col gap-2">
          {groupSpecs(specs).map(([group, items]) => (
            <Accordion.Item key={group} value={group} className="rounded-xl bg-soil-800/70">
              <Accordion.Header>
                <Accordion.Trigger className="group flex w-full items-center justify-between px-3 py-2 text-sm font-extrabold text-sand-200">
                  {GROUP_LABELS[group] ?? group}
                  <ChevronDown size={16} className="transition-transform duration-200 group-data-[state=open]:rotate-180" />
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className="divide-y divide-soil-700/60 px-3 pb-2">
                {items.map((spec) => (
                  <ParameterRow key={spec.key} spec={spec} />
                ))}
              </Accordion.Content>
            </Accordion.Item>
          ))}
        </Accordion.Root>
      )}
    </div>
  )
}
