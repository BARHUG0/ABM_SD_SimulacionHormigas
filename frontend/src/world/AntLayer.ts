import { Particle, ParticleContainer, type Texture } from 'pixi.js'
import type { FrameData } from '../api/types'
import { blend, indexById } from './interpolation'
import { ANT_IDLE_STATE, ANT_STATE_COLORS, SOLDIER_ROLE } from './palette'

type Ants = FrameData['ants']

const ANT_LENGTH_CELLS = 2.2
const SOLDIER_SCALE = 1.35

export class AntLayer {
  readonly container: ParticleContainer
  private readonly texture: Texture
  private readonly baseScale: number
  private particles: Particle[] = []
  private current: Ants | null = null
  private previous: Ants | null = null
  private previousIndex = new Map<number, number>()
  private currentIndex = new Map<number, number>()
  x = new Float32Array(0)
  y = new Float32Array(0)

  constructor(texture: Texture) {
    this.texture = texture
    this.baseScale = ANT_LENGTH_CELLS / texture.width
    this.container = new ParticleContainer({
      texture,
      dynamicProperties: { position: true, rotation: true, color: true, vertex: true },
    })
  }

  get ants(): Ants | null {
    return this.current
  }

  indexOf(id: number): number {
    return this.currentIndex.get(id) ?? -1
  }

  sync(frame: FrameData | null, previousFrame: FrameData | null): void {
    const ants = frame?.ants ?? null
    this.current = ants
    this.previous = previousFrame?.ants ?? ants
    this.previousIndex = indexById(this.previous?.ids ?? [])
    this.currentIndex = indexById(ants?.ids ?? [])
    const count = ants?.ids.length ?? 0
    this.resize(count)
    if (!ants) return
    for (let index = 0; index < count; index++) {
      const particle = this.particles[index]
      const state = ants.state[index]
      const scale = this.baseScale * (ants.role[index] === SOLDIER_ROLE ? SOLDIER_SCALE : 1)
      particle.scaleX = scale
      particle.scaleY = scale
      particle.tint = ANT_STATE_COLORS[state] ?? ANT_STATE_COLORS[0]
      particle.alpha = state === ANT_IDLE_STATE ? 0.55 : 1
    }
  }

  interpolate(t: number): void {
    const ants = this.current
    const previous = this.previous
    if (!ants || !previous) return
    for (let index = 0; index < ants.ids.length; index++) {
      const target = { x: ants.x[index], y: ants.y[index], heading: ants.heading[index] }
      const from = this.previousIndex.get(ants.ids[index])
      const track =
        from === undefined ? target : blend(previous.x[from], previous.y[from], previous.heading[from], target, t)
      const particle = this.particles[index]
      particle.x = track.x
      particle.y = track.y
      particle.rotation = track.heading
      this.x[index] = track.x
      this.y[index] = track.y
    }
  }

  nearest(x: number, y: number, radius: number): number {
    let best = -1
    let bestDistance = radius * radius
    const count = this.current?.ids.length ?? 0
    for (let index = 0; index < count; index++) {
      const dx = this.x[index] - x
      const dy = this.y[index] - y
      const distance = dx * dx + dy * dy
      if (distance < bestDistance) {
        best = index
        bestDistance = distance
      }
    }
    return best
  }

  private resize(count: number): void {
    if (this.x.length < count) {
      this.x = new Float32Array(count * 2)
      this.y = new Float32Array(count * 2)
    }
    if (count === this.particles.length) return
    if (count > this.particles.length) {
      const added: Particle[] = []
      for (let index = this.particles.length; index < count; index++) {
        added.push(new Particle({ texture: this.texture, anchorX: 0.5, anchorY: 0.5 }))
      }
      this.particles.push(...added)
      this.container.addParticle(...added)
      return
    }
    this.particles.length = count
    this.container.particleChildren.length = count
    this.container.update()
  }
}
