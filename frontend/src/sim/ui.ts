import { create } from 'zustand'

export type OverlayLayer = 'pheromone_food' | 'pheromone_home' | 'pheromone_alarm' | 'food'

export interface HoveredAnt {
  id: number
  role: number
  state: number
  age: number
  energy: number
  carrying: boolean
  screenX: number
  screenY: number
}

interface UiStore {
  visibleLayers: Record<OverlayLayer, boolean>
  hoveredAnt: HoveredAnt | null
  toggleLayer: (layer: OverlayLayer) => void
  setHoveredAnt: (ant: HoveredAnt | null) => void
}

export const useUi = create<UiStore>()((set) => ({
  visibleLayers: { pheromone_food: true, pheromone_home: true, pheromone_alarm: false, food: true },
  hoveredAnt: null,
  toggleLayer: (layer) =>
    set((state) => ({ visibleLayers: { ...state.visibleLayers, [layer]: !state.visibleLayers[layer] } })),
  setHoveredAnt: (hoveredAnt) => set({ hoveredAnt }),
}))
