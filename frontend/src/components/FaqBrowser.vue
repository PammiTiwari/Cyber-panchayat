<template>
  <div class="faq-browser">
    <header class="faq-head">
      <h1 class="faq-title">Help and FAQ</h1>
      <p class="faq-sub">Answers to the questions people ask us most. You do not need an account to read them.</p>
    </header>

    <div class="faq-search-wrap">
      <input
        v-model="query"
        type="search"
        class="form-control faq-search"
        placeholder="Search for help"
        aria-label="Search help articles"
      />
      <button v-if="query" class="faq-search-clear" aria-label="Clear search" @click="query = ''">&times;</button>
    </div>

    <!-- Admins can add their own questions here. Everyone else never sees this
         box, and the API checks the role again on save so hiding it is not the
         only thing stopping a non-admin. -->
    <section v-if="auth.isAdmin" class="faq-admin">
      <div class="faq-admin-head">
        <h2 class="faq-admin-title">Add a question</h2>
        <button class="btn btn-sm" :class="formOpen ? 'btn-outline' : 'btn-primary'" @click="toggleForm">
          {{ formOpen ? 'Cancel' : 'New question' }}
        </button>
      </div>

      <form v-if="formOpen" class="faq-admin-form" @submit.prevent="addFaq">
        <div class="form-group">
          <label for="faq-new-q">Question</label>
          <input id="faq-new-q" v-model="form.question" class="form-control" maxlength="200" placeholder="What do people ask?" />
        </div>
        <div class="form-group">
          <label for="faq-new-a">Answer</label>
          <textarea id="faq-new-a" v-model="form.answer" class="form-control" rows="4" placeholder="Write the answer in plain, simple language."></textarea>
        </div>
        <div class="form-group">
          <label for="faq-new-cat">Show it under</label>
          <select id="faq-new-cat" v-model="form.category" class="form-control">
            <option v-for="cat in visibleCategories" :key="cat.id" :value="cat.id">{{ cat.label }}</option>
          </select>
        </div>

        <p v-if="formError" class="faq-admin-error">{{ formError }}</p>

        <div class="faq-admin-actions">
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Saving' : 'Save question' }}
          </button>
        </div>
      </form>
    </section>

    <p v-if="searching" class="faq-count" aria-live="polite">
      {{ results.length }} {{ results.length === 1 ? 'answer' : 'answers' }} found
    </p>

    <div v-if="searching && !results.length" class="faq-empty">
      <p>We could not find anything for "{{ query }}".</p>
      <button class="btn btn-sm btn-secondary" @click="query = ''">Clear search</button>
    </div>

    <!-- Topic shortcuts, only useful when browsing the full list. -->
    <nav v-if="!searching" class="faq-jump" aria-label="Jump to a topic">
      <a v-for="cat in visibleCategories" :key="cat.id" class="faq-jump-chip" :href="`#cat-${cat.id}`">
        {{ cat.label }}
        <span class="faq-jump-n">{{ cat.nodes.length }}</span>
      </a>
    </nav>

    <!-- Searching swaps the category list for a single list of matches, so the
         question markup below is written once and used for both. -->
    <section v-for="section in sections" :id="`cat-${section.id}`" :key="section.id" class="faq-section">
      <template v-if="section.label">
        <h2 class="faq-cat-title">
          {{ section.label }}
          <span v-if="section.audience !== 'everyone'" class="faq-cat-badge">{{ section.audience }}</span>
        </h2>
        <p class="faq-cat-blurb">{{ section.blurb }}</p>
      </template>

      <div class="faq-list">
        <article v-for="id in section.nodes" :id="id" :key="id" class="faq-item">
          <h3 class="faq-item-h">
            <button
              class="faq-q"
              :aria-expanded="String(isOpen(id))"
              :aria-controls="`answer-${id}`"
              @click="toggle(id)"
            >
              <span class="faq-q-text">{{ allNodes[id].question }}</span>
              <!-- Searching replaces the section headings with one flat list,
                   which left every result looking like it came from the same
                   place. The tag puts the heading back on the result itself. -->
              <span v-if="searching && categoryForNode[id]" class="faq-result-cat">
                {{ categoryForNode[id].label }}
                <em v-if="categoryForNode[id].audience !== 'everyone'">{{ categoryForNode[id].audience }}</em>
              </span>
            </button>
          </h3>

          <div v-show="isOpen(id)" :id="`answer-${id}`" class="faq-a">
            <!-- Editing happens in place, under the question it belongs to, so
                 an admin can see the wording they are fixing while they fix it. -->
            <form
              v-if="editingId && editingId === allNodes[id].faqId"
              class="faq-admin-form faq-edit-form"
              @submit.prevent="saveEdit"
            >
              <div class="form-group">
                <label :for="`faq-edit-q-${id}`">Question</label>
                <input :id="`faq-edit-q-${id}`" v-model="editForm.question" class="form-control" maxlength="200" />
              </div>
              <div class="form-group">
                <label :for="`faq-edit-a-${id}`">Answer</label>
                <textarea :id="`faq-edit-a-${id}`" v-model="editForm.answer" class="form-control" rows="4"></textarea>
              </div>
              <div class="form-group">
                <label :for="`faq-edit-cat-${id}`">Show it under</label>
                <select :id="`faq-edit-cat-${id}`" v-model="editForm.category" class="form-control">
                  <option v-for="cat in visibleCategories" :key="cat.id" :value="cat.id">{{ cat.label }}</option>
                </select>
              </div>

              <p v-if="editError" class="faq-admin-error">{{ editError }}</p>
              <p class="faq-edit-note">
                The helpful and not helpful count stays with this question, so
                you can see whether the rewrite lands better.
              </p>

              <div class="faq-admin-actions">
                <button type="submit" class="btn btn-primary" :disabled="editSaving">
                  {{ editSaving ? 'Saving' : 'Save changes' }}
                </button>
                <button type="button" class="btn btn-outline" @click="cancelEdit">Cancel</button>
              </div>
            </form>

            <p v-else class="faq-answer">{{ allNodes[id].answer }}</p>

            <div v-if="!editingId || editingId !== allNodes[id].faqId" class="faq-foot">
              <router-link
                v-if="canUseAction(allNodes[id].action)"
                :to="allNodes[id].action.path"
                class="faq-action"
              >{{ allNodes[id].action.label }}</router-link>
              <button class="faq-link-btn" @click="copyLink(id)">
                {{ copiedId === id ? 'Link copied' : 'Copy link to this answer' }}
              </button>
              <button
                v-if="auth.isAdmin && allNodes[id].faqId"
                class="faq-link-btn"
                @click="startEdit(allNodes[id])"
              >Edit this answer</button>
              <button
                v-if="auth.isAdmin && allNodes[id].faqId"
                class="faq-link-btn faq-del"
                @click="removeFaq(allNodes[id].faqId)"
              >Delete this question</button>
            </div>

            <!-- Signed-out visitors are not asked. Their answer cannot be tied
                 to anyone, so it cannot be capped at one per reader, and a
                 count an admin cannot trust is worse than no count. -->
            <div v-if="auth.isLoggedIn" class="faq-helpful">
              <!-- Admins are not asked. They wrote or own this help, so the
                   useful thing to show them is what readers answered. -->
              <template v-if="auth.isAdmin">
                <span class="faq-helpful-q">Reader feedback:</span>
                <span v-if="tallyFor(id).total" class="faq-pills">
                  <span class="faq-pill faq-pill-yes">
                    <span class="faq-pill-n">{{ tallyFor(id).yes }}</span> helpful
                  </span>
                  <span class="faq-pill faq-pill-no">
                    <span class="faq-pill-n">{{ tallyFor(id).no }}</span> not helpful
                  </span>
                </span>
                <span v-else class="faq-pill faq-pill-none">No answers yet</span>
              </template>
              <span v-else-if="votes[id]" class="faq-thanks">Thanks for telling us.</span>
              <template v-else>
                <span class="faq-helpful-q">Was this helpful?</span>
                <button class="faq-vote" @click="vote(id, 'yes')">Yes</button>
                <button class="faq-vote" @click="vote(id, 'no')">No</button>
              </template>
            </div>
          </div>
        </article>
      </div>
    </section>

    <section class="faq-cta">
      <h2 class="faq-cta-title">Still need help?</h2>
      <p class="faq-cta-sub">If you did not find your answer here, get in touch and someone will help you.</p>
      <div class="faq-cta-actions">
        <!-- Logged-in readers stay in the app: "/#contact" is a section on the
             public landing page, and sending a signed-in citizen/staff/admin
             there drops them out of the app shell entirely — no sidebar, no
             sign of being logged in — which reads as an accidental logout
             even though the session itself is untouched. -->
        <button v-if="auth.isLoggedIn" class="btn btn-primary" @click="openContactModal">Contact the admin office</button>
        <router-link v-else to="/#contact" class="btn btn-primary">Contact the admin office</router-link>
        <!-- The assistant only shows for logged-in users, so we only offer it
             to them instead of pointing at something they cannot open. -->
        <button v-if="auth.isLoggedIn" class="btn btn-outline" @click="askAssistant">Ask the assistant</button>
        <router-link v-else to="/login" class="btn btn-outline">Log in for live help</router-link>
      </div>
    </section>

    <!-- Contact modal (logged-in readers only — see note above) -->
    <div v-if="contactModal.show" class="modal-overlay" @click.self="contactModal.show = false">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Contact the Admin Office</h2>
          <button class="modal-close" aria-label="Close" @click="contactModal.show = false">✕</button>
        </div>
        <div v-if="contactModal.loading" class="spinner"></div>
        <template v-else>
          <p class="faq-contact-sub">Have a question or need help? Reach out directly.</p>
          <div class="faq-contact-list">
            <a v-if="contactModal.email" :href="`mailto:${contactModal.email}`" class="faq-contact-row">
              <span class="faq-contact-icon">✉️</span>
              <div>
                <div class="faq-contact-label">Email</div>
                <div class="faq-contact-value">{{ contactModal.email }}</div>
              </div>
            </a>
            <a v-if="contactModal.phone" :href="`tel:+91${contactModal.phone}`" class="faq-contact-row">
              <span class="faq-contact-icon">📞</span>
              <div>
                <div class="faq-contact-label">Phone</div>
                <div class="faq-contact-value">{{ contactModal.phone }}</div>
              </div>
            </a>
            <p v-if="!contactModal.email && !contactModal.phone" class="faq-contact-empty">
              Contact details aren't available right now.
            </p>
          </div>
        </template>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="contactModal.show = false">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * FaqBrowser - the Help and FAQ content that people can read and search.
 *
 * Reads the same content as the chat assistant (data/chatbotFaq.js), so an
 * answer is written once and shows up in both places. The assistant is a
 * conversation. This is the full list, and unlike the assistant it also shows
 * for visitors who are not logged in, which is why the page exists.
 *
 * Kept separate from FAQ.vue so that page can put the app sidebar around it for
 * logged-in users, and a plain header for everyone else, without copying any of
 * this markup twice.
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { FAQ_NODES, FAQ_CATEGORIES, AUDIENCE } from '../data/chatbotFaq'
import { findMatches, useChatbot } from '../composables/useChatbot'
import { useAuthStore } from '../stores/auth'
import api from '../api'
import { useToast } from '../composables/useToast'

