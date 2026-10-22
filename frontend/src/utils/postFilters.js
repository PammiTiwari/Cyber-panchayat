// Shared vocabulary and helpers for community-post search and filtering.
//
// Used by the PostFilterBar component, the usePostFilters composable, and the
// create-post forms. Kept framework-free (no Vue) so it's trivially testable
// and importable anywhere. The three community views — citizen /feed, staff,
// and admin — all draw their category/ward options from here so they can never
// drift apart.

// Fixed category list rather than one derived from loaded posts: a filter whose
// options appear and vanish as the feed changes is unpredictable, and the set
// of civic categories is a property of the platform. Values match the complaint
// categories used elsewhere in the app.
// "General" leads the list because it is the fallback the API applies to any
// post that doesn't name a category, so it is also what the create-post form
// pre-selects — the default sits first, where a default belongs. The rest
// follow the complaint category dropdown's order, minus "Other".
//
// Labelled "General", not "General Complaint": a community post is an update or
// a question as often as a grievance, and the complaint form has its own
// separate category list (see NewRequest.vue) where that wording still fits.
export const CATEGORIES = [
  { value: "general", label: "General" },
  { value: "road", label: "Road" },
  { value: "water", label: "Water" },
  { value: "electricity", label: "Electricity" },
  { value: "sanitation", label: "Sanitation" },
  { value: "waste", label: "Waste" },
  { value: "parks", label: "Parks & Public Spaces" },
  { value: "maintenance", label: "Maintenance" },
]

// The one place the fallback category is written down. The mock API applies the
// same value server-side (`body?.category || "general"`), so if that ever
// changes, change it here too and both forms follow.
export const DEFAULT_CATEGORY = "general"

export const WARDS = ["Central", "Ward-1", "Ward-2", "Ward-3"]

// Service departments a staff member can post on behalf of. These are the exact
// strings stored in a post's author_department, so value === label.
//
// "Administration" is deliberately absent. Admin-authored posts are
// announcements, and those have their own page at /announcements — the
// community feed doesn't offer them as a department to filter by. Admin posts
// still appear under "Officials only"; they just aren't a department choice.
export const OFFICIAL_DEPARTMENTS = [
  "Road Maintenance",
  "Electricity Department",
  "Water Supply Department",
  "Sanitation Department",
  "Parks & Public Spaces",
]

// ---------------------------------------------------------------------------
// Filter sentinels
//
// One rule, applied by every dropdown in PostFilterBar:
//
//   ""       → no filter at all; the field is ignored.
//   NO_VALUE → keep only posts that genuinely have nothing in that field.
//
// Before this, "" was labelled "None" on the category/ward pickers (where it
// meant "show everything") while "__none__" on the officials picker meant
// "hide every official post". One word, two opposite behaviours. Splitting the
// two ideas apart — and never labelling "" as "None" — is what keeps the bar
// predictable.
export const NO_VALUE = "__none__"

// Who wrote the post. A separate axis from department, and the parent of it:
// a department is only a meaningful narrowing once OFFICIALS_ONLY is chosen,
// because only official posts carry an author_department at all.
export const OFFICIALS_ONLY = "__officials__"
export const CITIZENS_ONLY = "__citizens__"

// Treats null, undefined and whitespace alike, so a post saved with ward ""
// and one saved with the field absent both count as "no ward".
export function isBlank(v) {
  return v == null || String(v).trim() === ""
}

const CATEGORY_LABELS = Object.fromEntries(CATEGORIES.map(c => [c.value, c.label]))

// Falls back to title-casing an unknown value, so a category added server-side
// still renders sensibly instead of blank.
export function fmtCategory(c) {
  if (!c) return ""
  return CATEGORY_LABELS[c] || c.charAt(0).toUpperCase() + c.slice(1).replace(/_/g, " ")
}

// Keyword → category, used to pre-fill the picker from a caption. First match
// wins, so the specific civic terms come before the catch-alls. Deliberately
// lightweight (no external service) — it only proposes, the user confirms.
const CATEGORY_KEYWORDS = [
  ["road", ["road", "pothole", "street", "traffic", "footpath", "highway"]],
  ["water", ["water", "pipeline", "leak", "drainage", "sewage", "tap", "supply"]],
  ["electricity", ["electric", "power", "streetlight", "street light", "transformer", "outage", "wire", "pole"]],
  ["sanitation", ["sanitation", "toilet", "clean", "hygiene", "sewer"]],
  ["waste", ["waste", "garbage", "trash", "dustbin", "litter", "dump"]],
  ["parks", ["park", "playground", "garden", "tree", "bench", "public space"]],
  ["maintenance", ["repair", "broken", "maintenance", "damage", "fix"]],
]

