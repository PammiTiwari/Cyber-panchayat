<template>
  <div class="card similar-box">
    <div class="similar-header">
      <div class="similar-title">⚠ Similar Complaints <span class="similar-count">({{ items.length }})</span></div>
      <p class="similar-hint">Support an existing report with a "+1" instead of creating a duplicate — it helps the department prioritise.</p>
    </div>

    <div class="similar-list">
      <div v-for="m in items" :key="m.id" class="similar-item">
        <div class="similar-row-top">
          <span class="similar-text">{{ m.title }}</span>
          <span :class="['badge', `badge-${m.status}`]">{{ fmtStatus(m.status) }}</span>
        </div>
        <div class="similar-row-bottom">
          <span class="similar-sub">{{ m.cmp_id }} · 👍 {{ m.upvotes_count }}<template v-if="m.is_own"> · your complaint</template></span>
          <div class="similar-action">
            <button class="btn btn-xs btn-outline" @click="selected = m">View</button>
            <button v-if="!m.is_own" class="btn btn-xs" :class="m.upvoted ? 'btn-success' : 'btn-outline'"
              :disabled="m.busy" @click="toggle(m)">
              {{ m.upvoted ? '✓ Supported' : '+1 Me too' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="similar-footer">
      <button class="btn btn-sm btn-primary" @click="$emit('proceed')">None of these — submit my complaint</button>
    </div>

    <!-- Detail view — everything about the matched complaint except who filed it.
         Teleported to body: this component lives inside a `position: sticky`
         side panel, which traps a nested fixed-position modal in its own
         stacking context and lets the form's Leaflet map paint over it. -->
    <Teleport to="body">
    <div v-if="selected" class="modal-overlay" @click.self="selected = null">
      <div class="modal modal-lg">
        <div class="modal-header">
          <h2>{{ selected.cmp_id }} — Complaint Details</h2>
          <button class="modal-close" aria-label="Close" @click="selected = null">✕</button>
        </div>

        <div class="flex gap-2 mb-4">
          <span :class="['badge', `badge-${selected.status}`]">{{ fmtStatus(selected.status) }}</span>
          <span v-if="selected.priority" :class="['badge', `badge-${selected.priority}`]">{{ selected.priority }}</span>
        </div>

        <h3 class="detail-title">{{ selected.title }}</h3>

        <div class="detail-row"><div class="detail-label">Category</div><div class="detail-value capitalize">{{ selected.category }}</div></div>
        <div class="detail-row" v-if="selected.department"><div class="detail-label">Department</div><div class="detail-value">{{ selected.department }}</div></div>
        <div class="detail-row" v-if="selected.ward"><div class="detail-label">Ward</div><div class="detail-value">{{ selected.ward }}</div></div>
        <div class="detail-row" v-if="selected.address"><div class="detail-label">Location</div><div class="detail-value">{{ selected.address }}</div></div>
        <div class="detail-row"><div class="detail-label">Description</div><div class="detail-value">{{ selected.description }}</div></div>
        <div class="detail-row" v-if="selected.image_urls?.length">
          <div class="detail-label">Photos</div>
          <div class="detail-value"><ImageGallery :images="selected.image_urls" alt="Complaint photo" /></div>
        </div>
        <div class="detail-row" v-if="selected.evidence_urls?.length">
          <div class="detail-label">Resolution Evidence</div>
          <div class="detail-value"><ImageGallery :images="selected.evidence_urls" alt="Resolution evidence photo" /></div>
        </div>
        <div class="detail-row" v-if="selected.created_at"><div class="detail-label">Submitted On</div><div class="detail-value">{{ fmtDate(selected.created_at) }}</div></div>

        <div class="modal-footer">
          <button v-if="!selected.is_own" class="btn btn-sm" :class="selected.upvoted ? 'btn-success' : 'btn-outline'"
            :disabled="selected.busy" @click="toggle(selected)">
            👍 {{ selected.upvoted ? 'Supported' : '+1 Me too' }} ({{ selected.upvotes_count || 0 }})
          </button>
          <span v-else class="own-label">This is your complaint ({{ selected.upvotes_count || 0 }})</span>
          <button class="btn btn-secondary" @click="selected = null">Close</button>
        </div>
      </div>
    </div>
    </Teleport>
  </div>
</template>

<script setup>
/**
 * SimilarComplaints Component
 * Displayed when submitting a complaint: shows existing similar complaints.
 * Encourages users to upvote/support existing complaints instead of creating duplicates.
 * Helps department prioritize by aggregating community interest on single complaint.
 */
import { ref, watch } from 'vue'
import api from '../api'
import { fmtStatus } from '../utils/status'
import ImageGallery from './ImageGallery.vue'

const props = defineProps({ matches: { type: Array, default: () => [] } })
const emit = defineEmits(['proceed', 'upvoted'])

// Local copy of matches with per-item state (upvoted flag, busy loading state)
const items = ref([])
const selected = ref(null)
watch(() => props.matches, (m) => {
  items.value = m.map(x => ({ ...x, upvoted: !!x.upvoted_by_me, busy: false }))
}, { immediate: true })

/**
 * Toggle upvote on a similar complaint.
 * Posts to /requests/{id}/upvote endpoint and updates vote count.
 * Emits 'upvoted' event when user successfully votes.
 */
async function toggle(m) {
  m.busy = true
  try {
    const { data } = await api.post(`/requests/${m.id}/upvote`)
    m.upvoted = data.upvoted
    m.upvotes_count = data.upvotes_count
    if (data.upvoted) emit('upvoted', m)
  } finally {
    m.busy = false
  }
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.similar-box { text-align: left; padding: 1.5rem 1.65rem; }
.similar-header { margin-bottom: 1.1rem; }
.similar-title { font-weight: 800; font-size: 1.05rem; color: var(--navy); margin-bottom: 0.35rem; }
.similar-count { font-weight: 700; color: var(--text-muted); }
.similar-hint { font-size: 0.83rem; font-weight: 500; color: var(--text-muted); line-height: 1.45; }
.similar-list { display: flex; flex-direction: column; }
.similar-item {
  display: flex; flex-direction: column; gap: 0.6rem;
  padding: 1.15rem 0;
  border-bottom: 1px solid var(--border);
}
.similar-item:last-child { border-bottom: none; padding-bottom: 0.3rem; }
.similar-item:first-child { padding-top: 0.15rem; }
.similar-row-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.75rem; }
.similar-text { font-size: 1rem; font-weight: 700; color: var(--text); line-height: 1.4; }
.similar-row-bottom { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; flex-wrap: wrap; }
.similar-sub { font-size: 0.85rem; color: var(--text-muted); }
.own-label { font-size: 0.85rem; font-weight: 700; color: var(--text-muted); font-style: italic; }
.similar-action { display: flex; align-items: center; gap: 0.5rem; }
.similar-footer { margin-top: 1.25rem; }
.similar-footer .btn { width: 100%; padding-top: 0.65rem; padding-bottom: 0.65rem; }
.detail-title { font-size: 1.05rem; font-weight: 800; color: var(--navy); margin-bottom: 1rem; }
</style>
