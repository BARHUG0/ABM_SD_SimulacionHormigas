import type { FieldData, FrameData, ServerMessage, SimulationConfig, SimulationInfo } from '../api/types'

export function encodeBytes(bytes: number[]): string {
  return btoa(String.fromCharCode(...bytes))
}

export function makeField(overrides: Partial<FieldData> = {}): FieldData {
  return {
    layer: 'pheromone_food',
    width: 2,
    height: 2,
    downsample: 1,
    encoding: 'uint8_base64',
    scale: 10,
    data: encodeBytes([0, 51, 255, 102]),
    ...overrides,
  }
}

export function makeFrame(workers = 100, deaths = 0): FrameData {
  return {
    ants: {
      ids: [1, 2],
      x: [10, 20],
      y: [10, 20],
      heading: [0, 1],
      role: [0, 1],
      state: [0, 1],
      carrying: [false, true],
      energy: [50, 60],
      age: [5, 9],
    },
    predators: { ids: [], x: [], y: [], heading: [], state: [], energy: [], source: [] },
    nest: {
      stocks: { food: 200, eggs: 20, larvae: 20, workers },
      flows: { food_income: 1, consumption: 1, egg_laying: 0.5, hatching: 0.1, maturation: 0.05, mortality: 0.01 },
      forager_fraction: 0.4,
    },
    metrics: {
      alive_ants: workers,
      foragers_active: 40,
      ants_in_nest: 60,
      predators: 0,
      food_in_world: 1500,
      food_delivered_total: 0,
      foraging_efficiency: 0,
      deaths: { predator: deaths, flood: 0, starvation: 0, old_age: 0 },
    },
    active_event_ids: [],
  }
}

export const info: SimulationInfo = {
  id: 'sim_1',
  name: 'Prueba',
  status: 'created',
  finish_reason: null,
  tick: 0,
  sim_time: 0,
  speed: 30,
  seed: 1,
  scenario_id: 'baseline',
  created_at: '2026-01-01T00:00:00Z',
  world_width: 2,
  world_height: 2,
}

export const config = {} as SimulationConfig

export function initMessage(seq = 1): ServerMessage {
  return {
    type: 'init',
    seq,
    tick: 0,
    sim_time: 0,
    payload: {
      info,
      config,
      world: { width: 2, height: 2, nest: { x: 1, y: 1, radius: 1 }, obstacles: makeField({ layer: 'obstacles' }) },
      subscription: { layers: [], frame_every: 1, field_every: 10, field_downsample: 2 },
      events: [],
    },
  }
}

export function frameMessage(seq: number, tick: number, frame = makeFrame()): ServerMessage {
  return { type: 'frame', seq, tick, sim_time: tick, payload: frame }
}
