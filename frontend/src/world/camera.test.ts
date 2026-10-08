import type { Container } from 'pixi.js'
import { describe, expect, it } from 'vitest'
import { Camera } from './camera'

const fakeTarget = () => ({ position: { set: () => undefined }, scale: { set: () => undefined } }) as unknown as Container

describe('Camera.zoomAt', () => {
  it('keeps the world point under the cursor fixed', () => {
    const camera = new Camera(fakeTarget())
    camera.fit({ width: 1000, height: 800, top: 0, right: 0, bottom: 0, left: 0 }, 200, 160)
    const cursor = { x: 310, y: 245 }
    const before = camera.toWorld(cursor)
    camera.zoomAt(cursor, 2)
    const after = camera.toWorld(cursor)
    expect(after.x).toBeCloseTo(before.x)
    expect(after.y).toBeCloseTo(before.y)
  })

  it('clamps the zoom to the fitted range', () => {
    const camera = new Camera(fakeTarget())
    camera.fit({ width: 1000, height: 800, top: 0, right: 0, bottom: 0, left: 0 }, 200, 160)
    const fitted = camera.scale
    camera.zoomAt({ x: 0, y: 0 }, 1000)
    expect(camera.scale).toBeCloseTo(fitted * 14)
  })
})