const { error: toastError } = useToast()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chatbot = useChatbot()

const query = ref('')
const openIds = ref([])
const copiedId = ref('')

// Questions an admin has added, loaded from the API.
const customFaqs = ref([])
const formOpen = ref(false)
const form = ref({ question: '', answer: '', category: 'troubleshooting' })
const saving = ref(false)
const formError = ref('')

const searching = computed(() => query.value.trim().length > 0)

// Prefixed so an admin-added question can never collide with a built-in id,
// which would quietly replace shipped help content.
const nodeIdFor = faq => `custom-${faq.id}`

// The built-in content plus anything an admin added, in the one shape the rest
// of this component reads. `faqId` marks the added ones so only those get a
// delete button.
const allNodes = computed(() => {
  const map = { ...FAQ_NODES }
  for (const f of customFaqs.value) {
    map[nodeIdFor(f)] = {
      question: f.question,
      answer: f.answer,
      related: [],
      faqId: f.id,
      // Carried so the edit form can open on the section it is already filed
      // under, rather than resetting it to the default.
      category: f.category,
    }
  }
  return map
})

// The reader's own section, if they have one.
const ownAudience = computed(() =>
  auth.isAdmin ? AUDIENCE.ADMIN : auth.isStaff ? AUDIENCE.STAFF : null
)

