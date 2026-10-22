<template>
  <aside class="sidebar">
    <!-- Brand -->
    <router-link :to="homePath" class="sidebar-brand">
      <span class="logo-mark">CP</span>
      <span class="brand-name">Cyber Panchayat</span>
    </router-link>

    <!-- Nav links -->
    <nav class="sidebar-nav">
      <template v-for="item in navItems" :key="item.label">
        <router-link v-if="item.type === 'link'" :to="item.path" class="nav-link" :class="{ active: isActive(item) }">
          {{ item.label }}
        </router-link>
        <div v-else class="nav-group">
          <div class="nav-group-label">{{ item.label }}</div>
          <router-link
            v-for="sub in item.items"
            :key="sub.label"
            :to="sub.query ? { path: sub.path, query: sub.query } : sub.path"
            class="nav-link nav-sublink"
            :class="{ active: isActive(sub) }"
          >
            {{ sub.label }}
          </router-link>
        </div>
      </template>
    </nav>

    <!-- Bottom: notifications + user -->
    <div class="sidebar-footer">
      <router-link to="/notifications" class="footer-link">
        <span>Notifications</span>
      </router-link>

      <router-link to="/faq" class="footer-link">
        <span>Help and FAQ</span>
      </router-link>

      <button class="footer-link logout-link" @click="logout" title="Logout">
        <span>&#10132; Logout</span>
      </button>

      <!-- Only citizens have a profile page to go to (ProfileView.vue is
           citizen-only) — for staff/admin this stays a plain display. -->
      <component :is="auth.isCitizen ? 'router-link' : 'div'" :to="auth.isCitizen ? '/profile' : undefined" class="user-section">
        <div class="user-avatar">{{ userInitial }}</div>
        <div class="user-info">
          <div class="user-name">{{ auth.user?.name }}</div>
          <div class="user-role">{{ roleLabel }}</div>
        </div>
      </component>
    </div>
  </aside>
</template>

<script setup>
/**
 * AppSidebar Component
 * Main navigation sidebar with role-based menu items (citizen/staff/admin).
 * Displays user profile and logout button. The unread notification badge
 * lives on NotificationBell.vue (dashboard pages only) instead of here, to
 * avoid two separate live badges for the same count.
 * Menu items conditionally render based on user role.
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// Computed properties for display
const userInitial = computed(() => auth.user?.name?.charAt(0)?.toUpperCase() || 'U')
const roleLabel = computed(() => auth.role ? auth.role.charAt(0).toUpperCase() + auth.role.slice(1) : '')

// Determine home path based on role (admin/staff/citizen)
const homePath = computed(() => {
  if (auth.isAdmin) return '/admin/dashboard'
  if (auth.isStaff) return '/staff/dashboard'
  return '/dashboard'
})

/**
 * Clear auth state and redirect to login page.
 */
function logout() {
  auth.logout()
  router.push('/login')
}

/**
 * Determine if a nav item matches current route.
 * Supports exact match mode and prefix matching for nested routes.
 */
// Every nav entry, groups flattened, so the rules below can look at siblings.
const flatNav = computed(() =>
  navItems.value.flatMap(n => n.type === 'link' ? [n] : n.items)
)

function isActive(item) {
  if (!item.path) return false

  // Two entries can share a path and differ only by their query — Book Facility
  // is /facilities, My Favourites is /facilities?fav=1. The filtered one matches
  // only when its query is on the route...
  if (item.query) {
    return route.path === item.path &&
      Object.entries(item.query).every(([k, v]) => String(route.query[k]) === String(v))
  }
  // ...and the plain one steps aside while the filtered one is showing, so the
  // group never lights up twice.
  if (flatNav.value.some(n => n !== item && n.path === item.path && n.query && isActive(n))) {
    return false
  }

  if (item.exact) return route.path === item.path
  if (route.path === item.path) return true
  if (!route.path.startsWith(item.path + '/')) return false

  // A prefix match like "/complaints" matching "/complaints/track" would
  // otherwise also light up "My Complaints" while on the separate "Track
  // Complaint" page — back off if a sibling nav item is a more specific
  // (longer) match for the current route.
  const allPaths = flatNav.value.map(n => n.path)
  const moreSpecificMatch = allPaths.some(p =>
    p !== item.path &&
    p.startsWith(item.path + '/') &&
    (route.path === p || route.path.startsWith(p + '/'))
  )
  return !moreSpecificMatch
}

