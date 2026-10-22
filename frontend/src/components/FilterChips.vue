<template>
  <div v-if="filters.length" class="filter-chips">
    <span class="filter-chips-label">Filtering by</span>
    <button
      v-for="f in filters"
      :key="f.key"
      type="button"
      class="filter-chip"
      :title="`Remove ${f.label}`"
      @click="$emit('remove', f.key)"
    >
      {{ f.label }}
      <span class="filter-chip-x" aria-hidden="true">✕</span>
    </button>
  </div>
</template>

<script setup>
/**
 * FilterChips - removable pills summarising the filters currently applied.
 *
 * Pages with several filters spread across selects, date inputs, and a search
 * box make it hard to see at a glance why a list looks short. Each chip names
 * one active filter and clears just that one on click, so narrowing down and
 * backing out again doesn't mean hunting for which control to reset.
 */
defineProps({
  // [{ key: 'status', label: 'Status: Resolved' }] — `key` is echoed back on
  // remove so the parent knows which filter to clear.
  filters: { type: Array, default: () => [] },
})

defineEmits(["remove"])
</script>

<style scoped>
.filter-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.85rem;
}

.filter-chips-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: var(--accent);
  color: var(--accent-foreground);
  border: 1px solid transparent;
  border-radius: 100px;
  padding: 0.28rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition), border-color var(--transition);
}

.filter-chip:hover {
  background: rgba(0, 82, 255, 0.16);
  border-color: var(--primary);
}

.filter-chip-x {
  font-size: 0.65rem;
  opacity: 0.7;
}

.filter-chip:hover .filter-chip-x {
  opacity: 1;
}
</style>
