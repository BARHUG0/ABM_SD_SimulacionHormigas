import { describe, expect, it } from 'vitest'
import { pluralize } from './format'

describe('pluralize', () => {
  it('picks the singular only for one', () => {
    expect(pluralize(1, 'perturbación', 'perturbaciones')).toBe('1 perturbación')
    expect(pluralize(2, 'perturbación', 'perturbaciones')).toBe('2 perturbaciones')
    expect(pluralize(0, 'perturbación', 'perturbaciones')).toBe('0 perturbaciones')
  })
})
