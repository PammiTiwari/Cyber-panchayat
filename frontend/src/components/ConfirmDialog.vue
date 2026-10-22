<!-- The app's confirm dialog. Mounted once in App.vue, raised from anywhere
     through useConfirm(). Uses the shared .modal classes so it matches every
     other dialog in the app. -->
<template>
  <div
    v-if="pending"
    class="modal-overlay confirm-overlay"
    @click.self="cancel"
  >
    <div
      class="modal confirm-modal"
      role="alertdialog"
      aria-modal="true"
      :aria-label="pending.title"
    >
      <div class="modal-header">
        <h2>{{ pending.title }}</h2>
        <button class="modal-close" aria-label="Close" @click="cancel">✕</button>
      </div>

      <p v-if="pending.message" class="confirm-message">{{ pending.message }}</p>

      <div class="modal-footer">
        <button class="btn btn-outline btn-sm" @click="cancel">
          {{ pending.cancelLabel }}
        </button>
        <button
          ref="confirmBtn"
          class="btn btn-sm"
          :class="pending.danger ? 'btn-danger' : 'btn-primary'"
          @click="accept"
        >
          {{ pending.confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useConfirm } from '@/composables/useConfirm'

const { pending, accept, cancel } = useConfirm()
const confirmBtn = ref(null)

// Escape cancels, the same as clicking away or pressing Cancel. Listener lives
// on the document because focus starts on the button but can be tabbed off.
function onKeydown(e) {
  if (e.key === 'Escape' && pending.value) cancel()
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

// Focus the confirm button when the dialog opens, so a keyboard user can answer
// without tabbing into it first. This is what the native confirm() did for free.
watch(pending, async (open) => {
  if (!open) return
  await nextTick()
  confirmBtn.value?.focus()
})
</script>

<style scoped>
/* The confirm is raised from inside other modals (discarding a draft, for
   one). It shares .modal-overlay, so at the same z-index the modal that
   asked the question would paint over the answer. Sit above them. */
.confirm-overlay { z-index: 1800; }
.confirm-modal { max-width: 420px; }
.confirm-message {
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.5;
}
</style>
