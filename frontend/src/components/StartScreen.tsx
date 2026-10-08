import { motion } from 'motion/react'
import { Bug, Loader2, Sprout, Sun, Waves } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useScenarios } from '../api/queries'
import { startScenario } from '../sim/actions'

const LOOKS: Record<string, { icon: ReactNode; accent: string }> = {
  baseline: { icon: <Sprout size={36} />, accent: 'from-leaf-500/30 text-leaf-400' },
  drought: { icon: <Sun size={36} />, accent: 'from-amber-500/30 text-amber-500' },
  flood: { icon: <Waves size={36} />, accent: 'from-sky-500/30 text-sky-400' },
  predator_invasion: { icon: <Bug size={36} />, accent: 'from-ember-500/30 text-ember-400' },
}

export function StartScreen() {
  const { data: scenarios, isLoading, isError, refetch } = useScenarios()
  const [starting, setStarting] = useState<string | null>(null)

  const choose = async (scenarioId: string) => {
    setStarting(scenarioId)
    await startScenario(scenarioId)
    setStarting(null)
  }

  return (
    <main className="flex h-full flex-col items-center justify-center gap-10 overflow-auto bg-[radial-gradient(circle_at_50%_30%,var(--color-soil-700),var(--color-soil-950)_70%)] p-8">
      <div className="text-center">
        <h1 className="text-5xl font-black text-amber-500">Hormiguero Vivo</h1>
        <p className="mt-3 text-lg text-sand-300">Elige un escenario y mira cómo responde la colonia</p>
      </div>

      {isLoading && <Loader2 className="animate-spin text-sand-300" size={40} />}
      {isError && (
        <div className="panel px-6 py-4 text-center">
          <p className="text-sand-200">No se pudo contactar al servidor.</p>
          <button className="mt-3 font-bold text-amber-500" onClick={() => void refetch()}>
            Reintentar
          </button>
        </div>
      )}

      <div className="grid w-full max-w-5xl grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {scenarios?.map((scenario, index) => {
          const look = LOOKS[scenario.id] ?? LOOKS.baseline
          return (
            <motion.button
              key={scenario.id}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: index * 0.05 }}
              whileHover={{ y: -4 }}
              disabled={starting !== null}
              onClick={() => void choose(scenario.id)}
              className={`panel flex min-h-56 flex-col items-start gap-3 bg-gradient-to-b ${look.accent} to-transparent p-5 text-left disabled:opacity-60`}
            >
              {starting === scenario.id ? <Loader2 className="animate-spin" size={36} /> : look.icon}
              <h2 className="text-xl font-extrabold text-sand-100">{scenario.name}</h2>
              <p className="text-sm text-sand-300">{scenario.description}</p>
              <span className="mt-auto text-xs font-bold text-sand-400">
                {scenario.events.length === 0
                  ? 'Sin perturbaciones'
                  : `${scenario.events.length} perturbación programada`}
              </span>
            </motion.button>
          )
        })}
      </div>
    </main>
  )
}
