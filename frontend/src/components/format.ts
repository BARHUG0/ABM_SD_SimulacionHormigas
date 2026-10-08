const compact = new Intl.NumberFormat('es', { maximumFractionDigits: 0 })
const decimal = new Intl.NumberFormat('es', { maximumFractionDigits: 2 })

export function formatCount(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—'
  return compact.format(Math.round(value))
}

export function formatValue(value: number | undefined | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '—'
  return decimal.format(value)
}
