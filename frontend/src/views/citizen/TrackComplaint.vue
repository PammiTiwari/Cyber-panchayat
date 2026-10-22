<template>
  <div class="track-page">
    <!-- Which layout to show depends on which route got us here — not on
         whether a login session happens to exist — so the landing page's
         Track Complaint link is always the plain public page, even if an
         old session token is still sitting in localStorage. -->
    <div v-if="route.name === 'track-public'" class="public-track">
      <router-link to="/" class="back-home">← Back to Home</router-link>
      <div class="track-content">
        <div v-if="!result" class="track-card">
          <h2 class="track-title">Track Your Complaint</h2>
          <p class="track-sub">Enter your complaint ID to check the status</p>
          <SearchSection @found="setResult" />
        </div>
        <TrackResultCard v-else :result="result" @close="result = null" />
      </div>
    </div>

    <!-- Logged-in layout -->
    <div v-else class="app-layout">
      <AppSidebar />
      <div class="main-content">
        <AppTopbar title="Track Complaint" />
        <div class="content-area">
          <div class="page-header">
            <div class="page-header-left">
              <p>Enter your complaint ID to check the current status</p>
            </div>
          </div>
          <div v-if="!result" class="card modal-w-xl">
            <SearchSection @found="setResult" />
          </div>

          <!-- Browsing by keyword/status/category is only offered once signed
               in — it reads this citizen's own complaint list (GET /requests),
               unlike the ID box above which hits the public, unauthenticated
               /track endpoint for exactly one complaint. -->
          <div v-if="!result" class="card mt-4 browse-section">
            <div class="browse-header">
              <span class="browse-header-icon">🗂️</span>
              <div>
                <div class="browse-header-title">Or browse your complaints</div>
                <p class="browse-header-sub">Don't remember the ID? Search or filter instead.</p>
              </div>
            </div>

            <div class="browse-search-wrap">
              <span class="browse-search-icon">🔍</span>
              <input
                v-model="browseSearch"
                type="search"
                class="browse-search-input"
                placeholder="Search by title, category, or location..."
              />
            </div>
            <div class="browse-pills">
              <select v-model="browseStatus" class="browse-pill-select">
                <option value="">Status: All</option>
                <option value="pending">Pending</option>
                <option value="assigned">Assigned</option>
                <option value="in_progress">In Progress</option>
                <option value="on_hold_weather">On Hold - Weather</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
              <select v-model="browseCategory" class="browse-pill-select">
                <option value="">Category: All</option>
                <option value="road">🛣️ Road</option>
                <option value="water">💧 Water</option>
                <option value="electricity">⚡ Electricity</option>
                <option value="sanitation">🧹 Sanitation</option>
                <option value="waste">🗑️ Waste</option>
                <option value="parks">🌳 Parks & Public Spaces</option>
                <option value="maintenance">🔧 Maintenance</option>
                <option value="other">📌 Other</option>
              </select>
            </div>

            <SkeletonLoader v-if="browseLoading" type="list" :count="3" />
            <EmptyState
              v-else-if="!browseFiltered.length"
              type="search"
              title="No Matching Complaints"
              description="Try a different keyword or clear a filter."
            />
            <transition-group v-else name="browse-row" tag="div" class="browse-list">
              <button
                v-for="r in browseFiltered.slice(0, 8)"
                :key="r.id"
                type="button"
                class="browse-row"
                @click="setResult(r)"
              >
                <span class="browse-row-icon">{{ categoryIcon(r.category) }}</span>
                <div class="browse-row-main">
                  <div class="browse-row-title">{{ r.title }}</div>
                  <code class="cmp-id">{{ r.cmp_id }}</code>
                </div>
                <span :class="['badge', `badge-${r.status}`]">{{ fmtStatus(r.status) }}</span>
                <span class="browse-row-arrow">›</span>
              </button>
              <p v-if="browseFiltered.length > 8" key="more" class="browse-more">
                + {{ browseFiltered.length - 8 }} more — refine your search to narrow it down
              </p>
            </transition-group>
          </div>

          <TrackResultCard v-else :result="result" @close="result = null" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Track Complaint - Public complaint status lookup (no login required)
 * Citizens can search by complaint ID to view status, assignment, and resolution details
 * Dual layout: public page (for anonymous users) or authenticated sidebar view (for logged-in citizens)
 */
