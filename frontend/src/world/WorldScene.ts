import { Application, Container, Graphics, Sprite, type Texture } from 'pixi.js'
import { useSimulation, type WorldView } from '../sim/store'
import { useUi } from '../sim/ui'
import { AntLayer } from './AntLayer'
import { Camera, type Point } from './camera'
import { FieldLayers } from './FieldLayers'
import { EventLayer } from './EventLayer'
import { BACKGROUND, NEST_FILL, NEST_RING } from './palette'
import { PredatorLayer } from './PredatorLayer'
import { antTexture, predatorTexture, terrainTexture } from './textures'

export interface PointerHandler {
  down: (world: Point, event: PointerEvent) => boolean
  move: (world: Point, event: PointerEvent) => void
  up: (world: Point, event: PointerEvent) => void
  hover: (world: Point | null) => void
}

const HOVER_RADIUS_PX = 10
const VIEW_INSETS = { top: 88, right: 72, bottom: 92, left: 80 }

export class WorldScene {
  readonly app: Application
  readonly root = new Container()
  readonly world = new Container()
  readonly camera: Camera
  readonly tools = new Container()
  private readonly host: HTMLElement
  private readonly terrain = new Sprite()
  private terrainTexture: Texture | null = null
  private readonly nest = new Graphics()
  private readonly fields = new FieldLayers()
  private readonly eventLayer = new EventLayer()
  private readonly ants: AntLayer
  private readonly predators: PredatorLayer
  private readonly highlight = new Graphics()
  private readonly ownTextures: Texture[]
  private worldView: WorldView | null = null
  private frame: unknown = null
  private pointerHandler: PointerHandler | null = null
  private panning: { x: number; y: number } | null = null
  private toolActive = false
  private lastPointer: Point | null = null
  private hoveredId: number | null = null
  private readonly cleanups: (() => void)[] = []

  static async create(host: HTMLElement): Promise<WorldScene> {
    const app = new Application()
    await app.init({
      resizeTo: host,
      background: BACKGROUND,
      antialias: true,
      autoDensity: true,
      resolution: Math.min(window.devicePixelRatio || 1, 2),
      preference: 'webgl',
    })
    return new WorldScene(app, host)
  }

  private constructor(app: Application, host: HTMLElement) {
    this.app = app
    this.host = host
    this.camera = new Camera(this.world)
    const ant = antTexture()
    const predator = predatorTexture()
    this.ownTextures = [ant, predator]
    this.ants = new AntLayer(ant)
    this.predators = new PredatorLayer(predator)
    this.highlight.circle(0, 0, 1.6).stroke({ color: 0xffffff, width: 0.3, alpha: 0.9 })
    this.highlight.visible = false
    this.world.addChild(
      this.terrain,
      this.fields.overlays,
      this.fields.obstacles,
      this.eventLayer.container,
      this.nest,
      this.ants.container,
      this.predators.container,
      this.highlight,
      this.tools,
    )
    this.root.addChild(this.world)
    app.stage.addChild(this.root)
    host.appendChild(app.canvas)
    app.canvas.style.display = 'block'
    app.canvas.style.touchAction = 'none'
    this.bindInput(app.canvas)
    app.ticker.add(this.update)
  }

  setPointerHandler(handler: PointerHandler | null): void {
    this.pointerHandler = handler
  }

  fitView(): void {
    if (!this.worldView) return
    const view = { width: this.host.clientWidth, height: this.host.clientHeight, ...VIEW_INSETS }
    this.camera.fit(view, this.worldView.width, this.worldView.height)
  }

  get worldSize(): WorldView | null {
    return this.worldView
  }

  get predatorLayer(): PredatorLayer {
    return this.predators
  }

  destroy(): void {
    this.cleanups.forEach((cleanup) => cleanup())
    this.app.ticker.remove(this.update)
    this.fields.destroy()
    this.terrainTexture?.destroy(true)
    this.app.destroy({ removeView: true }, { children: true })
    this.ownTextures.forEach((texture) => texture.destroy(true))
    useUi.getState().setHoveredAnt(null)
  }

  private readonly update = () => {
    const now = performance.now()
    const simulation = useSimulation.getState()
    const ui = useUi.getState()
    if (simulation.world !== this.worldView) this.buildWorld(simulation.world)
    this.fields.update(simulation.fields, ui.visibleLayers)
    this.eventLayer.sync(simulation.events, simulation.world)
    this.eventLayer.animate(now)
    if (simulation.frame !== this.frame) {
      this.frame = simulation.frame
      this.ants.sync(simulation.frame, simulation.previousFrame)
      this.predators.sync(simulation.frame, simulation.previousFrame)
      this.refreshHover()
    }
    const t = Math.min(Math.max((now - simulation.frameReceivedAt) / simulation.frameInterval, 0), 1)
    this.ants.interpolate(t)
    this.predators.interpolate(t, now)
    this.placeHighlight()
  }

