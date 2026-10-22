import { ref, computed, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import {
  fmtCategory, highlightTerms, matchesPostFilters, firstQueryValue,
  NO_VALUE, OFFICIALS_ONLY, CITIZENS_ONLY,
} from "../utils/postFilters"
import { useDebouncedValue } from "./useDebounce"

/**
 * Search + category + ward filtering for the community post views.
 *
 * Shared by citizen /feed, staff, and admin community pages so all three search
 * identically. The caller owns the base list (usually already narrowed by an
 * all/mine tab) and passes it as a getter; this layer applies the text search
 * and the two dropdown filters on top.
 *
 *   const base = computed(() => tab.value === 'mine' ? mine.value : posts.value)
 *   const f = usePostFilters(base)
 *   // template: v-for="p in f.filtered" ... v-html="f.highlight(p.content)"
 *
 * Filter state is seeded from and mirrored to the URL query, so a filtered view
 * survives refresh and is shareable. `syncUrl: false` opts out for hosts that
 * manage their own query string.
 */
export function usePostFilters(baseList, { syncUrl = true } = {}) {
  const route = useRoute()
  const router = useRouter()

  const search = ref(firstQueryValue(route.query.q))
  // Typing stays instantly responsive; matching, highlighting and the URL
  // sync all wait for a pause instead of re-running on every keystroke.
  const debouncedSearch = useDebouncedValue(search, 300)
  const category = ref(firstQueryValue(route.query.category))
  const ward = ref(firstQueryValue(route.query.ward))
  const author = ref(firstQueryValue(route.query.by))
  // Seeded only when the author axis actually allows it, so a stale or
  // hand-edited "?dept=..." can't restore a filter with no visible control.
  const department = ref(
    author.value === OFFICIALS_ONLY ? firstQueryValue(route.query.dept) : ""
  )

  // Department is scoped to "Officials only". Dropping it the moment the
  // parent changes keeps the URL, the chips and the dropdowns telling the same
  // story — otherwise switching to "Citizens only" would silently keep a
  // department filter and show a permanently empty feed.
  watch(author, v => {
    if (v !== OFFICIALS_ONLY) department.value = ""
  })

  // Query split into lowercased words; every term must match (AND). Shared by
  // the filter and the highlighter so they never disagree about what matched.
  const searchTerms = computed(() =>
    debouncedSearch.value.toLowerCase().trim().split(/\s+/).filter(Boolean)
  )

  // The rule itself lives in matchesPostFilters so the three community views
  // share one definition of "matches"; this layer only supplies the state.
  const filtered = computed(() =>
    (baseList.value || []).filter(p => matchesPostFilters(p, {
      terms: searchTerms.value,
      category: category.value,
      ward: ward.value,
      author: author.value,
      department: department.value,
    }))
  )

  const hasActiveFilters = computed(() =>
    Boolean(search.value || category.value || ward.value || author.value || department.value)
  )

  // Chip text mirrors the option the user picked, so removing a chip and
  // resetting the dropdown are visibly the same action.
  const activeChips = computed(() => {
    const chips = []
    if (search.value) chips.push({ key: "search", label: `Search: "${search.value}"` })

    if (category.value === NO_VALUE) chips.push({ key: "category", label: "Category: Uncategorised" })
    else if (category.value) chips.push({ key: "category", label: `Category: ${fmtCategory(category.value)}` })

    if (ward.value === NO_VALUE) chips.push({ key: "ward", label: "Ward: Not set" })
    else if (ward.value) chips.push({ key: "ward", label: `Ward: ${ward.value}` })

    if (author.value === OFFICIALS_ONLY) chips.push({ key: "author", label: "Posted by: Officials only" })
    else if (author.value === CITIZENS_ONLY) chips.push({ key: "author", label: "Posted by: Citizens only" })

    // Its own chip, so the narrowing is removable without losing the
    // "Officials only" choice it sits under.
    if (department.value) chips.push({ key: "department", label: `Department: ${department.value}` })

    return chips
  })

  function clearFilter(key) {
    if (key === "search") search.value = ""
    else if (key === "category") category.value = ""
    else if (key === "ward") ward.value = ""
    // Clearing the parent clears the department too, via the watch above.
    else if (key === "author") author.value = ""
    else if (key === "department") department.value = ""
  }

  function clearAll() {
    search.value = ""
    category.value = ""
    ward.value = ""
    author.value = ""
    department.value = ""
  }

  function highlight(text) {
    return highlightTerms(text, searchTerms.value)
  }

  if (syncUrl) {
    // `replace` not `push`, so typing doesn't stack a history entry per
    // keystroke. Defaults are omitted to keep an unfiltered URL clean.
    watch([debouncedSearch, category, ward, author, department], () => {
      const q = { ...route.query }
      debouncedSearch.value ? (q.q = debouncedSearch.value) : delete q.q
      category.value ? (q.category = category.value) : delete q.category
      ward.value ? (q.ward = ward.value) : delete q.ward
      author.value ? (q.by = author.value) : delete q.by
      department.value ? (q.dept = department.value) : delete q.dept
      router.replace({ query: q }).catch(() => {})
    })
  }

  return {
    search, category, ward, author, department,
    searchTerms, filtered, hasActiveFilters, activeChips,
    clearFilter, clearAll, highlight,
  }
}
