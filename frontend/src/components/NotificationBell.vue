<template>
  <button class="notif-bell" @click="showNotif = true" aria-label="Notifications">
    🔔
    <span v-if="unread > 0" class="notif-badge">{{ unread > 9 ? '9+' : unread }}</span>
  </button>
  <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0, unread - 1)" />
</template>

<script setup>
/**
 * NotificationBell - the unread badge + quick-access panel trigger.
 * Deliberately only used on the three dashboard pages (citizen/staff/admin),
 * not globally, per product decision — the sidebar's plain "Notifications"
 * link remains the always-available way to reach the full list from any page.
 */
import { onMounted, onUnmounted, ref } from "vue"
import api from "../api"
import NotificationsPanel from "./NotificationsPanel.vue"
import { useAuthStore } from "../stores/auth"
import { useSettings } from "../composables/useSettings"
import { playNotifySound } from "../utils/notifySound"

const auth = useAuthStore()
const { soundEnabled } = useSettings()
const showNotif = ref(false)
const unread = ref(0)
let hasLoadedOnce = false // first fetch this mount just establishes the baseline for ongoing comparisons
let pollTimer = null
// Module-level (not reset on remount) — which user we've already done the
// "you have unread notifications waiting" login-check for, so revisiting the
// dashboard later in the same session doesn't replay it. A different user
// logging in (role switch) gets their own one-time check.
let welcomedUserId = null

async function refreshUnread() {
  try {
    const { data } = await api.get("/notifications")
    const uid = auth.user?.id
    if (!hasLoadedOnce) {
      if (uid && welcomedUserId !== uid && data.unread_count > 0 && soundEnabled.value) {
        playNotifySound()
      }
      if (uid) welcomedUserId = uid
    } else if (data.unread_count > unread.value && soundEnabled.value) {
      playNotifySound()
    }
    unread.value = data.unread_count
    hasLoadedOnce = true
  } catch {
    // Badge is a nice-to-have — a failed poll shouldn't surface an error.
  }
}

onMounted(() => {
  refreshUnread()
  pollTimer = setInterval(refreshUnread, 30000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<style scoped>
.notif-bell {
  position: fixed;
  top: 18px; right: 24px;
  z-index: 1300;
  width: 40px; height: 40px; border-radius: 50%;
  border: 1px solid var(--border);
  background: #fff;
  cursor: pointer;
  font-size: 1.05rem;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.notif-bell:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
.notif-badge {
  position: absolute; top: -4px; right: -4px;
  min-width: 18px; height: 18px; padding: 0 4px;
  border-radius: 100px;
  background: var(--danger, #DC2626); color: #fff;
  font-size: 0.65rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center;
  border: 2px solid #fff;
}

@media (max-width: 640px) {
  .notif-bell { top: 12px; right: 12px; width: 36px; height: 36px; }
}
</style>
