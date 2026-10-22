<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Manage Users" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header">
          <p>
            View and manage all citizens and staff members
            <span v-if="!loading" class="header-count">
              &middot; {{ roleCounts.all }} account{{ roleCounts.all === 1 ? '' : 's' }}
            </span>
          </p>
        </div>

        <div class="filters card mb-6 p-4">
          <div class="role-pills-label">👤 Filter by role</div>
          <div class="role-pills">
            <button
              type="button" class="role-pill pill-all" :class="{ active: !roleFilter }"
              @click="roleFilter = ''"
            >👥 All <span class="role-pill-count">{{ roleCounts.all }}</span></button>
            <button
              type="button" class="role-pill pill-citizen" :class="{ active: roleFilter === 'citizen' }"
              @click="roleFilter = 'citizen'"
            >🏠 Citizens <span class="role-pill-count">{{ roleCounts.citizen }}</span></button>
            <button
              type="button" class="role-pill pill-staff" :class="{ active: roleFilter === 'staff' }"
              @click="roleFilter = 'staff'"
            >🛠️ Staff <span class="role-pill-count">{{ roleCounts.staff }}</span></button>
            <button
              type="button" class="role-pill pill-admin" :class="{ active: roleFilter === 'admin' }"
              @click="roleFilter = 'admin'"
            >👑 Admins <span class="role-pill-count">{{ roleCounts.admin }}</span></button>
          </div>
          <div class="flex gap-3 flex-wrap mt-3">
            <input v-model="search" type="text" class="form-control flex-1" placeholder="🔍 Search by name or email…" />
            <button v-if="hasActiveFilters" class="btn btn-outline btn-sm" @click="clearFilters">Clear Filters</button>
          </div>
          <FilterChips :filters="activeChips" @remove="clearFilter" />
          <span v-if="hasActiveFilters" class="result-count" aria-live="polite">
            📊 {{ filtered.length }} user{{ filtered.length !== 1 ? 's' : '' }} found
          </span>
        </div>

        <div v-if="loading" class="spinner"></div>
        <EmptyState
          v-else-if="!filtered.length"
          type="search"
          title="No Matching Users"
          description="No users match these filters. Try a different search or clear the role filter."
          buttonText="Clear Filters"
          @action="clearFilters"
        />
        <div v-else class="card">
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>ID</th><th>User</th><th>Role</th>
                  <th>Ward / Department</th><th>Phone</th><th>Subscription</th><th>Status</th><th>Joined</th>
                  <th class="col-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in filtered" :key="u.id">
                  <td class="text-xs text-muted">#{{ u.id }}</td>
                  <td>
                    <div class="user-cell">
                      <div class="user-mini-avatar" :class="u.role">{{ initials(u.name) }}</div>
                      <div class="user-cell-text">
                        <div class="user-cell-name">{{ u.name }}</div>
                        <div class="user-cell-email">{{ u.email }}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span :class="`role-badge role-${u.role}`">{{ u.role }}</span>
                  </td>
                  <!-- Citizens belong to a ward; officers/admin work department-wide across all wards -->
                  <td class="text-sm">{{ u.role === 'citizen' ? (u.ward || '—') : (u.department || '—') }}</td>
                  <td class="text-sm">{{ u.phone || '—' }}</td>
                  <td>
                    <!-- Premium is a citizen feature (it gates filing a complaint).
                         Showing officers and admins as "Not Subscribed" reads like a
                         gap in their account when there is nothing for them to buy. -->
                    <template v-if="u.role === 'citizen'">
                      <span v-if="subMap[u.id]?.status === 'active'" class="sub-badge sub-active">⭐ Premium</span>
                      <span v-else class="sub-badge sub-cancelled">Not Subscribed</span>
                    </template>
                    <span v-else class="sub-badge sub-na"
                          title="Premium membership applies to citizens only — officers and admins don't need one.">
                      Not needed
                    </span>
                  </td>
                  <td>
                    <span :class="u.is_active ? 'badge-active' : 'badge-inactive'">
                      {{ u.is_active ? 'Active' : 'Disabled' }}
                    </span>
                  </td>
                  <td class="text-xs text-muted col-joined">{{ fmtDate(u.created_at) }}</td>
                  <!-- Admin accounts carry no Edit/Disable: demoting or disabling
                       an admin locks that person straight out of the console, and
                       with one admin account it would leave nobody able to run the
                       system at all. The API refuses it too. -->
                  <td class="col-actions">
                    <div v-if="u.role !== 'admin'" class="flex gap-2">
                      <button :class="`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`"
                              @click="toggleActive(u)">
                        {{ u.is_active ? 'Disable' : 'Enable' }}
                      </button>
                    </div>
                    <span v-else class="no-action"
                          title="Disabling or demoting an admin would lock that person out of the console — with a single admin account it would leave nobody able to run the system.">
                      Cannot modify admin
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />
  </div>
