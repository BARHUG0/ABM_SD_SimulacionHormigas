import * as Tabs from '@radix-ui/react-tabs'
import { ChartLine, Network, SlidersHorizontal, X } from 'lucide-react'
import { AnimatePresence, motion } from 'motion/react'
import type { ReactNode } from 'react'
import { useUi, type DrawerTab } from '../sim/ui'
import { ChartsPanel } from './charts/ChartsPanel'
import { NestDiagram } from './nest/NestDiagram'
import { ParametersPanel } from './parameters/ParametersPanel'
import { IconButton } from './ui/IconButton'

interface TabSpec {
  id: DrawerTab
  label: string
  icon: ReactNode
  content: () => ReactNode
}

const TABS: TabSpec[] = [
  { id: 'nest', label: 'Nido', icon: <Network size={20} />, content: () => <NestDiagram /> },
  { id: 'charts', label: 'Gráficas', icon: <ChartLine size={20} />, content: () => <ChartsPanel /> },
  { id: 'parameters', label: 'Parámetros', icon: <SlidersHorizontal size={20} />, content: () => <ParametersPanel /> },
]

export function Drawer() {
  const open = useUi((state) => state.drawerOpen)
  const tab = useUi((state) => state.drawerTab)
  const setDrawer = useUi((state) => state.setDrawer)

  const select = (id: DrawerTab) => setDrawer(!(open && tab === id), id)

  return (
    <div className="pointer-events-none absolute top-[88px] right-3 bottom-3 z-10 flex items-start gap-2">
      <AnimatePresence>
        {open && (
          <motion.aside
            key="drawer"
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 24 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="panel pointer-events-auto flex h-full w-[380px] flex-col overflow-hidden"
            onPointerDown={(event) => event.stopPropagation()}
          >
            <Tabs.Root
              value={tab}
              onValueChange={(value) => setDrawer(true, value as DrawerTab)}
              className="flex min-h-0 flex-1 flex-col"
            >
              <div className="flex items-center gap-2 border-b border-soil-700 px-3 py-2">
                <Tabs.List className="flex gap-1" aria-label="Paneles">
                  {TABS.map((spec) => (
                    <Tabs.Trigger
                      key={spec.id}
                      value={spec.id}
                      className="rounded-lg px-3 py-1.5 text-sm font-bold text-sand-300 transition-colors duration-150 hover:bg-soil-700 data-[state=active]:bg-sand-200 data-[state=active]:text-soil-950"
                    >
                      {spec.label}
                    </Tabs.Trigger>
                  ))}
                </Tabs.List>
                <button
                  onClick={() => setDrawer(false)}
                  aria-label="Cerrar panel"
                  className="ml-auto rounded-lg p-1.5 text-sand-300 hover:bg-soil-700"
                >
                  <X size={18} />
                </button>
              </div>
              {TABS.map((spec) => (
                <Tabs.Content key={spec.id} value={spec.id} className="min-h-0 flex-1 overflow-y-auto p-4">
                  {spec.content()}
                </Tabs.Content>
              ))}
            </Tabs.Root>
          </motion.aside>
        )}
      </AnimatePresence>
      <nav className="panel pointer-events-auto flex flex-col gap-1 p-1" aria-label="Abrir paneles">
        {TABS.map((spec) => (
          <IconButton
            key={spec.id}
            label={spec.label}
            active={open && tab === spec.id}
            onClick={() => select(spec.id)}
          >
            {spec.icon}
          </IconButton>
        ))}
      </nav>
    </div>
  )
}