  private buildWorld(world: WorldView | null): void {
    const firstWorld = this.worldView === null || world === null
    const resized =
      firstWorld || this.worldView?.width !== world?.width || this.worldView?.height !== world?.height
    this.worldView = world
    this.nest.clear()
    if (!world) return
    if (resized) {
      this.terrainTexture?.destroy(true)
      this.terrainTexture = terrainTexture(world.width, world.height)
      this.terrain.texture = this.terrainTexture
      this.fitView()
    }
    const { x, y, radius } = world.nest
    this.nest
      .circle(x, y, radius + 2.5)
      .fill({ color: NEST_RING, alpha: 0.12 })
      .circle(x, y, radius)
      .fill({ color: NEST_FILL })
      .stroke({ color: NEST_RING, width: 0.6 })
    for (let hole = 0; hole < 3; hole++) {
      const angle = (hole / 3) * Math.PI * 2 + 0.4
      this.nest.circle(x + Math.cos(angle) * radius * 0.45, y + Math.sin(angle) * radius * 0.45, radius * 0.18)
    }
    this.nest.fill({ color: 0x120c08 })
  }

  private refreshHover(): void {
    if (this.hoveredId === null) return
    const index = this.ants.indexOf(this.hoveredId)
    if (index === -1) {
      this.setHovered(-1)
      return
    }
    this.setHovered(index)
  }

  private placeHighlight(): void {
    const index = this.hoveredId === null ? -1 : this.ants.indexOf(this.hoveredId)
    this.highlight.visible = index !== -1
    if (index !== -1) this.highlight.position.set(this.ants.x[index], this.ants.y[index])
  }

  private setHovered(index: number): void {
    const ants = this.ants.ants
    const setHoveredAnt = useUi.getState().setHoveredAnt
    if (index === -1 || !ants || !this.lastPointer) {
      if (this.hoveredId === null) return
      this.hoveredId = null
      setHoveredAnt(null)
      return
    }
    this.hoveredId = ants.ids[index]
    setHoveredAnt({
      id: ants.ids[index],
      role: ants.role[index],
      state: ants.state[index],
      age: ants.age[index],
      energy: ants.energy[index],
      carrying: ants.carrying[index],
      screenX: this.lastPointer.x,
      screenY: this.lastPointer.y,
    })
  }

  private screenPoint(event: PointerEvent | WheelEvent): Point {
    const bounds = this.app.canvas.getBoundingClientRect()
    return { x: event.clientX - bounds.left, y: event.clientY - bounds.top }
  }

  private bindInput(canvas: HTMLCanvasElement): void {
    const listen = <K extends keyof HTMLElementEventMap>(
      type: K,
      handler: (event: HTMLElementEventMap[K]) => void,
      options?: AddEventListenerOptions,
    ) => {
      canvas.addEventListener(type, handler, options)
      this.cleanups.push(() => canvas.removeEventListener(type, handler))
    }

    listen('contextmenu', (event) => event.preventDefault())

    listen(
      'wheel',
      (event) => {
        event.preventDefault()
        this.camera.zoomAt(this.screenPoint(event), Math.exp(-event.deltaY * 0.0015))
      },
      { passive: false },
    )

    listen('pointerdown', (event) => {
      const screen = this.screenPoint(event)
      canvas.setPointerCapture(event.pointerId)
      const world = this.camera.toWorld(screen)
      if (event.button === 0 && this.pointerHandler?.down(world, event)) {
        this.toolActive = true
        return
      }
      this.panning = screen
      canvas.style.cursor = 'grabbing'
    })

    listen('pointermove', (event) => {
      const screen = this.screenPoint(event)
      this.lastPointer = screen
      const world = this.camera.toWorld(screen)
      this.pointerHandler?.hover(world)
      if (this.panning) {
        this.camera.panBy(screen.x - this.panning.x, screen.y - this.panning.y)
        this.panning = screen
        return
      }
      if (this.toolActive) {
        this.pointerHandler?.move(world, event)
        return
      }
      const radius = Math.max(HOVER_RADIUS_PX / this.camera.scale, 1)
      this.setHovered(this.ants.nearest(world.x, world.y, radius))
    })

    const release = (event: PointerEvent) => {
      if (this.toolActive) this.pointerHandler?.up(this.camera.toWorld(this.screenPoint(event)), event)
      this.toolActive = false
      this.panning = null
      canvas.style.cursor = ''
    }
    listen('pointerup', release)
    listen('pointercancel', release)

    listen('pointerleave', () => {
      this.lastPointer = null
      this.pointerHandler?.hover(null)
      this.setHovered(-1)
    })
  }
}
