import type { Container } from 'pixi.js'

export interface Point {
  x: number
  y: number
}

const FIT_MARGIN = 0.94

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

  fit(viewWidth: number, viewHeight: number, worldWidth: number, worldHeight: number): void {
    const scale = Math.min(viewWidth / worldWidth, viewHeight / worldHeight) * FIT_MARGIN
    this.minScale = scale * 0.5
    this.maxScale = scale * 14
    this.scale = scale
    this.x = (viewWidth - worldWidth * scale) / 2
    this.y = (viewHeight - worldHeight * scale) / 2
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

  toScreen(world: Point): Point {
    return { x: world.x * this.scale + this.x, y: world.y * this.scale + this.y }
  }

  private apply(): void {
    this.target.position.set(this.x, this.y)
    this.target.scale.set(this.scale)
  }
}
