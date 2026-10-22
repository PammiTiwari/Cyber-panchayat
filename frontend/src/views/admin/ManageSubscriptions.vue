<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Manage Subscriptions" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header">
          <p>Cyber Panchayat Premium — simple pay-per-month memberships, no auto-renewal</p>
        </div>

        <div class="stats-row">
          <div class="stat-card stat-ok">
            <div class="stat-val">{{ stats.active || 0 }}</div>
            <div class="stat-lbl">Active Subscribers</div>
          </div>
          <div class="stat-card stat-muted">
            <div class="stat-val">{{ stats.cancelled || 0 }}</div>
            <div class="stat-lbl">Expired</div>
          </div>
          <div class="stat-card stat-ok">
            <div class="stat-val">₹{{ stats.monthly_recurring_revenue || 0 }}</div>
            <div class="stat-lbl">Active Plan Value</div>
          </div>
          <div class="stat-card stat-ok">
            <div class="stat-val">₹{{ stats.total_collected || 0 }}</div>
            <div class="stat-lbl">Total Collected</div>
          </div>
        </div>

        <div class="card">
          <div class="filter-bar">
            <input v-model="search" class="form-control" placeholder="Search by citizen name or email..." />
            <select v-model="statusFilter" class="form-control filter-select">
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="cancelled">Expired</option>
            </select>
          </div>

          <div v-if="loading" class="spinner"></div>
          <div v-else-if="!filtered.length" class="empty-state">
            <div class="empty-icon">⭐</div>
            <p>No subscriptions found</p>
          </div>
          <template v-else>
            <div class="table-wrapper">
              <table class="data-table sub-table">
                <colgroup>
                  <col style="width: 34%">
                  <col style="width: 18%">
                  <col style="width: 20%">
                  <col style="width: 14%">
                  <col style="width: 14%">
                </colgroup>
                <thead>
                  <tr>
                    <th>Citizen</th><th>Status</th><th>Member Since</th>
                    <th class="text-right">Total Paid</th><th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in filtered" :key="s.id" :class="`row-${s.status}`">
                    <td>
                      <div class="citizen-cell">
                        <div class="avatar" :class="`avatar-${s.status}`">{{ initials(s.citizen_name) }}</div>
                        <div>
                          <div class="font-bold">{{ s.citizen_name }}</div>
                          <div class="td-sub">{{ s.citizen_email }}</div>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span :class="['badge', statusBadge(s).cls]">{{ statusBadge(s).label }}</span>
                      <div v-if="s.status === 'cancelled'" class="td-sub">Expired {{ fmtDateOnly(s.next_billing_date) }}</div>
                    </td>
                    <td class="text-sm">{{ fmtDate(s.started_at) }}</td>
                    <td class="text-sm text-right font-semibold">₹{{ lifetimePaid(s) }}</td>
                    <td>
                      <router-link :to="`/admin/subscriptions/${s.id}`" class="btn btn-xs btn-primary">View</router-link>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
        </div>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />
  </div>
</template>

<script setup>
/**
 * Manage Subscriptions - Admin view of Premium subscription revenue and analytics
 * Tracks: active subscribers, revenue, payment status
 * Simple pay-per-month model, no auto-renewal: active → expired → (resubscribed) → active
 * Key metric for business analytics and citizen engagement
 */
import { ref, computed, onMounted } from "vue"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import api from "../../api"
import { useDebouncedValue } from "../../composables/useDebounce"

const loading = ref(true)
const subscriptions = ref([]) // All citizen subscriptions
const stats = ref({}) // Subscription stats (active, expired, plan value, total collected)
const showNotif = ref(false)
const unread = ref(0)
const statusFilter = ref("") // Filter by active/cancelled
const search = ref("")
const debouncedSearch = useDebouncedValue(search, 300)

function statusBadge(s) {
  if (s.status === "active") return { label: "Active", cls: "badge-confirmed" }
  return { label: "Expired", cls: "badge-cancelled" }
}

const filtered = computed(() => {
  let list = subscriptions.value
  if (statusFilter.value) list = list.filter(s => s.status === statusFilter.value)
  if (debouncedSearch.value) {
    const q = debouncedSearch.value.toLowerCase()
    list = list.filter(s =>
      s.citizen_name?.toLowerCase().includes(q) ||
      s.citizen_email?.toLowerCase().includes(q)
    )
  }
  return list
})

onMounted(async () => {
  const [sRes, nRes] = await Promise.all([api.get("/admin/subscriptions"), api.get("/notifications")])
  subscriptions.value = sRes.data.subscriptions
  stats.value = sRes.data.stats
  unread.value = nRes.data.unread_count
  loading.value = false
})

function initials(name) {
  if (!name) return "?"
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] || "") + (parts[1]?.[0] || "")).toUpperCase()
}

// Total actually collected from this citizen across every cycle they've ever
// paid for — unlike a single "last invoice" badge (which is "Paid" for nearly
// everyone and says nothing useful), this varies meaningfully row to row.
function lifetimePaid(s) {
  return (s.payments || []).filter(p => p.status === "paid").reduce((sum, p) => sum + p.amount, 0)
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}
function fmtDateOnly(d) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}

</script>

<style scoped>
.sub-table { table-layout: fixed; }
.sub-table td, .sub-table th { overflow: hidden; text-overflow: ellipsis; }

.stats-row { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 150px;
  background: #fff; border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem 1.1rem;
}
.stat-val { font-size: 1.5rem; font-weight: 800; color: var(--text); line-height: 1; }
.stat-lbl { font-size: 0.7rem; color: var(--text-muted); margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.04em; }
.stat-ok   .stat-val { color: var(--primary); }
.stat-muted .stat-val { color: var(--text-muted); }
.badge-confirmed { background: rgba(21,128,61,0.14); color: var(--success); }
.badge-cancelled { background: rgba(148,163,184,0.2); color: #64748B; }
.td-sub { font-size: 0.75rem; color: var(--text-muted); }
.filter-bar { display: flex; gap: 0.75rem; padding: 1rem; }
.filter-select { max-width: 200px; }

.citizen-cell { display: flex; align-items: center; gap: 0.65rem; }
.avatar {
  width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.72rem; font-weight: 700; color: #fff;
  background: #94A3B8;
}
.avatar-active { background: var(--success); }
.avatar-cancelled { background: #94A3B8; }

/* A thin left accent per row echoes the status badge at a glance, without
   needing to read the badge text row by row while scanning the table. */
.row-active { box-shadow: inset 3px 0 0 var(--success); }
.row-cancelled { box-shadow: inset 3px 0 0 #CBD5E1; }
</style>
