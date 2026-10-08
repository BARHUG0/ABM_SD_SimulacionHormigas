export type PathPoints = readonly (readonly [number, number])[]

export function pointAlong(points: PathPoints, fraction: number): [number, number] {
  const lengths: number[] = []
  let total = 0
  for (let index = 1; index < points.length; index++) {
    const length = Math.hypot(points[index][0] - points[index - 1][0], points[index][1] - points[index - 1][1])
    lengths.push(length)
    total += length
  }
  let remaining = Math.min(Math.max(fraction, 0), 1) * total
  for (let index = 0; index < lengths.length; index++) {
    if (remaining <= lengths[index] || index === lengths.length - 1) {
      const t = lengths[index] === 0 ? 0 : remaining / lengths[index]
      const [x0, y0] = points[index]
      const [x1, y1] = points[index + 1]
      return [x0 + (x1 - x0) * t, y0 + (y1 - y0) * t]
    }
    remaining -= lengths[index]
  }
  return [points[0][0], points[0][1]]
}

export function toPath(points: PathPoints): string {
  return points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x} ${y}`).join(' ')
}

export class RunningMax {
  private value: number
  private readonly floor: number

  constructor(floor: number) {
    this.floor = floor
    this.value = floor
  }

  update(sample: number): number {
    this.value = Math.max(this.value * 0.999, sample, this.floor)
    return this.value
  }
}
