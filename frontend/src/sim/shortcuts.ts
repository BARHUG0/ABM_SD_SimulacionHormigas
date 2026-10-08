import type { DrawerTab, Tool } from './ui'

export type ShortcutAction =
  | { type: 'toggle-play' }
  | { type: 'step' }
  | { type: 'tool'; tool: Tool }
  | { type: 'drawer'; tab: DrawerTab }
  | { type: 'fit' }
  | { type: 'escape' }

const TOOL_KEYS: Record<string, Tool> = { '1': 'obstacle', '2': 'food', '3': 'predator', '4': 'erase' }
const DRAWER_KEYS: Record<string, DrawerTab> = { n: 'nest', g: 'charts', p: 'parameters' }

interface KeyInput {
  key: string
  ctrlKey: boolean
  metaKey: boolean
  altKey: boolean
  target: EventTarget | null
}

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  if (target.isContentEditable) return true
  if (target.closest('input, textarea, select, [role="slider"]')) return true
  return false
}

function isControl(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.closest('button, a, [role="tab"], [role="checkbox"]') !== null
}

export function shortcutFor(event: KeyInput): ShortcutAction | null {
  if (event.ctrlKey || event.metaKey || event.altKey) return null
  if (event.key === 'Escape') return { type: 'escape' }
  if (isTyping(event.target)) return null
  const key = event.key.toLowerCase()
  if ((key === ' ' || key === 'arrowright') && isControl(event.target)) return null
  if (key === ' ') return { type: 'toggle-play' }
  if (key === 'arrowright') return { type: 'step' }
  if (key === 'f') return { type: 'fit' }
  if (TOOL_KEYS[key]) return { type: 'tool', tool: TOOL_KEYS[key] }
  if (DRAWER_KEYS[key]) return { type: 'drawer', tab: DRAWER_KEYS[key] }
  return null
}
