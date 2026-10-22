<template>
  <div class="notif-overlay" @click.self="$emit('close')">
    <div class="notif-panel">
      <div class="notif-header">
        <h3>Notifications</h3>
        <div class="notif-header-actions">
          <button
            class="notif-sound-toggle"
            :class="{ 'notif-sound-on': soundEnabled }"
            :title="soundEnabled ? 'Notification sound on — click to mute' : 'Notification sound off — click to unmute'"
            :aria-label="soundEnabled ? 'Mute notification sound' : 'Unmute notification sound'"
            @click="toggleSoundWithFeedback"
          >{{ soundEnabled ? '🔊' : '🔇' }}</button>
          <button v-if="unread > 0" class="btn btn-sm btn-outline" @click="markAll">Mark all read</button>
          <button class="modal-close" aria-label="Close" @click="$emit('close')">✕</button>
        </div>
      </div>

      <div class="notif-tabs">
        <button
          v-for="tab in tabs" :key="tab.value"
          class="notif-tab" :class="{ active: category === tab.value }"
          @click="selectTab(tab.value)"
        >{{ tab.label }}</button>
      </div>

      <div v-if="loading" class="spinner" style="padding:2rem"></div>
      <div v-else-if="notifications.length === 0" class="empty-state" style="padding:2rem">
        <div class="empty-icon">🔔</div>
        <p>No notifications yet</p>
      </div>
      <div v-else class="notif-list">
        <div
          v-for="n in notifications"
          :key="n.id"
          class="notif-item"
          :class="{ unread: !n.is_read }"
          :style="swipeStyle(n.id)"
          @click="markRead(n)"
          @touchstart="onTouchStart($event, n)"
          @touchmove="onTouchMove($event, n)"
          @touchend="onTouchEnd($event, n)"
        >
          <div class="notif-dot" :class="n.notif_type"></div>
          <div class="notif-body">
            <div class="notif-title">{{ n.title }}</div>
            <div class="notif-msg">{{ n.message }}</div>
            <div class="notif-time">{{ timeAgo(n.created_at) }}</div>
          </div>
          <div class="notif-item-actions" @click.stop>
            <button
              v-if="!n.is_read"
              class="notif-icon-btn"
              title="Mark as read"
              aria-label="Mark as read"
              @click="markRead(n)"
            >✓</button>
            <button
              class="notif-icon-btn notif-icon-btn-danger"
              title="Delete"
              aria-label="Delete"
              @click="removeNotification(n)"
            >🗑</button>
          </div>
        </div>
      </div>

      <div v-if="total > limit" class="notif-pagination">
        <button class="btn btn-xs btn-outline" :disabled="page <= 1" @click="changePage(page - 1)">‹ Prev</button>
        <span>Page {{ page }} of {{ totalPages }}</span>
        <button class="btn btn-xs btn-outline" :disabled="page >= totalPages" @click="changePage(page + 1)">Next ›</button>
      </div>

      <div class="notif-footer">
        <button class="btn btn-sm btn-outline notif-clear-btn" @click="clearAll">Clear all</button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * NotificationsPanel Component
 * Slide-over panel (drawer) for viewing and managing user notifications.
 * Filterable by category, paginated, with per-item mark-read/delete and a
 * swipe-to-dismiss gesture on mobile. Owns its own fetch/state; triggered
 * from the bell in NotificationBell.vue. The sound on/off control lives here
 * too, right where notifications are actually seen, instead of a separate
 * Settings page.
 */
import { ref, computed, onMounted } from "vue"
import api from "../api"
import { useAuthStore } from "../stores/auth"
import { useSettings } from "../composables/useSettings"
import { playNotifySound } from "../utils/notifySound"
import { timeAgo } from "../utils/timeAgo"

const emit = defineEmits(["close", "read"])
const auth = useAuthStore()
const { soundEnabled, toggleSound } = useSettings()

// Clicking this is itself a real user gesture, so turning sound on both
// unlocks browser audio and immediately confirms it works — no separate
// "test sound" step needed.
function toggleSoundWithFeedback() {
  toggleSound()
  if (soundEnabled.value) playNotifySound()
}

const notifications = ref([])
const loading = ref(true)
const unread = ref(0)
const total = ref(0)
const page = ref(1)
const limit = 10
const category = ref("all")

// Same reasoning as the full Notifications page: booking and payment
// notifications never reach an officer, so those two tabs would always be
// empty. Assignments and status changes do reach them, so All and Complaints
// stay.
const tabs = computed(() => {
  const base = [
    { value: "all", label: "All" },
    { value: "complaints", label: "Complaints" },
  ]
  if (auth.user?.role === "staff") return base
  return [
    ...base,
    { value: "bookings", label: "Bookings" },
    { value: "payments", label: "Payments" },
  ]
})

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

async function load() {
  loading.value = true
  try {
    const { data } = await api.get(`/notifications?category=${category.value}&page=${page.value}&limit=${limit}`)
    notifications.value = data.notifications
    unread.value = data.unread_count
    total.value = data.total
  } finally {
    loading.value = false
  }
}

onMounted(load)

function selectTab(value) {
  if (category.value === value) return
  category.value = value
  page.value = 1
  load()
}

function changePage(p) {
  page.value = p
  load()
}

/**
 * Mark single notification as read.
 * Updates local state and emits 'read' event to trigger badge updates.
 */
async function markRead(n) {
  if (n.is_read) return // Skip if already read
  await api.put(`/notifications/${n.id}/read`)
  n.is_read = true
  unread.value = Math.max(0, unread.value - 1)
  emit("read")
}

/**
 * Mark all notifications as read in one operation.
 */
