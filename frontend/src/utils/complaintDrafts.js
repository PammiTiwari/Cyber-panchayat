// Complaint draft storage — a citizen's in-progress "Submit Complaint" form,
// saved client-side only. A draft never touches the server; it becomes a real
// complaint only once actually submitted, so this is plain localStorage CRUD,
// no API involved.

const DRAFTS_KEY = "civic_complaint_drafts"

export function readDrafts() {
  try {
    const list = JSON.parse(localStorage.getItem(DRAFTS_KEY) || "[]")
    return Array.isArray(list) ? list : []
  } catch {
    return []
  }
}

function writeDrafts(list) {
  try { localStorage.setItem(DRAFTS_KEY, JSON.stringify(list)) } catch { /* private browsing */ }
}

// True once the citizen has actually put something in — a single character is
// enough. Nothing is saved without them asking for it, so there is no reason to
// hold their work to a minimum length; the only thing this has to rule out is a
// form they never touched.
//
// `ward` and `priority` are deliberately not checked: both are pre-filled (ward
// from the profile, priority defaults to medium), so counting them would make
// every untouched form look like work in progress.
export function hasDraftContent(form) {
  if (form.title?.trim()) return true
  if (form.description?.trim()) return true
  if (form.address?.trim()) return true
  if (form.category) return true
  if (form.image_urls?.length) return true
  if (form.latitude != null || form.longitude != null) return true
  return false
}

// Creates a draft the first time, then keeps updating the same one on every
// later save (auto or manual) — one form-filling session is one draft, not a
// new row every 30 seconds. Returns the id, so the caller can remember which
// draft it's now attached to.
export function saveDraft(form, existingId) {
  const drafts = readDrafts()
  const now = new Date().toISOString()
  const idx = existingId ? drafts.findIndex(d => d.id === existingId) : -1
  if (idx !== -1) {
    drafts[idx] = { ...drafts[idx], form: { ...form }, updated_at: now }
    writeDrafts(drafts)
    return drafts[idx].id
  }
  const id = `draft-${Date.now()}`
  drafts.unshift({ id, form: { ...form }, created_at: now, updated_at: now })
  writeDrafts(drafts)
  return id
}

export function getDraft(id) {
  return readDrafts().find(d => d.id === id) || null
}

export function deleteDraft(id) {
  writeDrafts(readDrafts().filter(d => d.id !== id))
}

export function clearAllDrafts() {
  writeDrafts([])
}
