import { create } from 'zustand'

export type OverlayLayer = 'pheromone_food' | 'pheromone_home' | 'pheromone_alarm' | 'food'

export type Tool = 'pan' | 'obstacle' | 'food' | 'predator' | 'erase'

export const EDIT_TOOLS: Tool[] = ['obstacle', 'food', 'predator', 'erase']

export type ToastTone = 'info' | 'success' | 'warning' | 'error'

export interface Toast {
  id: number
  text: string
  tone: ToastTone
}

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

export type DrawerTab = 'nest' | 'charts' | 'parameters'

interface UiStore {
  drawerOpen: boolean
  drawerTab: DrawerTab
  setDrawer: (open: boolean, tab?: DrawerTab) => void
  summaryOpen: boolean
  setSummaryOpen: (open: boolean) => void
  visibleLayers: Record<OverlayLayer, boolean>
  hoveredAnt: HoveredAnt | null
  tool: Tool
  brushSize: number
  toasts: Toast[]
  toggleLayer: (layer: OverlayLayer) => void
  setHoveredAnt: (ant: HoveredAnt | null) => void
  setTool: (tool: Tool) => void
  setBrushSize: (size: number) => void
  pushToast: (text: string, tone?: ToastTone) => void
  dismissToast: (id: number) => void
}

const MAX_TOASTS = 4
let nextToastId = 1

export const useUi = create<UiStore>()((set) => ({
  drawerOpen: false,
  drawerTab: 'nest',
  setDrawer: (drawerOpen, tab) => set((state) => ({ drawerOpen, drawerTab: tab ?? state.drawerTab })),
  summaryOpen: false,
  setSummaryOpen: (summaryOpen) => set({ summaryOpen }),
  visibleLayers: { pheromone_food: true, pheromone_home: true, pheromone_alarm: false, food: true },
  hoveredAnt: null,
  tool: 'pan',
  brushSize: 2,
  toasts: [],
  toggleLayer: (layer) =>
    set((state) => ({ visibleLayers: { ...state.visibleLayers, [layer]: !state.visibleLayers[layer] } })),
  setHoveredAnt: (hoveredAnt) => set({ hoveredAnt }),
  setTool: (tool) => set((state) => ({ tool: state.tool === tool ? 'pan' : tool })),
  setBrushSize: (brushSize) => set({ brushSize }),
  pushToast: (text, tone = 'info') =>
    set((state) => ({ toasts: [...state.toasts, { id: nextToastId++, text, tone }].slice(-MAX_TOASTS) })),
  dismissToast: (id) => set((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) })),
}))
