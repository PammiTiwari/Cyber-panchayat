<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Officers" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Manage department officers and staff</p>
          </div>
          <button class="btn btn-primary" @click="openAdd">+ Add Officer</button>
        </div>

        <div class="card">
          <div class="filter-bar">
            <input v-model="search" class="form-control" placeholder="Search by name or department..." />
          </div>
          <div v-if="loading" class="spinner"></div>
          <div v-else class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Department</th>
                  <th>Contact</th>
                  <th>Rating</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!filteredOfficers.length">
                  <td colspan="7"><div class="empty-state"><p>No officers found</p></div></td>
                </tr>
                <tr v-for="o in filteredOfficers" :key="o.id">
                  <td><code class="off-id">{{ o.officer_id }}</code></td>
                  <td>
                    <div class="officer-name-cell">
                      <div class="avatar avatar-sm">{{ o.name?.charAt(0) }}</div>
                      <span>{{ o.name }}</span>
                    </div>
                  </td>
                  <td class="text-sm">{{ o.department || '—' }}</td>
                  <td class="td-phone">{{ o.phone || '—' }}</td>
                  <td>
                    <button
                      v-if="officerRatings[o.id]"
                      type="button"
                      class="rating-cell"
                      :title="`${officerRatings[o.id].count} rating(s) from citizens — click to view`"
                      @click="openRatings(o)"
                    >
                      <span class="rating-star">&#9733;</span> {{ officerRatings[o.id].avg }}
                      <span class="rating-count-inline">({{ officerRatings[o.id].count }})</span>
                    </button>
                    <span v-else class="text-xs text-muted">—</span>
                  </td>
                  <td>
                    <span :class="o.is_active ? 'badge-active' : 'badge-inactive'">
                      {{ o.is_active ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>
                    <div class="action-btns">
                      <button class="btn btn-xs btn-secondary" @click="openEdit(o)">&#9998; Edit</button>
                      <button class="btn btn-xs btn-danger" @click="deactivate(o)" v-if="o.is_active">Deactivate</button>
                      <button class="btn btn-xs btn-success" @click="reactivate(o)" v-else>Reactivate</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ editingOfficer ? 'Edit Officer' : 'Add Officer' }}</h2>
          <button class="modal-close" aria-label="Close" @click="showModal = false">&#x2715;</button>
        </div>
        <div v-if="modalError" class="alert alert-error">{{ modalError }}</div>
        <div class="form-grid-2">
          <div class="form-group">
            <label>Full Name</label>
            <input v-model="form.name" class="form-control" placeholder="Officer name" />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="form.email" type="email" class="form-control" placeholder="Email address" :disabled="!!editingOfficer" />
          </div>
        </div>
        <div class="form-group">
          <label>Phone</label>
          <input v-model="form.phone" class="form-control" placeholder="Phone number" />
        </div>
        <div class="form-group">
          <label>Department</label>
          <select v-model="form.department" class="form-control">
            <option value="">Select Department</option>
            <option v-for="d in departments" :key="d.id" :value="d.name">{{ d.name }}</option>
            <option v-if="form.department && !departments.some(d => d.name === form.department)" :value="form.department">
              {{ form.department }} (legacy — not in Manage Departments)
            </option>
          </select>
          <p v-if="!departments.length" class="text-xs text-faint mt-1">
            No departments yet — add one via Manage Departments first.
          </p>
        </div>
        <div class="form-group" v-if="!editingOfficer">
          <label>Password</label>
          <input v-model="form.password" type="password" class="form-control" placeholder="Set password" />
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showModal = false">Cancel</button>
          <button class="btn btn-primary" @click="saveOfficer" :disabled="saving">{{ saving ? 'Saving...' : 'Save' }}</button>
        </div>
      </div>
    </div>

    <!-- Ratings modal: distribution + individual reviews -->
    <div v-if="ratingsModal.show" class="modal-overlay" @click.self="ratingsModal.show = false">
      <div class="modal modal-w-lg">
        <div class="modal-header">
          <h2>Ratings — {{ ratingsModal.officer?.name }}</h2>
          <button class="modal-close" aria-label="Close" @click="ratingsModal.show = false">✕</button>
        </div>

        <template v-if="ratingsModal.officer && officerRatings[ratingsModal.officer.id]">
          <div class="rating-overview">
            <div class="rating-overview-score">{{ officerRatings[ratingsModal.officer.id].avg }}</div>
            <div>
              <StarRating :model-value="Number(officerRatings[ratingsModal.officer.id].avg)" readonly size="md" />
              <div class="rating-overview-count">
                {{ officerRatings[ratingsModal.officer.id].count }} rating{{ officerRatings[ratingsModal.officer.id].count !== 1 ? 's' : '' }}
              </div>
            </div>
          </div>

          <div class="rating-distribution">
            <div v-for="n in [5,4,3,2,1]" :key="n" class="dist-row">
              <span class="dist-star">{{ n }} ⭐</span>
              <div class="dist-bar-track">
                <div class="dist-bar-fill" :style="{ width: distPercent(n) + '%' }"></div>
              </div>
              <span class="dist-count">{{ officerRatings[ratingsModal.officer.id].distribution[n] || 0 }}</span>
            </div>
          </div>

          <div class="divider"></div>

          <div v-if="!officerReviews.length" class="empty-state">
            <p>No written reviews yet.</p>
          </div>
          <div v-else class="review-list">
            <div v-for="r in officerReviews" :key="r.id" class="review-row">
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
  </div>
