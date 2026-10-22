import { ref } from 'vue'

// Replacement for the native window.confirm(). Same one-question, two-answer
// shape, but rendered as the app's own modal so a destructive action does not
// hand the user an unstyled browser popup.
//
// Module-level singleton, the same pattern as useToast.js: one dialog is
// mounted once in App.vue, and any view can raise it without owning any markup.
// Only one question can be open at a time, which is what we want - two stacked
// confirms would be ambiguous about which one the buttons belong to.
const pending = ref(null)
let resolver = null

export function useConfirm() {
  // Returns a promise that settles true (confirmed) or false (cancelled or
  // dismissed), so a call site reads almost exactly like the confirm() it
  // replaces:  if (!await ask({ ... })) return
  function confirm({
    title = 'Are you sure?',
    message = '',
    confirmLabel = 'Confirm',
    cancelLabel = 'Cancel',
    danger = false,
  } = {}) {
    // A second question while one is open would strand the first promise
    // unresolved and leave its caller waiting forever. Answer it false first.
    settle(false)
    pending.value = { title, message, confirmLabel, cancelLabel, danger }
    return new Promise(resolve => { resolver = resolve })
  }

  function settle(answer) {
    pending.value = null
    if (resolver) {
      const done = resolver
      resolver = null
      done(answer)
    }
  }

  return {
    pending,
    confirm,
    accept: () => settle(true),
    cancel: () => settle(false),
  }
}
