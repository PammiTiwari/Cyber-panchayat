<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Announcements" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Official notices and updates from city administration</p>
          </div>
          <button v-if="auth.isAdmin" class="btn btn-primary" @click="showCreateAnn = true">+ Post Announcement</button>
        </div>

        <div class="filter-bar">
          <input v-model="search" class="form-control" placeholder="Search announcements..." />
          <select v-model="categoryFilter" class="form-control filter-select">
            <option value="">All Categories</option>
            <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
          <select v-model="wardFilter" class="form-control filter-select">
            <option value="">All Wards</option>
            <option v-for="w in WARDS" :key="w" :value="w">{{ w }}</option>
          </select>
          <button v-if="hasActiveFilters" class="btn btn-outline btn-sm" @click="clearFilters">Clear</button>
        </div>

        <div v-if="loading" class="spinner"></div>
        <div v-else class="announcements-list">
          <div v-if="!filteredPosts.length" class="empty-state">
            <div class="empty-icon">&#9993;</div>
            <p>{{ posts.length ? 'No announcements match your filters' : 'No announcements at this time' }}</p>
          </div>
          <div v-for="post in pagedPosts" :key="post.id" class="announcement-card card">
            <div class="ann-icon">&#9993;</div>
            <div class="ann-body">
              <div class="ann-header">
                <h3 class="ann-title">{{ post.title || 'Official Announcement' }}</h3>
                <span class="badge badge-official">Official</span>
                <div class="ann-header-right">
                  <span v-if="post.topic" class="ann-topic">{{ fmtCategory(post.topic) }}</span>
                  <button v-if="auth.isAdmin" class="ann-delete-btn" aria-label="Delete announcement" title="Delete announcement" @click="deleteAnnouncement(post)">&#128465;</button>
                </div>
              </div>
              <p class="ann-content">{{ post.content }}</p>
              <ImageGallery v-if="post.image_urls?.length" :images="post.image_urls" alt="Announcement image" />
              <div class="ann-footer">
                <span class="ann-date">{{ fmtDate(post.created_at) }}</span>
                <div class="ann-meta">
                  <span class="ann-by">By Preetam Nagar Admin</span>
                  <span class="ann-location" v-if="post.location">&#9679; {{ post.location }}</span>
                </div>
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

    <!-- Create Announcement Modal (admin only) -->
    <div v-if="showCreateAnn" class="modal-overlay" @click.self="showCreateAnn = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Post Official Announcement</h2>
          <button class="modal-close" aria-label="Close" @click="showCreateAnn = false">&#x2715;</button>
        </div>
        <div v-if="annError" class="alert alert-error">{{ annError }}</div>
        <div class="form-group">
          <label>Title</label>
          <input v-model="annForm.title" class="form-control" placeholder="Announcement title" />
        </div>
        <div class="form-group">
          <label>Content</label>
          <textarea v-model="annForm.content" class="form-control" rows="4" placeholder="Write announcement content..."></textarea>
        </div>
        <div class="form-group">
          <label>Category</label>
          <select v-model="annForm.topic" class="form-control">
            <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Location / Area</label>
          <!-- The "(Ward-N)" shape is not decoration: wardFromLocation parses
               it to auto-fill the ward below, same pattern as the community
               feed's create-post form. -->
          <input v-model="annForm.location" class="form-control" placeholder="e.g. All Wards, Ward-1, etc." />
        </div>
        <div class="form-group">
          <label>Ward <span class="optional-label">(optional)</span></label>
          <select v-model="annForm.ward" class="form-control" @change="onAnnWardSelected">
            <option value="">Not specified</option>
            <option v-for="w in WARDS" :key="w" :value="w">{{ w }}</option>
          </select>
        </div>
        <div class="form-group">
          <label>Pin location on map <span class="optional-label">(optional)</span></label>
          <LocationPicker @located="onAnnLocated" />
        </div>
        <div class="form-group">
          <label>Photos <span class="optional-label">(optional)</span></label>
          <MultiImageUpload v-model="annForm.image_urls" :max="3" />
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showCreateAnn = false">Cancel</button>
          <button class="btn btn-primary" @click="createAnnouncement" :disabled="annPosting">
            {{ annPosting ? 'Posting...' : 'Post Announcement' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * AnnouncementsView Component
 * Displays official announcements from city administration.
 * Allows admins to create and delete announcements; citizens can view all announcements.
 * Supports title, content, location, and multiple image attachments.
 */
import { ref, computed, onMounted, watch } from 'vue'
import AppSidebar from '../components/AppSidebar.vue'
import AppTopbar from '../components/AppTopbar.vue'
import ImageGallery from '../components/ImageGallery.vue'
import MultiImageUpload from '../components/MultiImageUpload.vue'
import LocationPicker from '../components/LocationPicker.vue'
import { CATEGORIES, WARDS, DEFAULT_CATEGORY, fmtCategory, wardFromLocation } from '../utils/postFilters'
import { useAuthStore } from '../stores/auth'
import { useDebouncedValue } from '../composables/useDebounce'
import api from '../api'
import { useToast } from '../composables/useToast'

const { error: toastError } = useToast()

const auth = useAuthStore()

// View state
const loading = ref(true)
const posts = ref([])

// Filters
const search = ref('')
const debouncedSearch = useDebouncedValue(search, 300)
const categoryFilter = ref('')
const wardFilter = ref('')
const hasActiveFilters = computed(() => !!(search.value || categoryFilter.value || wardFilter.value))
function clearFilters() {
  search.value = ''
  categoryFilter.value = ''
  wardFilter.value = ''
}
const filteredPosts = computed(() => {
  let list = posts.value
  if (categoryFilter.value) list = list.filter(p => p.topic === categoryFilter.value)
  if (wardFilter.value) list = list.filter(p => p.ward === wardFilter.value)
  if (debouncedSearch.value.trim()) {
    const q = debouncedSearch.value.trim().toLowerCase()
    list = list.filter(p => p.title?.toLowerCase().includes(q) || p.content?.toLowerCase().includes(q))
  }
  return list
})

// Pagination — client-side, since all announcements are already fetched in
// one shot (no server-side page/limit for this endpoint).
const page = ref(1)
const perPage = 10
const totalPages = computed(() => Math.ceil(filteredPosts.value.length / perPage))
const pagedPosts = computed(() => {
  const start = (page.value - 1) * perPage
  return filteredPosts.value.slice(start, start + perPage)
})
watch([categoryFilter, wardFilter, debouncedSearch], () => { page.value = 1 })

// Modal and form state (admin only)
const showCreateAnn = ref(false)
const annForm = ref({ title: '', content: '', location: '', ward: '', topic: DEFAULT_CATEGORY, image_urls: [] })
const annPosting = ref(false)
const annError = ref('')

// Fetch announcements on mount
onMounted(async () => {
  await loadAnnouncements()
})

/**
 * Load announcements from backend.
 * Fetches all posts with category='announcement'.
 */
async function loadAnnouncements() {
  loading.value = true
  try {
    const res = await api.get('/posts?category=announcement')
    posts.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

/**
 * Fill in the Location / Area field from a map pin, without overwriting
 * whatever the admin may have already typed there.
 */
function onAnnLocated({ address }) {
  if (address && !annForm.value.location) annForm.value.location = address
}

// Same two-way ward/location sync as the community feed's create-post form:
// picking a ward tags the location text with "(Ward-N)", and typing a
// location that already ends in "(Ward-N)" auto-fills the ward dropdown.
const wardAutoFilled = ref(false)

function onAnnWardSelected() {
  wardAutoFilled.value = false
  const w = annForm.value.ward
  const base = annForm.value.location.replace(/\s*\([^()]*\)\s*$/, '').trim()
  annForm.value.location = w ? `${base}${base ? ' ' : ''}(${w})` : base
}

watch(() => annForm.value.location, (loc) => {
  const w = wardFromLocation(loc)
  if (w) {
    annForm.value.ward = w
    wardAutoFilled.value = true
  } else if (wardAutoFilled.value) {
    annForm.value.ward = ''
    wardAutoFilled.value = false
  }
})

/**
 * Create new announcement (admin only).
 * Validates content is not empty, posts to /posts endpoint, and resets form.
 * Newly created announcement appears at top of list.
 */
async function createAnnouncement() {
  if (annPosting.value) return // Prevent duplicate submissions
  if (!annForm.value.content.trim()) { annError.value = 'Content required'; return }
  annPosting.value = true
  annError.value = ''
  try {
    const res = await api.post('/posts', {
      title: annForm.value.title,
      content: annForm.value.content,
      location: annForm.value.location,
      ward: annForm.value.ward,
      topic: annForm.value.topic,
      image_urls: annForm.value.image_urls,
      category: 'announcement',
    })
    posts.value.unshift(res.data) // Add to top of list
    showCreateAnn.value = false
    annForm.value = { title: '', content: '', location: '', ward: '', topic: DEFAULT_CATEGORY, image_urls: [] }
  } catch (e) {
    annError.value = e.response?.data?.message || 'Failed to post'
  } finally {
    annPosting.value = false
  }
}

/**
 * Delete announcement by ID (admin only).
 * Requires user confirmation before deletion.
 */
async function deleteAnnouncement(post) {
  if (!confirm('Delete this announcement?')) return
  try {
    await api.delete(`/posts/${post.id}`)
    posts.value = posts.value.filter(p => p.id !== post.id)
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to delete')
  }
}

/**
 * Format date to Indian locale string.
 * Timezone: Asia/Kolkata
 */
function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'long', year: 'numeric' })
}
</script>

<style scoped>
.announcements-list { display: flex; flex-direction: column; gap: 1rem; max-width: 760px; }
.announcement-card { display: flex; gap: 1rem; align-items: flex-start; padding: 1.25rem 1.5rem; }
.ann-icon {
  width: 40px; height: 40px; background: #D7F5E5; color: #0E7A4F;
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; flex-shrink: 0;
}
.ann-body { flex: 1; }
.ann-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem; }
.ann-title { font-size: 0.95rem; font-weight: 700; color: #5C1A41; }
.ann-header-right { margin-left: auto; display: flex; align-items: center; gap: 0.6rem; flex-shrink: 0; }
.ann-delete-btn { background: #FFE9F2; border: none; font-size: 1rem; color: #C23A72; cursor: pointer; padding: 0.35rem 0.55rem; border-radius: 6px; flex-shrink: 0; line-height: 1; }
.ann-delete-btn:hover { background: #FF2D6F; color: #fff; }
.ann-content { font-size: 0.875rem; color: #9B2C6F; line-height: 1.65; margin-bottom: 0.75rem; }
.ann-footer { display: flex; flex-direction: column; align-items: flex-start; gap: 0.4rem; }
.ann-meta { display: flex; gap: 0.5rem 0.75rem; align-items: center; flex-wrap: wrap; }
.ann-location { font-size: 0.78rem; color: #B0708F; }
.ann-topic {
  background: #FFE9F2; color: #9B2C6F;
  border-radius: 100px; padding: 0.15rem 0.6rem;
  font-size: 0.68rem; font-weight: 700;
}
.ann-date { font-size: 0.75rem; color: #D69AB8; }
.ann-by { font-size: 0.75rem; font-weight: 600; color: #9B2C6F; background: #FFE9F2; padding: 0.1rem 0.5rem; border-radius: 100px; }
.optional-label { font-weight: 400; color: #D69AB8; }
</style>