const citizenNav = [
  { type: 'link',  label: 'Dashboard',      path: '/dashboard', exact: true },
  { type: 'group', label: 'Complaints', items: [
    { label: 'Submit Complaint', path: '/submit' },
    { label: 'My Complaints',    path: '/complaints' },
    { label: 'All Complaints',   path: '/complaints/all' },
    { label: 'Track Complaint',  path: '/complaints/track' },
  ]},
  { type: 'group', label: 'Facilities', items: [
    { label: 'Book Facility', path: '/facilities' },
    { label: 'My Bookings',   path: '/bookings' },
  ]},
  { type: 'link', label: 'Premium Subscription', path: '/subscription' },
  { type: 'group', label: 'Community', items: [
    { label: 'Community Feed', path: '/feed' },
    { label: 'Announcements',  path: '/announcements' },
  ]},
]

const staffNav = [
  { type: 'link', label: 'Dashboard',          path: '/staff/dashboard', exact: true },
  { type: 'link', label: 'Assigned Complaints', path: '/staff/complaints' },
  { type: 'link', label: 'All Complaints',      path: '/staff/complaints/all' },
  { type: 'link', label: 'Community Posts',     path: '/staff/community' },
  { type: 'link', label: 'Announcements',       path: '/announcements' },
]

const adminNav = [
  { type: 'link',  label: 'Dashboard', path: '/admin/dashboard', exact: true },
  { type: 'group', label: 'Complaints', items: [
    { label: 'Complaints',  path: '/admin/complaints' },
    { label: 'Departments', path: '/admin/departments' },
    { label: 'Officers',    path: '/admin/officers' },
  ]},
  { type: 'group', label: 'Resources', items: [
    { label: 'Facilities',     path: '/admin/facilities' },
    { label: 'Bookings',       path: '/admin/bookings' },
    { label: 'Subscriptions',  path: '/admin/subscriptions' },
  ]},
  { type: 'link', label: 'Users',         path: '/admin/users' },
  { type: 'link', label: 'Community',     path: '/admin/community' },
  { type: 'link', label: 'Announcements', path: '/announcements' },
]

const navItems = computed(() => {
  if (auth.isAdmin) return adminNav
  if (auth.isStaff) return staffNav
  return citizenNav
})
</script>

<style scoped>
.sidebar {
  width: 220px;
  min-width: 220px;
  height: 100vh;
  position: sticky;
  top: 0;
  background: var(--surface-dark);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  z-index: 100;
}

/* Brand */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 1.25rem 1rem;
  text-decoration: none;
  border-bottom: 1px solid rgba(255,255,255,0.07);
  flex-shrink: 0;
}
.logo-mark {
  width: 32px; height: 32px;
  background: var(--primary);
  color: #fff;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.7rem;
  flex-shrink: 0;
}
.brand-name {
  font-weight: 700;
  font-size: 0.88rem;
  color: #fff;
  white-space: nowrap;
}

/* Nav */
.sidebar-nav {
  flex: 1;
  padding: 0.75rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
}
.nav-link {
  display: block;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  color: #93A3C2;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  transition: var(--transition);
}
.nav-link:hover  { background: rgba(255,255,255,0.06); color: #fff; }
.nav-link.active { background: rgba(0,82,255,0.2); color: #fff; }
.nav-sublink     { padding-left: 1.25rem; font-size: 0.8rem; }

.nav-group { margin-top: 0.5rem; }
.nav-group-label {
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #6B7A99;
  padding: 0.4rem 0.75rem 0.25rem;
}

/* Footer */
.sidebar-footer {
  border-top: 1px solid rgba(255,255,255,0.07);
  padding: 0.75rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  flex-shrink: 0;
}
.footer-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  color: #93A3C2;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  transition: var(--transition);
}
.footer-link:hover { background: rgba(255,255,255,0.06); color: #fff; }
.logout-link { width: 100%; background: none; border: none; cursor: pointer; font-family: inherit; }
.logout-link:hover { color: var(--danger); }

.user-section {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.04);
  text-decoration: none;
  color: inherit;
  transition: background var(--transition);
}
a.user-section { cursor: pointer; }
a.user-section:hover { background: rgba(255,255,255,0.09); }
.user-avatar {
  width: 30px; height: 30px;
  background: var(--primary);
  color: #fff;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.72rem; font-weight: 700;
  flex-shrink: 0;
}
.user-info { flex: 1; min-width: 0; }
.user-name {
  font-size: 0.8rem;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-role {
  font-size: 0.65rem;
  color: #6B7A99;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