async function markAll() {
  await api.put("/notifications/0/read")
  notifications.value.forEach(n => { n.is_read = true })
  unread.value = 0
  emit("read")
}

/**
 * Delete one notification. Citizens/staff get a reversible archive server-side
 * (same rule as Clear All); admins get a real, permanent delete. Either way it
 * just disappears from this list. If that empties the current (non-first)
 * page, steps back a page.
 */
async function removeNotification(n) {
  await api.put(`/notifications/${n.id}/archive`)
  const wasUnread = !n.is_read
  notifications.value = notifications.value.filter(x => x.id !== n.id)
  total.value = Math.max(0, total.value - 1)
  if (wasUnread) {
    unread.value = Math.max(0, unread.value - 1)
    emit("read")
  }
  if (!notifications.value.length && page.value > 1) {
    page.value -= 1
    load()
  }
}

/**
 * Clear all notifications. For citizens/staff this archives them (reversible
 * server-side, just hidden here); for admins it's a real, permanent delete —
 * the confirmation copy reflects that difference.
 */
async function clearAll() {
  const message = auth.isAdmin
    ? "This will permanently delete all your notifications. This cannot be undone. Continue?"
    : "This will clear all your notifications from this list. Continue?"
  if (!confirm(message)) return
  await api.post("/notifications/clear-all")
  notifications.value = []
  total.value = 0
  unread.value = 0
  page.value = 1
  emit("read")
}

/**
 * Format timestamp as relative time string (e.g. "2m ago", "3d ago").
 */
// Swipe-to-dismiss (mobile). Tracks drag distance per notification id and
// deletes it if the swipe passes a distance threshold on release.
const swipeState = ref({})

function onTouchStart(e, n) {
  swipeState.value[n.id] = { startX: e.touches[0].clientX, deltaX: 0, dragging: true }
}
function onTouchMove(e, n) {
  const s = swipeState.value[n.id]
  if (!s?.dragging) return
  s.deltaX = e.touches[0].clientX - s.startX
}
function onTouchEnd(e, n) {
  const s = swipeState.value[n.id]
  if (!s) return
  const dx = s.deltaX
  delete swipeState.value[n.id]
  if (Math.abs(dx) > 80) removeNotification(n)
}
function swipeStyle(id) {
  const s = swipeState.value[id]
  if (!s) return {}
  return {
    transform: `translateX(${s.deltaX}px)`,
    transition: s.dragging ? "none" : "transform 0.2s ease",
    opacity: s.dragging ? Math.max(0.3, 1 - Math.abs(s.deltaX) / 200) : 1,
  }
}
</script>

<style scoped>
.notif-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.3);
  z-index: 1500;
  display: flex;
  justify-content: flex-end;
  align-items: flex-start;
}
.notif-panel {
  width: 380px;
  max-height: 100vh;
  background: #fff;
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.notif-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.notif-header-actions { display: flex; gap: 0.5rem; align-items: center; }
.notif-header h3 { font-size: 1.05rem; font-weight: 800; color: var(--navy); }
.notif-sound-toggle {
  width: 30px; height: 30px; border-radius: 50%;
  border: 1px solid var(--border); background: var(--stone, #F1F5F9);
  cursor: pointer; font-size: 0.95rem;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.15s, border-color 0.15s;
}
.notif-sound-toggle:hover { background: var(--border); }
.notif-sound-toggle.notif-sound-on {
  background: rgba(0,82,255,0.14);
  border-color: var(--primary);
}

.notif-tabs {
  display: flex; gap: 0.35rem;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  overflow-x: auto;
}
.notif-tab {
  background: var(--stone, #F1F5F9); color: var(--text-muted);
  border: none; border-radius: 100px;
  padding: 0.35rem 0.8rem;
  font-size: 0.76rem; font-weight: 600; white-space: nowrap;
  cursor: pointer; transition: background 0.15s, color 0.15s;
}
.notif-tab.active { background: var(--primary); color: #fff; }
.notif-tab:not(.active):hover { background: var(--border); }

.notif-list { overflow-y: auto; flex: 1; }
.notif-item {
  display: flex;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
  touch-action: pan-y;
}
.notif-item:hover { background: var(--bg); }
.notif-item.unread { background: rgba(0,82,255,0.05); }
.notif-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 5px;
  background: var(--text-muted);
}
.notif-dot.info { background: var(--primary); }
.notif-dot.success { background: var(--success, #15803D); }
.notif-dot.warning { background: var(--warning, #B45309); }
.notif-title { font-size: 0.88rem; font-weight: 700; color: var(--text); }
.notif-msg { font-size: 0.83rem; color: var(--text-muted); margin-top: 0.2rem; line-height: 1.4; }
.notif-time { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem; }

.notif-item-actions {
  display: flex; flex-direction: row; gap: 0.4rem;
  flex-shrink: 0; align-items: flex-start;
}
.notif-icon-btn {
  width: 28px; height: 28px; border-radius: 8px;
  border: 1px solid var(--border); background: #fff;
  cursor: pointer; font-size: 0.85rem;
  display: flex; align-items: center; justify-content: center;
  color: var(--primary);
  transition: background 0.15s;
}
.notif-icon-btn:hover { background: var(--stone, #F1F5F9); }
.notif-icon-btn-danger { color: var(--danger, #DC2626); }
.notif-icon-btn-danger:hover { background: rgba(220,38,38,0.08); }

.notif-pagination {
  display: flex; align-items: center; justify-content: center; gap: 0.75rem;
  padding: 0.65rem; border-top: 1px solid var(--border);
  font-size: 0.78rem; color: var(--text-muted);
  flex-shrink: 0;
}

.notif-footer {
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.notif-clear-btn { width: 100%; }
</style>
