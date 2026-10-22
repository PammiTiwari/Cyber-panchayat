<template>
  <!-- Logged in: the normal app layout, so Help sits with every other page.
       Logged out: a plain header, because the sidebar shows role-based menus and
       a user card that a visitor has nothing to fill in. Both use one route on
       purpose. The chat assistant only shows for logged-in users, so this page
       is the only help someone can read before they sign up. -->
  <div v-if="auth.isLoggedIn" class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Help &amp; FAQ" />
      <div class="content-area">
        <FaqBrowser />
      </div>
    </div>
  </div>

  <div v-else class="faq-public">
    <nav class="faq-public-nav">
      <router-link to="/" class="faq-brand">
        <div class="brand-icon">CP</div>
        <span class="brand-name">Cyber Panchayat</span>
      </router-link>
      <div class="faq-public-actions">
        <router-link to="/login" class="btn btn-sm btn-outline">Login</router-link>
        <router-link to="/register" class="btn btn-sm btn-primary">Register</router-link>
      </div>
    </nav>

    <main class="faq-public-body">
      <FaqBrowser />
    </main>

    <footer class="faq-public-foot">
      <router-link to="/">&larr; Back to home</router-link>
    </footer>
  </div>
</template>

<script setup>
/**
 * FAQ - public Help & FAQ page.
 *
 * All content lives in FaqBrowser (which reads the same tree as the chat
 * assistant); this component only decides which chrome to wrap it in.
 */
import AppSidebar from '../components/AppSidebar.vue'
import AppTopbar from '../components/AppTopbar.vue'
import FaqBrowser from '../components/FaqBrowser.vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
</script>

<style scoped>
.faq-public { min-height: 100vh; background: var(--bg); display: flex; flex-direction: column; }

.faq-public-nav {
  display: flex; align-items: center; justify-content: space-between;
  gap: 1rem; padding: 0.9rem 1.5rem;
  background: var(--card); border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 10;
}
.faq-brand { display: flex; align-items: center; gap: 0.6rem; text-decoration: none; }
.brand-icon {
  width: 34px; height: 34px; border-radius: var(--radius-sm);
  background: var(--primary); color: #fff;
  display: grid; place-items: center; font-weight: 800; font-size: 0.85rem;
}
.brand-name { font-weight: 800; color: var(--text); }
.faq-public-actions { display: flex; gap: 0.5rem; }

.faq-public-body { flex: 1; padding: 2rem 1.5rem; }

.faq-public-foot {
  padding: 1.25rem 1.5rem 2rem; text-align: center;
  border-top: 1px solid var(--border);
}
.faq-public-foot a { color: var(--text-muted); font-size: 0.85rem; font-weight: 600; text-decoration: none; }
.faq-public-foot a:hover { color: var(--primary); }

@media (max-width: 640px) {
  .faq-public-nav { padding: 0.75rem 1rem; }
  .brand-name { display: none; }
  .faq-public-body { padding: 1.25rem 1rem; }
}
</style>
