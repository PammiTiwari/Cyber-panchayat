<template>
  <div>
    <div class="filter-bar">
      <div class="search-wrapper">
        <input
          ref="searchInput"
          :value="search"
          type="search"
          class="form-control"
          aria-label="Search posts by keyword, location, category, or author"
          placeholder="🔍 Search posts, location, category, author...  (press /)"
          @input="search = $event.target.value"
        />
        <button
          v-if="search"
          type="button"
          class="search-clear"
          aria-label="Clear search"
          @click="search = ''"
        >✕</button>
      </div>
      <!-- Every picker reads the same way: the first option is "All …" and
           applies no filter. "None"-style options sit lower down and always
           mean "posts that have nothing in this field" — never "no filter". -->
      <!-- No "uncategorised" option here on purpose: both create-post forms
           fall back to 'general', so a post can never reach the feed without a
           category and the option would always show zero results. -->
      <select v-model="category" class="form-control filter-select" aria-label="Filter by category">
        <option value="">All categories</option>
        <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
      </select>
      <select v-model="ward" class="form-control filter-select" aria-label="Filter by ward">
        <option value="">All wards</option>
        <option v-for="w in WARDS" :key="w" :value="w">{{ w }}</option>
        <option :value="NO_VALUE">Ward not set</option>
      </select>
      <!-- Two steps, not one list. Departments only mean something for
           official posts, so they appear once "Officials only" is chosen
           instead of sitting alongside it as if they were the same choice. -->
      <select v-model="author" class="form-control filter-select" aria-label="Filter by who posted">
        <option value="">Anyone</option>
        <option :value="OFFICIALS_ONLY">Officials only</option>
        <option :value="CITIZENS_ONLY">Citizens only</option>
      </select>
      <select
        v-if="author === OFFICIALS_ONLY"
        v-model="department"
        class="form-control filter-select"
        aria-label="Filter by department"
      >
        <option value="">All departments</option>
        <option v-for="d in OFFICIAL_DEPARTMENTS" :key="d" :value="d">{{ d }}</option>
      </select>
      <button v-if="hasActiveFilters" class="btn btn-outline btn-sm clear-filters" @click="$emit('clear-all')">
        Clear Filters
      </button>
    </div>

    <FilterChips :filters="activeChips" @remove="$emit('remove-chip', $event)" />

    <div v-if="hasActiveFilters" class="filter-info">
      <span class="result-count" aria-live="polite">
        📊 {{ resultCount }} post{{ resultCount !== 1 ? 's' : '' }} found
      </span>
    </div>
  </div>
</template>

<script setup>
/**
 * PostFilterBar - the shared search + category + ward bar for the three
 * community views (citizen /feed, staff, admin).
 *
 * Presentational: filter values are v-models, the filtering itself lives in
 * usePostFilters. Owns only what belongs to the search box — the "/" focus
 * shortcut and the clear button — since it owns the input.
 */
import { ref, onMounted, onBeforeUnmount } from "vue"
import FilterChips from "./FilterChips.vue"
import {
  CATEGORIES, WARDS, OFFICIAL_DEPARTMENTS,
  NO_VALUE, OFFICIALS_ONLY, CITIZENS_ONLY,
} from "../utils/postFilters"

const search = defineModel("search", { default: "" })
const category = defineModel("category", { default: "" })
const ward = defineModel("ward", { default: "" })
const author = defineModel("author", { default: "" })
const department = defineModel("department", { default: "" })

defineProps({
  hasActiveFilters: { type: Boolean, default: false },
  activeChips: { type: Array, default: () => [] },
  resultCount: { type: Number, default: 0 },
})

defineEmits(["clear-all", "remove-chip"])

const searchInput = ref(null)

/**
 * "/" jumps to the search box, the convention from GitHub, Slack, and friends.
 * Ignored while another field has focus so it doesn't swallow a slash being
 * typed into a post or comment, and ignored alongside modifiers so it never
 * shadows a browser shortcut.
 */
function onKeydown(e) {
  if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return
  const el = e.target
  if (el?.tagName === "INPUT" || el?.tagName === "TEXTAREA" || el?.tagName === "SELECT" || el?.isContentEditable) return
  e.preventDefault()
  searchInput.value?.focus()
}

onMounted(() => window.addEventListener("keydown", onKeydown))
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
  /* Stays put while scrolling a long feed, so search is always in reach. Sits
     just under the sticky AppTopbar; the backdrop keeps post cards from showing
     through as they scroll underneath. */
  position: sticky;
  top: 0;
  z-index: 20;
  background: var(--bg);
  padding: 12px 0;
}

.search-wrapper { flex: 1; position: relative; min-width: 220px; }
.search-wrapper .form-control { padding-right: 32px; }

/* type="search" earns the right semantics and a better mobile keyboard, but
   WebKit draws its own clear button that would land on top of ours. */
.search-wrapper input[type="search"]::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}

.search-clear {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 0;
  line-height: 1;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 18px;
  font-weight: bold;
  transition: color var(--transition);
}
.search-clear:hover { color: var(--text); }

.filter-select { min-width: 150px; }
.clear-filters { white-space: nowrap; }

.filter-info {
  background: var(--accent);
  border-left: 4px solid var(--primary);
  padding: 8px 12px;
  margin-bottom: 16px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--accent-foreground);
}
.result-count { font-weight: 500; }

@media (max-width: 640px) {
  .filter-bar { flex-direction: column; align-items: stretch; }
  .search-wrapper, .filter-select { width: 100%; }
}
</style>
