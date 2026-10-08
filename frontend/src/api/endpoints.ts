import { api, unwrap } from './client'
import type { ControlRequest, EventCreate, EventUpdate, HistoryKey } from './types'

type Path = { params: { path: { simulation_id: string } } }

const bySimulation = (simulationId: string): Path => ({ params: { path: { simulation_id: simulationId } } })

export const endpoints = {
  catalog: () => unwrap(api.GET('/api/v1/catalog')),
  parameterSchema: () => unwrap(api.GET('/api/v1/parameters/schema')),
  scenarios: () => unwrap(api.GET('/api/v1/scenarios')),

  createSimulation: (scenarioId: string) =>
    unwrap(api.POST('/api/v1/simulations', { body: { scenario_id: scenarioId } })),
  deleteSimulation: (simulationId: string) =>
    unwrap(api.DELETE('/api/v1/simulations/{simulation_id}', bySimulation(simulationId))),
  state: (simulationId: string) =>
    unwrap(api.GET('/api/v1/simulations/{simulation_id}/state', bySimulation(simulationId))),

  control: (simulationId: string, request: Partial<ControlRequest> & Pick<ControlRequest, 'action'>) =>
    unwrap(
      api.POST('/api/v1/simulations/{simulation_id}/control', {
        ...bySimulation(simulationId),
        body: { steps: 1, keep_obstacles: false, ...request },
      }),
    ),

  updateParameters: (simulationId: string, values: Record<string, number>) =>
    unwrap(
      api.PATCH('/api/v1/simulations/{simulation_id}/parameters', { ...bySimulation(simulationId), body: { values } }),
    ),

  history: (simulationId: string, keys: HistoryKey[], every: number) =>
    unwrap(
      api.GET('/api/v1/simulations/{simulation_id}/history', {
        params: { path: { simulation_id: simulationId }, query: { keys, every } },
      }),
    ),

  summary: (simulationId: string) =>
    unwrap(api.GET('/api/v1/simulations/{simulation_id}/metrics/summary', bySimulation(simulationId))),

  paintObstacles: (simulationId: string, cells: [number, number][], radius: number, mode: 'add' | 'erase') =>
    unwrap(
      api.POST('/api/v1/simulations/{simulation_id}/world/obstacles', {
        ...bySimulation(simulationId),
        body: { cells, radius, mode },
      }),
    ),

  placeFood: (simulationId: string, x: number, y: number, radius: number, mode: 'add' | 'erase') =>
    unwrap(
      api.POST('/api/v1/simulations/{simulation_id}/world/food', {
        ...bySimulation(simulationId),
        body: { x, y, radius, amount: radius * radius * 20, mode },
      }),
    ),

  placePredators: (simulationId: string, x: number, y: number, count = 1) =>
    unwrap(
      api.POST('/api/v1/simulations/{simulation_id}/predators', { ...bySimulation(simulationId), body: { x, y, count } }),
    ),

  removePredator: (simulationId: string, predatorId: number) =>
    unwrap(
      api.DELETE('/api/v1/simulations/{simulation_id}/predators/{predator_id}', {
        params: { path: { simulation_id: simulationId, predator_id: predatorId } },
      }),
    ),

  createEvent: (simulationId: string, event: EventCreate) =>
    unwrap(api.POST('/api/v1/simulations/{simulation_id}/events', { ...bySimulation(simulationId), body: event })),

  updateEvent: (simulationId: string, eventId: string, update: EventUpdate) =>
    unwrap(
      api.PATCH('/api/v1/simulations/{simulation_id}/events/{event_id}', {
        params: { path: { simulation_id: simulationId, event_id: eventId } },
        body: update,
      }),
    ),

  cancelEvent: (simulationId: string, eventId: string) =>
    unwrap(
      api.DELETE('/api/v1/simulations/{simulation_id}/events/{event_id}', {
        params: { path: { simulation_id: simulationId, event_id: eventId } },
      }),
    ),
}
