<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Notifications" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Stay updated on your complaints and activities</p>
          </div>
          <button class="btn btn-secondary" @click="markAllRead" v-if="unreadCount > 0">
            Mark All Read
          </button>
        </div>

        <div class="notif-tabs">
          <button
            v-for="tab in tabs" :key="tab.value"
            class="notif-tab" :class="{ active: category === tab.value }"
            @click="selectTab(tab.value)"
          >{{ tab.label }}</button>
        </div>

        <div v-if="loading" class="spinner"></div>
        <div v-else class="notif-list">
          <div v-if="!notifications.length" class="empty-state">
            <div class="empty-icon">&#9993;</div>
            <p>No notifications yet</p>
          </div>
          <div
            v-for="n in notifications"
            :key="n.id"
            class="notif-card card"
            :class="{ unread: !n.is_read }"
            @click="markRead(n)"
          >
            <div class="notif-dot-wrap">
              <div class="notif-type-icon" :class="n.notif_type">
                {{ typeIcon(n.notif_type) }}
              </div>
              <div v-if="!n.is_read" class="unread-dot"></div>
            </div>
            <div class="notif-body">
              <div class="notif-title">{{ n.title }}</div>
              <div class="notif-msg">{{ n.message }}</div>
              <div class="notif-time">{{ fmtDate(n.created_at) }}</div>
            </div>
            <button
              class="notif-delete-btn"
              title="Delete"
              aria-label="Delete"
              @click.stop="removeNotification(n)"
            >🗑</button>
          </div>

          <div class="pagination" v-if="totalPages >= 1">
            <button class="page-btn" aria-label="Previous page" :disabled="page === 1" @click="page--">&lt;</button>
            <button
              v-for="p in totalPages" :key="p"
              class="page-btn" :class="{ active: page === p }"
              @click="page = p"
            >{{ totalPages === 1 ? 0 : p }}</button>
            <button class="page-btn" aria-label="Next page" :disabled="page === totalPages" @click="page++">&gt;</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * NotificationsView Component
 * Displays user notifications for complaints, activities, and system updates.
 * Tracks read/unread status, allows marking individual or all notifications as read.
 * Supports different notification types (info, success, warning, error, assignment, status, request).
 */
import { ref, computed, onMounted, watch } from 'vue'
import AppSidebar from '../components/AppSidebar.vue'
import AppTopbar from '../components/AppTopbar.vue'
import api from '../api'
import { useToast } from '../composables/useToast'
import { useAuthStore } from '../stores/auth'

const { error: toastError } = useToast()
const auth = useAuthStore()

// View state
const loading = ref(true)
const notifications = ref([])

// The endpoint already paginates server-side (default limit 10), so
// unread_count comes straight from it too — it always reflects *every*
// notification, not just whichever page is currently on screen.
const unreadCount = ref(0)

// Pagination — `total` is server-reported (count across all pages), so
// totalPages stays correct even though `notifications` only ever holds the
// current page's rows.
const page = ref(1)
const perPage = 10
const total = ref(0)
const totalPages = computed(() => Math.ceil(total.value / perPage))

// Category filter — same tabs/values as the notification bell dropdown, so
// switching between the two feels consistent.
const category = ref('all')
// Booking, refund and subscription notifications only ever go to the citizen
// who made the booking and to the admin who manages them, so for an officer
// those two tabs would sit permanently empty. Assignments, reassignments,
// weather holds do reach them, and all of those are "complaints" —
// so those two tabs stay.
const tabs = computed(() => {
  const base = [
    { value: 'all', label: 'All' },
    { value: 'complaints', label: 'Complaints' },
  ]
  if (auth.user?.role === 'staff') return base
  return [
    ...base,
    { value: 'bookings', label: 'Bookings' },
    { value: 'payments', label: 'Payments' },
  ]
})

function selectTab(value) {
  if (category.value === value) return
  category.value = value
  page.value = 1
  loadNotifications()
}

async function loadNotifications() {
  loading.value = true
  try {
    const res = await api.get(`/notifications?category=${category.value}&page=${page.value}&limit=${perPage}`)
    notifications.value = res.data.notifications || []
    unreadCount.value = res.data.unread_count || 0
    total.value = res.data.total ?? notifications.value.length
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to load notifications')
  } finally {
    loading.value = false
  }
}

