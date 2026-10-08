import createClient from 'openapi-fetch'
import type { paths } from './schema'
import type { ErrorBody } from './types'

export const API_PREFIX = '/api/v1'

export const api = createClient<paths>({ baseUrl: globalThis.location?.origin ?? '' })

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: unknown

  constructor(status: number, body: ErrorBody) {
    super(body.message)
    this.code = body.code
    this.status = status
    this.details = body.details
  }
}

interface FetchResult<T> {
  data?: T
  error?: unknown
  response: Response
}

function toErrorBody(error: unknown, response: Response): ErrorBody {
  const body = (error as { error?: ErrorBody } | undefined)?.error
  if (body?.message) return body
  return { code: 'http_error', message: `Error ${response.status} del servidor`, details: null }
}

export async function unwrap<T>(request: Promise<FetchResult<T>>): Promise<T> {
  const { data, error, response } = await request
  if (error !== undefined || !response.ok) throw new ApiError(response.status, toErrorBody(error, response))
  return data as T
}

export function websocketUrl(simulationId: string): string {
  const protocol = globalThis.location?.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${globalThis.location?.host}${API_PREFIX}/ws/simulations/${simulationId}`
}