</template>

<script setup>
/**
 * Manage Users - Roster of every account (citizens, staff, admins)
 * Filter by role, search by name or email, see subscription status and
 * ward/department. The only action here is disabling or re-enabling an
 * account; roles and wards are not edited from this screen (officers are
 * managed in Manage Officers, which knows about departments).
 * Admin accounts have no actions at all — see the table comment above.
 */
import { ref, computed, onMounted } from "vue"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import EmptyState from "../../components/EmptyState.vue"
import FilterChips from "../../components/FilterChips.vue"
import api from "../../api"
import { useDebouncedValue } from "../../composables/useDebounce"

const loading = ref(true)
const users = ref([]) // All users (citizens, staff, admins)
const subscriptions = ref([]) // Subscription status per citizen
const showNotif = ref(false)
const unread = ref(0)
const roleFilter = ref("") // Filter by citizen/staff/admin
const search = ref("")
const debouncedSearch = useDebouncedValue(search, 300)

const subMap = computed(() => {
  const m = {}
  subscriptions.value.forEach(s => { m[s.citizen_id] = s })
  return m
})

const filtered = computed(() => {
  return users.value.filter(u => {
    if (roleFilter.value && u.role !== roleFilter.value) return false
    if (debouncedSearch.value) {
      const q = debouncedSearch.value.toLowerCase()
      if (!u.name.toLowerCase().includes(q) && !u.email.toLowerCase().includes(q)) return false
    }
    return true
  })
})

// Counts always reflect the full user list regardless of the current role
// selection, so switching pills shows a stable total to compare against
// rather than the count shrinking to match whatever's currently picked.
const roleCounts = computed(() => ({
  all: users.value.length,
  citizen: users.value.filter(u => u.role === 'citizen').length,
  staff: users.value.filter(u => u.role === 'staff').length,
  admin: users.value.filter(u => u.role === 'admin').length,
}))

const hasActiveFilters = computed(() => Boolean(roleFilter.value || search.value))

const ROLE_LABELS = { citizen: "Citizens", staff: "Staff", admin: "Admins" }
const activeChips = computed(() => {
  const chips = []
  if (roleFilter.value) chips.push({ key: "role", label: `Role: ${ROLE_LABELS[roleFilter.value]}` })
  if (search.value) chips.push({ key: "search", label: `Search: "${search.value}"` })
  return chips
})

function clearFilter(key) {
  if (key === "role") roleFilter.value = ""
  else if (key === "search") search.value = ""
}

function clearFilters() {
  roleFilter.value = ""
  search.value = ""
}

onMounted(async () => {
  const [uRes, nRes, sRes] = await Promise.all([
    api.get("/admin/users"), api.get("/notifications"), api.get("/admin/subscriptions"),
  ])
  users.value = uRes.data
  unread.value = nRes.data.unread_count
  subscriptions.value = sRes.data.subscriptions
  loading.value = false
})

