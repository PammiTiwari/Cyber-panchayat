<template>
  <div class="notfound">
    <div class="notfound-card">
      <div class="notfound-code">404</div>
      <h1 class="notfound-title">Page not found</h1>
      <p class="notfound-text">
        The page you're looking for doesn't exist, or may have moved. Check the
        address, or head back to somewhere familiar.
      </p>
      <div class="notfound-actions">
        <router-link :to="homePath" class="btn btn-primary">
          {{ auth.isLoggedIn ? 'Back to Dashboard' : 'Back to Home' }}
        </router-link>
        <button class="btn btn-outline" @click="goBack">Go back</button>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * NotFound - shown for any URL that doesn't match a route.
 *
 * Replaces the old silent redirect-to-home, which left a mistyped or dead link
 * indistinguishable from being logged out. "Home" points at the signed-in
 * user's own dashboard when there is one, so the way out never lands them on a
 * page their role can't use.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

// Same role-to-home mapping the sidebar uses, so a signed-in user is sent to a
// page they can actually see rather than a generic landing.
const homePath = computed(() => {
  if (!auth.isLoggedIn) return '/'
  if (auth.isAdmin) return '/admin/dashboard'
  if (auth.isStaff) return '/staff/dashboard'
  return '/dashboard'
})

// "Go back" only helps if there's real history to return to; landing on the
// 404 as the first page (a pasted bad link) has none, so fall back to home.
function goBack() {
  if (window.history.length > 1) router.back()
  else router.push(homePath.value)
}
</script>

<style scoped>
.notfound {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.25rem;
  background: var(--bg);
}
.notfound-card {
  max-width: 460px;
  text-align: center;
}
.notfound-code {
  font-size: 5.5rem;
  font-weight: 800;
  line-height: 1;
  color: var(--primary);
  letter-spacing: -0.03em;
}
.notfound-title {
  margin: 0.5rem 0 0.75rem;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
}
.notfound-text {
  color: var(--text-muted);
  font-size: 0.92rem;
  line-height: 1.6;
  margin: 0 0 1.75rem;
}
.notfound-actions {
  display: flex;
  gap: 0.6rem;
  justify-content: center;
  flex-wrap: wrap;
}

@media (max-width: 480px) {
  .notfound-code { font-size: 4rem; }
  .notfound-actions { flex-direction: column; }
  .notfound-actions > * { width: 100%; }
}
</style>
