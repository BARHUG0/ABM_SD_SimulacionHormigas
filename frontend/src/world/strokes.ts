export function foodRadius(brushSize: number): number {
  return Math.min(brushSize + 2, 20)
}

export function cellsBetween(from: [number, number], to: [number, number]): [number, number][] {
  const steps = Math.max(Math.abs(to[0] - from[0]), Math.abs(to[1] - from[1]))
  const cells: [number, number][] = []
  for (let index = 1; index <= steps; index++) {
    const t = index / steps
    cells.push([Math.round(from[0] + (to[0] - from[0]) * t), Math.round(from[1] + (to[1] - from[1]) * t)])
  }
  return cells
}
