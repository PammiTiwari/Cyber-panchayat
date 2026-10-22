<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar :title="`Complaint ${complaint?.cmp_id || ''}`" />
      <div class="content-area">
        <div class="detail-topbar">
          <router-link to="/complaints" class="back-link">&larr; Back to Complaints</router-link>
          <div class="detail-topbar-actions">
            <DownloadReportButton v-if="complaint" :loading="exporting" @click="downloadReport" />
            <button v-if="complaint?.status === 'pending'" class="btn btn-sm btn-danger" :disabled="deleting" @click="deleteComplaint">
              {{ deleting ? 'Deleting...' : '🗑 Delete Complaint' }}
            </button>
          </div>
        </div>

        <div v-if="loading" class="spinner"></div>
        <div v-else-if="!complaint" class="empty-state">
          <p>Complaint not found.</p>
        </div>
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
              <div class="detail-dept">{{ complaint.department }}</div>
            </div>

            <div v-if="complaint.status === 'on_hold_weather'" class="alert alert-info">
              &#9729; <strong>On hold — weather restrictions.</strong> {{ complaint.hold_reason }}
            </div>

            <div class="detail-section">
              <div class="detail-row">
                <div class="detail-label">Title</div>
                <div class="detail-value">{{ complaint.title }}</div>
              </div>
              <div class="detail-row">
                <div class="detail-label">Category</div>
                <div class="detail-value capitalize">{{ complaint.category }}</div>
              </div>
              <div class="detail-row">
                <div class="detail-label">Location</div>
                <div class="detail-value">{{ complaint.address }}</div>
              </div>
              <div class="detail-row" v-if="complaint.ward">
                <div class="detail-label">Ward</div>
                <div class="detail-value">{{ complaint.ward }}</div>
              </div>
              <div class="detail-row">
                <div class="detail-label">Description</div>
                <div class="detail-value">{{ complaint.description }}</div>
              </div>
              <div v-if="complaint.image_urls?.length" class="detail-row">
                <div class="detail-label">Photos</div>
                <div class="detail-value">
                  <ImageGallery :images="complaint.image_urls" alt="Complaint photo" />
                </div>
              </div>
              <div v-if="complaint.evidence_urls?.length" class="detail-row">
                <div class="detail-label">Resolution Evidence</div>
                <div class="detail-value">
                  <ImageGallery :images="complaint.evidence_urls" alt="Resolution evidence photo" />
                </div>
              </div>
              <div class="detail-row">
                <div class="detail-label">Submitted By</div>
                <div class="detail-value">{{ complaint.citizen_name }}</div>
              </div>
              <div class="detail-row">
                <div class="detail-label">Submitted On</div>
                <div class="detail-value">{{ fmtDateFull(complaint.created_at) }}</div>
              </div>
              <div class="detail-row" v-if="complaint.assignment">
                <div class="detail-label">Assigned To</div>
                <div class="detail-value">
                  {{ complaint.assignment.staff_name }}
                  <span v-if="complaint.assignment.staff_department" class="text-muted"> ({{ complaint.assignment.staff_department }})</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Timeline -->
          <div class="card mt-4">
            <div class="section-title">Timeline</div>
            <ul class="timeline">
              <li class="timeline-item">
                <div class="timeline-dot done">&#10003;</div>
                <div class="timeline-content">
                  <p>Complaint Submitted</p>
                  <span>{{ fmtDateFull(complaint.created_at) }}</span>
                </div>
              </li>
              <li class="timeline-item">
                <div :class="['timeline-dot', complaint.assignment ? 'done-yellow' : 'pending']">
                  {{ complaint.assignment ? '✓' : '' }}
                </div>
                <div class="timeline-content">
                  <p>Assigned to Department</p>
                  <span v-if="complaint.assignment">{{ fmtDateFull(complaint.assignment.assigned_at) }} — {{ complaint.assignment.staff_department }}</span>
                  <span v-else class="text-faint">Pending assignment</span>
                  <p v-if="complaint.assignment?.notes" class="timeline-remark">{{ complaint.assignment.notes }}</p>
                </div>
              </li>
              <li class="timeline-item">
                <div :class="['timeline-dot', complaint.in_progress_at ? 'done-orange' : 'pending']">
                  {{ complaint.in_progress_at ? '✓' : '' }}
                </div>
                <div class="timeline-content">
                  <p>Work In Progress</p>
                  <span v-if="complaint.in_progress_at">{{ fmtDateFull(complaint.in_progress_at) }}</span>
                  <span v-else-if="['resolved','closed'].includes(complaint.status)" class="text-faint">Not recorded — resolved in one step</span>
                  <span v-else-if="complaint.status === 'in_progress'" class="text-faint">Not recorded</span>
                  <span v-else class="text-faint">Yet to start</span>
                  <!-- Every in_progress update, each under the date it was
                       actually made. The single in_progress_notes field only
                       ever held the latest remark, so an officer's second
                       update silently replaced the first. -->
                  <ul v-if="progressEntries.length > 1" class="progress-log">
                    <li v-for="(e, i) in progressEntries" :key="i">
                      <span class="progress-log-date">{{ fmtDateFull(e.at) }}</span>
                      <span v-if="e.note" class="progress-log-note">{{ e.note }}</span>
                      <span v-else class="progress-log-note text-faint">No remark given</span>
                    </li>
                  </ul>
                  <p v-else-if="progressEntries.length === 1" class="timeline-remark"
                     :class="{ 'text-faint': !progressEntries[0].note }">
                    {{ progressEntries[0].note || 'No remark given' }}
                  </p>
                </div>
              </li>
              <li class="timeline-item">
                <div :class="['timeline-dot', complaint.status === 'rejected' ? 'done-red' : (['resolved','closed'].includes(complaint.status) ? 'done-green' : 'pending')]">
                  {{ complaint.status === 'rejected' ? '✕' : (['resolved','closed'].includes(complaint.status) ? '✓' : '') }}
                </div>
                <div class="timeline-content">
                  <p>{{ complaint.status === 'rejected' ? 'Rejected' : 'Resolved' }}</p>
                  <span v-if="complaint.status === 'rejected'" class="text-faint">This complaint was rejected</span>
                  <span v-else-if="['resolved','closed'].includes(complaint.status) && complaint.resolved_at">{{ fmtDateFull(complaint.resolved_at) }}</span>
                  <span v-else class="text-faint">Yet to be resolved</span>
                  <p v-if="complaint.status === 'rejected' && complaint.admin_notes" class="timeline-remark">{{ complaint.admin_notes }}</p>
                  <p v-else-if="complaint.resolved_notes" class="timeline-remark">{{ complaint.resolved_notes }}</p>
                </div>
              </li>
            </ul>
          </div>

          <ResolveActions
            v-if="['resolved','closed'].includes(complaint.status)"
            :complaint="complaint" @updated="onUpdated" />
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Complaint Detail - Full view of a single complaint with timeline and status tracking
 * Displays complaint information, attached photos, evidence, and workflow timeline
 * Citizens can delete pending complaints and confirm/rate resolved ones
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import ResolveActions from '../../components/ResolveActions.vue'
import DownloadReportButton from '../../components/DownloadReportButton.vue'
import ImageGallery from '../../components/ImageGallery.vue'
import api from '../../api'
import { fmtStatus } from '../../utils/status'
import { downloadComplaintReportPdf } from '../../utils/reportPdf'
import { useToast } from '../../composables/useToast'