onMounted(loadNotifications)
watch(page, loadNotifications)

/**
 * Delete one notification (archives it server-side, same as the bell
 * dropdown). If that empties the current non-first page, steps back a page
 * — otherwise just reloads the current page since a later page's rows shift
 * up to fill the gap.
 */
async function removeNotification(n) {
  try {
    await api.put(`/notifications/${n.id}/archive`)
    const wasUnread = !n.is_read
    total.value = Math.max(0, total.value - 1)
    if (wasUnread) unreadCount.value = Math.max(0, unreadCount.value - 1)
    if (notifications.value.length === 1 && page.value > 1) {
      page.value -= 1
    } else {
      await loadNotifications()
    }
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to remove notification')
  }
}

/**
 * Mark single notification as read.
 * Makes API call to update read status and updates local state.
 */
async function markRead(n) {
  if (n.is_read) return // Skip if already read
  try {
    await api.put(`/notifications/${n.id}/read`)
    n.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to mark as read')
  }
}

/**
 * Mark all notifications as read.
 * Calls API with ID 0 as convention for "all", then updates all items locally.
 */
async function markAllRead() {
  try {
    await api.put('/notifications/0/read')
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to mark all as read')
  }
}

/**
 * Map notification type to display icon.
 * Used for visual differentiation of notification categories.
 */
function typeIcon(type) {
  const icons = { info: 'i', success: '✓', warning: '!', error: '✕', assignment: '→', status: '⊙', request: '+' }
  return icons[type] || 'i'
}

/**
 * Format datetime to Indian locale.
 * Timezone: Asia/Kolkata. Includes time component for timestamp.
 */
function fmtDate(d) {
  return new Date(d).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.notif-tabs { display: flex; gap: 0.35rem; margin-bottom: 1rem; flex-wrap: wrap; }
.notif-tab {
  background: var(--stone); color: var(--text-muted);
  border: none; border-radius: 100px;
  padding: 0.35rem 0.9rem;
  font-size: 0.78rem; font-weight: 600; white-space: nowrap;
  cursor: pointer; transition: background 0.15s, color 0.15s;
}
.notif-tab.active { background: var(--primary); color: #fff; }
.notif-tab:not(.active):hover { background: var(--border); }
.notif-list { display: flex; flex-direction: column; gap: 0.6rem; max-width: 680px; }
.notif-card { display: flex; gap: 0.85rem; align-items: flex-start; cursor: pointer; transition: 0.12s; padding: 1rem 1.25rem; }
.notif-card.unread { background: #FFF0F6; border-left: 3px solid #FFB400; }
.notif-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.notif-dot-wrap { position: relative; flex-shrink: 0; }
.notif-delete-btn {
  width: 28px; height: 28px; border-radius: 8px;
  border: 1px solid var(--border); background: #fff;
  cursor: pointer; font-size: 0.85rem;
  display: flex; align-items: center; justify-content: center;
  color: var(--danger); flex-shrink: 0;
  transition: background 0.15s;
}
.notif-delete-btn:hover { background: rgba(220,38,38,0.08); }
.notif-type-icon {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.75rem; font-weight: 800;
}
.notif-type-icon.info { background: #FFF3DA; color: #A66E00; }
.notif-type-icon.success { background: #D7F5E5; color: #0E7A4F; }
.notif-type-icon.warning { background: #FFE0EE; color: #A66E00; }
.notif-type-icon.assignment { background: #FFE3ED; color: #b0123f; }
.notif-type-icon.status { background: #DFF7EC; color: #0E7A4F; }
.notif-type-icon.request { background: #FFF3DA; color: #A66E00; }
.unread-dot { width: 8px; height: 8px; background: #FFB400; border-radius: 50%; position: absolute; top: -2px; right: -2px; border: 1.5px solid #fff; }
.notif-body { flex: 1; }
.notif-title { font-size: 0.875rem; font-weight: 700; color: #5C1A41; margin-bottom: 0.2rem; }
.notif-msg { font-size: 0.82rem; color: #9B2C6F; line-height: 1.5; }
.notif-time { font-size: 0.72rem; color: #D69AB8; margin-top: 0.3rem; }
</style>
