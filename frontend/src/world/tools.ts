import { Graphics } from 'pixi.js'
import { endpoints } from '../api/endpoints'
import { attempt, currentSimulationId } from '../sim/actions'
import { useUi, type Tool } from '../sim/ui'
import type { Point } from './camera'
import type { PointerHandler, WorldScene } from './WorldScene'

const FLUSH_INTERVAL_MS = 120
const PREDATOR_PICK_RADIUS = 4
const MAX_CELLS_PER_REQUEST = 5000

const TOOL_COLORS: Record<Tool, number> = {
  pan: 0xffffff,
  obstacle: 0xb9aa98,
  food: 0xf4c448,
  predator: 0xe2412f,
  erase: 0xffffff,
}

export function foodRadius(brushSize: number): number {
  return Math.min(brushSize + 2, 20)
}

export function cellsBetween(from: [number, number], to: [number, number]): [number, number][] {
  const steps = Math.max(Math.abs(to[0] - from[0]), Math.abs(to[1] - from[1]))
  const cells: [number, number][] = []
  for (let index = 1; index <= steps; index++) {
    const t = index / steps
    cells.push([Math.round(from[0] + (to[0] - from[0]) * t), Math.round(from[1] + (to[1] - from[1]) * t)])
  }
  return cells
}

export function attachWorldTools(scene: WorldScene): () => void {
  const preview = new Graphics()
  const stroke = new Graphics()
  scene.tools.addChild(stroke, preview)

  let pending: [number, number][] = []
  let seen = new Set<string>()
  let lastCell: [number, number] | null = null
  let strokeMode: 'add' | 'erase' | null = null
  let flushTimer: ReturnType<typeof setInterval> | null = null
  let inFlight = 0

  const worldSize = () => scene.worldSize
  const toCell = (point: Point): [number, number] | null => {
    const size = worldSize()
    if (!size) return null
    const x = Math.floor(point.x)
    const y = Math.floor(point.y)
    if (x < 0 || y < 0 || x >= size.width || y >= size.height) return null
    return [x, y]
  }

  const addCell = (cell: [number, number]) => {
    const key = `${cell[0]},${cell[1]}`
    if (seen.has(key)) return
    seen.add(key)
    pending.push(cell)
    const { brushSize } = useUi.getState()
    stroke
      .circle(cell[0] + 0.5, cell[1] + 0.5, brushSize + 0.5)
      .fill({ color: strokeMode === 'erase' ? 0x000000 : TOOL_COLORS.obstacle, alpha: 0.35 })
  }

  const flush = () => {
    const simulationId = currentSimulationId()
    if (!simulationId || pending.length === 0 || !strokeMode) return
    const cells = pending.slice(0, MAX_CELLS_PER_REQUEST)
    pending = pending.slice(cells.length)
    const { brushSize } = useUi.getState()
    const mode = strokeMode
    inFlight++
    void attempt(async () => {
      await endpoints.paintObstacles(simulationId, cells, brushSize, mode)
      if (mode === 'erase') {
        const spots = cells.filter((_, index) => index % brushSize === 0 || index === cells.length - 1)
        await Promise.all(spots.map(([x, y]) => endpoints.placeFood(simulationId, x, y, brushSize, 'erase')))
      }
    }).finally(() => {
      inFlight--
      if (!strokeMode && inFlight === 0) stroke.clear()
    })
  }

  const endStroke = () => {
    if (flushTimer) clearInterval(flushTimer)
    flushTimer = null
    flush()
    strokeMode = null
    seen = new Set()
    lastCell = null
    if (inFlight === 0) stroke.clear()
  }

  const removePredatorNear = (point: Point): boolean => {
    const predators = scene.predatorLayer.predators
    const simulationId = currentSimulationId()
    if (!predators || !simulationId) return false
    let best: number | null = null
    let bestDistance = PREDATOR_PICK_RADIUS * PREDATOR_PICK_RADIUS
    for (const id of predators.ids) {
      const position = scene.predatorLayer.positionOf(id)
      if (!position) continue
      const distance = (position.x - point.x) ** 2 + (position.y - point.y) ** 2
      if (distance < bestDistance) {
        best = id
        bestDistance = distance
      }
    }
    if (best === null) return false
    const predatorId = best
    void attempt(() => endpoints.removePredator(simulationId, predatorId))
    return true
  }

  const drawPreview = (point: Point | null) => {
    preview.clear()
    const { tool, brushSize } = useUi.getState()
    if (!point || tool === 'pan') return
    const radius = tool === 'food' ? foodRadius(brushSize) : tool === 'predator' ? 2.5 : brushSize + 0.5
    preview.circle(point.x, point.y, radius).stroke({ color: TOOL_COLORS[tool], width: 0.35, alpha: 0.9 })
  }

  const handler: PointerHandler = {
    down: (point) => {
      const { tool, brushSize } = useUi.getState()
      const simulationId = currentSimulationId()
      const cell = toCell(point)
      if (tool === 'pan' || !simulationId || !cell) return false
      if (tool === 'food') {
        void attempt(() => endpoints.placeFood(simulationId, cell[0], cell[1], foodRadius(brushSize), 'add'))
        return true
      }
      if (tool === 'predator') {
        void attempt(() => endpoints.placePredators(simulationId, cell[0], cell[1]))
        return true
      }
      if (tool === 'erase' && removePredatorNear(point)) return true
      strokeMode = tool === 'erase' ? 'erase' : 'add'
      stroke.clear()
      addCell(cell)
      lastCell = cell
      flushTimer = setInterval(flush, FLUSH_INTERVAL_MS)
      return true
    },
    move: (point) => {
      drawPreview(point)
      const cell = toCell(point)
      if (!strokeMode || !cell) return
      for (const next of lastCell ? cellsBetween(lastCell, cell) : [cell]) addCell(next)
      lastCell = cell
    },
    up: () => {
      if (strokeMode) endStroke()
    },
    hover: drawPreview,
  }

  scene.setPointerHandler(handler)
  const stopToolWatch = useUi.subscribe((state, previous) => {
    if (state.tool !== previous.tool) drawPreview(null)
  })

  return () => {
    endStroke()
    stopToolWatch()
    scene.setPointerHandler(null)
    preview.destroy()
    stroke.destroy()
  }
}