// Staff and admin sections stay hidden from citizens and signed-out visitors,
// who see only the EVERYONE sections. Added questions are appended to whichever
// section the admin chose.
//
// A reader's own section is moved to the top rather than the shared sections
// being hidden from them. Staff answer citizens' questions, so they need to be
// able to look up what a citizen sees. Putting their own work first solves the
// noise without taking that away.
//
// Admins see every section, including For Staff. They write and moderate the
// help, so the list they browse has to be the list they can file into. When it
// was not, "For Staff" was missing from the add-a-question form, and anything
// filed there would have been invisible to the person who wrote it, with no way
// to fix a mistake.
const visibleCategories = computed(() => {
  const allowed = FAQ_CATEGORIES.filter(c =>
    c.audience === AUDIENCE.EVERYONE ||
    (c.audience === AUDIENCE.STAFF && (auth.isStaff || auth.isAdmin)) ||
    (c.audience === AUDIENCE.ADMIN && auth.isAdmin)
  )
  // Role sections first, the reader's own at the very top, then the shared
  // ones. For an admin that reads "For Admins, For Staff, then everything
  // else", keeping the two sections they manage next to each other instead of
  // splitting them around six shared sections.
  const mine = ownAudience.value
  const isRoleSection = c => c.audience !== AUDIENCE.EVERYONE
  const ordered = mine
    ? [
        ...allowed.filter(c => c.audience === mine),
        ...allowed.filter(c => c.audience !== mine && isRoleSection(c)),
        ...allowed.filter(c => !isRoleSection(c)),
      ]
    : allowed
  return ordered.map(c => ({
    ...c,
    nodes: [...c.nodes, ...customFaqs.value.filter(f => f.category === c.id).map(nodeIdFor)],
  }))
})

