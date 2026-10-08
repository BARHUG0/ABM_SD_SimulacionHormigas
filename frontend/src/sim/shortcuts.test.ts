import { describe, expect, it } from 'vitest'
import { shortcutFor } from './shortcuts'

const press = (key: string, target: EventTarget | null = document.body, modifiers = {}) =>
  shortcutFor({ key, ctrlKey: false, metaKey: false, altKey: false, target, ...modifiers })

describe('shortcutFor', () => {
  it('maps playback, tools and panels', () => {
    expect(press(' ')).toEqual({ type: 'toggle-play' })
    expect(press('ArrowRight')).toEqual({ type: 'step' })
    expect(press('2')).toEqual({ type: 'tool', tool: 'food' })
    expect(press('G')).toEqual({ type: 'drawer', tab: 'charts' })
    expect(press('f')).toEqual({ type: 'fit' })
  })

  it('ignores keys while typing or adjusting sliders', () => {
    const input = document.createElement('input')
    const slider = document.createElement('span')
    slider.setAttribute('role', 'slider')
    expect(press(' ', input)).toBeNull()
    expect(press('ArrowRight', slider)).toBeNull()
  })

  it('leaves space and arrows to focused buttons and tabs', () => {
    const button = document.createElement('button')
    const tab = document.createElement('div')
    tab.setAttribute('role', 'tab')
    expect(press(' ', button)).toBeNull()
    expect(press('ArrowRight', tab)).toBeNull()
    expect(press('2', button)).toEqual({ type: 'tool', tool: 'food' })
  })

  it('always allows escape and ignores modified keys', () => {
    expect(press('Escape', document.createElement('input'))).toEqual({ type: 'escape' })
    expect(press('1', document.body, { ctrlKey: true })).toBeNull()
    expect(press('x')).toBeNull()
  })
})
