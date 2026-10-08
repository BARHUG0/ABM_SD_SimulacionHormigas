import { useEffect } from 'react'
import type { FieldLayer } from '../api/types'
import { updateSubscription } from './session'
import { useUi, type OverlayLayer } from './ui'

const ALWAYS_SUBSCRIBED: FieldLayer[] = ['food']

export function subscribedLayers(visible: Record<OverlayLayer, boolean>): FieldLayer[] {
  const layers = new Set<FieldLayer>(ALWAYS_SUBSCRIBED)
  for (const [layer, shown] of Object.entries(visible)) if (shown) layers.add(layer as FieldLayer)
  return [...layers]
}

export function useSessionSync(): void {
  const visibleLayers = useUi((state) => state.visibleLayers)

  useEffect(() => {
    updateSubscription({ layers: subscribedLayers(visibleLayers) })
  }, [visibleLayers])
}