import { ref, computed, defineComponent, h, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import TrackResultCard from '../../components/TrackResultCard.vue'
import EmptyState from '../../components/EmptyState.vue'
import SkeletonLoader from '../../components/SkeletonLoader.vue'
import { useDebouncedValue } from '../../composables/useDebounce'
import { fmtStatus } from '../../utils/status'
import api from '../../api'

const route = useRoute()
const result = ref(null) // Result of complaint search

function setResult(r) { result.value = r }

// Browse-by-keyword section (authenticated view only, see template).
const browseRequests = ref([])
const browseLoading = ref(true)
const browseSearch = ref('')
const debouncedBrowseSearch = useDebouncedValue(browseSearch, 300)
const browseStatus = ref('')
const browseCategory = ref('')

onMounted(async () => {
  if (route.name === 'track-public') return
  try {
    const res = await api.get('/requests')
    browseRequests.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    browseLoading.value = false
  }
})

const CATEGORY_ICONS = {
  road: '🛣️', water: '💧', electricity: '⚡', sanitation: '🧹',
  waste: '🗑️', parks: '🌳', maintenance: '🔧', other: '📌',
}
function categoryIcon(category) {
  return CATEGORY_ICONS[category] || '📌'
}

const browseFiltered = computed(() => {
  let list = browseRequests.value
  if (debouncedBrowseSearch.value) {
    const q = debouncedBrowseSearch.value.toLowerCase()
    list = list.filter(r =>
      r.cmp_id?.toLowerCase().includes(q) ||
      r.title?.toLowerCase().includes(q) ||
      r.category?.toLowerCase().includes(q) ||
      r.address?.toLowerCase().includes(q)
    )
  }
  if (browseStatus.value) list = list.filter(r => r.status === browseStatus.value)
  if (browseCategory.value) list = list.filter(r => r.category === browseCategory.value)
  return list
})

/**
 * Inline search component - searchable without authentication
 * Searches for complaint by ID (/track endpoint does NOT require login)
 * Supports Enter key for submission
 */
const SearchSection = defineComponent({
  emits: ['found'],
  setup(_, { emit }) {
    const cmpId = ref('')
    const loading = ref(false)
    const error = ref('')

    /**
     * Search for complaint by ID and emit result to parent
     * ID is uppercased for consistency with complaint ID format
     */
    async function search() {
      error.value = ''
      if (!cmpId.value.trim()) { error.value = 'Please enter a complaint ID'; return }
      loading.value = true
      try {
        const res = await api.get(`/track?id=${cmpId.value.trim().toUpperCase()}`)
        emit('found', res.data)
      } catch (e) {
        error.value = e.response?.data?.message || 'Complaint not found'
      } finally {
        loading.value = false
      }
    }

    return () => h('div', [
      error.value ? h('div', { class: 'alert alert-error', style: 'margin-bottom:1rem' }, error.value) : null,
      h('div', { style: 'display:flex; gap:0.75rem; align-items:flex-end' }, [
        h('div', { class: 'form-group', style: 'flex:1; margin:0' }, [
          h('label', { style: 'display:block; font-size:0.82rem; font-weight:600; margin-bottom:0.3rem' }, 'Complaint ID'),
          h('input', {
            class: 'form-control',
            placeholder: 'Enter Complaint ID (e.g. CMP0001)',
            value: cmpId.value,
            onInput: e => { cmpId.value = e.target.value },
            onKeydown: e => { if (e.key === 'Enter') search() },
          }),
        ]),
        h('button', {
          class: 'btn btn-primary',
          onClick: search,
          disabled: loading.value,
          style: 'flex-shrink:0; padding:0.55rem 1.25rem',
        }, loading.value ? 'Searching...' : 'Search'),
      ]),
    ])
  },
})
</script>

<style scoped>
.mt-4 { margin-top: 1.25rem; }
.browse-section {
  max-width: 720px;
  background: linear-gradient(180deg, var(--accent) 0%, var(--card) 140px);
}

.browse-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.1rem; }
.browse-header-icon {
  width: 42px; height: 42px; flex-shrink: 0; border-radius: 12px;
  background: var(--card); box-shadow: var(--shadow);
  display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
}
.browse-header-title { font-family: var(--font-heading); font-size: 1.1rem; font-weight: 700; color: var(--text); }
.browse-header-sub { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.1rem; }

