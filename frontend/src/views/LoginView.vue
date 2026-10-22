<template>
  <div class="auth-page">
    <router-link to="/" class="back-home">← Back to Home</router-link>

    <div class="auth-shell">
      <div class="auth-brand">
        <div class="brand-content">
          <div class="brand-logo">
            <div class="logo-icon">CP</div>
            <span>Cyber Panchayat</span>
          </div>
          <h2 class="brand-heading">Welcome Back to Cyber Panchayat</h2>
          <p class="brand-sub">Your gateway to faster civic services — raise, track and resolve issues in your community.</p>
          <ul class="brand-features">
            <li><span class="feature-icon">✓</span> Track your complaints in real-time</li>
            <li><span class="feature-icon">✓</span> Book community halls &amp; facilities</li>
            <li><span class="feature-icon">✓</span> Get instant updates &amp; announcements</li>
          </ul>
        </div>
      </div>

      <div class="auth-card">
          <h1 class="auth-title">Welcome Back!</h1>
          <p class="auth-sub">Login to your account</p>

          <div v-if="error" class="alert alert-error">{{ error }}</div>

          <form @submit.prevent="handleLogin">
            <div class="form-group">
              <label>Email Address</label>
              <div class="field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>
                <input v-model="form.email" type="email" class="form-control" placeholder="Enter your email" required />
              </div>
            </div>
            <div class="form-group">
              <label>Password</label>
              <div class="input-group field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  class="form-control"
                  placeholder="Enter your password"
                  required
                />
                <button type="button" class="input-group-btn" @click="showPassword = !showPassword">
                  {{ showPassword ? '◡' : '◉' }}
                </button>
              </div>
            </div>

            <button type="submit" class="btn btn-primary btn-full" :disabled="loading">
              {{ loading ? 'Logging in...' : 'Login' }}
            </button>
          </form>

          <!-- ─── DEV ONLY: demo login shortcuts ───────────────────────────
               Temporary scaffolding while the app is being worked on. To
               remove: delete this block, the `demoAccounts` / `fillDemo`
               bits in the script, and the .demo-* rules in the style block.
               `import.meta.env.DEV` already keeps it out of a production
               build (`npm run build`), so it can't leak by accident. -->
          <div v-if="isDev" class="demo-box">
            <div class="demo-head">
              <span class="demo-tag">DEV</span>
              <span>Demo accounts — click one to fill the form</span>
            </div>
            <button
              v-for="acct in demoAccounts"
              :key="acct.email"
              type="button"
              class="demo-row"
              @click="fillDemo(acct)"
            >
              <span class="demo-role">{{ acct.role }}</span>
              <span class="demo-creds">{{ acct.email }}<span class="demo-dot">·</span>{{ acct.password }}</span>
            </button>
          </div>

          <p class="auth-switch">
            Don't have an account? <router-link to="/register">Register here</router-link>
          </p>
      </div>
    </div>
  </div>
</template>

<!-- Login logic and form handling -->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

// Form state and UI controls
const form = ref({ email: '', password: '' })
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

// ─── DEV ONLY: demo login shortcuts (see the template block above) ───
// These are the seeded accounts from the README, kept here only so the
// login form doesn't have to be retyped on every reload.
const isDev = import.meta.env.DEV
const demoAccounts = [
  { role: 'Admin', email: 'admin@civic.gov', password: 'Admin@123' },
  { role: 'Officer', email: 'rajesh@civic.gov', password: 'Staff@123' },
  { role: 'Citizen', email: 'amit@gmail.com', password: 'Citizen@123' },
]
function fillDemo(acct) {
  form.value = { email: acct.email, password: acct.password }
  error.value = ''
}

// Handle login form submission
// Authenticates user and redirects to appropriate dashboard based on role
async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(form.value.email, form.value.password)
    // Route to role-specific dashboard after successful login
    if (auth.isCitizen) router.push('/dashboard')
    else if (auth.isStaff) router.push('/staff/dashboard')
    else if (auth.isAdmin) router.push('/admin/dashboard')
  } catch (e) {
    error.value = e.response?.data?.message || 'Login failed. Please check your credentials.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: var(--bg);
  position: relative;
}
.back-home {
  position: fixed;
  top: 1.25rem;
  left: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: 999px;
  padding: 0.45rem 1rem;
  transition: all 0.15s;
  z-index: 10;
}
.back-home:hover {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.auth-shell {
  display: flex;
  width: 100%;
  min-height: 100vh;
}

/* ── Brand panel (left) — real photo of a citizen reporting an issue via phone ── */
.auth-brand {
  flex: 1 1 62%;
  position: relative;
  background:
    linear-gradient(195deg, rgba(7,26,92,0.35) 0%, rgba(0,64,204,0.88) 78%),
    url('/ui-images/login-hero.jpg') center/cover no-repeat;
  color: #fff;
  padding: 3rem 3.5rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
  min-height: 100vh;
}
.brand-content { position: relative; z-index: 2; }
.brand-logo { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 2.5rem; }
.brand-logo .logo-icon {
  width: 34px; height: 34px; background: rgba(255,255,255,0.2);
  border: 1px solid rgba(255,255,255,0.35); color: #fff;
  border-radius: 9px; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.68rem;
}
.brand-logo span { font-weight: 700; font-size: 1.05rem; }
.brand-heading { font-family: var(--font-heading); font-size: 1.85rem; font-weight: 500; line-height: 1.28; margin-bottom: 0.9rem; }
.brand-sub { font-size: 0.9rem; line-height: 1.65; opacity: 0.92; max-width: 360px; margin-bottom: 2.25rem; }
.brand-features { list-style: none; display: flex; flex-direction: column; gap: 0.9rem; }
.brand-features li { display: flex; align-items: center; gap: 0.7rem; font-size: 0.85rem; font-weight: 600; }
.feature-icon {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.32);
  display: flex; align-items: center; justify-content: center; font-size: 0.68rem;
}

