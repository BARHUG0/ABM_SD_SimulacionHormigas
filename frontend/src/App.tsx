import * as Tooltip from '@radix-ui/react-tooltip'
import { MotionConfig } from 'motion/react'
import { lazy, Suspense } from 'react'
import { StartScreen } from './components/StartScreen'
import { Toasts } from './components/Toasts'
import { useSimulation } from './sim/store'

const SimulationView = lazy(() => import('./SimulationView'))

export default function App() {
  const simulationId = useSimulation((state) => state.simulationId)

  return (
    <MotionConfig reducedMotion="user">
      <Tooltip.Provider delayDuration={300}>
        {simulationId ? (
          <Suspense fallback={null}>
            <SimulationView key={simulationId} />
          </Suspense>
        ) : (
          <StartScreen />
        )}
        <Toasts />
      </Tooltip.Provider>
    </MotionConfig>
  )
}
