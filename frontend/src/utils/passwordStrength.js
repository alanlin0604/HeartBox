export function evaluatePasswordStrength(password) {
  let score = 0
  if (password.length >= 8) score += 1
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1

  if (score <= 1) return { level: 'weak', value: 33 }
  if (score <= 3) return { level: 'medium', value: 66 }
  return { level: 'strong', value: 100 }
}
