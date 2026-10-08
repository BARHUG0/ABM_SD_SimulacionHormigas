import { Container, Graphics, Sprite, type Texture } from 'pixi.js'
import type { FrameData } from '../api/types'
import { blendInto, indexById, type Track } from './interpolation'
import { prefersReducedMotion } from './motion'
import { PREDATOR_COLOR, PREDATOR_HUNTING_COLOR } from './palette'

type Predators = FrameData['predators']

const PREDATOR_SIZE_CELLS = 4.5

interface PredatorView {
  root: Container
  body: Sprite
  pulse: Graphics
  phase: number
}

export class PredatorLayer {
  readonly container = new Container()
  private readonly texture: Texture
  private readonly views = new Map<number, PredatorView>()
  private current: Predators | null = null
  private previous: Predators | null = null
  private previousIndex = new Map<number, number>()
  private readonly track: Track = { x: 0, y: 0, heading: 0 }

  constructor(texture: Texture) {
    this.texture = texture
  }

  get predators(): Predators | null {
    return this.current
  }

  positionOf(id: number): { x: number; y: number } | null {
    const view = this.views.get(id)
    return view ? { x: view.root.x, y: view.root.y } : null
  }

  sync(frame: FrameData | null, previousFrame: FrameData | null): void {
    const predators = frame?.predators ?? null
    this.current = predators
    this.previous = previousFrame?.predators ?? predators
    this.previousIndex = indexById(this.previous?.ids ?? [])
    const alive = new Set(predators?.ids ?? [])
    for (const [id, view] of this.views) {
      if (alive.has(id)) continue
      view.root.destroy({ children: true })
      this.views.delete(id)
    }
    predators?.ids.forEach((id, index) => {
      const view = this.views.get(id) ?? this.createView(id)
      view.body.tint = predators.state[index] === 'hunting' ? PREDATOR_HUNTING_COLOR : PREDATOR_COLOR
    })
  }

  interpolate(t: number, now: number, maxDistance: number): void {
    const predators = this.current
    const previous = this.previous
    if (!predators || !previous) return
    const pulsing = !prefersReducedMotion()
    predators.ids.forEach((id, index) => {
      const view = this.views.get(id)
      if (!view) return
      const track = this.track
      track.x = predators.x[index]
      track.y = predators.y[index]
      track.heading = predators.heading[index]
      const from = this.previousIndex.get(id)
      if (from !== undefined) blendInto(track, previous.x[from], previous.y[from], previous.heading[from], t, maxDistance)
      view.root.position.set(track.x, track.y)
      view.body.rotation = track.heading + Math.PI / 2
      view.pulse.visible = pulsing
      if (!pulsing) return
      const period = predators.state[index] === 'hunting' ? 450 : 1100
      const progress = (now / period + view.phase) % 1
      view.pulse.scale.set(1 + progress * 1.6)
      view.pulse.alpha = 0.7 * (1 - progress)
    })
  }

  private createView(id: number): PredatorView {
    const root = new Container()
    const pulse = new Graphics().circle(0, 0, PREDATOR_SIZE_CELLS * 0.55).stroke({ color: PREDATOR_COLOR, width: 0.35 })
    const body = new Sprite(this.texture)
    body.anchor.set(0.5)
    body.scale.set(PREDATOR_SIZE_CELLS / this.texture.width)
    root.addChild(pulse, body)
    this.container.addChild(root)
    const view = { root, body, pulse, phase: (id * 0.618) % 1 }
    this.views.set(id, view)
    return view
  }
}