</template>

<script setup>
/**
 * Manage Officers - CRUD for department staff members
 * Features: add, edit, deactivate officers, track citizen ratings from complaints they handled
 * Officers are assigned to departments and handle complaint assignments
 * Shows officer performance through average citizen satisfaction ratings
 */
import { ref, computed, onMounted } from 'vue'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import StarRating from '../../components/StarRating.vue'
import api from '../../api'
import { useDebouncedValue } from '../../composables/useDebounce'
import { useToast } from '../../composables/useToast'

const { error: toastError, warning: toastWarning, success: toastSuccess } = useToast()

const loading = ref(true)
const officers = ref([])
const departments = ref([])
const search = ref('')
const debouncedSearch = useDebouncedValue(search, 300)
const showModal = ref(false)
const editingOfficer = ref(null) // Officer being edited (null for new)
const saving = ref(false)
const modalError = ref('')

const form = ref({ name: '', email: '', phone: '', department: '', password: '' })

const requests = ref([]) // Used to calculate officer ratings from complaints

onMounted(async () => {
  try {
    const [offRes, deptRes, reqRes] = await Promise.all([api.get('/officers'), api.get('/departments'), api.get('/requests')])
    officers.value = offRes.data
    departments.value = deptRes.data
    requests.value = reqRes.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

// Average citizen rating per officer, from the complaints they handled that
// were closed with a rating. Computed client-side from data already fetched —
// works identically in mock mode and against the real backend.
const officerRatings = computed(() => {
  const acc = {}
  for (const r of requests.value) {
    const staffId = r.assignment?.staff_id
    if (!staffId || !r.rating) continue
    if (!acc[staffId]) acc[staffId] = { sum: 0, count: 0, distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 } }
    acc[staffId].sum += r.rating
    acc[staffId].count += 1
    acc[staffId].distribution[r.rating] = (acc[staffId].distribution[r.rating] || 0) + 1
  }
  const out = {}
  for (const [id, { sum, count, distribution }] of Object.entries(acc)) {
    out[id] = { avg: (sum / count).toFixed(1), count, distribution }
  }
  return out
})

// Ratings modal — same "distribution + written reviews" pattern as the
// citizen-facing facility ratings modal, computed client-side from the
// complaints already fetched above (no dedicated endpoint needed).
const ratingsModal = ref({ show: false, officer: null })

function openRatings(o) {
  if (!officerRatings.value[o.id]) return
  ratingsModal.value = { show: true, officer: o }
}

const officerReviews = computed(() => {
  const id = ratingsModal.value.officer?.id
  if (!id) return []
  return requests.value
    .filter(r => r.assignment?.staff_id === id && r.rating && r.feedback)
    .map(r => ({ id: r.id, citizen_name: r.citizen_name, rating: r.rating, comment: r.feedback }))
})

function distPercent(star) {
  const id = ratingsModal.value.officer?.id
  const d = id ? officerRatings.value[id] : null
  if (!d || !d.count) return 0
  return Math.round(((d.distribution[star] || 0) / d.count) * 100)
}

const filteredOfficers = computed(() => {
  if (!debouncedSearch.value) return officers.value
  const q = debouncedSearch.value.toLowerCase()
  return officers.value.filter(o =>
    o.name?.toLowerCase().includes(q) ||
    o.department?.toLowerCase().includes(q) ||
    o.email?.toLowerCase().includes(q)
  )
})

function openAdd() {
  editingOfficer.value = null
  form.value = { name: '', email: '', phone: '', department: '', password: '' }
  modalError.value = ''
  showModal.value = true
}

function openEdit(officer) {
  editingOfficer.value = officer
  form.value = { name: officer.name, email: officer.email, phone: officer.phone || '', department: officer.department || '', password: '' }
  modalError.value = ''
  showModal.value = true
}

async function saveOfficer() {
  const name = form.value.name.trim()
  if (!/^[A-Za-z][A-Za-z\s.'-]{1,79}$/.test(name)) { modalError.value = 'Please enter a valid name — letters only, numbers are not a name'; return }
  const phone = form.value.phone.trim()
  if (phone && !/^[6-9]\d{9}$/.test(phone)) { modalError.value = 'Phone must be a valid 10-digit mobile number'; return }
  saving.value = true
  modalError.value = ''
  try {
    if (editingOfficer.value) {
      const res = await api.put(`/officers/${editingOfficer.value.id}`, {
        name,
        phone,
        department: form.value.department,
      })
      const idx = officers.value.findIndex(o => o.id === editingOfficer.value.id)
      if (idx >= 0) officers.value[idx] = res.data
    } else {
      if (!form.value.email.trim() || !form.value.password) { modalError.value = 'Email and password required'; saving.value = false; return }
      if (!/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/.test(form.value.email.trim())) { modalError.value = 'Please enter a valid email address'; saving.value = false; return }
      if (form.value.password.length < 6) { modalError.value = 'Password must be at least 6 characters'; saving.value = false; return }
      const res = await api.post('/officers', { ...form.value, name, phone, email: form.value.email.trim() })
      officers.value.push(res.data)
    }
    showModal.value = false
  } catch (e) {
    modalError.value = e.response?.data?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

async function deactivate(officer) {
  if (!confirm(`Deactivate officer "${officer.name}"?`)) return
  try {
    const res = await api.delete(`/officers/${officer.id}`)
    const idx = officers.value.findIndex(o => o.id === officer.id)
    if (idx >= 0) officers.value[idx].is_active = false
    if (res.data.open_complaints) {
      toastWarning(`Officer deactivated. They had ${res.data.open_complaints} open complaint(s) — go to Manage Complaints to reassign them.`)
    }
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed')
  }
}

async function reactivate(officer) {
  try {
    await api.put(`/officers/${officer.id}`, { is_active: true })
    const idx = officers.value.findIndex(o => o.id === officer.id)
    if (idx >= 0) officers.value[idx].is_active = true
    toastSuccess(`Officer "${officer.name}" reactivated`)
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed')
  }
}
</script>

<style scoped>
.off-id { font-family: monospace; font-size: 0.8rem; background: #FFE9F2; padding: 0.1rem 0.4rem; border-radius: 4px; }
.rating-cell {
  display: inline-flex; align-items: center; gap: 0.3rem;
  font-size: 0.85rem; font-weight: 700; color: var(--primary); white-space: nowrap;
  background: none; border: none; padding: 0.15rem 0.3rem; border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--transition), text-decoration-color var(--transition);
  text-decoration: underline; text-decoration-color: transparent; text-underline-offset: 2px;
}
.rating-cell:hover { background: var(--accent); text-decoration-color: var(--primary); }
.rating-star { color: #FFC107; }
.rating-count-inline { font-weight: 500; color: var(--text-muted); font-size: 0.78rem; }

/* Ratings modal — distribution + written reviews, same pattern as the
   citizen-facing facility ratings modal. */
.rating-overview { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
.rating-overview-score { font-size: 2.2rem; font-weight: 800; color: var(--text); line-height: 1; }
.rating-overview-count { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
.rating-distribution { display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1.25rem; }
.dist-row { display: flex; align-items: center; gap: 0.6rem; font-size: 0.8rem; }
.dist-star { width: 42px; color: var(--text-muted); flex-shrink: 0; }
.dist-bar-track { flex: 1; height: 8px; background: var(--border); border-radius: 100px; overflow: hidden; }
.dist-bar-fill { height: 100%; background: #FFC107; border-radius: 100px; }
.dist-count { width: 24px; text-align: right; color: var(--text-muted); flex-shrink: 0; }
.divider { border-top: 1px solid var(--border); margin: 1rem 0; }
.review-list { display: flex; flex-direction: column; gap: 0.85rem; max-height: 280px; overflow-y: auto; }
.review-head { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.2rem; }
.review-comment { font-size: 0.85rem; color: var(--text-muted); }
.officer-name-cell { display: flex; align-items: center; gap: 0.5rem; }
.action-btns { display: flex; gap: 0.35rem; }
.badge-active { font-size: 0.72rem; font-weight: 700; color: #0E7A4F; background: #D7F5E5; padding: 0.15rem 0.5rem; border-radius: 100px; }
.badge-inactive { font-size: 0.72rem; font-weight: 700; color: #9B2C6F; background: #FFE9F2; padding: 0.15rem 0.5rem; border-radius: 100px; }
.td-phone { font-size: 0.8rem; color: #9B2C6F; }
</style>
