import { BufferImageSource, Texture } from 'pixi.js'

function canvas(width: number, height: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const element = document.createElement('canvas')
  element.width = width
  element.height = height
  return [element, element.getContext('2d')!]
}

function seededRandom(seed: number) {
  let value = seed
  return () => {
    value = (value * 1664525 + 1013904223) % 4294967296
    return value / 4294967296
  }
}

export function terrainTexture(width: number, height: number): Texture {
  const [element, context] = canvas(width, height)
  const random = seededRandom(width * 7919 + height)
  context.fillStyle = '#3a2a1c'
  context.fillRect(0, 0, width, height)
  const patches = Math.round((width * height) / 160)
  for (let index = 0; index < patches; index++) {
    const radius = 1.5 + random() * 6
    const shade = random()
    context.fillStyle =
      shade < 0.5 ? `rgba(84, 62, 40, ${0.08 + random() * 0.14})` : `rgba(44, 31, 21, ${0.1 + random() * 0.16})`
    context.beginPath()
    context.arc(random() * width, random() * height, radius, 0, Math.PI * 2)
    context.fill()
  }
  const pebbles = Math.round((width * height) / 40)
  for (let index = 0; index < pebbles; index++) {
    context.fillStyle = `rgba(120, 96, 70, ${0.15 + random() * 0.25})`
    context.fillRect(Math.floor(random() * width), Math.floor(random() * height), 1, 1)
  }
  return Texture.from(element)
}

export function antTexture(): Texture {
  const [element, context] = canvas(16, 8)
  context.fillStyle = '#ffffff'
  for (const [x, rx, ry] of [
    [3, 2.6, 2.4],
    [7.5, 2, 1.8],
    [12, 2.6, 2.6],
  ]) {
    context.beginPath()
    context.ellipse(x, 4, rx, ry, 0, 0, Math.PI * 2)
    context.fill()
  }
  return Texture.from(element)
}

export function predatorTexture(): Texture {
  const [element, context] = canvas(32, 32)
  context.fillStyle = '#ffffff'
  context.strokeStyle = '#ffffff'
  context.lineWidth = 2
  context.lineCap = 'round'
  for (const angle of [-0.9, -0.3, 0.3, 0.9]) {
    for (const side of [-1, 1]) {
      context.beginPath()
      context.moveTo(16, 16)
      context.lineTo(16 + Math.cos(angle) * 4 * side + side * 2, 16 + Math.sin(angle) * 14)
      context.lineTo(16 + side * 14, 16 + Math.sin(angle) * 15)
      context.stroke()
    }
  }
  context.beginPath()
  context.ellipse(16, 16, 6, 8, 0, 0, Math.PI * 2)
  context.fill()
  context.beginPath()
  context.ellipse(16, 6, 4, 3.5, 0, 0, Math.PI * 2)
  context.fill()
  return Texture.from(element)
}

export class FieldTexture {
  readonly texture: Texture
  readonly width: number
  readonly height: number
  private readonly source: BufferImageSource

  constructor(pixels: Uint8Array, width: number, height: number, smooth: boolean) {
    this.width = width
    this.height = height
    this.source = new BufferImageSource({
      resource: pixels,
      width,
      height,
      format: 'rgba8unorm',
      alphaMode: 'premultiplied-alpha',
      scaleMode: smooth ? 'linear' : 'nearest',
    })
    this.texture = new Texture({ source: this.source })
  }

  fits(width: number, height: number): boolean {
    return this.width === width && this.height === height
  }

  replace(pixels: Uint8Array): void {
    this.source.resource = pixels
    this.source.update()
  }

  destroy(): void {
    this.texture.destroy(true)
  }
}