.auth-card {
  flex: 1 1 38%;
  position: relative;
  background: var(--card);
  padding: 2.5rem 2.25rem;
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  overflow: hidden;
}
/* Soft corner accents so the panel doesn't read as a bare flat void */
.auth-card::before, .auth-card::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  z-index: 0;
  pointer-events: none;
}
.auth-card::before {
  width: 320px; height: 320px; top: -140px; right: -120px;
  background: radial-gradient(circle, rgba(0,82,255,0.07), transparent 70%);
}
.auth-card::after {
  width: 260px; height: 260px; bottom: -120px; left: -100px;
  background: radial-gradient(circle, rgba(77,124,255,0.06), transparent 70%);
}
.auth-card > * { position: relative; z-index: 1; width: 100%; max-width: 420px; margin-left: auto; margin-right: auto; }

.auth-title { font-size: 1.4rem; font-weight: 600; color: var(--text); margin-bottom: 0.25rem; }
.auth-sub { font-size: 0.875rem; color: var(--text-muted); margin-bottom: 1.5rem; }

.form-group { margin-bottom: 1rem; }
.form-group label { display: block; font-size: 0.82rem; font-weight: 600; color: var(--text); margin-bottom: 0.3rem; }

.field-icon { position: relative; }
.field-icon .icon {
  position: absolute; left: 0.9rem; top: 50%; transform: translateY(-50%);
  width: 16px; height: 16px; color: var(--text-muted); opacity: 0.75; pointer-events: none; z-index: 1;
}
.field-icon .form-control { padding-left: 2.5rem; }
.field-icon.input-group .input-group-btn { z-index: 1; }

/* Professional bordered field style, scoped to this page — the app-wide
   .form-control is a flat Material "filled" field; this page wants a
   cleaner Stripe/Linear-style outlined field instead. */
.auth-card .form-control {
  background: #fff;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.72rem 1rem;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.auth-card .form-control::placeholder { color: var(--text-muted); }
.auth-card .form-control:focus {
  border-color: var(--primary);
  border-bottom-width: 1.5px;
  box-shadow: 0 0 0 3px rgba(0,82,255,0.12);
}
.auth-card .field-icon .form-control { padding-left: 2.5rem; }
.auth-card .input-group .form-control { padding-right: 2.75rem; }

.btn-full { width: 100%; justify-content: center; padding: 0.65rem; font-size: 0.9rem; margin-top: 0.5rem; }

.auth-switch {
  text-align: center; margin-top: 1.25rem;
  font-size: 0.82rem; color: var(--text-muted);
}
.auth-switch a { color: var(--primary); font-weight: 700; text-decoration: underline; }


/* ─── DEV ONLY: demo login shortcuts — delete with the template block ─── */
.demo-box {
  margin-top: 1.25rem;
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-sm);
  background: rgba(0, 82, 255, 0.02);
  padding: 0.7rem;
}
.demo-head {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.demo-tag {
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--primary);
  background: rgba(0, 82, 255, 0.1);
  border-radius: 4px;
  padding: 0.12rem 0.35rem;
}
.demo-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  text-align: left;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.42rem 0.6rem;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.demo-row + .demo-row { margin-top: 0.35rem; }
.demo-row:hover {
  border-color: var(--primary);
  background: rgba(0, 82, 255, 0.04);
}
.demo-role {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text);
  flex-shrink: 0;
}
.demo-creds {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 0.7rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.demo-dot { margin: 0 0.35rem; opacity: 0.5; }

/* Below this width the image panel can't fit comfortably, so it's dropped —
   but a bare white form on its own looked plain, so this brings back a soft
   gradient backdrop and an elevated card instead of a flat full-bleed panel. */
@media (max-width: 860px) {
  .auth-page {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4.5rem 1rem 2rem;
    background: radial-gradient(circle at 20% 15%, rgba(0,82,255,0.08), transparent 45%), var(--bg);
  }
  .auth-shell { min-height: auto; }
  .auth-brand { display: none; }
  .auth-card {
    flex: none;
    min-height: auto;
    width: 100%;
    max-width: 440px;
    margin: 0 auto;
    border-radius: var(--radius-xl);
    box-shadow: var(--shadow-float);
    border: 1px solid var(--border);
  }
}
@media (max-width: 480px) {
  .auth-page { padding: 4.5rem 0.75rem 1.5rem; }
  .auth-card { padding: 2rem 1.5rem; }
}
</style>
