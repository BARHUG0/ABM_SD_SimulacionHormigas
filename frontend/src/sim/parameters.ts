import type { ParameterSpec, SimulationConfig, SimulationStatus } from '../api/types'

export const BASIC_KEYS = [
  'ants.speed',
  'ants.random_turn',
  'pheromones.food_evaporation',
  'pheromones.deposit_amount',
  'world.food_regen_rate',
  'predators.attack_probability',
  'nest.max_egg_laying_rate',
]

export const GROUP_LABELS: Record<string, string> = {
  run: 'Ejecución',
  world: 'Mundo',
  pheromones: 'Feromonas',
  ants: 'Hormigas',
  predators: 'Depredadores',
  nest: 'Nido',
}

export function readParameter(config: SimulationConfig | null, spec: ParameterSpec): number {
  const group = config?.[spec.group as keyof SimulationConfig] as Record<string, unknown> | undefined
  const value = group?.[spec.name]
  return typeof value === 'number' ? value : spec.default
}

export function isEditable(spec: ParameterSpec, status: SimulationStatus): boolean {
  return spec.live_editable || status === 'created'
}

export function normalizeValue(spec: ParameterSpec, value: number): number {
  const clamped = Math.min(Math.max(value, spec.minimum), spec.maximum)
  const stepped = spec.minimum + Math.round((clamped - spec.minimum) / spec.step) * spec.step
  const bounded = Math.min(stepped, spec.maximum)
  if (spec.type === 'int') return Math.round(bounded)
  const decimals = Math.max(0, -Math.floor(Math.log10(spec.step)))
  return Number(bounded.toFixed(decimals))
}

export function groupSpecs(specs: ParameterSpec[]): [string, ParameterSpec[]][] {
  const groups = new Map<string, ParameterSpec[]>()
  for (const spec of specs) {
    const list = groups.get(spec.group) ?? []
    list.push(spec)
    groups.set(spec.group, list)
  }
  return [...groups.entries()]
}

export function basicSpecs(specs: ParameterSpec[]): ParameterSpec[] {
  return BASIC_KEYS.map((key) => specs.find((spec) => spec.key === key)).filter(
    (spec): spec is ParameterSpec => spec !== undefined,
  )
}
