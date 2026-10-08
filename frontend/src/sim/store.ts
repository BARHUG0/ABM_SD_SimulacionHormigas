import { create } from 'zustand'
import type {
  ErrorBody,
  EventInfo,
  FieldLayer,
  FinishReason,
  FrameData,
  NestGeometry,
  Notice,
  ServerMessage,
  SimulationConfig,
  SimulationInfo,
  SimulationState,
  SimulationStatus,
  WorldStatic,
} from '../api/types'
import { decodeField, type DecodedField } from './fields'
import { LiveHistory } from './liveHistory'

export type ConnectionState = 'idle' | 'connecting' | 'open' | 'reconnecting' | 'closed'

export interface WorldView {
  width: number
  height: number
  nest: NestGeometry
}

const DEFAULT_FRAME_INTERVAL = 1000 / 30
const MIN_FRAME_INTERVAL = 8
const MAX_FRAME_INTERVAL = 500

interface SimulationData {
  simulationId: string | null
  connection: ConnectionState
  info: SimulationInfo | null
  config: SimulationConfig | null
  world: WorldView | null
  status: SimulationStatus
  speed: number
  finishReason: FinishReason | null
  tick: number
  frame: FrameData | null
  previousFrame: FrameData | null
  frameReceivedAt: number
  frameInterval: number
  fields: Partial<Record<FieldLayer, DecodedField>>
  events: EventInfo[]
  lastSeq: number
  needsResync: boolean
  live: LiveHistory
  liveVersion: number
  lastNotice: Notice | null
  lastError: ErrorBody | null
}

interface SimulationActions {
  begin: (simulationId: string) => void
  end: () => void
  setConnection: (connection: ConnectionState) => void
  applyMessage: (message: ServerMessage, now?: number) => void
  applyState: (state: SimulationState, now?: number) => void
  upsertEvent: (event: EventInfo) => void
}

export type SimulationStore = SimulationData & SimulationActions

const initialData = (): SimulationData => ({
  simulationId: null,
  connection: 'idle',
  info: null,
  config: null,
  world: null,
  status: 'created',
  speed: 30,
  finishReason: null,
  tick: 0,
  frame: null,
  previousFrame: null,
  frameReceivedAt: 0,
  frameInterval: DEFAULT_FRAME_INTERVAL,
  fields: {},
  events: [],
  lastSeq: 0,
  needsResync: false,
  live: new LiveHistory(),
  liveVersion: 0,
  lastNotice: null,
  lastError: null,
})

function mergeEvent(events: EventInfo[], event: EventInfo): EventInfo[] {
  const index = events.findIndex((item) => item.id === event.id)
  if (index === -1) return [...events, event]
  const next = events.slice()
  next[index] = event
  return next
}

function worldFrom(world: WorldStatic, fields: SimulationData['fields']) {
  return {
    world: { width: world.width, height: world.height, nest: world.nest },
    fields: { ...fields, obstacles: decodeField(world.obstacles) },
  }
}

export const useSimulation = create<SimulationStore>()((set, get) => {
  const receiveFrame = (frame: FrameData, tick: number, now: number) => {
    const state = get()
    const elapsed = now - state.frameReceivedAt
    const measured = Math.min(Math.max(elapsed, MIN_FRAME_INTERVAL), MAX_FRAME_INTERVAL)
    const frameInterval =
      state.frameReceivedAt === 0 ? DEFAULT_FRAME_INTERVAL : state.frameInterval * 0.7 + measured * 0.3
    state.live.push(tick, frame)
    set({
      previousFrame: state.frame ?? frame,
      frame,
      tick,
      frameReceivedAt: now,
      frameInterval,
      liveVersion: state.liveVersion + 1,
    })
  }

  return {
    ...initialData(),

    begin: (simulationId) => set({ ...initialData(), simulationId, connection: 'connecting' }),

    end: () => set(initialData()),

    setConnection: (connection) =>
      set(connection === 'connecting' || connection === 'reconnecting' ? { connection, lastSeq: 0 } : { connection }),

    applyMessage: (message, now = performance.now()) => {
      const { lastSeq } = get()
      const skipped = lastSeq > 0 && message.seq > lastSeq + 1
      set({ lastSeq: message.seq, ...(skipped ? { needsResync: true } : {}) })

      switch (message.type) {
        case 'init': {
          const { info, config, world, events } = message.payload
          get().live.clear()
          set({
            info,
            config,
            ...worldFrom(world, {}),
            events,
            status: info.status,
            speed: info.speed,
            finishReason: info.finish_reason,
            tick: message.tick,
            frame: null,
            previousFrame: null,
            frameReceivedAt: 0,
            needsResync: false,
          })
          break
        }
        case 'status':
          set({
            status: message.payload.status,
            speed: message.payload.speed,
            finishReason: message.payload.finish_reason,
          })
          break
        case 'config':
          set({ config: message.payload })
          break
        case 'frame':
          receiveFrame(message.payload, message.tick, now)
          break
        case 'field': {
          const field = decodeField(message.payload)
          set({ fields: { ...get().fields, [field.layer]: field } })
          break
        }
        case 'event': {
          const notice = message.payload
          set({
            lastNotice: notice,
            ...(notice.event ? { events: mergeEvent(get().events, notice.event) } : {}),
          })
          break
        }
        case 'error':
          set({ lastError: message.payload })
          break
        case 'pong':
          break
      }
    },

    applyState: (state, now = performance.now()) => {
      set({
        info: state.info,
        config: state.config,
        ...worldFrom(state.world, get().fields),
        events: state.events,
        status: state.info.status,
        speed: state.info.speed,
        finishReason: state.info.finish_reason,
        needsResync: false,
      })
      receiveFrame(state.frame, state.info.tick, now)
    },

    upsertEvent: (event) => set({ events: mergeEvent(get().events, event) }),
  }
})
