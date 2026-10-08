import createClient from 'openapi-fetch'
import type { paths } from './schema'
import type { ErrorBody } from './types'

export const API_PREFIX = '/api/v1'

export const api = createClient<paths>({ baseUrl: globalThis.location?.origin ?? '' })

export class ApiError extends Error {}

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

function errorMessage(error: unknown, response: Response): string {
  const body = (error as { error?: ErrorBody } | undefined)?.error
  return body?.message || `Error ${response.status} del servidor`
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await request
  if (error !== undefined || !response.ok) throw new ApiError(errorMessage(error, response))
  return data as T
}

export function websocketUrl(simulationId: string): string {
  const protocol = globalThis.location?.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${globalThis.location?.host}${API_PREFIX}/ws/simulations/${simulationId}`
}
