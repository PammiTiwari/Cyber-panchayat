<template>
  <button class="dl-report-btn" :disabled="loading" @click="$emit('click')">
    <span class="dl-report-icon" :class="{ 'dl-report-icon-spinning': loading }">
      <svg v-if="!loading" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v11" />
        <path d="M7.5 10.5 12 15l4.5-4.5" />
        <path d="M4.5 19h15" />
      </svg>
      <svg v-else viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="#fff" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="34 100" />
      </svg>
    </span>
    <span>{{ loading ? 'Generating…' : label }}</span>
  </button>
</template>

<script setup>
/**
 * DownloadReportButton - shared PDF-export trigger for MyRequests.vue and
 * ComplaintDetail.vue. Deliberately styled nothing like the app's solid-blue
 * primary buttons ("+ Submit New" etc.) so it doesn't read as just another
 * one in the row: white pill body, a green icon-chip (green = export/done
 * elsewhere in this app's own palette, see --success), and a real SVG icon
 * rather than an emoji.
 */
defineProps({
  loading: { type: Boolean, default: false },
  label: { type: String, default: 'Download Report' },
})
defineEmits(['click'])
</script>

<style scoped>
.dl-report-btn {
  display: inline-flex; align-items: center; gap: 0.6rem;
  padding: 0.3rem 1.1rem 0.3rem 0.3rem;
  border-radius: 100px;
  border: 1.5px solid var(--success, #15803D);
  background: #fff;
  color: var(--success, #15803D);
  font-weight: 700; font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.15s, box-shadow 0.15s, transform 0.15s;
  white-space: nowrap;
}
.dl-report-btn:hover:not(:disabled) {
  background: rgba(21,128,61,0.06);
  box-shadow: 0 4px 12px rgba(21,128,61,0.18);
  transform: translateY(-1px);
}
.dl-report-btn:active:not(:disabled) { transform: translateY(0); }
.dl-report-btn:disabled { opacity: 0.7; cursor: default; }

.dl-report-icon {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  background: var(--success, #15803D);
  display: flex; align-items: center; justify-content: center;
}
.dl-report-icon svg { width: 15px; height: 15px; }
.dl-report-icon-spinning svg { animation: dl-report-spin 0.8s linear infinite; }
@keyframes dl-report-spin { to { transform: rotate(360deg); } }
</style>