.browse-search-wrap { position: relative; margin-bottom: 0.65rem; }
.browse-search-icon {
  position: absolute; left: 1rem; top: 50%; transform: translateY(-50%);
  font-size: 0.95rem; pointer-events: none; opacity: 0.6;
}
.browse-search-input {
  width: 100%; padding: 0.7rem 1rem 0.7rem 2.6rem;
  border: 1.5px solid var(--border); border-radius: 100px;
  background: var(--card); font-size: 0.9rem; color: var(--text);
  transition: border-color var(--transition), box-shadow var(--transition);
}
.browse-search-input:focus {
  outline: none; border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(0, 82, 255, 0.12);
}

.browse-pills { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1.1rem; }
.browse-pill-select {
  flex: 1; min-width: 150px; padding: 0.5rem 0.9rem;
  border: 1.5px solid var(--border); border-radius: 100px;
  background: var(--card); font-size: 0.82rem; font-weight: 600; color: var(--text-muted);
  cursor: pointer; transition: border-color var(--transition), color var(--transition);
}
.browse-pill-select:focus { outline: none; border-color: var(--primary); color: var(--text); }

.browse-list { display: flex; flex-direction: column; gap: 0.5rem; }
.browse-row {
  display: flex; align-items: center; gap: 0.85rem;
  width: 100%; text-align: left; background: var(--card); border: 1.5px solid var(--border);
  border-radius: var(--radius-sm); padding: 0.75rem 1rem; cursor: pointer;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
}
.browse-row:hover {
  border-color: var(--primary); transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(0, 82, 255, 0.12);
}
.browse-row-icon {
  width: 34px; height: 34px; flex-shrink: 0; border-radius: 10px;
  background: var(--accent); display: flex; align-items: center; justify-content: center;
  font-size: 1rem;
}
.browse-row-main { flex: 1; min-width: 0; }
.browse-row-title {
  font-size: 0.88rem; font-weight: 600; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cmp-id { font-family: monospace; font-size: 0.72rem; color: var(--text-muted); }
.browse-row-arrow { font-size: 1.2rem; color: var(--text-muted); flex-shrink: 0; }
.browse-more { font-size: 0.78rem; color: var(--text-muted); text-align: center; margin-top: 0.4rem; }

.browse-row-enter-active, .browse-row-leave-active { transition: opacity 0.2s, transform 0.2s; }
.browse-row-enter-from { opacity: 0; transform: translateY(4px); }
.browse-row-leave-to { opacity: 0; }

.public-track { min-height: 100vh; background: var(--bg); position: relative; }
.back-home {
  position: fixed;
  top: 1.25rem;
  left: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 999px;
  padding: 0.45rem 1rem;
  transition: all 0.15s;
  z-index: 10;
}
.back-home:hover {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.track-content { padding: 6rem 2rem 4rem; display: flex; justify-content: center; align-items: flex-start; }
.track-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 2rem; width: 100%; max-width: 540px; box-shadow: var(--shadow); }
.track-title { font-family: var(--font-heading); font-size: 1.5rem; font-weight: 400; color: var(--text); margin-bottom: 0.35rem; }
.track-sub { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 1.5rem; }
</style>
