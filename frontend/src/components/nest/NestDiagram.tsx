import { motion, useAnimationFrame } from 'motion/react'
import { useEffect, useRef, useState } from 'react'
import { useSimulation } from '../../sim/store'
import { formatCount, formatValue } from '../format'
import { pointAlong, RunningMax, toPath, type PathPoints } from './pipes'

type StockKey = 'food' | 'eggs' | 'larvae' | 'workers'
type FlowKey = 'food_income' | 'consumption' | 'egg_laying' | 'hatching' | 'maturation' | 'mortality' | 'foraging'

const TANK_WIDTH = 92
const TANK_HEIGHT = 104
const PARTICLES_PER_PIPE = 4
const MIN_TANK_CAPACITY = 10

const TANKS: { key: StockKey; label: string; x: number; y: number; color: string }[] = [
  { key: 'food', label: 'Comida', x: 34, y: 56, color: '#e9a23b' },
  { key: 'eggs', label: 'Huevos', x: 234, y: 56, color: '#86c1e3' },
  { key: 'larvae', label: 'Larvas', x: 234, y: 250, color: '#9cc985' },
  { key: 'workers', label: 'Obreras', x: 34, y: 250, color: '#f3e2bf' },
]

const PIPES: { key: FlowKey; label: string; points: PathPoints; labelAt: [number, number] }[] = [
  { key: 'food_income', label: 'Ingreso', points: [[180, 206], [80, 166]], labelAt: [118, 198] },
  { key: 'consumption', label: 'Consumo', points: [[34, 108], [4, 108], [4, 24]], labelAt: [6, 18] },
  { key: 'egg_laying', label: 'Puesta', points: [[126, 108], [234, 108]], labelAt: [180, 100] },
  { key: 'hatching', label: 'Eclosión', points: [[280, 160], [280, 250]], labelAt: [334, 208] },
  { key: 'maturation', label: 'Maduración', points: [[234, 302], [126, 302]], labelAt: [180, 294] },
  { key: 'mortality', label: 'Mortalidad', points: [[80, 354], [80, 392]], labelAt: [130, 386] },
  { key: 'foraging', label: 'Forrajeo', points: [[80, 250], [180, 206]], labelAt: [104, 226] },
]

function useNestNumbers() {
  const nest = useSimulation((state) => state.frame?.nest)
  const active = useSimulation((state) => state.frame?.metrics.foragers_active)
  return { nest, active }
}

