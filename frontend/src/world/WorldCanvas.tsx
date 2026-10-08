import { useEffect, useRef } from 'react'
import { useUi } from '../sim/ui'
import { AntTooltip } from './AntTooltip'
import { WorldScene } from './WorldScene'

interface WorldCanvasProps {
  onReady?: (scene: WorldScene | null) => void
}

export function WorldCanvas({ onReady }: WorldCanvasProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const readyRef = useRef(onReady)

  useEffect(() => {
    readyRef.current = onReady
  }, [onReady])

  useEffect(() => {
    const host = hostRef.current
    if (!host) return
    let scene: WorldScene | null = null
    let cancelled = false
    void WorldScene.create(host)
      .then((created) => {
        if (cancelled) {
          created.destroy()
          return
        }
        scene = created
        readyRef.current?.(created)
      })
      .catch(() => {
        if (!cancelled) useUi.getState().pushToast('No se pudo iniciar el renderizado del mundo', 'error')
      })
    return () => {
      cancelled = true
      readyRef.current?.(null)
      scene?.destroy()
    }
  }, [])

  return (
    <div className="absolute inset-0">
      <div ref={hostRef} className="absolute inset-0 overflow-hidden" />
      <AntTooltip />
    </div>
  )
}
