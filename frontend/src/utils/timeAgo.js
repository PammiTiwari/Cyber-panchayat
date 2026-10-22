// Relative timestamp ("just now" / "5m ago" / "3h ago" / "2d ago"), used
// wherever a feed or notification list shows when something happened rather
// than a full date.
export function timeAgo(d) {
  const diff = (Date.now() - new Date(d)) / 1000
  if (diff < 60) return 'just now'
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}
