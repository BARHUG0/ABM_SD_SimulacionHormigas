import { beforeEach, describe, expect, it } from 'vitest'
import type { EventInfo, ServerMessage } from '../api/types'
import { frameMessage, initMessage, makeField, makeFrame, makeState } from '../test/fixtures'
import { useSimulation } from './store'

const store = () => useSimulation.getState()

const drought: EventInfo = {
  id: 'evt_1',
  type: 'drought',
  intensity: 0.5,
  duration: 100,
  region: null,
  start_tick: 10,
  end_tick: 110,
  predator_count: null,
  status: 'active',
}

describe('simulation store', () => {
  beforeEach(() => {
    store().begin('sim_1')
    store().applyMessage(initMessage(1), 0)
  })

  it('loads world, config and obstacles from init', () => {
    expect(store().world).toEqual({ width: 2, height: 2, nest: { x: 1, y: 1, radius: 1 } })
    expect(store().fields.obstacles?.bytes.length).toBe(4)
    expect(store().status).toBe('created')
  })

  it('keeps the previous frame for interpolation', () => {
    store().applyMessage(frameMessage(2, 1, makeFrame(100)), 100)
    store().applyMessage(frameMessage(3, 2, makeFrame(101)), 133)
    expect(store().tick).toBe(2)
    expect(store().frame?.nest.stocks.workers).toBe(101)
    expect(store().previousFrame?.nest.stocks.workers).toBe(100)
    expect(store().live.ticks).toEqual([1, 2])
  })

  it('ignores frames older than the current tick', () => {
    store().applyMessage(frameMessage(2, 5, makeFrame(100)), 100)
    store().applyMessage(frameMessage(3, 4, makeFrame(90)), 133)
    expect(store().tick).toBe(5)
    expect(store().frame?.nest.stocks.workers).toBe(100)
    expect(store().live.ticks).toEqual([5])
    store().applyMessage(frameMessage(4, 5, makeFrame(101)), 166)
    expect(store().frame?.nest.stocks.workers).toBe(101)
  })

  it('accepts lower ticks again after a new init', () => {
    store().applyMessage(frameMessage(2, 50, makeFrame(100)), 100)
    store().applyMessage(initMessage(3), 133)
    store().applyMessage(frameMessage(4, 1, makeFrame(10)), 166)
    expect(store().tick).toBe(1)
    expect(store().live.ticks).toEqual([1])
  })

  it('decodes field messages into the field map', () => {
    const message: ServerMessage = { type: 'field', seq: 2, tick: 0, sim_time: 0, payload: makeField() }
    store().applyMessage(message)
    expect(store().fields.pheromone_food?.scale).toBe(10)
  })

  it('updates status and config', () => {
    store().applyMessage({
      type: 'status',
      seq: 2,
      tick: 0,
      sim_time: 0,
      payload: { status: 'running', speed: 60, finish_reason: null },
    })
    expect(store().status).toBe('running')
    expect(store().speed).toBe(60)
  })

  it('merges events carried by notices', () => {
    const notice = (event: EventInfo, seq: number): ServerMessage => ({
      type: 'event',
      seq,
      tick: 10,
      sim_time: 10,
      payload: { kind: 'event_started', message: 'Inicia', event, command_id: null },
    })
    store().applyMessage(notice({ ...drought, status: 'scheduled' }, 2))
    store().applyMessage(notice(drought, 3))
    expect(store().events).toHaveLength(1)
    expect(store().events[0].status).toBe('active')
    expect(store().lastNotice?.kind).toBe('event_started')
  })

  it('flags a resync when sequence numbers skip', () => {
    store().applyMessage(frameMessage(2, 1))
    expect(store().needsResync).toBe(false)
    store().applyMessage(frameMessage(5, 4))
    expect(store().needsResync).toBe(true)
  })

  it('applies a resynced state while keeping streamed fields', () => {
    store().applyMessage({ type: 'field', seq: 2, tick: 0, sim_time: 0, payload: makeField() })
    store().applyMessage(frameMessage(9, 3))
    expect(store().needsResync).toBe(true)
    store().applyState(makeState(8, makeFrame(120)), 200)
    expect(store().needsResync).toBe(false)
    expect(store().tick).toBe(8)
    expect(store().status).toBe('paused')
    expect(store().speed).toBe(60)
    expect(store().frame?.nest.stocks.workers).toBe(120)
    expect(store().fields.pheromone_food).toBeDefined()
    expect(store().fields.obstacles).toBeDefined()
  })

  it('restarts sequence tracking on reconnect', () => {
    store().applyMessage(frameMessage(8, 1))
    store().setConnection('reconnecting')
    store().applyMessage(initMessage(1))
    expect(store().needsResync).toBe(false)
    expect(store().live.ticks).toEqual([])
  })
})
