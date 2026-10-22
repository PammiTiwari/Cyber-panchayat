<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="My Complaints" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Track all your submitted complaints</p>
          </div>
          <div class="page-header-actions">
            <button v-if="drafts.length" class="btn btn-outline" @click="showDraftsModal = true">
              📝 Drafts ({{ drafts.length }})
            </button>
            <DownloadReportButton :loading="exporting" @click="downloadReport" />
            <router-link to="/submit" class="btn btn-primary">+ Submit New</router-link>
          </div>
        </div>

        <div v-if="showDraftsModal" class="modal-overlay" @click.self="showDraftsModal = false">
          <div class="modal">
            <div class="modal-header">
              <h2>📝 Your Drafts</h2>
              <button class="modal-close" aria-label="Close" @click="showDraftsModal = false">✕</button>
            </div>
            <div class="drafts-list">
              <div v-for="d in drafts" :key="d.id" class="draft-item">
                <div class="draft-info">
                  <span class="draft-item-title">{{ d.form.title || 'Untitled complaint' }}</span>
                  <span class="draft-item-meta">
                    <span v-if="d.form.category" class="cat-text">{{ d.form.category }}</span>
                    <span v-if="d.form.category"> · </span>Created {{ fmtDate(d.created_at) }} · Last edited {{ fmtDate(d.updated_at) }}
                  </span>
                </div>
                <div class="draft-actions">
                  <button class="btn btn-xs btn-primary" @click="resumeDraft(d)">Resume</button>
                  <button class="btn btn-xs btn-danger" @click="removeDraft(d)">Delete</button>
                </div>
              </div>
            </div>
            <div class="modal-footer">
              <!-- Drafts are deliberately never sent to the server, so they do
                   not follow the citizen to another phone or survive clearing
                   browser data. Better to say so than to let them find out. -->
              <p class="drafts-note">Saved on this device only</p>
              <button class="btn btn-outline btn-sm" @click="clearAllDraftsNow">Clear All Drafts</button>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="filter-bar">
            <div class="search-wrapper">
              <input
                ref="searchInput"
                v-model="searchQuery"
                type="search"
                class="form-control"
                aria-label="Search complaints by ID, title, or category"
                placeholder="🔍 Search by ID, title, or category...  (press /)"
              />
              <button
                v-if="searchQuery"
                type="button"
                class="search-clear"
                aria-label="Clear search"
                @click="clearSearch"
              >✕</button>
            </div>
            <select v-model="statusFilter" class="form-control filter-select">
              <option value="">Status: All</option>
              <option value="pending">Pending</option>
              <option value="assigned">Assigned</option>
              <option value="in_progress">In Progress</option>
              <option value="on_hold_weather">On Hold - Weather</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
            <select v-model="categoryFilter" class="form-control filter-select">
              <option value="">Category: All</option>
              <option value="road">Road</option>
              <option value="water">Water</option>
              <option value="electricity">Electricity</option>
              <option value="sanitation">Sanitation</option>
              <option value="waste">Waste</option>
              <option value="parks">Parks & Public Spaces</option>
              <option value="maintenance">Maintenance</option>
              <option value="other">Other</option>
            </select>
            <div class="date-range">
              <label class="date-label">
                From
                <input v-model="dateFrom" type="date" class="form-control date-input" :max="dateTo || undefined" />
              </label>
              <label class="date-label">
                To
                <input v-model="dateTo" type="date" class="form-control date-input" :min="dateFrom || undefined" />
              </label>
              <button
                v-for="p in DATE_PRESETS" :key="p.days"
                type="button"
                class="date-preset"
                :class="{ active: activePreset === p.days }"
                @click="applyPreset(p.days)"
              >{{ p.label }}</button>
            </div>
            <button
              v-if="hasActiveFilters"
              class="btn btn-outline btn-sm clear-filters"
              @click="clearAllFilters"
            >
              Clear Filters
            </button>
          </div>

          <FilterChips :filters="activeChips" @remove="clearFilter" />

          <div v-if="hasActiveFilters" class="filter-info">
            <span class="result-count" aria-live="polite">📊 {{ filtered.length }} result{{ filtered.length !== 1 ? 's' : '' }} found</span>
          </div>

          <SkeletonLoader v-if="loading" type="table" :count="5" />
          <!-- Two distinct empty states: a genuinely empty account gets the
               onboarding nudge, while a list emptied by filters gets a way back
               out. Offering "Submit Your First Complaint" to someone who has 20
               complaints and an over-narrow filter is just confusing. -->
          <EmptyState
            v-else-if="!paged.length && hasActiveFilters"
            type="search"
            title="No Matching Complaints"
            description="No complaints match these filters. Try widening the date range or clearing a filter."
            buttonText="Clear Filters"
            @action="clearAllFilters"
          />
          <EmptyState
            v-else-if="!paged.length"
            type="complaints"
            title="No Complaints Found"
            description="You haven't submitted any complaints yet. Start helping your community!"
            buttonText="Submit Your First Complaint"
            @action="$router.push('/submit')"
          />
          <div v-else class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th
                    v-for="key in ['cmp_id', 'category', 'title', 'created_at', 'status', 'upvotes_count']"
                    :key="key"
                    class="th-sortable"
                    :aria-sort="sortKey === key ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'"
                    @click="toggleSort(key)"
                  >
                    {{ SORT_LABELS[key] }}
                    <span class="sort-caret" :class="{ on: sortKey === key }">
                      {{ sortKey === key && sortDir === 'asc' ? '▲' : '▼' }}
                    </span>
                  </th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in paged" :key="r.id">
                  <td><code class="cmp-id">{{ r.cmp_id }}</code></td>
                  <td><span class="cat-text">{{ r.category }}</span></td>
                  <td class="td-title">
                    <div class="title-with-thumb">
                      <img v-if="r.image_urls?.length" :src="r.image_urls[0]" class="thumb" alt="" />
                      <span>{{ r.title }}</span>
                    </div>
                  </td>
                  <td>{{ fmtDate(r.created_at) }}</td>
                  <td><span :class="['badge', `badge-${r.status}`]">{{ fmtStatus(r.status) }}</span></td>
                  <td class="text-center">👍 {{ r.upvotes_count || 0 }}</td>
                  <td>
                    <div class="action-btns">
                      <router-link :to="`/complaints/${r.id}`" class="btn btn-xs btn-primary">View</router-link>
                      <button v-if="r.status === 'pending'" class="btn btn-xs btn-danger" :disabled="deletingId === r.id" @click="deleteRequest(r)">
                        {{ deletingId === r.id ? 'Deleting...' : 'Delete' }}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="pagination" v-if="totalPages > 1">
            <button class="page-btn" aria-label="Previous page" :disabled="page === 1" @click="page--">&lt;</button>
            <button
              v-for="p in totalPages" :key="p"
              class="page-btn" :class="{ active: page === p }"
              @click="page = p"
            >{{ p }}</button>
            <button class="page-btn" aria-label="Next page" :disabled="page === totalPages" @click="page++">&gt;</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * My Complaints - Citizen view for all their submitted complaints
 * Features: search, status filtering, pagination, and delete pending complaints
 * Only complaints in "pending" status can be deleted by the citizen
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import SkeletonLoader from '../../components/SkeletonLoader.vue'
import DownloadReportButton from '../../components/DownloadReportButton.vue'
import EmptyState from '../../components/EmptyState.vue'
import FilterChips from '../../components/FilterChips.vue'
import { useToast } from '../../composables/useToast'
import { useDebouncedValue } from '../../composables/useDebounce'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'
import { fmtStatus } from '../../utils/status'
import { downloadComplaintsReportPdf } from '../../utils/reportPdf'
import { readDrafts, deleteDraft, clearAllDrafts } from '../../utils/complaintDrafts'
import { useConfirm } from '../../composables/useConfirm'

