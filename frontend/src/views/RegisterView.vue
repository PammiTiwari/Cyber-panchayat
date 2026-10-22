<!-- User registration page for creating new citizen accounts
     Validates name (letters only), email format, and password strength
     Registers user through auth API and auto-logs in on successful registration
     Routes to citizen dashboard after account creation -->

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
          <h2 class="brand-heading">Join Your Community</h2>
          <p class="brand-sub">Create an account to report issues, book facilities, and stay connected with your local panchayat.</p>
          <ul class="brand-features">
            <li><span class="feature-icon">✓</span> Quick complaint registration</li>
            <li><span class="feature-icon">✓</span> Transparent status tracking</li>
            <li><span class="feature-icon">✓</span> Ward-wise local updates</li>
          </ul>
        </div>
      </div>

      <div class="auth-card">
          <h1 class="auth-title">Create Your Account</h1>
          <p class="auth-sub">Join us and help your colony</p>

          <div v-if="error" class="alert alert-error">{{ error }}</div>
          <div v-if="success" class="alert alert-success">{{ success }}</div>

          <form @submit.prevent="handleRegister">
            <div class="form-group">
              <label>Full Name</label>
              <div class="field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <input v-model="form.name" type="text" class="form-control" placeholder="Enter full name" required />
              </div>
            </div>
            <div class="form-group">
              <label>Email Address</label>
              <div class="field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>
                <input v-model="form.email" type="email" class="form-control" placeholder="Enter email" required />
              </div>
            </div>
            <div class="form-group">
              <label>Phone Number</label>
              <div class="field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                <input v-model="form.phone" type="tel" class="form-control" placeholder="Enter 10-digit phone number" required />
              </div>
            </div>
            <div class="form-group">
              <label>Ward</label>
              <div class="field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
                <select v-model="form.ward" class="form-control" required>
                  <option value="" disabled>Select your ward</option>
                  <option v-for="w in wards" :key="w" :value="w">{{ w }}</option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Password</label>
              <div class="input-group field-icon">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                <input
                  v-model="form.password"
                  :type="showPass ? 'text' : 'password'"
                  class="form-control"
                  placeholder="Create password (min 6 characters)"
                  required
                />
                <button type="button" class="input-group-btn" @click="showPass = !showPass">
                  {{ showPass ? '◡' : '◉' }}
                </button>
              </div>
            </div>

            <button type="submit" class="btn btn-primary btn-full" :disabled="loading">
              {{ loading ? 'Registering...' : 'Register' }}
            </button>
          </form>

          <p class="auth-switch">
            Already have an account? <router-link to="/login">Login here</router-link>
          </p>
      </div>
    </div>
  </div>
</template>

<!-- Registration form logic and validation -->
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

// Form state and UI control
const form = ref({ name: '', email: '', phone: '', ward: '', password: '' })
const wards = ['Ward-1', 'Ward-2', 'Ward-3']
const showPass = ref(false)
const loading = ref(false)
const error = ref('')
const success = ref('')

// Handle registration form submission
// Validates input locally and calls auth API to create new user account
async function handleRegister() {
  error.value = ''
  const name = form.value.name.trim()

  // Validate name format: letters only, with optional spaces/dots/hyphens
  // Prevents numbers, special characters, and non-human names
  if (!/^[A-Za-z][A-Za-z\s.'-]{1,79}$/.test(name)) {
    error.value = 'Please enter a valid name — letters only, numbers are not a name'
    return
  }

  // Validate phone: exactly 10 digits
  const phone = form.value.phone.trim()
  if (!/^[0-9]{10}$/.test(phone)) {
    error.value = 'Please enter a valid 10-digit phone number'
    return
  }

  if (!form.value.ward) {
    error.value = 'Please select your ward'
    return
  }

  // Enforce minimum password length
  if (form.value.password.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }

  loading.value = true
  try {
    // Send registration request to auth store
    await auth.register({
      name,
      email: form.value.email.trim(),
      phone,
      ward: form.value.ward,
      password: form.value.password,
    })
    // Auto-login successful, redirect to citizen dashboard
    router.push('/dashboard')
  } catch (e) {
    error.value = e.response?.data?.message || 'Registration failed. Please try again.'
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
    url('/ui-images/register-hero.jpg') center/cover no-repeat;
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
