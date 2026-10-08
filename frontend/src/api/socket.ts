import type { ServerMessage, Subscription } from './types'

export type SocketState = 'connecting' | 'open' | 'reconnecting' | 'closed'

export interface SocketHandlers {
  onMessage: (message: ServerMessage) => void
  onStateChange: (state: SocketState) => void
}

export interface SocketOptions {
  createSocket?: (url: string) => WebSocket
  pingInterval?: number
  initialDelay?: number
  maxDelay?: number
}

const CLOSE_NOT_FOUND = 4404

export class SimulationSocket {
  private socket: WebSocket | null = null
  private subscription: Subscription | null = null
  private retryDelay: number
  private retryTimer: ReturnType<typeof setTimeout> | null = null
  private pingTimer: ReturnType<typeof setInterval> | null = null
  private stopped = false
  private readonly createSocket: (url: string) => WebSocket
  private readonly pingInterval: number
  private readonly initialDelay: number
  private readonly maxDelay: number
  private readonly url: string
  private readonly handlers: SocketHandlers

  constructor(url: string, handlers: SocketHandlers, options: SocketOptions = {}) {
    this.url = url
    this.handlers = handlers
    this.createSocket = options.createSocket ?? ((target) => new WebSocket(target))
    this.pingInterval = options.pingInterval ?? 15000
    this.initialDelay = options.initialDelay ?? 500
    this.maxDelay = options.maxDelay ?? 8000
    this.retryDelay = this.initialDelay
  }

  connect(): void {
    this.stopped = false
    this.open('connecting')
  }

  subscribe(subscription: Subscription): void {
    this.subscription = subscription
    this.send({ type: 'subscribe', payload: subscription })
  }

  close(): void {
    this.stopped = true
    this.clearTimers()
    this.socket?.close()
    this.socket = null
    this.handlers.onStateChange('closed')
  }

  private open(state: SocketState): void {
    this.handlers.onStateChange(state)
    const socket = this.createSocket(this.url)
    this.socket = socket
    socket.onopen = () => {
      this.retryDelay = this.initialDelay
      this.handlers.onStateChange('open')
      if (this.subscription) this.send({ type: 'subscribe', payload: this.subscription })
      this.pingTimer = setInterval(() => this.send({ type: 'ping' }), this.pingInterval)
    }
    socket.onmessage = (event) => this.handlers.onMessage(JSON.parse(event.data as string) as ServerMessage)
    socket.onclose = (event) => {
      if (this.socket !== socket) return
      this.clearTimers()
      this.socket = null
      if (this.stopped || event.code === CLOSE_NOT_FOUND) {
        this.handlers.onStateChange('closed')
        return
      }
      this.handlers.onStateChange('reconnecting')
      this.retryTimer = setTimeout(() => this.open('reconnecting'), this.retryDelay)
      this.retryDelay = Math.min(this.retryDelay * 2, this.maxDelay)
    }
  }

  private send(message: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(message))
  }

  private clearTimers(): void {
    if (this.retryTimer) clearTimeout(this.retryTimer)
    if (this.pingTimer) clearInterval(this.pingTimer)
    this.retryTimer = null
    this.pingTimer = null
  }
}
