import { Container, Sprite, Texture } from 'pixi.js'
import type { FieldLayer } from '../api/types'
import { colorizeField, type DecodedField, type Rgb } from '../sim/fields'
import type { OverlayLayer } from '../sim/ui'
import { OBSTACLE_RGB, OVERLAY_ORDER, OVERLAY_STYLES } from './palette'
import { FieldTexture } from './textures'

interface LayerView {
  sprite: Sprite
  texture: FieldTexture | null
  field: DecodedField | null
  color: Rgb
  gamma: number
  smooth: boolean
}

export class FieldLayers {
  readonly overlays = new Container()
  readonly obstacles = new Container()
  private readonly views = new Map<FieldLayer, LayerView>()

  constructor() {
    for (const layer of OVERLAY_ORDER) {
      const style = OVERLAY_STYLES[layer]
      const view = this.createView(style.color, style.gamma, true)
      if (style.additive) view.sprite.blendMode = 'add'
      this.overlays.addChild(view.sprite)
      this.views.set(layer, view)
    }
    const obstacles = this.createView(OBSTACLE_RGB, 1, false)
    this.obstacles.addChild(obstacles.sprite)
    this.views.set('obstacles', obstacles)
  }

  update(fields: Partial<Record<FieldLayer, DecodedField>>, visible: Record<OverlayLayer, boolean>): void {
    for (const [layer, view] of this.views) {
      const field = fields[layer] ?? null
      if (field !== view.field) this.paint(view, field)
      view.sprite.visible = field !== null && (layer === 'obstacles' || visible[layer as OverlayLayer])
    }
  }

  destroy(): void {
    for (const view of this.views.values()) view.texture?.destroy()
  }

  private createView(color: Rgb, gamma: number, smooth: boolean): LayerView {
    const sprite = new Sprite(Texture.EMPTY)
    sprite.visible = false
    return { sprite, texture: null, field: null, color, gamma, smooth }
  }

  private paint(view: LayerView, field: DecodedField | null): void {
    view.field = field
    if (!field) return
    const pixels = colorizeField(field, view.color, view.gamma)
    if (view.texture?.fits(field.width, field.height)) {
      view.texture.replace(pixels)
    } else {
      view.texture?.destroy()
      view.texture = new FieldTexture(pixels, field.width, field.height, view.smooth)
      view.sprite.texture = view.texture.texture
    }
    view.sprite.scale.set(field.downsample)
  }
}
