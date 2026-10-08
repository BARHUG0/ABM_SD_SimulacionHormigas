import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { SimulationState, Subscription } from '../api/types'
import { frameMessage, initMessage, makeFrame, makeState } from '../test/fixtures'
import { closeSession, frameEveryFor, openSession, updateSubscription } from './session'
import { useSimulation } from './store'
import { subscribedLayers } from './useSessionSync'

const mocks = vi.hoisted(() => ({
  sockets: [] as { subscribe: (subscription: Subscription) => void; subscriptions: Subscription[] }[],
  state: vi.fn<(simulationId: string) => Promise<SimulationState>>(),
}))

vi.mock('../api/socket', () => ({
  SimulationSocket: class {
    subscriptions: Subscription[] = []
    constructor() {
      mocks.sockets.push(this)
    }
    subscribe(subscription: Subscription) {
      this.subscriptions.push(subscription)
    }
    connect() {}
    close() {}
  },
}))

vi.mock('../api/endpoints', () => ({ endpoints: { state: mocks.state } }))

const store = () => useSimulation.getState()
const latestSocket = () => mocks.sockets[mocks.sockets.length - 1]

function deferred<T>() {
  let resolve: (value: T) => void = () => undefined
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('session', () => {
  beforeEach(() => {
    mocks.sockets.length = 0
    mocks.state.mockReset()
  })

  afterEach(() => closeSession())

  it('fetches the full state when sequence numbers skip', async () => {
    mocks.state.mockResolvedValue(makeState(40, makeFrame(150)))
    openSession('sim_1')
    store().applyMessage(initMessage(1))
    store().applyMessage(frameMessage(5, 4))
    expect(mocks.state).toHaveBeenCalledWith('sim_1')
    await vi.waitFor(() => expect(store().tick).toBe(40))
    expect(store().needsResync).toBe(false)
    expect(store().frame?.nest.stocks.workers).toBe(150)
  })

  it('drops a resync that answers after switching simulations', async () => {
    const pending = deferred<SimulationState>()
    mocks.state.mockReturnValue(pending.promise)
    openSession('sim_1')
    store().applyMessage(initMessage(1))
    store().applyMessage(frameMessage(5, 4))
    openSession('sim_2')
    pending.resolve(makeState(40))
    await pending.promise
    await Promise.resolve()
    expect(store().simulationId).toBe('sim_2')
    expect(store().info).toBeNull()
    expect(store().tick).toBe(0)
  })

  it('ignores subscriptions that only reorder layers', () => {
    openSession('sim_1')
    const socket = latestSocket()
    const sent = socket.subscriptions.length
    const layers = [...(socket.subscriptions[0].layers ?? [])].reverse()
    updateSubscription({ layers })
    expect(socket.subscriptions).toHaveLength(sent)
    updateSubscription({ frame_every: 3 })
    expect(socket.subscriptions).toHaveLength(sent + 1)
    expect(socket.subscriptions.at(-1)?.frame_every).toBe(3)
    updateSubscription({ frame_every: 1 })
  })

  it('subscribes only to visible overlays', () => {
    expect(subscribedLayers({ pheromone_food: true, pheromone_home: false, pheromone_alarm: true, food: false })).toEqual([
      'pheromone_food',
      'pheromone_alarm',
    ])
  })

  it('thins frames to the display rate at high speeds', () => {
    expect(frameEveryFor(1)).toBe(1)
    expect(frameEveryFor(30)).toBe(1)
    expect(frameEveryFor(60)).toBe(2)
    expect(frameEveryFor(120)).toBe(4)
  })
})