// Whether this reader can actually reach an answer's action button.
//
// Several citizen routes are closed to staff and admins, so "Submit a
// Complaint" on a staff member's screen used to bounce them to their own
// dashboard and look broken. The answer still shows, only the dead button goes.
//
// Read from the router itself rather than a list kept here, so it cannot drift
// as route permissions change.
function canUseAction(action) {
  if (!action?.path) return false
  const meta = router.resolve(action.path)?.meta || {}
  if (meta.public) return true
  // Signed out, the guard sends them to the login page, which is the right next
  // step for someone reading about a feature they want. Worth keeping.
  if (!auth.isLoggedIn) return true
  if (!meta.roles) return true
  return meta.roles.includes(auth.role)
}

async function loadCustomFaqs() {
  try {
    const res = await api.get('/faqs')
    customFaqs.value = Array.isArray(res.data) ? res.data : []
  } catch {
    // Help that already shipped is more useful than an error here, so a failed
    // load just means no added questions rather than a broken page.
    customFaqs.value = []
  }
}

function toggleForm() {
  formOpen.value = !formOpen.value
  formError.value = ''
}

async function addFaq() {
  if (saving.value) return
  formError.value = ''
  if (!form.value.question.trim() || !form.value.answer.trim()) {
    formError.value = 'Please fill in both the question and the answer.'
    return
  }
  saving.value = true
  try {
    const res = await api.post('/faqs', {
      question: form.value.question.trim(),
      answer: form.value.answer.trim(),
      category: form.value.category,
    })
    customFaqs.value = [...customFaqs.value, res.data]
    form.value = { question: '', answer: '', category: form.value.category }
    formOpen.value = false
  } catch (e) {
    formError.value = e.response?.data?.message || 'Could not save the question.'
  } finally {
    saving.value = false
  }
}

