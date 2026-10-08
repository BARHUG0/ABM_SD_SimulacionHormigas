import { describe, expect, it } from 'vitest'
import { encodeBytes, makeField } from '../test/fixtures'
import { colorizeField, decodeField, fieldValueAt } from './fields'

describe('decodeField', () => {
  it('turns base64 rows into bytes', () => {
    const field = decodeField(makeField())
    expect(Array.from(field.bytes)).toEqual([0, 51, 255, 102])
    expect(field.width).toBe(2)
    expect(field.scale).toBe(10)
  })

  it('rejects data whose length does not match the grid', () => {
    expect(() => decodeField(makeField({ data: encodeBytes([1, 2, 3]) }))).toThrow(/se esperaban 4/)
  })
})

describe('fieldValueAt', () => {
  it('scales bytes back to real values', () => {
    const field = decodeField(makeField())
    expect(fieldValueAt(field, 1, 0)).toBeCloseTo(2)
    expect(fieldValueAt(field, 0, 1)).toBeCloseTo(10)
  })

  it('maps world cells through the downsample factor', () => {
    const field = decodeField(makeField({ downsample: 4 }))
    expect(fieldValueAt(field, 7.5, 0)).toBeCloseTo(2)
    expect(fieldValueAt(field, 3, 5)).toBeCloseTo(10)
  })

  it('returns zero outside the grid', () => {
    const field = decodeField(makeField())
    expect(fieldValueAt(field, -1, 0)).toBe(0)
    expect(fieldValueAt(field, 5, 5)).toBe(0)
  })
})

describe('colorizeField', () => {
  it('writes premultiplied pixels and leaves empty cells transparent', () => {
    const pixels = colorizeField(decodeField(makeField()), [200, 100, 0])
    expect(Array.from(pixels.slice(0, 4))).toEqual([0, 0, 0, 0])
    expect(Array.from(pixels.slice(8, 12))).toEqual([200, 100, 0, 255])
    expect(Array.from(pixels.slice(4, 8))).toEqual([40, 20, 0, 51])
  })
})
