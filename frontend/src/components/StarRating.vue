<template>
  <div class="star-rating" :class="{ readonly, [`size-${size}`]: true }">
    <!-- Readonly: each star renders its own fractional fill (e.g. 4.5 shows a
         half-lit 5th star) so an average like 4.5 doesn't misleadingly round
         up to a full 5 stars. -->
    <template v-if="readonly">
      <span v-for="n in 5" :key="n" class="star-wrap">
        <span class="star star-bg">&#9733;</span>
        <span class="star star-fill" :style="{ width: fillPercent(n) + '%' }">&#9733;</span>
      </span>
    </template>
    <!-- Interactive: only whole-star input makes sense here, so a simple
         filled/unfilled toggle driven by click or hover is enough. -->
    <template v-else>
      <span
        v-for="n in 5" :key="n"
        class="star"
        :class="{ filled: n <= displayValue }"
        @click="select(n)"
        @mouseenter="hover = n"
        @mouseleave="hover = 0"
      >&#9733;</span>
    </template>
    <span v-if="showValue && modelValue" class="star-rating-num">{{ modelValue.toFixed(1) }}</span>
  </div>
</template>

<script setup>
/**
 * StarRating - shared 1-5 star picker/display.
 * Interactive by default (click to set, hover to preview); pass `readonly`
 * to render a fractional-fill display instead (used for showing an existing
 * average rating like 4.5).
 */
import { ref, computed } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  readonly: { type: Boolean, default: false },
  showValue: { type: Boolean, default: false },
  size: { type: String, default: 'md' }, // sm | md | lg
})
const emit = defineEmits(['update:modelValue'])

const hover = ref(0)
const displayValue = computed(() => hover.value || Math.round(props.modelValue))

// How full star `n` (1-5) should be, as a percentage — 100 for a star fully
// below the rating, 0 for one fully above it, and something in between for
// the single star the rating falls inside (e.g. star 5 at rating 4.5 → 50).
function fillPercent(n) {
  const value = props.modelValue || 0
  return Math.max(0, Math.min(1, value - (n - 1))) * 100
}

function select(n) {
  if (props.readonly) return
  emit('update:modelValue', n)
}
</script>

<style scoped>
.star-rating { display: inline-flex; align-items: center; gap: 0.15rem; }
.star { color: var(--outline); transition: color 0.1s; }
.star.filled { color: #F59E0B; }
.star-rating:not(.readonly) .star { cursor: pointer; }
.star-wrap { position: relative; display: inline-block; line-height: 1; }
.star-bg { color: var(--outline); }
.star-fill { position: absolute; left: 0; top: 0; overflow: hidden; white-space: nowrap; color: #F59E0B; }
.size-sm .star, .size-sm .star-wrap { font-size: 1.05rem; }
.size-md .star, .size-md .star-wrap { font-size: 1.4rem; }
.size-lg .star, .size-lg .star-wrap { font-size: 1.9rem; }
.star-rating-num { font-size: 0.85rem; font-weight: 700; color: var(--text); margin-left: 0.4rem; }
</style>
