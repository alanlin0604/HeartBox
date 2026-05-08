export function formatPrice(amount, currency = 'TWD') {
  const num = Number(amount)
  if (isNaN(num)) return ''
  const symbols = { TWD: 'NT$', USD: '$', JPY: '¥' }
  const prefix = symbols[currency] || currency + ' '
  return `${prefix} ${num.toLocaleString()}`
}
