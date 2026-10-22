<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar :title="`Complaint ${complaint?.cmp_id || ''}`" />
      <div class="content-area">
        <router-link to="/staff/complaints" class="back-link">&larr; Back to Assignments</router-link>

        <div v-if="loading" class="spinner mt-4"></div>
        <div v-else-if="!complaint" class="empty-state mt-4"><p>Complaint not found.</p></div>
        <template v-else>
          <div class="card mt-4">
            <div class="detail-header">
              <div>
                <div class="cmp-id-big">{{ complaint.cmp_id }}</div>
                <div class="mt-1">
                  <span :class="['badge', `badge-${complaint.status}`]">{{ fmtStatus(complaint.status) }}</span>
                  <span :class="['badge', `badge-${complaint.priority}`]" class="ml-2">{{ complaint.priority }}</span>
                </div>
              </div>
            </div>

            <h3 class="req-title">{{ complaint.title }}</h3>

            <div class="detail-row"><div class="detail-label">Category</div><div class="detail-value capitalize">{{ complaint.category }}</div></div>
            <div class="detail-row"><div class="detail-label">Location</div><div class="detail-value">{{ complaint.address }}</div></div>
            <div class="detail-row"><div class="detail-label">Description</div><div class="detail-value">{{ complaint.description }}</div></div>
            <div v-if="complaint.image_urls?.length" class="detail-row">
              <div class="detail-label">Photos</div>
              <div class="detail-value"><ImageGallery :images="complaint.image_urls" alt="Complaint photo" /></div>
            </div>
            <div class="detail-row"><div class="detail-label">Citizen</div><div class="detail-value">{{ complaint.citizen_name }} ({{ complaint.citizen_email || 'no email on file' }})<span v-if="complaint.citizen_phone"> · 📞 {{ complaint.citizen_phone }}</span></div></div>
            <div class="detail-row"><div class="detail-label">Submitted On</div><div class="detail-value">{{ fmtDate(complaint.created_at) }}</div></div>
            <div class="detail-row" v-if="complaint.admin_notes">
              <div class="detail-label">Remarks</div>
              <div class="detail-value">{{ complaint.admin_notes }}</div>
            </div>
            <div class="detail-row" v-if="complaint.rating">
              <div class="detail-label">Citizen Rating</div>
              <div class="detail-value">
                <span class="rating-stars">
                  <span v-for="n in 5" :key="n" :class="{ filled: n <= complaint.rating }">&#9733;</span>
                  <span class="rating-num">{{ complaint.rating }}/5</span>
                </span>
                <p v-if="complaint.feedback" class="rating-feedback">"{{ complaint.feedback }}"</p>
              </div>
            </div>
          </div>

          <div v-if="complaint.evidence_urls?.length" class="card mt-4">
            <div class="section-title mb-4">Resolution Evidence</div>
            <ImageGallery :images="complaint.evidence_urls" alt="Resolution evidence photo" />
          </div>

          <div class="card mt-4">
            <div class="section-title mb-4">Update Status</div>

            <div v-if="complaint.status === 'closed'" class="alert alert-info">
              The citizen has closed this complaint — it's final and can no longer be updated.
            </div>
            <div v-else-if="complaint.status === 'on_hold_weather'" class="alert alert-info">
              &#9729; This complaint is on hold for weather restrictions. {{ complaint.hold_reason }} An admin needs to resume it before you can update the status.
            </div>
            <div v-else-if="complaint.status === 'resolved'" class="alert alert-info">
              &#10003; You already marked this complaint resolved. No further updates until the citizen closes it.
            </div>
            <template v-else>
              <div v-if="successMsg" class="alert alert-success">{{ successMsg }}</div>
              <div v-if="errMsg" class="alert alert-error">{{ errMsg }}</div>

              <div class="form-group">
                <label>New Status</label>
                <select v-model="newStatus" class="form-control status-select">
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
              <div class="form-group">
                <label>Remarks</label>
                <textarea v-model="remarks" class="form-control" rows="3" placeholder="Add remarks about the progress..."></textarea>
              </div>
              <div class="form-group" v-if="newStatus === 'resolved'">
                <label>Upload Evidence Photos (Optional)</label>
                <MultiImageUpload v-model="evidenceUrls" :max="3" />
              </div>
              <button class="btn btn-primary" @click="updateStatus" :disabled="updating">
                {{ updating ? 'Updating...' : 'Update Status' }}
              </button>
            </template>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Update Status - Staff workflow for updating complaint status
 * Workflow: assigned → in_progress → resolved → citizen confirms and closes
 * Staff can mark as "in_progress" or "resolved"
 * Only staff member assigned to the complaint can update it
 * Resolved complaints require optional resolution evidence photos
 */
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import ImageGallery from '../../components/ImageGallery.vue'
import MultiImageUpload from '../../components/MultiImageUpload.vue'
import api from '../../api'
import { fmtStatus } from '../../utils/status'
import { useToast } from '../../composables/useToast'

const { success: toastSuccess, error: toastError } = useToast()
const route = useRoute()
const loading = ref(true)
const complaint = ref(null)
const newStatus = ref('in_progress') // Only these options: in_progress, resolved
const remarks = ref('') // Admin notes visible to citizen
const updating = ref(false)
const successMsg = ref('')
const errMsg = ref('')
const evidenceUrls = ref([]) // Resolution photos (only used if resolved)

onMounted(async () => {
  try {
    const res = await api.get(`/requests/${route.params.id}`)
    complaint.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

/**
 * Update complaint status to in_progress or resolved
 * Remarks are saved as admin_notes visible to citizen in complaint detail
 * Evidence photos only included if marking as resolved and photos provided
 * Returns updated complaint data from server
 * Permission: only assigned staff member can update (server validates)
 */
async function updateStatus() {
  if (updating.value) return
  successMsg.value = ''
  errMsg.value = ''
  updating.value = true
  try {
    const res = await api.put(`/requests/${route.params.id}/status`, {
      status: newStatus.value,
      admin_notes: remarks.value,
      evidence_urls: newStatus.value === 'resolved' && evidenceUrls.value.length ? evidenceUrls.value : undefined,
    })
    complaint.value = res.data // Refresh complaint with updated status and evidence
    successMsg.value = `Status updated to "${fmtStatus(newStatus.value)}" successfully!`
    toastSuccess(successMsg.value)
    remarks.value = ''
    evidenceUrls.value = []
  } catch (e) {
    errMsg.value = e.response?.data?.message || 'Failed to update status'
    toastError(errMsg.value)
  } finally {
    updating.value = false
  }
}

function fmtDate(d) {
  return new Date(d).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.back-link { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); display: inline-flex; align-items: center; gap: 0.3rem; }
.back-link:hover { color: var(--text); }
.detail-header { padding-bottom: 1rem; margin-bottom: 1rem; border-bottom: 1px solid var(--border); }
.cmp-id-big { font-family: monospace; font-size: 1.1rem; font-weight: 800; color: var(--text); }
.req-title { font-size: 1.05rem; font-weight: 800; color: var(--navy); margin-bottom: 1rem; }
.status-select { max-width: 280px; }
.detail-value :deep(.image-gallery) { max-width: 440px; }
.rating-stars { display: inline-flex; align-items: center; gap: 0.15rem; font-size: 1.2rem; color: var(--border); }
.rating-stars span.filled { color: #FFC107; }
.rating-num { font-size: 0.8rem; font-weight: 700; color: var(--text); margin-left: 0.4rem; }
.rating-feedback { font-size: 0.85rem; color: var(--text); font-style: italic; margin-top: 0.4rem; }
</style>
