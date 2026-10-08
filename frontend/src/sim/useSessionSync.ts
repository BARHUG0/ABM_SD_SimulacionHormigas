import { useEffect } from 'react'
import type { FieldLayer } from '../api/types'
import { releaseSimulation } from './actions'
import { reachedMilestones } from './milestones'
import { noticeToast } from './perturbations'
import { frameEveryFor, updateSubscription } from './session'
import { useSimulation } from './store'
import { useUi, type OverlayLayer } from './ui'

export function subscribedLayers(visible: Record<OverlayLayer, boolean>): FieldLayer[] {
  return (Object.keys(visible) as OverlayLayer[]).filter((layer) => visible[layer])
}

export function useSessionSync(): void {
  const visibleLayers = useUi((state) => state.visibleLayers)
  const speed = useSimulation((state) => state.speed)

  useEffect(() => {
    updateSubscription({ layers: subscribedLayers(visibleLayers) })
  }, [visibleLayers])

  useEffect(() => {
    updateSubscription({ frame_every: frameEveryFor(speed) })
  }, [speed])

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
