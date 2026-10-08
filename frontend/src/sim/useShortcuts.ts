import { useEffect } from 'react'
import type { WorldScene } from '../world/WorldScene'
import { step, togglePlay } from './actions'
import { shortcutFor } from './shortcuts'
import { useUi } from './ui'

export function useShortcuts(scene: WorldScene | null): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat && event.key !== 'ArrowRight') return
      const action = shortcutFor(event)
      if (!action) return
      event.preventDefault()
      const ui = useUi.getState()
      switch (action.type) {
        case 'toggle-play':
          void togglePlay()
          break
        case 'step':
          void step()
          break
        case 'tool':
          ui.setTool(action.tool)
          break
        case 'drawer':
          ui.setDrawer(!(ui.drawerOpen && ui.drawerTab === action.tab), action.tab)
          break
        case 'fit':
          scene?.fitView()
          break
        case 'escape':
          if (ui.summaryOpen) ui.setSummaryOpen(false)
          else if (ui.popover) ui.setPopover(null)
          else if (ui.tool !== 'pan') ui.setTool('pan')
          else ui.setDrawer(false)
          break
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [scene])
}
