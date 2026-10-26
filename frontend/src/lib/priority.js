// Design tokens copied from the design reference: priority colour palette and
// the clinical target waiting times per priority level.

export const PALETTE = [
  { bg: '#fee2e2', fg: '#991b1b', dot: '#dc2626', bd: '#fecaca' }, // P1
  { bg: '#ffedd5', fg: '#9a3412', dot: '#ea580c', bd: '#fed7aa' }, // P2
  { bg: '#fef9c3', fg: '#854d0e', dot: '#ca8a04', bd: '#fde68a' }, // P3
  { bg: '#f1f5f9', fg: '#475569', dot: '#64748b', bd: '#e2e8f0' }, // P4
  { bg: '#f8fafc', fg: '#475569', dot: '#94a3b8', bd: '#cbd5e1' } // P5
]

// Target waiting time (minutes) per priority level, P1..P5.
export const TARGET = [5, 10, 30, 90, 120]

export function palette(level) {
  return PALETTE[level - 1] || PALETTE[4]
}

export function priorityLabel(t, level) {
  return t.labels[level - 1] || t.labels[4]
}

export function initials(name) {
  const parts = String(name || '')
    .replace(/^Dr\.\s*/i, '')
    .split(' ')
    .filter(Boolean)
  return ((parts[0] || '')[0] || '') + ((parts[parts.length - 1] || '')[0] || '')
}

// "18:40" -> 1120 minutes since midnight. Returns null when unparseable.
export function minutesOfDay(hhmm) {
  const match = /^(\d{1,2}):(\d{2})/.exec(String(hhmm || '').trim())
  if (!match) return null
  return Number(match[1]) * 60 + Number(match[2])
}

export function waitMinutes(appointmentTime, nowMinutes) {
  const arrived = minutesOfDay(appointmentTime)
  if (arrived === null) return 0
  return Math.max(0, nowMinutes - arrived)
}

export function clockString(date = new Date()) {
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