// Editing an added question.
//
// Deleting and re-adding was the only way to fix an answer before, and it
// changed the entry's id. The helpful / not helpful counts are keyed on
// "custom-<id>", so the rewrite always started from zero and there was no way
// to tell whether it had landed any better. Editing keeps the id.
const editingId = ref(null)
const editForm = ref({ question: '', answer: '', category: '' })
const editError = ref('')
const editSaving = ref(false)

function startEdit(node) {
  editingId.value = node.faqId
  editForm.value = {
    question: node.question,
    answer: node.answer,
    category: node.category || 'troubleshooting',
  }
  editError.value = ''
}

function cancelEdit() {
  editingId.value = null
  editError.value = ''
}

async function saveEdit() {
  if (editSaving.value) return
  editError.value = ''
  if (!editForm.value.question.trim() || !editForm.value.answer.trim()) {
    editError.value = 'Please fill in both the question and the answer.'
    return
  }
  editSaving.value = true
  try {
    const res = await api.put(`/faqs/${editingId.value}`, {
      question: editForm.value.question.trim(),
      answer: editForm.value.answer.trim(),
      category: editForm.value.category,
    })
    customFaqs.value = customFaqs.value.map(f => (f.id === editingId.value ? res.data : f))
    editingId.value = null
  } catch (e) {
    editError.value = e.response?.data?.message || 'Could not save the changes.'
  } finally {
    editSaving.value = false
  }
}

async function removeFaq(faqId) {
  if (!confirm('Delete this question?')) return
  try {
    await api.delete(`/faqs/${faqId}`)
    customFaqs.value = customFaqs.value.filter(f => f.id !== faqId)
  } catch (e) {
    toastError(e.response?.data?.message || 'Could not delete the question.')
  }
}

// Only search what the reader is allowed to browse, so a search can never show
// an admin answer to a citizen.
const searchableIds = computed(() => visibleCategories.value.flatMap(c => c.nodes))

// Same scoring the assistant uses, without its top-few limit, because a page has
// room to show every match.
const results = computed(() => {
  if (!searching.value) return []
  const allowed = new Set(searchableIds.value)
  // Passing allNodes means questions an admin added are searchable too.
  return findMatches(query.value.trim(), Number.MAX_SAFE_INTEGER, allNodes.value)
    .filter(id => allowed.has(id))
})

// Which section each answer belongs to, so a search result can say where it
// came from. Built from visibleCategories rather than FAQ_CATEGORIES, so it
// covers the questions an admin added and is filtered to this reader's role
// exactly the same way the list itself is.
const categoryForNode = computed(() => {
  const map = {}
  for (const cat of visibleCategories.value) {
    for (const id of cat.nodes) map[id] = cat
  }
  return map
})

// One shape for both modes, so the question markup is written once.
const sections = computed(() =>
  searching.value
    ? [{ id: 'results', label: '', blurb: '', audience: 'everyone', nodes: results.value }]
    : visibleCategories.value
)

function isOpen(id) {
  return openIds.value.includes(id)
}

function toggle(id) {
  openIds.value = isOpen(id) ? openIds.value.filter(i => i !== id) : [...openIds.value, id]
}

// Was this helpful.
//
// The answer goes to the API so an admin can see the running count. It is also
// kept on this device, which is what stops the same reader being asked the same
// question again on their next visit.
const HELPFUL_KEY = 'faq_helpful'

