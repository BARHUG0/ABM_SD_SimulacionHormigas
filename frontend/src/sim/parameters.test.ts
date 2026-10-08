import { describe, expect, it } from 'vitest'
import type { ParameterSpec } from '../api/types'
import { basicSpecs, groupSpecs, isEditable, normalizeValue, readParameter } from './parameters'

const spec = (overrides: Partial<ParameterSpec>): ParameterSpec => ({
  key: 'ants.speed',
  group: 'ants',
  name: 'speed',
  description: 'Velocidad de las hormigas',
  type: 'float',
  default: 1,
  minimum: 0.1,
  maximum: 3,
  step: 0.01,
  unit: 'celdas/tick',
  live_editable: true,
  constraints: [],
  ...overrides,
})

describe('readParameter', () => {
  it('reads the nested config value', () => {
    expect(readParameter({ ants: { speed: 2.5 } } as never, spec({}))).toBe(2.5)
  })

  it('falls back to the default when missing', () => {
    expect(readParameter(null, spec({}))).toBe(1)
    expect(readParameter({ ants: {} } as never, spec({}))).toBe(1)
  })
})

describe('normalizeValue', () => {
  it('clamps to the range', () => {
    expect(normalizeValue(spec({}), 10)).toBe(3)
    expect(normalizeValue(spec({}), -1)).toBe(0.1)
  })

  it('snaps to the step without float noise', () => {
    expect(normalizeValue(spec({}), 1.234)).toBe(1.23)
    expect(normalizeValue(spec({ minimum: 0, step: 0.1, maximum: 10 }), 0.30000000004)).toBe(0.3)
  })

  it('rounds integer parameters', () => {
    expect(normalizeValue(spec({ type: 'int', minimum: 0, maximum: 2000, step: 1 }), 99.6)).toBe(100)
  })
})

describe('isEditable', () => {
  it('locks non-live parameters once the run started', () => {
    const locked = spec({ live_editable: false })
    expect(isEditable(locked, 'created')).toBe(true)
    expect(isEditable(locked, 'running')).toBe(false)
    expect(isEditable(locked, 'paused')).toBe(false)
    expect(isEditable(spec({}), 'running')).toBe(true)
  })
})

describe('grouping', () => {
  const specs = [
    spec({}),
    spec({ key: 'nest.egg_duration', group: 'nest', name: 'egg_duration' }),
    spec({ key: 'ants.random_turn', name: 'random_turn' }),
  ]

  it('groups specs in first-seen order', () => {
    const groups = groupSpecs(specs)
    expect(groups.map(([group]) => group)).toEqual(['ants', 'nest'])
    expect(groups[0][1]).toHaveLength(2)
  })

  it('selects curated basic specs in curated order', () => {
    expect(basicSpecs(specs).map((item) => item.key)).toEqual(['ants.speed', 'ants.random_turn'])
  })
})
