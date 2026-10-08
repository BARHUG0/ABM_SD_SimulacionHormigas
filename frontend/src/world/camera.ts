import type { Container } from 'pixi.js'

export interface Point {
  x: number
  y: number
}

export interface Insets {
  top: number
  right: number
  bottom: number
  left: number
}

const FIT_MARGIN = 0.96

export class Camera {
  scale = 1
  x = 0
  y = 0
  private minScale = 0.1
  private maxScale = 50
  private readonly target: Container

  constructor(target: Container) {
    this.target = target
  }

  fit(view: Insets & { width: number; height: number }, worldWidth: number, worldHeight: number): void {
    const width = Math.max(view.width - view.left - view.right, 50)
    const height = Math.max(view.height - view.top - view.bottom, 50)
    const scale = Math.min(width / worldWidth, height / worldHeight) * FIT_MARGIN
    this.minScale = scale * 0.5
    this.maxScale = scale * 14
    this.scale = scale
    this.x = view.left + (width - worldWidth * scale) / 2
    this.y = view.top + (height - worldHeight * scale) / 2
    this.apply()
  }

  zoomAt(screen: Point, factor: number): void {
    const next = Math.min(Math.max(this.scale * factor, this.minScale), this.maxScale)
    const world = this.toWorld(screen)
    this.scale = next
    this.x = screen.x - world.x * next
    this.y = screen.y - world.y * next
    this.apply()
  }

  panBy(dx: number, dy: number): void {
    this.x += dx
    this.y += dy
    this.apply()
  }

  toWorld(screen: Point): Point {
    return { x: (screen.x - this.x) / this.scale, y: (screen.y - this.y) / this.scale }
  }

  private apply(): void {
    this.target.position.set(this.x, this.y)
    this.target.scale.set(this.scale)
  }
}