function readVotes() {
  try { return JSON.parse(localStorage.getItem(HELPFUL_KEY) || '{}') } catch { return {} }
}

const votes = ref(readVotes())
const feedbackTally = ref({})

function tallyFor(id) {
  const t = feedbackTally.value[id]
  const yes = t?.yes ?? 0
  const no = t?.no ?? 0
  return { yes, no, total: yes + no }
}

async function vote(id, verdict) {
  // Recorded locally first, so the reader stops being asked even if the request
  // fails. Their answer mattering more than our bookkeeping.
  votes.value = { ...votes.value, [id]: verdict }
  try { localStorage.setItem(HELPFUL_KEY, JSON.stringify(votes.value)) } catch { /* private browsing */ }
  try {
    await api.post('/faqs/feedback', { article_id: id, helpful: verdict === 'yes' })
  } catch { /* the reader does not need to know the count failed to save */ }
}

// Admins only. Everyone else gets a 403, which is fine and expected here.
async function loadFeedback() {
  if (!auth.isAdmin) return
  try {
    const res = await api.get('/faqs/feedback')
    feedbackTally.value = res.data && typeof res.data === 'object' ? res.data : {}
  } catch {
    feedbackTally.value = {}
  }
}

// Every answer has its own web address, like /faq#cit-premium. That is what lets
// a help link on another page, or a reply from support, point straight at it.
// An answer opened by address is expanded for the reader instead of making them
// look for it.
function revealFromHash() {
  const id = decodeURIComponent(route.hash || '').replace(/^#/, '')
  if (!id || !allNodes.value[id]) return
  if (!isOpen(id)) openIds.value = [...openIds.value, id]
  // Wait one frame so the answer is open before we scroll to it.
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  })
}

async function copyLink(id) {
  const url = `${window.location.origin}/faq#${id}`
  try {
    await navigator.clipboard.writeText(url)
    copiedId.value = id
    setTimeout(() => { if (copiedId.value === id) copiedId.value = '' }, 1600)
  } catch {
    // Copying is blocked on insecure pages and in some browsers. Putting the
    // link in the address bar at least lets the reader copy it by hand.
    window.location.hash = id
  }
}

function askAssistant() {
  chatbot.open()
}

// Same admin email/phone the public landing page's #contact section shows,
// fetched on demand so a logged-in reader gets it without ever leaving the
// app shell (see the template note on why that navigation was a problem).
const contactModal = ref({ show: false, loading: false, email: null, phone: null })

async function openContactModal() {
  contactModal.value = { show: true, loading: true, email: null, phone: null }
  try {
    const { data } = await api.get('/public-stats')
    contactModal.value.email = data.admin_email || null
    contactModal.value.phone = data.admin_phone || null
  } catch {
    // Empty state in the modal already covers this — nothing else to do.
  } finally {
    contactModal.value.loading = false
  }
}

onMounted(async () => {
  // Added questions load first, so a link straight to one can still open it.
  await loadCustomFaqs()
  revealFromHash()
  loadFeedback()
})
watch(() => route.hash, revealFromHash)
</script>

<style scoped>
.faq-browser { max-width: 820px; margin: 0 auto; }

.faq-head { margin-bottom: 1.25rem; }
.faq-title { font-size: 1.9rem; font-weight: 800; margin: 0 0 0.35rem; color: var(--text); }
.faq-sub { color: var(--text-muted); margin: 0; }

.faq-search-wrap { position: relative; margin-bottom: 1rem; }
.faq-search { width: 100%; padding-right: 2.25rem; }
.faq-search::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; }
.faq-search-clear {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; cursor: pointer; font-size: 1.2rem;
  color: var(--text-muted); line-height: 1; padding: 0;
}
.faq-search-clear:hover { color: var(--text); }

.faq-count { font-size: 0.82rem; color: var(--text-muted); margin: 0 0 0.75rem; font-weight: 500; }
.faq-empty {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 1.5rem; text-align: center;
  color: var(--text-muted); font-size: 0.9rem;
}
.faq-empty p { margin: 0 0 0.75rem; }