const { success, error: toastError } = useToast()
const { confirm: ask } = useConfirm()
const auth = useAuthStore()
const loading = ref(true)
const requests = ref([])
const exporting = ref(false)
const route = useRoute()
const router = useRouter()

// Filters seed straight from the URL rather than hydrating after mount, so a
// refresh or a back-navigation lands on the same filtered view instead of
// flashing the unfiltered list first.
const searchQuery = ref(route.query.q || '')
// Input stays instantly responsive; filtering and the URL sync wait for a
// pause in typing instead of re-running on every keystroke.
const debouncedSearchQuery = useDebouncedValue(searchQuery, 300)
const statusFilter = ref(route.query.status || '')
const categoryFilter = ref(route.query.category || '')
const dateFrom = ref(route.query.from || '')
const dateTo = ref(route.query.to || '')
const sortKey = ref(route.query.sort || 'created_at')
const sortDir = ref(route.query.dir === 'asc' ? 'asc' : 'desc')
const page = ref(Number(route.query.page) > 0 ? Number(route.query.page) : 1)
const perPage = 10
const deletingId = ref(null)
const searchInput = ref(null)
const drafts = ref([])
const showDraftsModal = ref(false)

function loadDrafts() {
  drafts.value = readDrafts()
}

function resumeDraft(d) {
  router.push(`/submit?draft=${d.id}`)
}

