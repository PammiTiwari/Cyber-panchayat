<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="All Complaints" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Browse every complaint in the city — upvote one you've faced too instead of filing a duplicate</p>
          </div>
        </div>

        <div class="card">
          <div class="filter-bar">
            <input
              v-model="search"
              type="search"
              class="form-control"
              placeholder="🔍 Search by ID, title, or location..."
            />
            <select v-model="categoryFilter" class="form-control filter-select">
              <option value="">All Categories</option>
              <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
            </select>
            <select v-model="statusFilter" class="form-control filter-select">
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="assigned">Assigned</option>
              <option value="reassigned">Reassigned</option>
              <option value="in_progress">In Progress</option>
              <option value="on_hold_weather">On Hold - Weather</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
            <select v-model="wardFilter" class="form-control filter-select">
              <option value="">All Wards</option>
              <option v-for="w in WARDS" :key="w" :value="w">{{ w }}</option>
            </select>
            <button
              class="btn btn-sm"
              :class="myUpvotedOnly ? 'btn-primary' : 'btn-outline'"
              @click="myUpvotedOnly = !myUpvotedOnly"
            >👍 My Upvoted</button>
            <button v-if="hasActiveFilters" class="btn btn-outline btn-sm" @click="clearFilters">Clear</button>
          </div>

          <SkeletonLoader v-if="loading" type="table" :count="5" />
          <EmptyState
            v-else-if="!filtered.length"
            type="search"
            title="No Complaints Found"
            :description="complaints.length ? 'No complaints match your filters.' : 'No complaints have been raised yet.'"
            buttonText="Clear Filters"
            @action="clearFilters"
          />
          <div v-else class="complaint-list">
            <div v-for="c in paged" :key="c.id" class="complaint-card" @click="selectedComplaint = c">
              <div class="complaint-main">
                <div class="complaint-head">
                  <code class="cmp-id">{{ c.cmp_id }}</code>
                  <span class="cat-text">{{ c.category }}</span>
                  <span :class="['badge', `badge-${c.status}`]">{{ fmtStatus(c.status) }}</span>
                </div>
                <p class="complaint-title">{{ c.title }}</p>
                <p class="complaint-desc">{{ c.description }}</p>
                <div class="complaint-meta">
                  <span v-if="c.address">📍 {{ c.address }}</span>
                  <span v-if="c.ward">{{ c.ward }}</span>
                  <span>{{ fmtDate(c.created_at) }}</span>
                  <span v-if="c.image_urls?.length">🖼 {{ c.image_urls.length }}</span>
                </div>
              </div>
              <div v-if="!['resolved', 'closed'].includes(c.status)" class="complaint-upvote" @click.stop>
                <button
                  v-if="!c.is_own"
                  class="btn btn-xs"
                  :class="c.upvoted_by_me ? 'btn-success' : 'btn-outline'"
                  :disabled="c.busy"
                  @click="toggleUpvote(c)"
                >
                  👍 {{ c.upvoted_by_me ? 'Supported' : '+1 Me too' }}
                </button>
                <span v-else class="own-label">Your complaint</span>
                <span class="upvote-count">{{ c.upvotes_count || 0 }} {{ c.upvotes_count === 1 ? 'upvote' : 'upvotes' }}</span>
              </div>
            </div>
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

    <!-- Detail view — everything about the complaint except who filed it -->
    <div v-if="selectedComplaint" class="modal-overlay" @click.self="selectedComplaint = null">
      <div class="modal modal-lg">
        <div class="modal-header">
          <h2>{{ selectedComplaint.cmp_id }} — Complaint Details</h2>
          <button class="modal-close" aria-label="Close" @click="selectedComplaint = null">✕</button>
        </div>

        <div class="flex gap-2 mb-4">
          <span :class="['badge', `badge-${selectedComplaint.status}`]">{{ fmtStatus(selectedComplaint.status) }}</span>
          <span :class="['badge', `badge-${selectedComplaint.priority}`]">{{ selectedComplaint.priority }}</span>
        </div>

        <h3 class="detail-title">{{ selectedComplaint.title }}</h3>

        <div class="detail-row"><div class="detail-label">Category</div><div class="detail-value capitalize">{{ selectedComplaint.category }}</div></div>
        <div class="detail-row"><div class="detail-label">Department</div><div class="detail-value">{{ selectedComplaint.department }}</div></div>
        <div class="detail-row" v-if="selectedComplaint.assignment">
          <div class="detail-label">Assigned To</div>
          <div class="detail-value">
            {{ selectedComplaint.assignment.staff_name }}
            <span v-if="selectedComplaint.assignment.staff_department" class="text-muted"> ({{ selectedComplaint.assignment.staff_department }})</span>
          </div>
        </div>
        <div class="detail-row" v-if="selectedComplaint.ward"><div class="detail-label">Ward</div><div class="detail-value">{{ selectedComplaint.ward }}</div></div>
        <div class="detail-row"><div class="detail-label">Location</div><div class="detail-value">{{ selectedComplaint.address }}</div></div>
        <div class="detail-row"><div class="detail-label">Description</div><div class="detail-value">{{ selectedComplaint.description }}</div></div>
        <div class="detail-row" v-if="selectedComplaint.image_urls?.length">
          <div class="detail-label">Photos</div>
          <div class="detail-value"><ImageGallery :images="selectedComplaint.image_urls" alt="Complaint photo" /></div>
        </div>
        <div class="detail-row" v-if="selectedComplaint.evidence_urls?.length">
          <div class="detail-label">Resolution Evidence</div>
          <div class="detail-value"><ImageGallery :images="selectedComplaint.evidence_urls" alt="Resolution evidence photo" /></div>
        </div>
        <div class="detail-row"><div class="detail-label">Submitted On</div><div class="detail-value">{{ fmtDate(selectedComplaint.created_at) }}</div></div>
        <div class="detail-row" v-if="selectedComplaint.resolved_at"><div class="detail-label">Resolved On</div><div class="detail-value">{{ fmtDate(selectedComplaint.resolved_at) }}</div></div>

        <div class="modal-footer">
          <button
            v-if="!['resolved', 'closed'].includes(selectedComplaint.status) && !selectedComplaint.is_own"
            class="btn btn-sm"
            :class="selectedComplaint.upvoted_by_me ? 'btn-success' : 'btn-outline'"
            :disabled="selectedComplaint.busy"
            @click="toggleUpvote(selectedComplaint)"
          >
            👍 {{ selectedComplaint.upvoted_by_me ? 'Supported' : '+1 Me too' }}
            ({{ selectedComplaint.upvotes_count || 0 }} {{ selectedComplaint.upvotes_count === 1 ? 'upvote' : 'upvotes' }})
          </button>
          <span
            v-else-if="!['resolved', 'closed'].includes(selectedComplaint.status)"
            class="own-label"
          >This is your complaint ({{ selectedComplaint.upvotes_count || 0 }} {{ selectedComplaint.upvotes_count === 1 ? 'upvote' : 'upvotes' }})</span>
          <button class="btn btn-secondary" @click="selectedComplaint = null">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * AllComplaints — every citizen's complaints in one read-only, upvotable feed.
 * Whoever filed a complaint is not shown here (see /requests/community); a
 * citizen can only browse, filter, and back an existing complaint with an
 * upvote instead of raising a duplicate — no edit/delete/comment ability.
 */
