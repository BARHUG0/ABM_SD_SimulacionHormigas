import { describe, expect, it } from 'vitest'
import type { EventInfo } from '../api/types'
import { DEFAULT_LAUNCH, eventRequest, floodRegion, noticeToast, timelineDomain, visibleEvents } from './perturbations'

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
    expect(eventRequest('drought', DEFAULT_LAUNCH, world)).toMatchObject({ region: null, predator_count: null })
    expect(eventRequest('predator_wave', DEFAULT_LAUNCH, world).predator_count).toBe(DEFAULT_LAUNCH.predatorCount)
    expect(eventRequest('flood', DEFAULT_LAUNCH, world).region).not.toBeNull()
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
