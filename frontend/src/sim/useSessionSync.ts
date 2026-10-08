import { useEffect } from 'react'
import type { FieldLayer } from '../api/types'
import { releaseSimulation } from './actions'
import { reachedMilestones } from './milestones'
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
        if (state.lastError && state.lastError !== previous.lastError) {
          useUi.getState().pushToast(state.lastError.message, 'error')
        }
        if (!state.lastNotice || state.lastNotice === previous.lastNotice) return
        const toast = noticeToast(state.lastNotice)
        if (toast) useUi.getState().pushToast(toast.text, toast.tone)
      }),
    [],
  )

  useEffect(() => {
    const reached = new Set<string>()
    let primed = false
    return useSimulation.subscribe((state, previous) => {
      if (state.tick < previous.tick) {
        reached.clear()
        primed = false
      }
      if (!state.frame || state.frame === previous.frame) return
      const found = reachedMilestones(state.frame, reached)
      found.forEach((milestone) => reached.add(milestone.id))
      if (primed) found.forEach((milestone) => useUi.getState().pushToast(milestone.text, 'success'))
      primed = true
    })
  }, [])

  useEffect(() => {
    const stopWatching = useSimulation.subscribe((state, previous) => {
      if (state.status === 'finished' && previous.status !== 'finished') useUi.getState().setSummaryOpen(true)
    })
    window.addEventListener('pagehide', releaseSimulation)
    return () => {
      stopWatching()
      window.removeEventListener('pagehide', releaseSimulation)
    }
  }, [])
}
