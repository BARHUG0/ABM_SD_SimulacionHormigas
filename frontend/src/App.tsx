import { endpoints } from './api/endpoints'
import { openSession } from './sim/session'
import { useSimulation } from './sim/store'
import { WorldCanvas } from './world/WorldCanvas'

export default function App() {
  const simulationId = useSimulation((state) => state.simulationId)

  const startBaseline = async () => {
    const info = await endpoints.createSimulation('baseline')
    openSession(info.id)
    await endpoints.control(info.id, { action: 'start' })
  }

  if (!simulationId) {
    return (
      <main className="grid h-full place-items-center">
        <button className="rounded-xl bg-amber-500 px-6 py-3 font-bold text-soil-950" onClick={startBaseline}>
          Iniciar colonia base
        </button>
      </main>
    )
  }

  return (
    <main className="relative h-full">
      <WorldCanvas />
    </main>
  )
}
