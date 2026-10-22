<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Manage Facilities" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header flex-between">
          <div>
            <p>Add, edit and manage civic facilities available for booking</p>
          </div>
          <button class="btn btn-primary" @click="openAdd">+ Add Facility</button>
        </div>

        <div v-if="loading" class="spinner"></div>
        <template v-else>
          <!-- Same shape as the bar on Manage Bookings, and the .filter-bar /
               .filter-select classes are global, so this needs no new CSS and
               stays consistent with the rest of the admin pages. -->
          <div class="filter-bar">
            <input
              v-model="search"
              type="search"
              class="form-control"
              aria-label="Search facilities by name, type, ward or address"
              placeholder="Search by name, type, ward or address..."
            />
            <select v-model="typeFilter" class="form-control filter-select" aria-label="Filter by type">
              <option value="">Type: All</option>
              <option v-for="t in facilityTypes" :key="t" :value="t">{{ t }}</option>
            </select>
            <select v-model="wardFilter" class="form-control filter-select" aria-label="Filter by ward">
              <option value="">Ward: All</option>
              <option v-for="w in wards" :key="w" :value="w">{{ w }}</option>
            </select>
            <!-- Admin-only filter: this page lists inactive facilities too,
                 which citizens never see. -->
            <select v-model="statusFilter" class="form-control filter-select" aria-label="Filter by status">
              <option value="">Status: All</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
            <button
              v-if="hasActiveFilters"
              class="btn btn-outline btn-sm"
              @click="clearAllFilters"
            >
              Clear Filters
            </button>
          </div>

          <div v-if="hasActiveFilters" class="filter-info">
            <span class="result-count" aria-live="polite">
              {{ filtered.length }} facilit{{ filtered.length !== 1 ? 'ies' : 'y' }} found
            </span>
          </div>

          <div v-if="!filtered.length" class="empty-state">
            <div class="empty-icon">&#128269;</div>
            <p>No facilities match these filters</p>
            <button class="btn btn-sm btn-secondary" @click="clearAllFilters">Clear Filters</button>
          </div>

          <div v-else class="facilities-grid">
          <div v-for="f in filtered" :key="f.id" class="facility-card card">
            <ImageGallery v-if="f.image_urls?.length" :images="f.image_urls" alt="Facility photo" class="fac-gallery" />
            <div class="fac-top">
              <div>
                <span class="fac-type">{{ f.facility_type }}</span>
                <span :class="f.is_active ? 'status-active' : 'status-inactive'" class="ml-3">
                  {{ f.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <div class="text-sm text-muted">#{{ f.id }}</div>
            </div>
            <h3 class="fac-name">{{ f.name }}</h3>
            <div class="fac-details">
              <span>👥 {{ f.capacity }}</span>
              <span>📍 {{ f.ward }}</span>
              <span>{{ f.fee_per_hour > 0 ? `₹${f.fee_per_hour}/hr` : 'Free' }}</span>
            </div>
            <button
              v-if="f.rating_count > 0"
              type="button"
              class="fac-rating-row"
              :title="`See all ${f.rating_count} review${f.rating_count !== 1 ? 's' : ''} for ${f.name}`"
              :aria-label="`See all ${f.rating_count} review${f.rating_count !== 1 ? 's' : ''} for ${f.name}`"
              @click="openRatings(f)"
            >
              <StarRating :model-value="f.avg_rating" readonly size="sm" />
              <span class="rating-score">{{ f.avg_rating }}</span>
              <span class="rating-dot" aria-hidden="true">·</span>
              <span class="rating-summary">{{ f.rating_count }} review{{ f.rating_count !== 1 ? 's' : '' }}</span>
              <span class="rating-chevron" aria-hidden="true">&rsaquo;</span>
            </button>
            <div v-else class="fac-rating-row fac-rating-empty">
              <span class="rating-summary">No ratings yet</span>
            </div>
            <p class="fac-desc">{{ f.description }}</p>
            <div class="fac-actions">
              <button class="btn btn-outline btn-sm" @click="openEdit(f)">✏️ Edit</button>
              <button :class="`btn btn-sm ${f.is_active ? 'btn-warning' : 'btn-success'}`"
                      @click="toggleActive(f)">
                {{ f.is_active ? 'Deactivate' : 'Activate' }}
              </button>
            </div>
          </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Add / Edit modal -->
    <div v-if="modal.show" class="modal-overlay" @click.self="modal.show = false">
      <div class="modal modal-w-lg">
        <div class="modal-header">
          <h2>{{ modal.isEdit ? 'Edit Facility' : 'Add New Facility' }}</h2>
          <button class="modal-close" aria-label="Close" @click="modal.show = false">✕</button>
        </div>
        <div v-if="modal.error" class="alert alert-error mb-4">{{ modal.error }}</div>
        <form @submit.prevent="submitFacility" class="flex-col gap-4">
          <div class="grid-2">
            <div class="form-group col-span-full">
              <label>Facility Name *</label>
              <input v-model="form.name" type="text" class="form-control" required placeholder="e.g., City Community Hall" />
            </div>
            <div class="form-group">
              <label>Type *</label>
              <select v-model="form.facility_type" class="form-control" required>
                <option value="">Select type</option>
                <option v-for="t in facilityTypes" :key="t" :value="t">{{ t }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>Ward</label>
              <select v-model="form.ward" class="form-control">
                <option value="">Select Ward</option>
                <option v-for="w in wards" :key="w" :value="w">{{ w }}</option>
              </select>
            </div>
            <div class="form-group col-span-full">
              <label>Address *</label>
              <input v-model="form.address" type="text" class="form-control" required />
            </div>
            <div class="form-group">
              <label>Capacity *</label>
              <input v-model.number="form.capacity" type="number" class="form-control" required min="1" />
            </div>
            <div class="form-group">
              <label>Fee per Hour (₹) *</label>
              <input v-model.number="form.fee_per_hour" type="number" class="form-control" required min="50" step="50" />
            </div>
            <div class="form-group col-span-full">
              <label>Description</label>
              <textarea v-model="form.description" class="form-control" rows="2"></textarea>
            </div>
            <div class="form-group col-span-full">
              <label>Amenities <span class="text-xs text-muted">(comma-separated)</span></label>
              <input v-model="form.amenities" type="text" class="form-control" placeholder="AC, Parking, WiFi, Projector" />
            </div>
            <div class="form-group col-span-full">
              <label>Photos</label>
              <MultiImageUpload v-model="form.image_urls" :max="3" />
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline" @click="modal.show = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="modal.loading">
              {{ modal.loading ? 'Saving…' : (modal.isEdit ? 'Save Changes' : 'Add Facility') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Ratings modal: distribution + individual reviews -->
    <div v-if="ratingsModal.show" class="modal-overlay" @click.self="ratingsModal.show = false">
      <div class="modal modal-w-lg">
        <div class="modal-header">
          <h2>Ratings — {{ ratingsModal.facility?.name }}</h2>
          <button class="modal-close" aria-label="Close" @click="ratingsModal.show = false">✕</button>
        </div>

        <div v-if="ratingsModal.loading" class="spinner"></div>
        <template v-else-if="ratingsModal.data">
          <div class="rating-overview">
            <div class="rating-overview-score">{{ ratingsModal.data.avg }}</div>
            <div>
              <StarRating :model-value="ratingsModal.data.avg" readonly size="md" />
              <div class="rating-overview-count">{{ ratingsModal.data.count }} review{{ ratingsModal.data.count !== 1 ? 's' : '' }}</div>
            </div>
          </div>

          <div class="rating-distribution">
            <div v-for="n in [5,4,3,2,1]" :key="n" class="dist-row">
              <span class="dist-star">{{ n }} ⭐</span>
              <div class="dist-bar-track">
                <div class="dist-bar-fill" :style="{ width: distPercent(n) + '%' }"></div>
              </div>
              <span class="dist-count">{{ ratingsModal.data.distribution[n] }}</span>
            </div>
          </div>

          <div class="rating-divider"></div>

          <div v-if="!ratingsWithComments.length" class="empty-state">
            <p>No written reviews yet.</p>
          </div>
          <div v-else class="review-list">
            <div v-for="r in ratingsWithComments" :key="r.id" class="review-row">
              <div class="review-head">
                <strong>{{ r.citizen_name }}</strong>
                <StarRating :model-value="r.rating" readonly size="sm" />
              </div>
              <p class="review-comment">{{ r.comment }}</p>
            </div>
          </div>
        </template>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="ratingsModal.show = false">Close</button>
        </div>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
/**
 * Manage Facilities - CRUD for civic facilities available for citizen booking
 * Features: add, edit, activate/deactivate facilities
 * Facilities can be free or paid, with capacity and amenities
 * Citizens browse and book facilities that are marked active
 */
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import ImageGallery from "../../components/ImageGallery.vue"
import MultiImageUpload from "../../components/MultiImageUpload.vue"
import StarRating from "../../components/StarRating.vue"
import api from "../../api"
import { useDebouncedValue } from "../../composables/useDebounce"
import { useToast } from "../../composables/useToast"

const { error: toastError } = useToast()

const loading = ref(true)
const facilities = ref([]) // All facilities (active and inactive)
const showNotif = ref(false)
const unread = ref(0)
const facilityTypes = ["Community Hall","Sports Ground","Conference Room","Park","Auditorium","Library Hall","Swimming Pool","Other"]
const wards = ["Ward-1","Ward-2","Ward-3","Central"]

// Search and filters. The same two lists above feed both the add/edit form and
// these dropdowns, so a new facility type only has to be added in one place.
const search = ref("")
const debouncedSearch = useDebouncedValue(search, 300)
const typeFilter = ref("")
const wardFilter = ref("")
const statusFilter = ref("")

const filtered = computed(() => {
  let list = facilities.value

  const q = debouncedSearch.value.trim().toLowerCase()
  if (q) {
    list = list.filter(f =>
      [f.name, f.facility_type, f.ward, f.address]
        .some(v => v?.toLowerCase().includes(q))
    )
  }
  if (typeFilter.value) list = list.filter(f => f.facility_type === typeFilter.value)
  if (wardFilter.value) list = list.filter(f => f.ward === wardFilter.value)
  // Compared as a boolean rather than truthiness, so a facility saved without
  // the field is treated as inactive instead of silently matching neither.
  if (statusFilter.value) {
    const wantActive = statusFilter.value === "active"
    list = list.filter(f => Boolean(f.is_active) === wantActive)
  }

  return list
})

const hasActiveFilters = computed(() =>
  Boolean(search.value || typeFilter.value || wardFilter.value || statusFilter.value)
)

function clearAllFilters() {
  search.value = ""
  typeFilter.value = ""
  wardFilter.value = ""
  statusFilter.value = ""
}

const ratingsModal = ref({ show: false, facility: null, loading: false, data: null })
const ratingsWithComments = computed(() => (ratingsModal.value.data?.ratings || []).filter(r => r.comment))

async function openRatings(f) {
  ratingsModal.value = { show: true, facility: f, loading: true, data: null }
  try {
    const { data } = await api.get(`/facilities/${f.id}/ratings`)
    ratingsModal.value.data = data
  } finally {
    ratingsModal.value.loading = false
  }
}

function distPercent(star) {
  const d = ratingsModal.value.data
  if (!d || !d.count) return 0
  return Math.round((d.distribution[star] / d.count) * 100)
}

const modal = ref({ show: false, isEdit: false, facilityId: null, loading: false, error: "" })
const form = ref({ name: "", facility_type: "", address: "", ward: "", capacity: 50, fee_per_hour: 50, description: "", amenities: "", image_urls: [] })

onMounted(async () => {
  const [fRes, nRes] = await Promise.all([api.get("/facilities?active=false"), api.get("/notifications")])
  facilities.value = fRes.data
  unread.value = nRes.data.unread_count
  loading.value = false
})

function openAdd() {
  form.value = { name: "", facility_type: "", address: "", ward: "", capacity: 50, fee_per_hour: 50, description: "", amenities: "", image_urls: [] }
  modal.value = { show: true, isEdit: false, facilityId: null, loading: false, error: "" }
}

function openEdit(f) {
  form.value = { name: f.name, facility_type: f.facility_type, address: f.address, ward: f.ward || "",
                 capacity: f.capacity, fee_per_hour: f.fee_per_hour, description: f.description || "",
                 amenities: f.amenities || "", image_urls: f.image_urls || [] }
  modal.value = { show: true, isEdit: true, facilityId: f.id, loading: false, error: "" }
}

async function submitFacility() {
  if (modal.value.loading) return
  modal.value.loading = true
  modal.value.error = ""
  try {
    if (modal.value.isEdit) {
      const { data } = await api.put(`/facilities/${modal.value.facilityId}`, form.value)
      const idx = facilities.value.findIndex(f => f.id === modal.value.facilityId)
      if (idx !== -1) facilities.value[idx] = data
    } else {
      const { data } = await api.post("/facilities", form.value)
      facilities.value.unshift(data)
    }
    modal.value.show = false
  } catch (e) {
    modal.value.error = e.response?.data?.message || "Operation failed."
  } finally {
    modal.value.loading = false
  }
}

async function toggleActive(f) {
  try {
    await api.put(`/facilities/${f.id}`, { is_active: !f.is_active })
    f.is_active = !f.is_active
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to update facility')
  }
}
</script>

<style scoped>
.facilities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.25rem;
}
.facility-card { padding: 1.25rem; }
.fac-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.fac-type {
  font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
  background: var(--bg); color: var(--text-muted);
  padding: 0.2rem 0.6rem; border-radius: 100px; letter-spacing: 0.04em;
}
.status-active { color: var(--success); font-size: 0.78rem; font-weight: 700; }
.status-inactive { color: var(--danger); font-size: 0.78rem; font-weight: 700; }
.fac-name { font-size: 1rem; font-weight: 800; color: var(--navy); margin-bottom: 0.4rem; }
.fac-details { display: flex; gap: 0.85rem; font-size: 0.82rem; color: var(--text-muted); font-weight: 500; margin-bottom: 0.5rem; }
.fac-desc { font-size: 0.85rem; color: var(--text-muted); line-height: 1.4; margin-bottom: 1rem; }
.fac-actions { display: flex; gap: 0.5rem; }
textarea.form-control { resize: vertical; }
.fac-gallery.count-1 :deep(img) { max-height: 160px; }

/* Coloured with --accent, not --bg, on purpose. This card's decorative chips
   (.fac-type, amenities) are grey on muted text; the app's clickable pills
   (.filter-chip) are accent on accent-foreground. A grey pill here read as one
   more label sitting among labels. Accent puts it in the interactive family at
   a glance, before any hover, which is what touch users get. */
.fac-rating-row {
  display: inline-flex; align-items: center; gap: 0.45rem; margin-bottom: 0.6rem;
  background: var(--accent); border: 1px solid transparent; border-radius: 100px;
  padding: 0.3rem 0.75rem;
  cursor: pointer; text-align: left; width: fit-content; font-family: inherit;
  transition: background var(--transition), border-color var(--transition);
}
/* Scoped to button: the "No ratings yet" variant is a div and must stay inert. */
button.fac-rating-row:hover { background: rgba(0, 82, 255, 0.16); border-color: var(--primary); }
button.fac-rating-row:hover .rating-chevron { transform: translateX(2px); }
button.fac-rating-row:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.rating-score { font-size: 0.84rem; font-weight: 800; color: var(--accent-foreground); }
.rating-dot { color: var(--accent-foreground); opacity: 0.45; }
.fac-rating-row .rating-summary { color: var(--accent-foreground); }
/* An arrow says "this opens something" without spending a word on it. */
.rating-chevron {
  font-size: 1.05rem; font-weight: 700; line-height: 1;
  color: var(--accent-foreground);
  transition: transform var(--transition);
}
.fac-rating-row.fac-rating-empty {
  cursor: default; background: none; border-color: transparent; padding-left: 0;
}
.rating-summary { font-size: 0.82rem; font-weight: 600; color: var(--text-muted); }
.rating-overview { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
.rating-overview-score { font-size: 2.2rem; font-weight: 800; color: var(--text); line-height: 1; }
.rating-overview-count { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
.rating-distribution { display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1.25rem; }
.dist-row { display: flex; align-items: center; gap: 0.6rem; font-size: 0.8rem; }
.dist-star { width: 42px; color: var(--text-muted); flex-shrink: 0; }
.dist-bar-track { flex: 1; height: 8px; background: var(--border); border-radius: 100px; overflow: hidden; }
.dist-bar-fill { height: 100%; background: #FFC107; border-radius: 100px; }
.dist-count { width: 24px; text-align: right; color: var(--text-muted); flex-shrink: 0; }
.rating-divider { border-top: 1px solid var(--border); margin: 1rem 0; }
.review-list { display: flex; flex-direction: column; gap: 0.85rem; max-height: 280px; overflow-y: auto; }
.review-head { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.2rem; }
.review-comment { font-size: 0.85rem; color: var(--text-muted); }
</style>
