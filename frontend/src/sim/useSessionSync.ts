import { useEffect } from 'react'
import type { FieldLayer } from '../api/types'
import { noticeToast } from './perturbations'
import { updateSubscription } from './session'
import { useSimulation } from './store'
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

  useEffect(
    () =>
      useSimulation.subscribe((state, previous) => {
        if (!state.lastNotice || state.lastNotice === previous.lastNotice) return
        const toast = noticeToast(state.lastNotice)
        if (toast) useUi.getState().pushToast(toast.text, toast.tone)
      }),
    [],
  )
}
