import { websocketUrl } from '../api/client'
import { endpoints } from '../api/endpoints'
import { SimulationSocket } from '../api/socket'
import type { Subscription } from '../api/types'
import { useSimulation } from './store'

export const DEFAULT_SUBSCRIPTION: Subscription = {
  layers: ['pheromone_food', 'pheromone_home', 'food'],
  frame_every: 1,
  field_every: 5,
  field_downsample: 2,
}

let socket: SimulationSocket | null = null
let subscription: Subscription = DEFAULT_SUBSCRIPTION
let stopWatching: (() => void) | null = null
let resyncing = false

async function resync(simulationId: string): Promise<void> {
  resyncing = true
  try {
    useSimulation.getState().applyState(await endpoints.state(simulationId))
  } catch {
    useSimulation.setState({ needsResync: false })
  } finally {
    resyncing = false
  }
}

export function openSession(simulationId: string): void {
  closeSession()
  useSimulation.getState().begin(simulationId)
  socket = new SimulationSocket(websocketUrl(simulationId), {
    onMessage: (message) => useSimulation.getState().applyMessage(message),
    onStateChange: (state) => useSimulation.getState().setConnection(state),
  })
  socket.subscribe(subscription)
  socket.connect()
  stopWatching = useSimulation.subscribe((state) => {
    if (state.needsResync && !resyncing && state.simulationId === simulationId) void resync(simulationId)
  })
}

export function updateSubscription(changes: Partial<Subscription>): void {
  const next = { ...subscription, ...changes }
  const unchanged =
    next.frame_every === subscription.frame_every &&
    next.field_every === subscription.field_every &&
    next.field_downsample === subscription.field_downsample &&
    (next.layers ?? []).join() === (subscription.layers ?? []).join()
  if (unchanged) return
  subscription = next
  socket?.subscribe(subscription)
}

export function closeSession(): void {
  stopWatching?.()
  stopWatching = null
  socket?.close()
  socket = null
  useSimulation.getState().end()
}
