// Status formatting utilities for displaying complaint and request statuses
// Converts internal status codes to user-friendly display text

// Custom status labels that override the default underscored format
const LABELS = {
  on_hold_weather: 'on hold - weather restrictions',
}

// Convert status string to human-readable format
// Replaces underscores with spaces and applies custom labels when available
// CSS text-transform:capitalize automatically capitalizes each word
export function fmtStatus(status) {
  if (!status) return ''
  return LABELS[status] || status.replace(/_/g, ' ')
}
