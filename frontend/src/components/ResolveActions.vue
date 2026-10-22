<template>
  <div class="card resolve-card mt-4">
    <!-- Resolved → citizen confirms and rates -->
    <template v-if="complaint.status === 'resolved'">
      <div class="section-title">Was this resolved to your satisfaction?</div>
      <p class="resolve-hint">Confirm and rate the work. If the issue isn't actually fixed, contact the department.</p>
      <div class="resolve-actions">
        <button class="btn btn-success" @click="openClose">&#10003; Confirm &amp; Close</button>
      </div>
    </template>

    <!-- Closed with a rating → show what was given -->
    <template v-else-if="complaint.status === 'closed' && complaint.rating">
      <div class="section-title">Your Feedback</div>
      <div class="stars-static">
        <span v-for="n in 5" :key="n" :class="{ filled: n <= complaint.rating }">&#9733;</span>
        <span class="rating-num">{{ complaint.rating }}/5</span>
      </div>
      <p v-if="complaint.feedback" class="resolve-feedback">"{{ complaint.feedback }}"</p>
    </template>

    <div v-if="error" class="alert alert-error mt-3">{{ error }}</div>

    <!-- Rating modal -->
    <div v-if="showClose" class="modal-overlay" @click.self="showClose = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Rate the resolution</h2>
          <button class="modal-close" aria-label="Close" @click="showClose = false">&times;</button>
        </div>
        <div class="form-group">
          <label>How satisfied are you?</label>
          <div class="stars-input">
            <span v-for="n in 5" :key="n"
              :class="{ filled: n <= rating }"
              @click="rating = n">&#9733;</span>
          </div>
        </div>
        <div class="form-group">
          <label>Comment (optional)</label>
          <textarea v-model="feedback" class="form-control" placeholder="Tell us about the work done..."></textarea>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showClose = false">Cancel</button>
          <button class="btn btn-success" :disabled="!rating || submitting" @click="submitClose">
            {{ submitting ? 'Saving...' : 'Confirm & Close' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
/**
 * ResolveActions Component
 * Handles the last step of a complaint: the citizen confirms the work and
 * rates it 1-5 with optional feedback, which closes the complaint.
 * Shows the feedback summary once a complaint has been closed with a rating.
 */
import { ref } from 'vue'
import api from '../api'

const props = defineProps({ complaint: { type: Object, required: true } })
const emit = defineEmits(['updated'])

// Modal visibility state
const showClose = ref(false)

// Close/rating form state
const rating = ref(0)
const feedback = ref('')

// Request state and error handling
const submitting = ref(false)
const error = ref('')

/**
 * Open close/rating modal.
 * Resets form fields and error state.
 */
function openClose() { rating.value = 0; feedback.value = ''; error.value = ''; showClose.value = true }

/**
 * Submit complaint closure with rating and optional feedback.
 * Updates complaint status to 'closed' and stores user satisfaction rating (1-5 stars).
 */
async function submitClose() {
  submitting.value = true
  error.value = ''
  try {
    const { data } = await api.put(`/requests/${props.complaint.id}/status`, {
      status: 'closed', rating: rating.value, feedback: feedback.value,
    })
    showClose.value = false
    emit('updated', data)
  } catch (e) {
    error.value = e.response?.data?.message || 'Could not close the complaint.'
  } finally {
    submitting.value = false
  }
}

</script>

<style scoped>
.resolve-hint { font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.85rem; }
.resolve-actions { display: flex; gap: 0.75rem; }
.resolve-note { font-size: 0.82rem; color: #D69AB8; margin-top: 0.6rem; }
.resolve-feedback { font-size: 0.875rem; color: var(--text); font-style: italic; margin-top: 0.4rem; }
.stars-static, .stars-input { display: flex; align-items: center; gap: 0.15rem; font-size: 1.5rem; color: var(--border); }
.stars-static span.filled, .stars-input span.filled { color: #FFC107; }
.stars-input span { cursor: pointer; transition: color 0.1s; }
.stars-input span:hover { color: #FFC933; }
.rating-num { font-size: 0.85rem; font-weight: 700; color: var(--text); margin-left: 0.5rem; }
</style>
