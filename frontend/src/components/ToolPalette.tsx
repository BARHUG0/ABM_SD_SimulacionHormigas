import { BrickWall, Bug, Eraser, Hand, Layers, Maximize2, Wheat } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useUi, type OverlayLayer, type Tool } from '../sim/ui'
import type { WorldScene } from '../world/WorldScene'
import { IconButton } from './ui/IconButton'
import { Slider } from './ui/Slider'

const TOOLS: { tool: Tool; label: string; icon: ReactNode; shortcut: string }[] = [
  { tool: 'obstacle', label: 'Dibujar obstáculo', icon: <BrickWall size={20} />, shortcut: '1' },
  { tool: 'food', label: 'Colocar comida', icon: <Wheat size={20} />, shortcut: '2' },
  { tool: 'predator', label: 'Soltar depredador', icon: <Bug size={20} />, shortcut: '3' },
  { tool: 'erase', label: 'Borrar', icon: <Eraser size={20} />, shortcut: '4' },
]

const LAYERS: { layer: OverlayLayer; label: string; color: string }[] = [
  { layer: 'pheromone_food', label: 'Rastro a comida', color: '#6eeb78' },
  { layer: 'pheromone_home', label: 'Rastro al nido', color: '#5aa0ff' },
  { layer: 'pheromone_alarm', label: 'Alarma', color: '#ff5046' },
  { layer: 'food', label: 'Comida', color: '#f4c448' },
]

export function ToolPalette({ scene }: { scene: WorldScene | null }) {
  const tool = useUi((state) => state.tool)
  const brushSize = useUi((state) => state.brushSize)
  const visibleLayers = useUi((state) => state.visibleLayers)
  const { setTool, setBrushSize, toggleLayer } = useUi.getState()
  const [optionsOpen, setOptionsOpen] = useState(false)

  return (
    <aside className="panel pointer-events-auto absolute top-1/2 left-3 z-10 flex w-14 -translate-y-1/2 flex-col items-center gap-1 py-2">
      <IconButton label="Mover la cámara" shortcut="Esc" active={tool === 'pan'} onClick={() => setTool('pan')}>
        <Hand size={20} />
      </IconButton>
      {TOOLS.map((item) => (
        <IconButton
          key={item.tool}
          label={item.label}
          shortcut={item.shortcut}
          active={tool === item.tool}
          onClick={() => setTool(item.tool)}
        >
          {item.icon}
        </IconButton>
      ))}

      <div className="mt-1 flex flex-col gap-1 border-t border-soil-700 pt-1">
        <IconButton label="Pincel y capas" active={optionsOpen} onClick={() => setOptionsOpen(!optionsOpen)}>
          <Layers size={18} />
        </IconButton>
        <IconButton label="Encuadrar el mundo" shortcut="F" onClick={() => scene?.fitView()}>
          <Maximize2 size={18} />
        </IconButton>
      </div>

      {optionsOpen && (
        <div className="panel absolute top-0 left-16 flex w-48 flex-col gap-2 px-3 py-3">
          <label className="text-xs font-bold text-sand-400">Pincel: {brushSize}</label>
          <Slider label="Tamaño del pincel" value={brushSize} min={1} max={10} step={1} onChange={setBrushSize} />
          <div className="mt-1 text-xs font-bold text-sand-400">Capas</div>
          {LAYERS.map((item) => (
            <label key={item.layer} className="flex cursor-pointer items-center gap-2 text-xs text-sand-200">
              <input
                type="checkbox"
                className="accent-amber-500"
                checked={visibleLayers[item.layer]}
                onChange={() => toggleLayer(item.layer)}
              />
              <span className="size-2 rounded-full" style={{ background: item.color }} />
              {item.label}
            </label>
          ))}
        </div>
      )}
    </aside>
  )
}