const route = useRoute()
const router = useRouter()
const { success, error: toastError } = useToast()
const loading = ref(true)
const complaint = ref(null)
const deleting = ref(false)

// One entry per in_progress update. Falls back to the older single-value
// fields for any complaint written before progress_log existed, so nothing
// that used to be visible disappears.
const progressEntries = computed(() => {
  const c = complaint.value
  if (!c || !['in_progress', 'resolved', 'closed'].includes(c.status)) return []
  const log = Array.isArray(c.progress_log) ? c.progress_log : []
  if (log.length) return log
  return c.in_progress_at ? [{ at: c.in_progress_at, note: c.in_progress_notes || null }] : []
})
const exporting = ref(false)

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

function onUpdated(data) {
  complaint.value = data
}

/**
 * Delete complaint - only allowed when status is "pending"
 * Button is conditionally hidden in template, server validates on DELETE endpoint
 * On success, redirects back to complaints list
 */
async function deleteComplaint() {
  if (deleting.value) return // Prevent duplicate requests
  if (!confirm(`Delete complaint ${complaint.value.cmp_id}? This cannot be undone.`)) return
  deleting.value = true
  try {
    await api.delete(`/requests/${complaint.value.id}`)
    router.push('/complaints')
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to delete complaint')
    deleting.value = false
  }
}

async function downloadReport() {
  exporting.value = true
  try {
    downloadComplaintReportPdf({ complaint: complaint.value })
    success('✓ Report downloaded')
  } catch (e) {
    toastError('Could not generate the report — please try again')
  } finally {
    exporting.value = false
  }
}

function fmtDateFull(d) {
  if (!d) return ''
  return new Date(d).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.progress-log { list-style: none; margin: 0.35rem 0 0; padding: 0; }
.progress-log li {
  display: flex; flex-direction: column; gap: 0.1rem;
  padding: 0.3rem 0 0.3rem 0.6rem;
  border-left: 2px solid var(--border);
  margin-bottom: 0.3rem;
}
.progress-log li:last-child { margin-bottom: 0; }
.progress-log-date { font-size: 0.74rem; color: var(--text-muted); font-weight: 600; }
.progress-log-note { font-size: 0.8rem; }

.detail-topbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.6rem; }
.detail-topbar-actions { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }

@media (max-width: 480px) {
  .detail-topbar-actions { width: 100%; }
  .detail-topbar-actions > * { flex: 1; }
}
.back-link { font-size: 0.85rem; font-weight: 600; color: #9B2C6F; display: inline-flex; align-items: center; gap: 0.3rem; }
.back-link:hover { color: #5C1A41; }
.detail-header { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 1rem; margin-bottom: 1rem; border-bottom: 1px solid #FFD1E6; }
.cmp-id-big { font-family: monospace; font-size: 1.1rem; font-weight: 800; color: #5C1A41; }
.detail-dept { font-size: 0.8rem; font-weight: 600; color: #B0708F; background: #FFE9F2; padding: 0.3rem 0.75rem; border-radius: 100px; }
.detail-section { margin-top: 0.5rem; }
.detail-value :deep(.image-gallery) { max-width: 480px; }
</style>
