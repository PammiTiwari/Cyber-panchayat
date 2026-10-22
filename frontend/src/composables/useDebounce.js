import { ref, watch, onBeforeUnmount } from 'vue'

// Tracks `source` but only updates its own value `delay`ms after typing
// pauses, so a search box stays instantly responsive to keystrokes while
// whatever reads the debounced value (a filter, a URL sync, an API call)
// only re-runs once the user stops typing.
export function useDebouncedValue(source, delay = 300) {
  const debounced = ref(source.value)
  let timer = null

  watch(source, (val) => {
    clearTimeout(timer)
    timer = setTimeout(() => { debounced.value = val }, delay)
  })

  onBeforeUnmount(() => clearTimeout(timer))

  return debounced
}
