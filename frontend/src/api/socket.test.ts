import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SimulationSocket, type SocketState } from './socket'

class FakeSocket {
  static instances: FakeSocket[] = []
  readyState = 0
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null

  constructor() {
    FakeSocket.instances.push(this)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = 3
  }

  open() {
    this.readyState = 1
    this.onopen?.()
  }

  drop(code = 1006) {
    this.readyState = 3
    this.onclose?.({ code })
  }
}

describe('SimulationSocket', () => {
  let states: SocketState[]
  let client: SimulationSocket

  beforeEach(() => {
    vi.useFakeTimers()
    FakeSocket.instances = []
    states = []
    client = new SimulationSocket(
      'ws://test',
      { onMessage: vi.fn(), onStateChange: (state) => states.push(state) },
      { createSocket: () => new FakeSocket() as unknown as WebSocket, initialDelay: 100 },
    )
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('sends the subscription once open and again after reconnecting', () => {
    client.subscribe({ layers: ['food'], frame_every: 1, field_every: 5, field_downsample: 2 })
    client.connect()
    FakeSocket.instances[0].open()
    expect(FakeSocket.instances[0].sent[0]).toContain('"subscribe"')

    FakeSocket.instances[0].drop()
    expect(states.at(-1)).toBe('reconnecting')
    vi.advanceTimersByTime(100)
    FakeSocket.instances[1].open()
    expect(FakeSocket.instances[1].sent[0]).toContain('"food"')
    expect(states.at(-1)).toBe('open')
  })

  it('backs off between failed attempts', () => {
    client.connect()
    FakeSocket.instances[0].drop()
    vi.advanceTimersByTime(100)
    FakeSocket.instances[1].drop()
    vi.advanceTimersByTime(150)
    expect(FakeSocket.instances).toHaveLength(2)
    vi.advanceTimersByTime(50)
    expect(FakeSocket.instances).toHaveLength(3)
  })

  it('stops when the simulation does not exist', () => {
    client.connect()
    FakeSocket.instances[0].drop(4404)
    vi.advanceTimersByTime(10000)
    expect(FakeSocket.instances).toHaveLength(1)
    expect(states.at(-1)).toBe('closed')
  })
})
