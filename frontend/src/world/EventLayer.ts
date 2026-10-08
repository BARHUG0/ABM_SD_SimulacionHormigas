import { Container, Graphics } from 'pixi.js'
import type { EventInfo, PerturbationType, Region } from '../api/types'
import type { WorldView } from '../sim/store'
import { prefersReducedMotion } from './motion'
import { DROUGHT_COLOR, FLOOD_COLOR, PREDATOR_COLOR } from './palette'

const STYLES: Record<PerturbationType, { color: number; alpha: number; pulse: number; speed: number }> = {
  drought: { color: DROUGHT_COLOR, alpha: 0.2, pulse: 0.05, speed: 0.0015 },
  flood: { color: FLOOD_COLOR, alpha: 0.38, pulse: 0.1, speed: 0.003 },
  predator_wave: { color: PREDATOR_COLOR, alpha: 0.1, pulse: 0.08, speed: 0.005 },
}

const BORDER_WIDTH = 1.2

export class EventLayer {
  readonly container = new Container()
  private readonly views = new Map<PerturbationType, Graphics>()
  private events: EventInfo[] | null = null
  private world: WorldView | null = null

  constructor() {
    for (const type of Object.keys(STYLES) as PerturbationType[]) {
      const graphics = new Graphics()
      graphics.visible = false
      this.views.set(type, graphics)
      this.container.addChild(graphics)
    }
  }

  sync(events: EventInfo[], world: WorldView | null): void {
    if (events === this.events && world === this.world) return
    this.events = events
    this.world = world
    for (const [type, graphics] of this.views) {
      graphics.clear()
      const active = world ? events.filter((event) => event.type === type && event.status === 'active') : []
      graphics.visible = active.length > 0
      if (!world) continue
      const { color } = STYLES[type]
      for (const event of active) {
        const region: Region = event.region ?? { x: 0, y: 0, width: world.width, height: world.height }
        graphics
          .rect(region.x, region.y, region.width, region.height)
          .fill({ color, alpha: 1 })
          .stroke({ color, width: BORDER_WIDTH, alpha: 1, alignment: 1 })
      }
    }
  }

  animate(now: number): void {
    const pulsing = !prefersReducedMotion()
    for (const [type, graphics] of this.views) {
      if (!graphics.visible) continue
      const style = STYLES[type]
      graphics.alpha = pulsing ? style.alpha + Math.sin(now * style.speed) * style.pulse : style.alpha
    }
  }
}
