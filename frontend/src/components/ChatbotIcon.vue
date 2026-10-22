<template>
  <svg
    class="chatbot-icon"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
  >
    <!-- The face is cut out of the silhouette rather than painted on top, so the
         eyes and smile show whatever sits behind the icon (the gradient bubble,
         the white header disc, the tinted message avatar). That way one
         component works on every background without a per-context fill. -->
    <mask :id="maskId">
      <rect width="24" height="24" fill="black" />
      <circle cx="12" cy="2.7" r="1.35" fill="white" />
      <rect x="11.4" y="3.5" width="1.2" height="2.1" fill="white" />
      <rect x="1" y="9.4" width="2.6" height="5" rx="1.3" fill="white" />
      <rect x="20.4" y="9.4" width="2.6" height="5" rx="1.3" fill="white" />
      <rect x="3.4" y="5.5" width="17.2" height="13.2" rx="4.6" fill="white" />
      <circle cx="9.1" cy="11.3" r="1.75" fill="black" />
      <circle cx="14.9" cy="11.3" r="1.75" fill="black" />
      <path
        d="M9.3 14.9c.85.95 4.55.95 5.4 0"
        stroke="black"
        stroke-width="1.35"
        stroke-linecap="round"
        fill="none"
      />
    </mask>
    <rect width="24" height="24" fill="currentColor" :mask="`url(#${maskId})`" />
  </svg>
</template>

<script setup>
/**
 * ChatbotIcon - brand mark for the help assistant.
 *
 * Draws in `currentColor`, so each call site picks the colour with plain CSS
 * and theme tokens rather than props. Replaces the old raster
 * chatbot-icon.jpg, whose purple/cyan palette fought the blue brand and went
 * soft when scaled down into the 22px message avatars.
 */
import { useId } from "vue"

// Several copies render at once (bubble, header, every bot message). Duplicate
// mask ids in one document make the browser resolve them all to the first
// match, so the id has to be per-instance.
const maskId = `chatbot-icon-mask-${useId()}`
</script>

<style scoped>
.chatbot-icon {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