import { ref, computed, onMounted, watch } from 'vue'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import SkeletonLoader from '../../components/SkeletonLoader.vue'
import EmptyState from '../../components/EmptyState.vue'
import ImageGallery from '../../components/ImageGallery.vue'
import api from '../../api'
import { fmtStatus } from '../../utils/status'
import { useDebouncedValue } from '../../composables/useDebounce'

const CATEGORIES = ['road', 'water', 'electricity', 'sanitation', 'waste', 'parks', 'complaint', 'maintenance', 'other']
const WARDS = ['Ward-1', 'Ward-2', 'Ward-3', 'Central']

const loading = ref(true)
const complaints = ref([])
const selectedComplaint = ref(null)

const search = ref('')
const debouncedSearch = useDebouncedValue(search, 300)
const categoryFilter = ref('')
const statusFilter = ref('')
const wardFilter = ref('')
const myUpvotedOnly = ref(false)
const hasActiveFilters = computed(() => !!(search.value || categoryFilter.value || statusFilter.value || wardFilter.value || myUpvotedOnly.value))
function clearFilters() {
  search.value = ''
  categoryFilter.value = ''
  statusFilter.value = ''
  wardFilter.value = ''
  myUpvotedOnly.value = false
}

onMounted(async () => {
  try {
    const res = await api.get('/requests/community')
    complaints.value = res.data.map(c => ({ ...c, busy: false }))
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

const filtered = computed(() => {
  let list = complaints.value
  if (categoryFilter.value) list = list.filter(c => c.category === categoryFilter.value)
  if (statusFilter.value) list = list.filter(c => c.status === statusFilter.value)
  if (wardFilter.value) list = list.filter(c => c.ward === wardFilter.value)
  if (myUpvotedOnly.value) list = list.filter(c => c.upvoted_by_me)
  if (debouncedSearch.value.trim()) {
    const q = debouncedSearch.value.trim().toLowerCase()
    list = list.filter(c => c.cmp_id?.toLowerCase().includes(q) || c.title?.toLowerCase().includes(q) || c.address?.toLowerCase().includes(q))
  }
  return list
})

const page = ref(1)
const perPage = 10
const totalPages = computed(() => Math.ceil(filtered.value.length / perPage))
const paged = computed(() => {
  const start = (page.value - 1) * perPage
  return filtered.value.slice(start, start + perPage)
})
watch([categoryFilter, statusFilter, wardFilter, myUpvotedOnly, debouncedSearch], () => { page.value = 1 })

async function toggleUpvote(c) {
  c.busy = true
  try {
    const { data } = await api.post(`/requests/${c.id}/upvote`)
    c.upvoted_by_me = data.upvoted
    c.upvotes_count = data.upvotes_count
  } catch (e) {
    console.error(e)
  } finally {
    c.busy = false
  }
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.filter-select { min-width: 160px; }
.complaint-list { display: flex; flex-direction: column; gap: 0.75rem; }
.complaint-card {
  display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;
  padding: 1rem 1.25rem; border: 1px solid var(--border); border-radius: var(--radius);
  cursor: pointer; transition: box-shadow var(--transition), border-color var(--transition), transform var(--transition);
}
.complaint-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: var(--primary); transform: translateY(-2px); }
.detail-title { font-size: 1.05rem; font-weight: 800; color: var(--navy); margin-bottom: 1rem; }
.complaint-main { flex: 1; min-width: 0; }
.complaint-head { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.4rem; flex-wrap: wrap; }
.cmp-id { font-family: var(--font-mono); font-size: 0.75rem; background: var(--accent); color: var(--accent-foreground); padding: 0.1rem 0.4rem; border-radius: 4px; }
.cat-text { font-size: 0.78rem; font-weight: 700; color: var(--primary); text-transform: capitalize; }
.complaint-title { font-size: 0.92rem; font-weight: 700; color: var(--text); margin-bottom: 0.2rem; }
.complaint-desc { font-size: 0.82rem; color: var(--text-muted); line-height: 1.5; margin-bottom: 0.5rem; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.complaint-meta { display: flex; gap: 0.9rem; flex-wrap: wrap; font-size: 0.75rem; color: var(--text-muted); }
.complaint-upvote { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; flex-shrink: 0; }
.upvote-count { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); }
.own-label { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); font-style: italic; }
</style>