/* Admin compose box */
.faq-admin {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 1rem; margin-bottom: 1.5rem;
}
.faq-admin-head { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.faq-admin-title { margin: 0; font-size: 0.95rem; font-weight: 700; color: var(--text); }
.faq-admin-form { margin-top: 1rem; }
.faq-admin-form .form-group:last-of-type { margin-bottom: 0.75rem; }
.faq-admin-error { color: var(--danger); font-size: 0.8rem; margin: 0 0 0.75rem; font-weight: 500; }
.faq-admin-actions { display: flex; justify-content: flex-end; gap: 0.5rem; }

/* The in-place edit form. Same fields as the add form, sitting inside the
   answer it is rewriting rather than at the top of the page. */
.faq-edit-form { margin-top: 0; }
.faq-edit-note { font-size: 0.76rem; color: var(--text-muted); margin: 0 0 0.75rem; }
.faq-del { color: var(--danger); }
.faq-del:hover { color: var(--danger); text-decoration: underline; }

.faq-jump { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.5rem; }
.faq-jump-chip {
  display: inline-flex; align-items: center; gap: 0.35rem;
  background: var(--accent); color: var(--accent-foreground);
  border: 1px solid transparent; border-radius: 100px;
  padding: 0.3rem 0.75rem; font-size: 0.78rem; font-weight: 600;
  text-decoration: none; transition: background var(--transition), border-color var(--transition);
}
.faq-jump-chip:hover { background: rgba(0, 82, 255, 0.16); border-color: var(--primary); }
.faq-jump-n { opacity: 0.65; font-weight: 700; }

.faq-section { margin-bottom: 2rem; scroll-margin-top: 1rem; }
.faq-cat-title {
  font-size: 1.15rem; font-weight: 700; margin: 0 0 0.2rem;
  display: flex; align-items: center; gap: 0.5rem; color: var(--text);
}
.faq-cat-badge {
  font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  background: var(--stone); color: var(--text-muted);
  border-radius: 100px; padding: 0.12rem 0.5rem;
}
.faq-cat-blurb { color: var(--text-muted); font-size: 0.85rem; margin: 0 0 0.85rem; }

/* The section name, carried onto a search result. Same pill as the heading
   badge, since it is the same information in a different place. */
.faq-result-cat {
  flex-shrink: 0;
  display: inline-flex; align-items: center; gap: 0.35rem;
  font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  background: var(--stone); color: var(--text-muted);
  border-radius: 100px; padding: 0.12rem 0.5rem;
}
.faq-result-cat em { font-style: normal; color: var(--primary); }

.faq-list { display: flex; flex-direction: column; gap: 0.5rem; }
.faq-item {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius-sm); overflow: hidden;
  scroll-margin-top: 1rem;
}
.faq-item:target { border-color: var(--primary); box-shadow: 0 0 0 3px var(--accent); }
.faq-item-h { margin: 0; font-size: inherit; font-weight: inherit; }
.faq-q {
  width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  background: none; border: none; cursor: pointer; text-align: left;
  padding: 0.9rem 1rem; font-size: 0.92rem; font-weight: 600; color: var(--text);
  font-family: inherit;
}
.faq-q:hover { background: var(--stone); }
.faq-sign {
  flex-shrink: 0; width: 20px; text-align: center;
  font-size: 1.1rem; font-weight: 700; color: var(--text-muted);
}

.faq-a { padding: 0 1rem 1rem; border-top: 1px solid var(--border); }
.faq-answer { margin: 0.85rem 0 0; color: var(--text); font-size: 0.88rem; line-height: 1.65; }

.faq-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 0.9rem; margin-top: 0.85rem; }
.faq-action { font-size: 0.82rem; font-weight: 700; color: var(--primary); text-decoration: none; }
.faq-action:hover { text-decoration: underline; }
.faq-link-btn {
  background: none; border: none; padding: 0; cursor: pointer; font-family: inherit;
  font-size: 0.78rem; font-weight: 600; color: var(--text-muted);
}
.faq-link-btn:hover { color: var(--text); }

