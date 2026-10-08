import type { Rgb } from '../sim/fields'
import type { OverlayLayer } from '../sim/ui'

export const BACKGROUND = 0x17110c

export const ANT_STATE_COLORS = [0xf3e2bf, 0x9fdc7c, 0xff7a5c, 0x9a7d60]
export const ANT_IDLE_STATE = 3
export const SOLDIER_ROLE = 2

export const PREDATOR_COLOR = 0xe2412f
export const PREDATOR_HUNTING_COLOR = 0xff6b4a

export const NEST_FILL = 0x3b2a1c
export const NEST_RING = 0xe9a23b

export const OBSTACLE_RGB: Rgb = [104, 94, 86]
export const DROUGHT_COLOR = 0xc98a2b
export const FLOOD_COLOR = 0x3d8fd1

export interface OverlayStyle {
  color: Rgb
  gamma: number
  additive: boolean
}

export const OVERLAY_STYLES: Record<OverlayLayer, OverlayStyle> = {
  food: { color: [244, 196, 72], gamma: 0.45, additive: false },
  pheromone_food: { color: [110, 235, 120], gamma: 0.55, additive: true },
  pheromone_home: { color: [90, 160, 255], gamma: 0.55, additive: true },
  pheromone_alarm: { color: [255, 80, 70], gamma: 0.6, additive: true },
}

export const OVERLAY_ORDER: OverlayLayer[] = ['food', 'pheromone_home', 'pheromone_food', 'pheromone_alarm']
