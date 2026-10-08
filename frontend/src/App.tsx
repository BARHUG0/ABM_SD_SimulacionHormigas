import * as Tooltip from '@radix-ui/react-tooltip'
import { useEffect, useState } from 'react'
import { StartScreen } from './components/StartScreen'
import { Toasts } from './components/Toasts'
import { ToolPalette } from './components/ToolPalette'
import { TopBar } from './components/TopBar'
import { useSimulation } from './sim/store'
import { useUi } from './sim/ui'
import { useSessionSync } from './sim/useSessionSync'
import { attachWorldTools } from './world/tools'
import { WorldCanvas } from './world/WorldCanvas'
import type { WorldScene } from './world/WorldScene'

function SimulationView() {
  const [scene, setScene] = useState<WorldScene | null>(null)
  const tool = useUi((state) => state.tool)
  useSessionSync()

  useEffect(() => {
    if (!scene) return
    return attachWorldTools(scene)
  }, [scene])

  return (
    <main className={`relative h-full overflow-hidden ${tool === 'pan' ? 'cursor-grab' : 'cursor-crosshair'}`}>
      <WorldCanvas onReady={setScene} />
      <TopBar />
      <ToolPalette scene={scene} />
    </main>
  )
}

export default function App() {
  const simulationId = useSimulation((state) => state.simulationId)

  return (
    <Tooltip.Provider delayDuration={300}>
      {simulationId ? <SimulationView key={simulationId} /> : <StartScreen />}
      <Toasts />
    </Tooltip.Provider>
  )
}
