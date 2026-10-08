import type { EventCreate, EventInfo, EventUpdate, Notice, PerturbationType, Region } from '../api/types'
import type { WorldView } from './store'
import type { ToastTone } from './ui'

export interface PerturbationMeta {
  label: string
  color: string
  description: string
}

export const PERTURBATIONS: Record<PerturbationType, PerturbationMeta> = {
  drought: { label: 'Sequía', color: '#c98a2b', description: 'Reduce la comida disponible en todo el mundo' },
  flood: { label: 'Inundación', color: '#3d8fd1', description: 'El agua cubre una zona lejos del nido' },
  predator_wave: { label: 'Oleada', color: '#e2412f', description: 'Llega un grupo de depredadores' },
}

export const PERTURBATION_ORDER: PerturbationType[] = ['drought', 'flood', 'predator_wave']

export interface LaunchOptions {
  intensity: number
  duration: number
  predatorCount: number
  delay: number
}

export const DEFAULT_LAUNCH: LaunchOptions = { intensity: 0.5, duration: 500, predatorCount: 6, delay: 0 }

export const MIN_EDIT_DELAY = 50

export function launchOptionsOf(event: EventInfo, tick: number): LaunchOptions {
  return {
    intensity: event.intensity,
    duration: event.duration,
    predatorCount: event.predator_count ?? DEFAULT_LAUNCH.predatorCount,
    delay: Math.max(MIN_EDIT_DELAY, Math.round((event.start_tick - tick) / MIN_EDIT_DELAY) * MIN_EDIT_DELAY),
  }
}

const FLOOD_FRACTION = 0.3

export function floodRegion(world: WorldView): Region {
  const width = Math.max(1, Math.round(world.width * FLOOD_FRACTION))
  const height = Math.max(1, Math.round(world.height * FLOOD_FRACTION))
  const margin = Math.round(Math.min(world.width, world.height) * 0.05)
  const x = world.nest.x < world.width / 2 ? world.width - width - margin : margin
  const y = world.nest.y < world.height / 2 ? world.height - height - margin : margin
  return { x, y, width, height }
}

export function eventRequest(
  type: PerturbationType,
  options: LaunchOptions,
  world: WorldView | null,
  tick: number,
): EventCreate {
  return {
    type,
    intensity: options.intensity,
    duration: options.duration,
    region: type === 'flood' && world ? floodRegion(world) : null,
    start_tick: options.delay > 0 ? tick + options.delay : null,
    predator_count: type === 'predator_wave' ? options.predatorCount : null,
  }
}

export function eventUpdate(type: PerturbationType, options: LaunchOptions, tick: number): EventUpdate {
  return {
    intensity: options.intensity,
    duration: options.duration,
    start_tick: tick + options.delay,
    ...(type === 'predator_wave' ? { predator_count: options.predatorCount } : {}),
  }
}

export interface TimelineDomain {
  start: number
  end: number
}

const PAST_WINDOW = 1500
const MIN_SPAN = 3000

export function timelineDomain(tick: number, events: EventInfo[]): TimelineDomain {
  const start = Math.max(0, tick - PAST_WINDOW)
  const furthest = events
    .filter((event) => event.status === 'scheduled' || event.status === 'active')
    .reduce((max, event) => Math.max(max, event.end_tick), tick)
  const end = Math.max(start + MIN_SPAN, Math.ceil(furthest * 1.05))
  return { start, end }
}

export function visibleEvents(events: EventInfo[], domain: TimelineDomain): EventInfo[] {
  return events.filter(
    (event) => event.status !== 'cancelled' && event.end_tick >= domain.start && event.start_tick <= domain.end,
  )
}

export function noticeToast(notice: Notice): { text: string; tone: ToastTone } | null {
  const label = notice.event ? PERTURBATIONS[notice.event.type].label : ''
  switch (notice.kind) {
    case 'event_scheduled':
      return { text: `${label} programada para el tick ${notice.event?.start_tick}`, tone: 'info' }
    case 'event_started':
      return { text: `¡Comienza: ${label.toLowerCase()}!`, tone: 'warning' }
    case 'event_ended':
      return { text: `Terminó: ${label.toLowerCase()}`, tone: 'success' }
    case 'event_cancelled':
      return { text: `${label} cancelada`, tone: 'info' }
    case 'colony_collapsed':
      return { text: 'La colonia colapsó', tone: 'error' }
    case 'simulation_finished':
      return { text: 'La simulación terminó', tone: 'info' }
    case 'simulation_reset':
      return { text: 'Simulación reiniciada', tone: 'info' }
    default:
      return null
  }
}
