import type { FieldData, FieldLayer } from '../api/types'

export interface DecodedField {
  layer: FieldLayer
  width: number
  height: number
  downsample: number
  scale: number
  bytes: Uint8Array
}

export type Rgb = readonly [number, number, number]

export function decodeField(field: FieldData): DecodedField {
  const binary = atob(field.data)
  const expected = field.width * field.height
  if (binary.length !== expected) {
    throw new Error(`La capa ${field.layer} trae ${binary.length} bytes y se esperaban ${expected}`)
  }
  const bytes = new Uint8Array(expected)
  for (let index = 0; index < expected; index++) bytes[index] = binary.charCodeAt(index)
  return {
    layer: field.layer,
    width: field.width,
    height: field.height,
    downsample: field.downsample,
    scale: field.scale,
    bytes,
  }
}

export function fieldValueAt(field: DecodedField, worldX: number, worldY: number): number {
  const column = Math.floor(worldX / field.downsample)
  const row = Math.floor(worldY / field.downsample)
  if (column < 0 || row < 0 || column >= field.width || row >= field.height) return 0
  return (field.bytes[row * field.width + column] / 255) * field.scale
}

export function colorizeField(field: DecodedField, color: Rgb, gamma = 1): Uint8Array {
  const pixels = new Uint8Array(field.bytes.length * 4)
  for (let index = 0; index < field.bytes.length; index++) {
    const byte = field.bytes[index]
    if (byte === 0) continue
    const alpha = gamma === 1 ? byte / 255 : Math.pow(byte / 255, gamma)
    const offset = index * 4
    pixels[offset] = color[0] * alpha
    pixels[offset + 1] = color[1] * alpha
    pixels[offset + 2] = color[2] * alpha
    pixels[offset + 3] = alpha * 255
  }
  return pixels
}