function Tank({ tank, value }: { tank: (typeof TANKS)[number]; value: number }) {
  const [peak, setPeak] = useState(MIN_TANK_CAPACITY)
  if (value > peak) setPeak(value)
  const level = Math.min(value / (peak * 1.2), 1)
  const height = level * (TANK_HEIGHT - 8)
  return (
    <g>
      <rect
        x={tank.x}
        y={tank.y}
        width={TANK_WIDTH}
        height={TANK_HEIGHT}
        rx={14}
        fill="#17110c"
        stroke="#5a432f"
        strokeWidth={2}
      />
      <motion.rect
        x={tank.x + 4}
        width={TANK_WIDTH - 8}
        rx={10}
        fill={tank.color}
        fillOpacity={0.75}
        initial={false}
        animate={{ y: tank.y + TANK_HEIGHT - 4 - height, height }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
      />
      <text x={tank.x + TANK_WIDTH / 2} y={tank.y - 8} textAnchor="middle" className="fill-sand-300 text-[12px] font-bold">
        {tank.label}
      </text>
      <text
        x={tank.x + TANK_WIDTH / 2}
        y={tank.y + TANK_HEIGHT / 2 + 6}
        textAnchor="middle"
        className="fill-sand-100 text-[18px] font-black"
        style={{ paintOrder: 'stroke', stroke: '#17110c', strokeWidth: 4 }}
      >
        {formatCount(value)}
      </text>
    </g>
  )
}

export function NestDiagram() {
  const { nest, active } = useNestNumbers()
  const flowMax = useRef(
    Object.fromEntries(PIPES.map((pipe) => [pipe.key, new RunningMax(0.01)])) as Record<FlowKey, RunningMax>,
  )
  const flows = useRef<Record<FlowKey, number>>({} as Record<FlowKey, number>)
  const phases = useRef(PIPES.map(() => 0))
  const dots = useRef<(SVGCircleElement | null)[]>([])

  const flowValues: Record<FlowKey, number> = {
    food_income: nest?.flows.food_income ?? 0,
    consumption: nest?.flows.consumption ?? 0,
    egg_laying: nest?.flows.egg_laying ?? 0,
    hatching: nest?.flows.hatching ?? 0,
    maturation: nest?.flows.maturation ?? 0,
    mortality: nest?.flows.mortality ?? 0,
    foraging: active ?? 0,
  }
  useEffect(() => {
    flows.current = flowValues
  })

  useAnimationFrame((_, delta) => {
    PIPES.forEach((pipe, pipeIndex) => {
      const flow = flows.current[pipe.key] ?? 0
      const intensity = flow <= 0 ? 0 : Math.min(flow / flowMax.current[pipe.key].update(flow), 1)
      phases.current[pipeIndex] = (phases.current[pipeIndex] + (delta / 1000) * (0.1 + 0.6 * intensity)) % 1
      for (let index = 0; index < PARTICLES_PER_PIPE; index++) {
        const dot = dots.current[pipeIndex * PARTICLES_PER_PIPE + index]
        if (!dot) continue
        const [x, y] = pointAlong(pipe.points, (phases.current[pipeIndex] + index / PARTICLES_PER_PIPE) % 1)
        dot.setAttribute('cx', `${x}`)
        dot.setAttribute('cy', `${y}`)
        dot.setAttribute('opacity', intensity > 0 ? `${0.35 + 0.65 * intensity}` : '0')
      }
    })
  })

  return (
    <div className="flex flex-col gap-3">
      <svg viewBox="-40 0 440 404" className="w-full" role="img" aria-label="Diagrama de stocks y flujos del nido">
        {PIPES.map((pipe) => (
          <g key={pipe.key}>
            <path d={toPath(pipe.points)} stroke="#413022" strokeWidth={10} strokeLinecap="round" fill="none" />
            <path d={toPath(pipe.points)} stroke="#2f2318" strokeWidth={5} strokeLinecap="round" fill="none" />
            <text x={pipe.labelAt[0]} y={pipe.labelAt[1]} textAnchor="middle" className="fill-sand-400 text-[10px]">
              {pipe.label} {formatValue(flowValues[pipe.key])}
            </text>
          </g>
        ))}
        {PIPES.flatMap((pipe, pipeIndex) =>
          Array.from({ length: PARTICLES_PER_PIPE }, (_, index) => (
            <circle
              key={`${pipe.key}-${index}`}
              ref={(element) => {
                dots.current[pipeIndex * PARTICLES_PER_PIPE + index] = element
              }}
              r={3}
              fill={pipe.key === 'mortality' || pipe.key === 'consumption' ? '#e8785e' : '#f8eedb'}
              opacity={0}
            />
          )),
        )}
        <g>
          <circle cx={180} cy={206} r={26} fill="#2f2318" stroke="#7fb069" strokeWidth={2} />
          <text x={180} y={203} textAnchor="middle" className="fill-leaf-400 text-[10px] font-bold">
            Mundo
          </text>
          <text x={180} y={216} textAnchor="middle" className="fill-sand-400 text-[9px]">
            agentes
          </text>
        </g>
        {TANKS.map((tank) => (
          <Tank key={tank.key} tank={tank} value={nest?.stocks[tank.key] ?? 0} />
        ))}
      </svg>
      <p className="text-xs leading-relaxed text-sand-400">
        Los depósitos son el modelo SD del nido. Las hormigas del mundo traen la comida que entra por la tubería de
        ingreso, y el nido decide cuántas obreras salen a forrajear:{' '}
        <span className="font-bold text-sand-200">{Math.round((nest?.forager_fraction ?? 0) * 100)}%</span>.
      </p>
    </div>
  )
}
