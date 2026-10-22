<template>
  <div class="track-result">
    <button class="btn btn-outline btn-sm mb-3" @click="$emit('close')">← Search Another Complaint</button>

    <div class="card">
      <div class="detail-header">
        <div>
          <div class="cmp-id-big">{{ result.cmp_id }}</div>
          <div class="mt-1">
            <span :class="['badge', `badge-${result.status}`]">{{ fmtStatus(result.status) }}</span>
            <span :class="['badge', `badge-${result.priority}`]" class="ml-2">{{ result.priority }}</span>
          </div>
        </div>
        <div class="detail-dept">{{ result.department }}</div>
      </div>

      <div v-if="result.status === 'on_hold_weather'" class="alert alert-info">
        &#9729; <strong>On hold — weather restrictions.</strong> {{ result.hold_reason }}
      </div>

      <div class="detail-section">
        <div class="detail-row">
          <div class="detail-label">Category</div>
          <div class="detail-value capitalize">{{ result.category }}</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Location</div>
          <div class="detail-value">{{ result.address }}</div>
        </div>
        <div class="detail-row" v-if="result.ward">
          <div class="detail-label">Ward</div>
          <div class="detail-value">{{ result.ward }}</div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Description</div>
          <div class="detail-value">{{ result.description }}</div>
        </div>
        <div v-if="result.image_urls?.length" class="detail-row">
          <div class="detail-label">Photos</div>
          <div class="detail-value">
            <ImageGallery :images="result.image_urls" alt="Complaint photo" />
          </div>
        </div>
        <div v-if="result.evidence_urls?.length" class="detail-row">
          <div class="detail-label">Resolution Photo</div>
          <div class="detail-value">
            <ImageGallery :images="result.evidence_urls" alt="Resolution evidence photo" />
          </div>
        </div>
        <div class="detail-row">
          <div class="detail-label">Submitted On</div>
          <div class="detail-value">{{ fmtDate(result.created_at) }}</div>
        </div>
        <div class="detail-row" v-if="result.assignment">
          <div class="detail-label">Assigned To</div>
          <div class="detail-value">
            {{ result.assignment.staff_name }}
            <span v-if="result.assignment.staff_department" class="text-muted"> ({{ result.assignment.staff_department }})</span>
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
            <span>{{ fmtDate(result.created_at) }}</span>
          </div>
        </li>
        <li class="timeline-item">
          <div :class="['timeline-dot', result.assignment ? 'done-yellow' : 'pending']">
            {{ result.assignment ? '✓' : '' }}
          </div>
          <div class="timeline-content">
            <p>Assigned to Department</p>
            <span v-if="result.assignment">{{ fmtDate(result.assignment.assigned_at) }} — {{ result.assignment.staff_department }}</span>
            <span v-else class="text-faint">Pending assignment</span>
            <p v-if="result.assignment?.notes" class="timeline-remark">{{ result.assignment.notes }}</p>
          </div>
        </li>
        <li class="timeline-item">
          <div :class="['timeline-dot', result.in_progress_at ? 'done-orange' : 'pending']">
            {{ progressEntries.length ? '✓' : '' }}
          </div>
          <div class="timeline-content">
            <p>Work In Progress</p>
            <span v-if="progressEntries.length">{{ fmtDate(progressEntries[0].at) }}</span>
            <span v-else-if="['resolved','closed'].includes(result.status)" class="text-faint">Not recorded — resolved in one step</span>
            <span v-else-if="result.status === 'in_progress'" class="text-faint">Not recorded</span>
            <span v-else class="text-faint">Yet to start</span>
            <ul v-if="progressEntries.length > 1" class="progress-log">
              <li v-for="(e, i) in progressEntries" :key="i">
                <span class="progress-log-date">{{ fmtDate(e.at) }}</span>
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
          <div :class="['timeline-dot', result.status === 'rejected' ? 'done-red' : (['resolved','closed'].includes(result.status) ? 'done-green' : 'pending')]">
            {{ result.status === 'rejected' ? '✕' : (['resolved','closed'].includes(result.status) ? '✓' : '') }}
          </div>
          <div class="timeline-content">
            <p>{{ result.status === 'rejected' ? 'Rejected' : 'Resolved' }}</p>
            <span v-if="result.status === 'rejected'" class="text-faint">This complaint was rejected</span>
            <span v-else-if="['resolved','closed'].includes(result.status) && result.resolved_at">{{ fmtDate(result.resolved_at) }}</span>
            <span v-else class="text-faint">Yet to be resolved</span>
            <p v-if="result.status === 'rejected' && result.admin_notes" class="timeline-remark">{{ result.admin_notes }}</p>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ImageGallery from './ImageGallery.vue'
import { fmtStatus } from '../utils/status'

const props = defineProps({ result: { type: Object, required: true } })

// The public payload carries progress_log but not in_progress_at /
// in_progress_notes, so this step used to render empty here no matter what
// the officer had logged.
const progressEntries = computed(() => {
  const r = props.result
  if (!r || !['in_progress', 'resolved', 'closed'].includes(r.status)) return []
  return Array.isArray(r.progress_log) ? r.progress_log : []
})
defineEmits(['close'])

function fmtDate(d) {
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

.track-result { max-width: 640px; }
.detail-header { display: flex; justify-content: space-between; align-items: flex-start; padding-bottom: 1rem; margin-bottom: 1rem; border-bottom: 1px solid var(--border); }
.cmp-id-big { font-family: monospace; font-size: 1.1rem; font-weight: 800; color: var(--text); }
.detail-dept { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); background: var(--accent); padding: 0.3rem 0.75rem; border-radius: 100px; }
.detail-section { margin-top: 0.5rem; }
.detail-value :deep(.image-gallery) { max-width: 480px; }
</style>