async function toggleActive(u) {
  const action = u.is_active ? "disable" : "enable"
  if (!confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} ${u.name}?`)) return
  await api.put(`/admin/users/${u.id}`, { is_active: !u.is_active })
  u.is_active = !u.is_active
}

function initials(name) {
  return (name || "U").split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}
</script>

<style scoped>
/* ── Table polish ──────────────────────────────────────────────────── */
.header-count { color: var(--text-muted); font-weight: 600; }

/* Name and email in one column: two columns for the same person was what
   pushed the table wider than its container and forced a horizontal scroll. */
.user-cell { display: flex; align-items: center; gap: 0.55rem; }
.user-cell-text { min-width: 0; }
.user-cell-name { font-weight: 700; font-size: 0.88rem; color: var(--text); line-height: 1.25; }
.user-cell-email {
  font-size: 0.75rem; color: var(--text-muted); line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 190px;
}

.data-table tbody tr { transition: background 0.12s; }
.data-table tbody tr:hover { background: var(--accent); }

/* The header stays put while a long roster scrolls under it. */
.data-table thead th {
  position: sticky; top: 0; z-index: 2;
  background: var(--card);
  box-shadow: inset 0 -1px 0 var(--border);
}

.col-joined { white-space: nowrap; }
.col-actions { text-align: right; }
.col-actions .flex { justify-content: flex-end; }


/* Shown instead of the row buttons on an admin account. */
.no-action {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 600;
  line-height: 1.3;
  color: var(--text-muted);
  background: var(--accent);
  border: 1px dashed var(--border);
  border-radius: 999px;
  padding: 0.28rem 0.5rem;
  cursor: help;
}

.filters.card { background: linear-gradient(180deg, var(--accent) 0%, var(--card) 120px); }
.result-count { display: block; margin-top: 0.6rem; font-size: 0.82rem; font-weight: 600; color: var(--text-muted); }

.role-pills-label {
  font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--text-muted); margin-bottom: 0.5rem;
}
.role-pills { display: flex; gap: 0.55rem; flex-wrap: wrap; }
.role-pill {
  display: inline-flex; align-items: center; gap: 0.45rem;
  background: var(--bg); border: 1.5px solid var(--border); border-radius: 100px;
  padding: 0.5rem 1rem; font-size: 0.86rem; font-weight: 700; color: var(--text-muted);
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s, border-color 0.15s, background 0.15s, color 0.15s;
}
.role-pill:hover { transform: translateY(-2px); box-shadow: 0 3px 10px rgba(0,0,0,0.08); }
.role-pill-count {
  background: rgba(0,0,0,0.07); border-radius: 100px; padding: 0.08rem 0.55rem; font-size: 0.76rem; font-weight: 800;
  transition: background 0.15s, color 0.15s;
}

/* Each role's active color matches its badge/avatar color elsewhere on this
   page (.role-badge, .user-mini-avatar), so the pill and the rows it filters
   to visually agree instead of introducing a fourth, unrelated color. */
.pill-all.active { background: var(--primary); border-color: var(--primary); color: #fff; box-shadow: 0 4px 14px rgba(0,82,255,0.3); }
.pill-citizen.active { background: #E0218A; border-color: #E0218A; color: #fff; box-shadow: 0 4px 14px rgba(224,33,138,0.3); }
.pill-staff.active { background: #D99A00; border-color: #D99A00; color: #fff; box-shadow: 0 4px 14px rgba(217,154,0,0.3); }
.pill-admin.active { background: #FF2D6F; border-color: #FF2D6F; color: #fff; box-shadow: 0 4px 14px rgba(255,45,111,0.3); }
.role-pill.active .role-pill-count { background: rgba(255,255,255,0.28); color: #fff; }

.pill-citizen:hover:not(.active) { border-color: #E0218A; color: #9B2C6F; }
.pill-staff:hover:not(.active) { border-color: #D99A00; color: #A66E00; }
.pill-admin:hover:not(.active) { border-color: #FF2D6F; color: #FF2D6F; }
.pill-all:hover:not(.active) { border-color: var(--primary); color: var(--primary); }
.user-mini-avatar {
  width: 30px; height: 30px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 0.75rem;
  flex-shrink: 0;
  background: #FFF3DA; color: #A66E00;
}
.user-mini-avatar.admin { background: rgba(255,45,111,0.15); color: #FF2D6F; }
.user-mini-avatar.staff { background: rgba(255,180,0,0.18); color: #A66E00; }
.role-badge {
  display: inline-block; padding: 0.2rem 0.7rem;
  border-radius: 100px; font-size: 0.75rem; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.04em;
}
.role-citizen { background: #FFE9F2; color: #9B2C6F; }
.role-staff { background: #FFF3DA; color: #A66E00; }
.role-admin { background: rgba(255,45,111,0.15); color: #FF2D6F; }
.badge-active { color: var(--success); font-size: 0.83rem; font-weight: 700; }
.badge-inactive { color: var(--danger); font-size: 0.83rem; font-weight: 700; }
.sub-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 100px; font-size: 0.72rem; font-weight: 700; white-space: nowrap; }
.sub-active { background: rgba(224,33,138,0.14); color: #E0218A; }
.sub-cancelled { background: rgba(148,163,184,0.2); color: #64748B; }
/* Deliberately flatter than the other two — it is an "N/A", not a status. */
.sub-na { background: transparent; border: 1px dashed var(--border); color: var(--text-muted); font-weight: 600; cursor: help; }
</style>