async function removeDraft(d) {
  const ok = await ask({
    title: 'Discard this draft?',
    message: `"${d.form.title || 'Untitled complaint'}" will be removed from this device. This cannot be undone.`,
    confirmLabel: 'Discard draft',
    danger: true,
  })
  if (!ok) return
  deleteDraft(d.id)
  loadDrafts()
  if (!drafts.value.length) showDraftsModal.value = false
}

async function clearAllDraftsNow() {
  const n = drafts.value.length
  const ok = await ask({
    title: `Discard all ${n} draft${n !== 1 ? 's' : ''}?`,
    message: 'Every saved draft will be removed from this device. This cannot be undone.',
    confirmLabel: 'Discard all',
    danger: true,
  })
  if (!ok) return
  clearAllDrafts()
  loadDrafts()
  showDraftsModal.value = false
}

onMounted(async () => {
  loadDrafts()
  // ?drafts=1 opens the drafts straight away, so the "Drafts" link on the
  // submit page lands on the list itself rather than on this page with the
  // reader still hunting for the button.
  if (route.query.drafts && drafts.value.length) showDraftsModal.value = true
  try {
    const res = await api.get('/requests')
    requests.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

/**
 * Filter complaints by search term (across ID, title, category, address)
 * and by status, category. Reset pagination when filters change.
 */
const filtered = computed(() => {
  let list = requests.value
  // Search across complaint ID, title, category, and address fields
  if (debouncedSearchQuery.value) {
    const q = debouncedSearchQuery.value.toLowerCase()
    list = list.filter(r =>
      r.cmp_id?.toLowerCase().includes(q) ||
      r.title?.toLowerCase().includes(q) ||
      r.category?.toLowerCase().includes(q) ||
      r.address?.toLowerCase().includes(q)
    )
  }
  // Filter by status if selected
  if (statusFilter.value) list = list.filter(r => r.status === statusFilter.value)
  // Filter by category if selected
  if (categoryFilter.value) list = list.filter(r => r.category === categoryFilter.value)
  // Filter by submission date range. Both bounds are inclusive, and the
  // comparison is done on the IST calendar date rather than the raw timestamp,
  // so a complaint filed late in the evening still counts as that day — the
  // same day the table shows next to it.
  if (dateFrom.value) list = list.filter(r => istDate(r.created_at) >= dateFrom.value)
  if (dateTo.value) list = list.filter(r => istDate(r.created_at) <= dateTo.value)
  return list
})

const hasActiveFilters = computed(() =>
  Boolean(statusFilter.value || categoryFilter.value || searchQuery.value || dateFrom.value || dateTo.value)
)

/**
 * Mirror the current view into the query string.
 *
 * `replace` rather than `push` deliberately: typing in the search box would
 * otherwise stack a history entry per keystroke and make the back button
 * useless. The URL still carries the state when navigating away, so returning
 * to this page restores the same filtered view.
 *
 * Defaults are omitted so an unfiltered list keeps a clean URL.
 */
function syncUrl() {
  const q = {}
  if (debouncedSearchQuery.value) q.q = debouncedSearchQuery.value
  if (statusFilter.value) q.status = statusFilter.value
  if (categoryFilter.value) q.category = categoryFilter.value
  if (dateFrom.value) q.from = dateFrom.value
  if (dateTo.value) q.to = dateTo.value
  if (sortKey.value !== 'created_at') q.sort = sortKey.value
  if (sortDir.value !== 'desc') q.dir = sortDir.value
  if (page.value > 1) q.page = String(page.value)
  router.replace({ query: q }).catch(() => {})
}

watch([debouncedSearchQuery, statusFilter, categoryFilter, dateFrom, dateTo], () => {
  page.value = 1
  syncUrl()
})
watch([sortKey, sortDir, page], syncUrl)

const SORT_LABELS = { cmp_id: 'ID', category: 'Category', title: 'Title', created_at: 'Date', status: 'Status', upvotes_count: 'Upvotes' }

const sorted = computed(() => {
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1
  // Copy first — Array.sort mutates, and `filtered` hands back the source array
  // untouched when no filter is active.
  return [...filtered.value].sort((a, b) => {
    let av = a[key]
    let bv = b[key]
    if (key === 'created_at') {
      av = new Date(av).getTime()
      bv = new Date(bv).getTime()
    } else if (key === 'upvotes_count') {
      av = Number(av) || 0
      bv = Number(bv) || 0
    } else {
      av = String(av ?? '').toLowerCase()
      bv = String(bv ?? '').toLowerCase()
    }
    if (av < bv) return -dir
    if (av > bv) return dir
    return 0
  })
})

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    // Dates and upvotes read highest/most-recent first by default; text reads A-Z.
    sortDir.value = (key === 'created_at' || key === 'upvotes_count') ? 'desc' : 'asc'
  }
  page.value = 1
}

const CATEGORY_LABELS = {
  road: 'Road', water: 'Water', electricity: 'Electricity', sanitation: 'Sanitation',
  waste: 'Waste', parks: 'Parks & Public Spaces', maintenance: 'Maintenance', other: 'Other',
}

// Removable summary of what's currently narrowing the list.
const activeChips = computed(() => {
  const chips = []
  if (searchQuery.value) chips.push({ key: 'search', label: `Search: "${searchQuery.value}"` })
  if (statusFilter.value) chips.push({ key: 'status', label: `Status: ${fmtStatus(statusFilter.value)}` })
  if (categoryFilter.value) chips.push({ key: 'category', label: `Category: ${CATEGORY_LABELS[categoryFilter.value] || categoryFilter.value}` })
  if (dateFrom.value) chips.push({ key: 'dateFrom', label: `From: ${dateFrom.value}` })
  if (dateTo.value) chips.push({ key: 'dateTo', label: `To: ${dateTo.value}` })
  return chips
})

function clearFilter(key) {
  if (key === 'search') searchQuery.value = ''
  else if (key === 'status') statusFilter.value = ''
  else if (key === 'category') categoryFilter.value = ''
  else if (key === 'dateFrom') dateFrom.value = ''
  else if (key === 'dateTo') dateTo.value = ''
}

const DATE_PRESETS = [
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
  { days: 90, label: '90d' },
]

// Highlights a preset only when the range still matches it exactly, so editing
// either date by hand visibly drops the highlight.
const activePreset = computed(() => {
  if (!dateFrom.value || dateTo.value !== istDate(Date.now())) return null
  return DATE_PRESETS.find(p => dateFrom.value === istDate(Date.now() - p.days * 864e5))?.days ?? null
})

// Clicking the active preset again clears it, so the button toggles.
function applyPreset(days) {
  if (activePreset.value === days) {
    dateFrom.value = ''
    dateTo.value = ''
    return
  }
  dateTo.value = istDate(Date.now())
  dateFrom.value = istDate(Date.now() - days * 864e5)
}

// One reused formatter — constructing an Intl formatter per call is expensive,
// and this runs for every row on every keystroke.
const IST_FORMAT = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' })
const istCache = new Map()

// en-CA formats as YYYY-MM-DD, which is what <input type="date"> binds, so the
// two can be compared as plain strings.
function istDate(d) {
  // Only record timestamps (strings) repeat across calls, so only those are
  // worth caching — keying on a live Date.now() would grow the map forever.
  if (typeof d !== 'string') return IST_FORMAT.format(new Date(d))
  let v = istCache.get(d)
  if (v === undefined) {
    v = IST_FORMAT.format(new Date(d))
    istCache.set(d, v)
  }
  return v
}

const totalPages = computed(() => Math.ceil(sorted.value.length / perPage))
const paged = computed(() => {
  const start = (page.value - 1) * perPage
  return sorted.value.slice(start, start + perPage)
})

/**
 * Delete a complaint - only allowed for complaints in "pending" status
 * UI button is hidden for non-pending complaints, server validates on DELETE
 * Shows confirmation dialog and provides user feedback during deletion
 */
async function deleteRequest(r) {
  if (deletingId.value) return // Prevent multiple simultaneous delete requests
  if (!confirm(`Delete complaint ${r.cmp_id}? This cannot be undone.`)) return
  deletingId.value = r.id
  try {
    await api.delete(`/requests/${r.id}`)
    requests.value = requests.value.filter(x => x.id !== r.id)
    success(`✓ Complaint ${r.cmp_id} deleted successfully`)
  } catch (e) {
    toastError(`Error: ${e.response?.data?.message || 'Failed to delete complaint'}`)
  } finally {
    deletingId.value = null
  }
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric' })
}

/**
 * Exports whatever the current filters show (search/status/category/date
 * range) — "the filtered view" doubles as the bulk-export date range picker
 * the feature needs, without a second, separate control.
 */
async function downloadReport() {
  exporting.value = true
  try {
    downloadComplaintsReportPdf({
      citizenName: auth.user?.name || 'Citizen',
      complaints: sorted.value,
      dateFrom: dateFrom.value,
      dateTo: dateTo.value,
    })
    success('✓ Report downloaded')
  } catch (e) {
    toastError('Could not generate the report — please try again')
  } finally {
    exporting.value = false
  }
}

/**
 * "/" jumps to the search box, the convention from GitHub, Slack, and friends.
 * Ignored while another field has focus so it doesn't swallow a literal slash
 * being typed into an input, and ignored alongside modifiers so it never
 * shadows a browser shortcut.
 */
function onKeydown(e) {
  if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return
  const el = e.target
  if (el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.tagName === 'SELECT' || el?.isContentEditable) return
  e.preventDefault()
  searchInput.value?.focus()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

function clearSearch() {
  searchQuery.value = ''
  page.value = 1
}

function clearAllFilters() {
  searchQuery.value = ''
  statusFilter.value = ''
  categoryFilter.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  page.value = 1
}
</script>

<style scoped>
.page-header-actions { display: flex; gap: 0.6rem; align-items: center; flex-shrink: 0; }

.drafts-list { display: flex; flex-direction: column; gap: 0.6rem; max-height: 60vh; overflow-y: auto; }
.draft-item {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  background: var(--accent); border-radius: var(--radius-sm); padding: 0.6rem 0.9rem;
}
.draft-info { display: flex; flex-direction: column; gap: 0.15rem; min-width: 0; }
.draft-item-title { font-weight: 700; font-size: 0.88rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.draft-item-meta { font-size: 0.74rem; color: var(--text-muted); }
.draft-actions { display: flex; gap: 0.4rem; flex-shrink: 0; }
/* margin-right:auto keeps the note left while the footer's flex-end pushes the
   button right, the same trick the submit form uses for its saved hint. */
.drafts-note { margin: 0 auto 0 0; align-self: center; font-size: 0.74rem; color: var(--text-muted); }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.search-wrapper {
  flex: 1;
  position: relative;
  min-width: 200px;
}

.search-wrapper .form-control {
  padding-right: 32px;
}

/* type="search" earns the right semantics and a better mobile keyboard, but
   WebKit draws its own clear button that would land on top of ours. */
.search-wrapper input[type="search"]::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}

.search-clear {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 0;
  line-height: 1;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 18px;
  font-weight: bold;
  transition: color var(--transition);
}

.search-clear:hover {
  color: var(--text);
}

.filter-select {
  min-width: 140px;
}

.date-range {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.date-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}

.date-input {
  width: auto;
  min-width: 140px;
}

.date-preset {
  background: var(--stone);
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 100px;
  padding: 0.32rem 0.7rem;
  font-size: 0.74rem;
  font-weight: 700;
  transition: background var(--transition), color var(--transition), border-color var(--transition);
}

.date-preset:hover {
  background: var(--accent);
  color: var(--accent-foreground);
}

.date-preset.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.clear-filters {
  white-space: nowrap;
}

.filter-info {
  background: var(--accent);
  border-left: 4px solid var(--primary);
  padding: 8px 12px;
  margin-bottom: 16px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--accent-foreground);
}

.result-count {
  font-weight: 500;
}

.th-sortable {
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  transition: color var(--transition);
}
.th-sortable:hover { color: var(--primary); }

.sort-caret {
  font-size: 0.6em;
  margin-left: 0.25rem;
  opacity: 0;
  transition: opacity var(--transition);
}
/* The inactive caret only appears on hover, so the header row isn't a wall of
   arrows while still hinting that columns are clickable. */
.th-sortable:hover .sort-caret { opacity: 0.45; }
.sort-caret.on { opacity: 1; }

.cmp-id { font-family: var(--font-mono); font-size: 0.8rem; background: var(--accent); color: var(--accent-foreground); padding: 0.1rem 0.35rem; border-radius: 4px; }
.cat-text { font-size: 0.8rem; font-weight: 600; color: var(--primary); text-transform: capitalize; }
.td-title { max-width: 220px; }
.title-with-thumb { display: flex; align-items: center; gap: 0.6rem; }
.title-with-thumb span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 160px; }
.thumb { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; flex-shrink: 0; border: 1px solid var(--border); }
.action-btns { display: flex; gap: 0.35rem; }

@media (max-width: 640px) {
  .page-header-actions {
    width: 100%;
    flex-direction: column;
  }
  .page-header-actions .btn { width: 100%; }

  .filter-bar {
    flex-direction: column;
  }

  .search-wrapper,
  .filter-select,
  .date-range {
    width: 100%;
  }

  .date-label {
    flex: 1;
  }

  .date-input {
    width: 100%;
    min-width: 0;
  }

  .filter-info {
    font-size: 12px;
  }
}
</style>
