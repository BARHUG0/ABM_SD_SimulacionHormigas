import { useEffect, useState } from 'react'
import { Drawer } from './components/Drawer'
import { EventTimeline } from './components/events/EventTimeline'
import { ResilienceCard } from './components/ResilienceCard'
import { ToolPalette } from './components/ToolPalette'
import { TopBar } from './components/TopBar'
import { useUi } from './sim/ui'
import { useSessionSync } from './sim/useSessionSync'
import { useShortcuts } from './sim/useShortcuts'
import { attachWorldTools } from './world/tools'
import { WorldCanvas } from './world/WorldCanvas'
import type { WorldScene } from './world/WorldScene'

export default function SimulationView() {
  const [scene, setScene] = useState<WorldScene | null>(null)
  const tool = useUi((state) => state.tool)
  useSessionSync()
  useShortcuts(scene)

  useEffect(() => {
    if (!scene) return
    return attachWorldTools(scene)
  }, [scene])

  return (
    <main className={`relative h-full overflow-hidden ${tool === 'pan' ? 'cursor-grab' : 'cursor-crosshair'}`}>
      <WorldCanvas onReady={setScene} />
      <TopBar />
      <ToolPalette scene={scene} />
      <Drawer />
      <EventTimeline />
      <ResilienceCard />
    </main>
  )
}
