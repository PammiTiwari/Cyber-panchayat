import { ref, watch } from "vue"
import { useRoute } from "vue-router"
import { useAuthStore } from "../stores/auth"
import { FAQ_NODES, FAQ_ROOTS, FAQ_CATEGORIES, HELP_FOR_ROUTE } from "../data/chatbotFaq"

// Module-level singleton state (same pattern as useToast.js) so the widget
// keeps its transcript while the user navigates between pages.
const isOpen = ref(false)
const hasOpened = ref(false) // true after the first open, stops the attention pulse
const transcript = ref([]) // { kind: 'bot' | 'user', text }
const currentOptions = ref([]) // node ids currently offered as clickable chips
// Who the current conversation was built for, as "<audience>:<user id>", or
// "guest" for a signed-out reader on one of the public pages.
//
// Keyed on the user and not just the role, because role alone was not enough:
// logging out reports no role, which audienceFor() reads as "citizen", so
// leaving a citizen account looked identical to still being that citizen and
// nothing was cleared. Their conversation then carried over to whoever logged
// in next. Comparing the whole key catches every switch, including one citizen
// handing the device to another.
let seededFor = null

// Staff and admin get their own content tier. Everyone else - citizens, and
// signed-out readers on the public pages, who have no role at all - gets the
// citizen tier, which is the content marked audience "everyone". That also
// covers role data being momentarily missing (e.g. a corrupted localStorage
// read) without crashing.
function audienceFor(role) {
  return role === "staff" || role === "admin" ? role : "citizen"
}

// Which content each role may see in the chatbot. Derived once from the FAQ
// data so it can never drift from what the categories actually say.
//
// A role's own tier: citizen maps to the "everyone" (citizen-facing) content,
// staff to "staff", admin to "admin". Category audience -> role tier.
const TIER_FOR_ROLE = { citizen: "everyone", staff: "staff", admin: "admin" }

// A node's audience, taken from the category it sits in.
const NODE_AUDIENCE = {}
for (const cat of FAQ_CATEGORIES) for (const id of cat.nodes) NODE_AUDIENCE[id] = cat.audience

// Nodes deliberately shared across roles show up on more than one role's menu
// (e.g. "Something isn't working?" is on all three). Those stay visible to
// everyone; anything on a single role's menu does not. Data-driven so adding a
// shared entry to two menus is all it takes, no code change here.
const SHARED_IDS = (() => {
  const count = {}
  for (const ids of Object.values(FAQ_ROOTS)) for (const id of ids) count[id] = (count[id] || 0) + 1
  return new Set(Object.keys(count).filter(id => count[id] >= 2))
})()

// The set of node ids a role is allowed to reach in the chatbot: its own tier
// plus the genuinely-shared nodes. This is what stops a citizen's typed search
// from surfacing staff or admin answers, which was the whole bug.
function allowedIdsFor(role) {
  const tier = TIER_FOR_ROLE[audienceFor(role)]
  const ids = new Set(SHARED_IDS)
  for (const [id, audience] of Object.entries(NODE_AUDIENCE)) {
    if (audience === tier) ids.add(id)
  }
  return ids
}

// A signed-out reader is a session too, not the absence of one. The Help and
// FAQ page is public, so the assistant has to work there; keying guests under
// their own name means signing in or out still reads as a change of session and
// clears the previous conversation.
const GUEST_KEY = "guest"

function sessionKeyFor(auth) {
  return auth.isLoggedIn ? `${audienceFor(auth.role)}:${auth.user?.id ?? "unknown"}` : GUEST_KEY
}

function greetingFor(audience, isGuest = false) {
  // Guests read the same citizen-tier content, but the citizen greeting offers
  // to help with their complaints and bookings, which they do not have yet.
  if (isGuest) {
    return "Hi! You can read every answer here without an account. Pick a question below, or type what you're looking for."
  }
  return {
    citizen: "Hi! Need help with complaints, Premium, bookings, or the community feed? Pick a question below, or just type what you're looking for.",
    staff: "Hi! Need help with your assigned complaints or department? Pick a question below, or type your own.",
    admin: "Hi! Need help managing officers, users, subscriptions, or reports? Pick a question below, or type your own.",
  }[audience]
}

// The menu for a role, with the current page's question moved to the front.
// This is what makes the assistant contextual: opened on the Bookings page it
// leads with the bookings answer. A page with no mapped answer, or one whose
// answer is already on the menu, just gets the normal list.
//
// Copy, not alias. FAQ_ROOTS/node.related are shared module-level data, so
// returning the array by reference would let any future mutation of
// currentOptions (e.g. a sort or push) silently corrupt the FAQ content for
// the rest of the session.
function menuFor(audience, routeName) {
  const roots = [...FAQ_ROOTS[audience]]
  const contextual = HELP_FOR_ROUTE[routeName]
  // Only prepend the page's contextual question if this role is actually
  // allowed to see it, so a shared route can't slip another tier's answer onto
  // the menu.
  if (!contextual || !FAQ_NODES[contextual] || !allowedIdsFor(audience).has(contextual)) return roots
  // Moved to the front if it is already on the menu, added to the front if it
  // is not. Either way the page's own question is offered first and is never
  // listed twice.
  return [contextual, ...roots.filter(id => id !== contextual)]
}

function seedRoot(audience, { reset = false, routeName = null, key = null } = {}) {
  if (reset) transcript.value = []
  if (transcript.value.length === 0) {
    transcript.value.push({ kind: "bot", text: greetingFor(audience, key === GUEST_KEY) })
  }
  currentOptions.value = menuFor(audience, routeName)
  seededFor = key
}

