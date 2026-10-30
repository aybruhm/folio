import type { Decimal } from 'decimal.js'

export function formatCurrency(
  amount: string | number,
  currency: string = 'USD',
  locale: string = 'en-US'
): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(num)
}

export function formatPercent(
  value: string | number,
  decimals: number = 2,
  showSign: boolean = true
): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  const sign = showSign && num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(decimals)}%`
}

export function formatNumber(
  value: string | number,
  decimals: number = 2,
  locale: string = 'en-US'
): string {
  const num = typeof value === 'string' ? parseFloat(value) : value

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num)
}

// Trade quantities carry up to 8 decimal places (QUANTITY_SCALE in the API).
export const QUANTITY_DECIMALS = 8

export function formatQuantity(
  value: string | number,
  minDecimals: number = 2,
  locale: string = 'en-US'
): string {
  const num = typeof value === 'string' ? parseFloat(value) : value

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: minDecimals,
    maximumFractionDigits: QUANTITY_DECIMALS
  }).format(num)
}

// Truncates instead of rounding so a shortened quantity never overstates it.
export function formatQuantityShort(
  value: string | number,
  decimals: number = 2,
  locale: string = 'en-US'
): string {
  const num = typeof value === 'string' ? parseFloat(value) : value

  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
    roundingMode: 'trunc'
  }).format(num)
}

export function formatDate(date: Date | string, format: string = 'en-US'): string {
  const d = typeof date === 'string' ? new Date(date) : date

  return new Intl.DateTimeFormat(format === 'en-US' ? 'en-US' : 'en-GB', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).format(d)
}

// e.g. "Tue, Feb 2026. 09:30"
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      weekday: 'short',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23'
    })
      .formatToParts(d)
      .map((p) => [p.type, p.value])
  )
  return `${parts.weekday}, ${parts.month} ${parts.year}. ${parts.hour}:${parts.minute}`
}

export function parseDate(dateStr: string, format: string = 'YYYY-MM-DD'): Date {
  if (format === 'YYYY-MM-DD') {
    const [year, month, day] = dateStr.split('-').map(Number)
    return new Date(year, month - 1, day)
  }
  return new Date(dateStr)
}

export function getDaysFromNow(date: Date | string): number {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diff = d.getTime() - now.getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

export function getMonthsFromNow(date: Date | string): number {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  return (d.getFullYear() - now.getFullYear()) * 12 + (d.getMonth() - now.getMonth())
}
