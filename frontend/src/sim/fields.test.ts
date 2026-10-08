import { describe, expect, it } from 'vitest'
import { encodeBytes, makeField } from '../test/fixtures'
import { colorizeField, decodeField } from './fields'

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

describe('colorizeField', () => {
  it('writes premultiplied pixels and leaves empty cells transparent', () => {
    const pixels = colorizeField(decodeField(makeField()), [200, 100, 0])
    expect(Array.from(pixels.slice(0, 4))).toEqual([0, 0, 0, 0])
    expect(Array.from(pixels.slice(8, 12))).toEqual([200, 100, 0, 255])
    expect(Array.from(pixels.slice(4, 8))).toEqual([40, 20, 0, 51])
  })
})