// Very small keyword matcher for free-typed questions. Not NLP, just scores
// each FAQ node by how many of the typed words (minus filler words) show up
// in its question/answer text, so a typed question can still surface the
// right scripted answer even if it's not one of the listed chips.
const STOPWORDS = new Set([
  "a", "an", "the", "is", "are", "am", "was", "were", "do", "does", "did",
  "i", "my", "me", "you", "your", "it", "its", "this", "that", "these", "those",
  "how", "what", "when", "where", "why", "who", "which",
  "can", "could", "should", "would", "will", "shall",
  "to", "for", "of", "in", "on", "at", "with", "and", "or", "so", "but",
  "need", "want", "please", "pls", "plz", "about", "there", "here",
])

function tokenize(text) {
  return (text.toLowerCase().match(/[a-z0-9]+/g) || [])
}

// Exported so the /faq page searches with the same scoring the assistant uses.
// One matcher means the same words rank the same way in both places. The page
// passes a large limit to get every match, not just the top few that fit in the
// chat bubble.
// `nodes` defaults to the built-in content. The /faq page passes its own set so
// questions an admin added are searchable there too, without the assistant's
// guided menu having to know about them.
export function findMatches(query, limit = 3, nodes = FAQ_NODES) {
  const tokens = tokenize(query).filter((t) => t.length > 2 && !STOPWORDS.has(t))
  if (!tokens.length) return []
  const scored = Object.entries(nodes)
    .map(([id, node]) => {
      const hay = new Set(tokenize(node.question + " " + node.answer))
      const score = tokens.reduce((sum, t) => sum + (hay.has(t) ? 1 : 0), 0)
      return { id, score }
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score)
  return scored.slice(0, limit).map((s) => s.id)
}

export function useChatbot() {
  const auth = useAuthStore()
  const route = useRoute()

  // Keeps the conversation tied to whoever is logged in right now. Runs on
  // login, on logout, on a role switch, and immediately on mount, because the
  // account can change while this component is unmounted (logging out lands on
  // /login, where the widget is not rendered) and a non-immediate watcher would
  // never notice.
  function syncSession() {
    const key = sessionKeyFor(auth)
    if (key === seededFor) return

    // Signing out closes the panel as well as reseeding it. On a shared device
    // the next person should not find the previous one's conversation sitting
    // open, and the guest greeting should be something they choose to open.
    if (key === GUEST_KEY) {
      isOpen.value = false
      hasOpened.value = false
    }

    seedRoot(audienceFor(auth.role), { reset: true, routeName: route.name, key })
  }

  watch(
    () => [auth.isLoggedIn, auth.role, auth.user?.id],
    syncSession,
    { immediate: true }
  )

  function open() {
    // Cheap no-op when the account hasn't changed; the safety net for any path
    // that reaches open() before the watcher has caught up.
    syncSession()
    if (transcript.value.length <= 1) {
      // Nothing has been asked yet, so the menu is still the opening one and is
      // safe to re-point at whatever page the reader is on now. Mid-conversation
      // it is left alone, because reordering the follow-ups someone is reading
      // would be worse than not being contextual.
      currentOptions.value = menuFor(audienceFor(auth.role), route.name)
    }
    isOpen.value = true
    hasOpened.value = true
  }

  function close() {
    isOpen.value = false
  }

  function select(nodeId) {
    const node = FAQ_NODES[nodeId]
    if (!node) return
    transcript.value.push({ kind: "user", text: node.question })
    transcript.value.push({ kind: "bot", text: node.answer, action: node.action })
    // Follow-ups are filtered to this role too, so clicking a shared answer
    // (like troubleshooting) can't surface another role's questions as its
    // related chips.
    const allowed = allowedIdsFor(auth.role)
    currentOptions.value = (node.related || []).filter(id => allowed.has(id))
  }

  // Free-text fallback for anything not already listed as a chip.
  function ask(query) {
    const text = query.trim()
    if (!text) return
    transcript.value.push({ kind: "user", text })
    // Search only this role's own content. Building a scoped node set and
    // passing it to findMatches (rather than filtering the top-3 afterwards)
    // means a citizen still gets their 3 best citizen answers even when a
    // staff/admin answer would have scored higher.
    const allowed = allowedIdsFor(auth.role)
    const scoped = Object.fromEntries(Object.entries(FAQ_NODES).filter(([id]) => allowed.has(id)))
    const matches = findMatches(text, 3, scoped)
    if (matches.length) {
      transcript.value.push({ kind: "bot", text: "Here's what I found. Tap one to see the full answer." })
      currentOptions.value = matches
    } else {
      transcript.value.push({ kind: "bot", text: "Sorry, I'm not quite sure about that one yet! Here's what I can help with instead:" })
      currentOptions.value = [...FAQ_ROOTS[audienceFor(auth.role)]]
    }
  }

  // "Main Menu" should feel like the rest of the flow, so it appends to the
  // transcript instead of erasing it. A hard reset (seedRoot with reset:true)
  // is reserved for genuine context changes, i.e. the logged-in role changing.
  function restart() {
    const audience = audienceFor(auth.role)
    transcript.value.push({ kind: "bot", text: "Sure, here's the main menu:" })
    currentOptions.value = menuFor(audience, route.name)
  }

  return { isOpen, hasOpened, transcript, currentOptions, faqNodes: FAQ_NODES, open, close, select, ask, restart }
}
