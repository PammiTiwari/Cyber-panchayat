import { ref, watch } from "vue"

// Module-level singleton (same pattern as useToast.js) — persisted so the
// preference survives reloads and is shared across every component instance.
const STORAGE_KEY = "civic_notif_sound"
const soundEnabled = ref(localStorage.getItem(STORAGE_KEY) !== "false") // defaults on

watch(soundEnabled, (v) => {
  localStorage.setItem(STORAGE_KEY, String(v))
})

export function useSettings() {
  function toggleSound() {
    soundEnabled.value = !soundEnabled.value
  }
  return { soundEnabled, toggleSound }
}
