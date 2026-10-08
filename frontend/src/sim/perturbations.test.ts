import { describe, expect, it } from 'vitest'
import type { EventInfo } from '../api/types'
import {
  DEFAULT_LAUNCH,
  eventRequest,
  eventUpdate,
  floodRegion,
  launchOptionsOf,
  MIN_EDIT_DELAY,
  noticeToast,
  timelineDomain,
  visibleEvents,
} from './perturbations'

const world = { width: 200, height: 200, nest: { x: 40, y: 40, radius: 5 } }

const event = (overrides: Partial<EventInfo>): EventInfo => ({
  id: 'evt',
  type: 'drought',
  intensity: 0.5,
  duration: 500,
  region: null,
  start_tick: 100,
  end_tick: 600,
  predator_count: null,
  status: 'scheduled',
  ...overrides,
})

describe('eventRequest', () => {
  it('places floods away from the nest', () => {
    const region = floodRegion(world)
    expect(region.x).toBeGreaterThan(world.nest.x)
    expect(region.y).toBeGreaterThan(world.nest.y)
    expect(region.x + region.width).toBeLessThanOrEqual(world.width)
    expect(region.y + region.height).toBeLessThanOrEqual(world.height)
  })

  it('only sends predator count for waves', () => {
    expect(eventRequest('drought', DEFAULT_LAUNCH, world, 0)).toMatchObject({ region: null, predator_count: null })
    expect(eventRequest('predator_wave', DEFAULT_LAUNCH, world, 0).predator_count).toBe(DEFAULT_LAUNCH.predatorCount)
    expect(eventRequest('flood', DEFAULT_LAUNCH, world, 0).region).not.toBeNull()
  })

  it('starts immediately without delay and schedules relative to the current tick', () => {
    expect(eventRequest('drought', DEFAULT_LAUNCH, world, 120).start_tick).toBeNull()
    expect(eventRequest('drought', { ...DEFAULT_LAUNCH, delay: 300 }, world, 120).start_tick).toBe(420)
  })
})

describe('eventUpdate', () => {
  it('rebuilds options from a scheduled event', () => {
    const options = launchOptionsOf(event({ start_tick: 430, predator_count: null }), 100)
    expect(options).toEqual({ intensity: 0.5, duration: 500, predatorCount: DEFAULT_LAUNCH.predatorCount, delay: 350 })
    expect(launchOptionsOf(event({ start_tick: 101 }), 100).delay).toBe(MIN_EDIT_DELAY)
  })

  it('sends the new start relative to the current tick and predators only for waves', () => {
    const options = { ...DEFAULT_LAUNCH, delay: 200, predatorCount: 9 }
    expect(eventUpdate('drought', options, 50)).toEqual({ intensity: 0.5, duration: 500, start_tick: 250 })
    expect(eventUpdate('predator_wave', options, 50).predator_count).toBe(9)
  })
})

describe('timeline', () => {
  it('keeps a minimum span around the current tick', () => {
    expect(timelineDomain(0, [])).toEqual({ start: 0, end: 3000 })
    expect(timelineDomain(5000, [])).toEqual({ start: 3500, end: 6500 })
  })

  it('extends to reach pending events', () => {
    const domain = timelineDomain(100, [event({ end_tick: 10000 })])
    expect(domain.end).toBeGreaterThanOrEqual(10000)
  })

  it('hides cancelled and out-of-range events', () => {
    const domain = { start: 1000, end: 4000 }
    const events = [
      event({ id: 'old', start_tick: 0, end_tick: 500, status: 'finished' }),
      event({ id: 'cancelled', start_tick: 1500, end_tick: 2000, status: 'cancelled' }),
      event({ id: 'shown', start_tick: 900, end_tick: 1200, status: 'active' }),
    ]
    expect(visibleEvents(events, domain).map((item) => item.id)).toEqual(['shown'])
  })
})

describe('noticeToast', () => {
  it('describes event notices in Spanish', () => {
    expect(noticeToast({ kind: 'event_started', message: '', event: event({}), command_id: null })).toEqual({
      text: '¡Comienza: sequía!',
      tone: 'warning',
    })
  })

  it('ignores noisy notices', () => {
    expect(noticeToast({ kind: 'command_applied', message: '', event: null, command_id: 'cmd' })).toBeNull()
  })
})