export function suggestCategory(text) {
  const t = (text || "").toLowerCase()
  if (!t.trim()) return ""
  for (const [cat, words] of CATEGORY_KEYWORDS) {
    if (words.some(w => t.includes(w))) return cat
  }
  return ""
}

// Pull "Ward-1" out of a location string like
// "Block A Park, Preetam Nagar (Ward-1)". Used to tag a new post so it becomes
// ward-filterable without adding another field to the form.
export function wardFromLocation(loc) {
  const m = (loc || "").match(/\bWard-\d\b/i)
  if (!m) return ""
  return WARDS.find(w => w.toLowerCase() === m[0].toLowerCase()) || ""
}

const HTML_ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }
export function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, ch => HTML_ESCAPES[ch])
}

/**
 * Escape text, then wrap each search term in a <mark class="search-hl">.
 *
 * Order is load-bearing for safety: the raw, user-authored text is escaped
 * FIRST, so it can never introduce markup; only the <mark> tags added
 * afterwards are real HTML. The result is intended for v-html — never feed it
 * unescaped input.
 */
export function highlightTerms(text, terms) {
  const escaped = escapeHtml(text)
  if (!terms || !terms.length) return escaped
  const pattern = terms
    // Escape regex metacharacters so a search for "c++" or "a.b" can't throw or
    // match unintended characters.
    .map(t => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("|")
  return escaped.replace(new RegExp(`(${pattern})`, "gi"), '<mark class="search-hl">$1</mark>')
}

// The searchable text of a post, flattened once. Everything a reader can see on
// a card, plus the category label so "road" matches a road-tagged post.
export function postHaystack(p) {
  return [
    p.content, p.title, p.location, p.ward,
    fmtCategory(p.category), p.author_name, p.author_department,
  ].filter(Boolean).join(" ").toLowerCase()
}

/**
 * Does one post survive one filter setting?
 *
 * The whole filter rule lives here, in plain functions, so the citizen, staff
 * and admin feeds cannot answer the same question differently — and so it can
 * be checked without mounting a component.
 *
 * Fields are ANDed and an unset field ("") never removes a post, so the empty
 * setting always means "show everything" — with one deliberate exception:
 * `department` is a child of `author`. It narrows only within OFFICIALS_ONLY
 * and is ignored otherwise, because only official posts carry a department.
 * Enforcing that here, not just by hiding the dropdown, means a hand-typed
 * "?dept=..." can never apply a filter the user cannot see or undo.
 *
 * `terms` are already lowercased words; all of them must appear somewhere in
 * the post's text (AND), which is what lets "road ward-1" match a road post in
 * Ward-1 even though those words never sit next to each other.
 */
export function matchesPostFilters(post, { terms = [], category = "", ward = "", author = "", department = "" } = {}) {
  if (terms.length) {
    const hay = postHaystack(post)
    if (!terms.every(t => hay.includes(t))) return false
  }

  if (category === NO_VALUE) {
    if (!isBlank(post.category)) return false
  } else if (category && post.category !== category) return false

  if (ward === NO_VALUE) {
    if (!isBlank(post.ward)) return false
  } else if (ward && post.ward !== ward) return false

  // is_official can be absent on older posts, so compare truthiness rather
  // than === true; an untagged post reads as a citizen post, which is right.
  if (author === OFFICIALS_ONLY) {
    if (!post.is_official) return false
    if (department && post.author_department !== department) return false
  } else if (author === CITIZENS_ONLY) {
    if (post.is_official) return false
  }

  return true
}

/**
 * Normalise one value out of `route.query`.
 *
 * A repeated query param ("?q=a&q=b") arrives as an array, which used to reach
 * `.toLowerCase()` and throw, blanking the whole feed. Take the last one, the
 * same way a form resubmit would.
 */
export function firstQueryValue(v) {
  if (Array.isArray(v)) v = v[v.length - 1]
  return typeof v === "string" ? v : ""
}
