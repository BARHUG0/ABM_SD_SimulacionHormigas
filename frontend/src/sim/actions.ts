import { API_PREFIX, ApiError } from '../api/client'
import { endpoints } from '../api/endpoints'
import type { ControlRequest } from '../api/types'
import { closeSession, openSession } from './session'
import { useSimulation } from './store'
import { useUi } from './ui'

export async function attempt<T>(request: () => Promise<T>): Promise<T | undefined> {
  try {
    return await request()
  } catch (error) {
    const message = error instanceof ApiError ? error.message : 'No se pudo contactar al servidor'
    useUi.getState().pushToast(message, 'error')
    return undefined
  }
}

export function currentSimulationId(): string | null {
  return useSimulation.getState().simulationId
}

export function control(request: Partial<ControlRequest> & Pick<ControlRequest, 'action'>) {
  const simulationId = currentSimulationId()
  if (!simulationId) return Promise.resolve(undefined)
  return attempt(() => endpoints.control(simulationId, request))
}

export function togglePlay() {
  const { status } = useSimulation.getState()
  return control({ action: status === 'running' ? 'pause' : 'start' })
}

export function step(steps = 1) {
  if (useSimulation.getState().status === 'running') return Promise.resolve(undefined)
  return control({ action: 'step', steps })
}

export async function startScenario(scenarioId: string) {
  const info = await attempt(() => endpoints.createSimulation(scenarioId))
  if (!info) return
  openSession(info.id)
  await control({ action: 'start' })
}

export function releaseSimulation() {
  const simulationId = currentSimulationId()
  if (!simulationId) return
  void fetch(`${API_PREFIX}/simulations/${simulationId}`, { method: 'DELETE', keepalive: true }).catch(() => undefined)
}

export function leaveSimulation() {
  const simulationId = currentSimulationId()
  closeSession()
  useUi.getState().setTool('pan')
  if (simulationId) void endpoints.deleteSimulation(simulationId).catch(() => undefined)
}