.faq-helpful {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.5rem;
  margin-top: 0.85rem; padding-top: 0.75rem; border-top: 1px dashed var(--border);
}
.faq-helpful-q { font-size: 0.78rem; color: var(--text-muted); font-weight: 500; }
.faq-vote {
  background: var(--stone); border: 1px solid var(--border); border-radius: 100px;
  padding: 0.2rem 0.85rem; font-size: 0.75rem; font-weight: 600; cursor: pointer;
  color: var(--text); font-family: inherit; transition: background var(--transition);
}
.faq-vote:hover { background: var(--accent); border-color: var(--primary); color: var(--accent-foreground); }
.faq-thanks { font-size: 0.78rem; color: var(--success); font-weight: 600; }
/* Counts an admin reads at a glance. Pill shaped to match the filter chips and
   vote buttons used elsewhere, and colour coded so the split is obvious without
   reading the numbers. Not clickable, so no hover or pointer cursor: they are
   labels, and looking pressable would promise an action that isn't there. */
.faq-pills { display: inline-flex; flex-wrap: wrap; gap: 0.35rem; }
.faq-pill {
  display: inline-flex; align-items: baseline; gap: 0.3rem;
  border: 1px solid transparent; border-radius: 100px;
  padding: 0.22rem 0.7rem;
  font-size: 0.73rem; font-weight: 600; line-height: 1.5;
  white-space: nowrap;
}
.faq-pill-n { font-size: 0.82rem; font-weight: 800; }
.faq-pill-yes {
  background: rgba(21, 128, 61, 0.10);
  border-color: rgba(21, 128, 61, 0.22);
  color: var(--success);
}
.faq-pill-no {
  background: rgba(220, 38, 38, 0.08);
  border-color: rgba(220, 38, 38, 0.18);
  color: var(--danger);
}
.faq-pill-none {
  background: var(--stone);
  border-color: var(--border);
  color: var(--text-muted);
  font-weight: 500;
}

.faq-cta {
  background: var(--accent); border-radius: var(--radius);
  padding: 1.5rem; text-align: center; margin-top: 2.5rem;
}
.faq-cta-title { margin: 0 0 0.3rem; font-size: 1.15rem; font-weight: 700; color: var(--text); }
.faq-cta-sub { margin: 0 0 1rem; color: var(--text-muted); font-size: 0.86rem; }
.faq-cta-actions { display: flex; flex-wrap: wrap; gap: 0.6rem; justify-content: center; }

/* Contact modal */
.faq-contact-sub { margin: 0 0 1rem; color: var(--text-muted); font-size: 0.86rem; }
.faq-contact-list { display: flex; flex-direction: column; gap: 0.6rem; }
.faq-contact-row {
  display: flex; align-items: center; gap: 0.75rem;
  background: var(--accent); border-radius: var(--radius-sm);
  padding: 0.75rem 0.9rem; text-decoration: none;
  transition: background var(--transition);
}
.faq-contact-row:hover { background: rgba(0, 82, 255, 0.14); }
.faq-contact-icon { font-size: 1.1rem; flex-shrink: 0; }
.faq-contact-label { font-size: 0.72rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }
.faq-contact-value { font-size: 0.9rem; color: var(--text); font-weight: 600; }
.faq-contact-empty { font-size: 0.85rem; color: var(--text-muted); text-align: center; margin: 0.5rem 0; }

@media (max-width: 640px) {
  .faq-title { font-size: 1.5rem; }
  .faq-q { padding: 0.8rem 0.85rem; font-size: 0.88rem; }
  .faq-a { padding: 0 0.85rem 0.85rem; }
  .faq-cta { padding: 1.25rem 1rem; }
  .faq-cta-actions { flex-direction: column; }
  .faq-cta-actions > * { width: 100%; }
}
</style>
