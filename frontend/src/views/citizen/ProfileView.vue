<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="My Profile" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header">
          <p>Manage your personal information and account security</p>
        </div>

        <div class="profile-hero">
          <div class="profile-hero-avatar">{{ userInitial }}</div>
          <div class="profile-hero-info">
            <h1 class="profile-hero-name">{{ auth.user?.name }}</h1>
            <p class="profile-hero-email">{{ auth.user?.email }}</p>
            <div class="profile-hero-chips">
              <span class="profile-chip">Citizen</span>
              <span v-if="auth.user?.ward" class="profile-chip profile-chip-ward">&#128205; {{ auth.user.ward }}</span>
              <span v-if="auth.user?.created_at" class="profile-hero-since">Member since {{ fmtJoined(auth.user.created_at) }}</span>
            </div>
          </div>
        </div>

        <div class="profile-grid">
          <div class="card profile-card">
            <h2 class="profile-card-title">
              <span class="profile-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              </span>
              Personal Information
            </h2>
            <div v-if="profileError" class="alert alert-error">{{ profileError }}</div>
            <div v-if="profileSuccess" class="alert alert-success">{{ profileSuccess }}</div>

            <div class="form-group">
              <label>Name</label>
              <input v-model="profileForm.name" class="form-control" placeholder="Your full name" maxlength="80" />
            </div>
            <div class="form-group">
              <label>Phone Number</label>
              <input v-model="profileForm.phone" type="tel" class="form-control" placeholder="10-digit mobile number" maxlength="10" />
            </div>
            <div class="form-group">
              <label>Ward</label>
              <select v-model="profileForm.ward" class="form-control">
                <option v-for="w in wards" :key="w" :value="w">{{ w }}</option>
              </select>
              <!-- Only this row changes. Complaints, bookings, and posts already
                   submitted keep the ward they were filed under, since that's a
                   record of where the issue/booking/post actually was — not a
                   live pointer back to whatever the citizen's ward is today. -->
              <p class="field-hint">Changing your ward only updates your profile — complaints, bookings, and posts you've already submitted keep the ward they were filed under.</p>
            </div>
            <div class="form-actions">
              <button class="btn btn-primary" :disabled="savingProfile" @click="saveProfile">
                {{ savingProfile ? 'Saving…' : 'Save Changes' }}
              </button>
            </div>
          </div>

          <div class="card profile-card">
            <h2 class="profile-card-title">
              <span class="profile-card-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              </span>
              Change Password
            </h2>
            <div v-if="passwordError" class="alert alert-error">{{ passwordError }}</div>
            <div v-if="passwordSuccess" class="alert alert-success">{{ passwordSuccess }}</div>

            <div class="form-group">
              <label>Current Password</label>
              <input v-model="passwordForm.current" type="password" autocomplete="current-password" class="form-control" placeholder="Enter your current password" />
            </div>
            <div class="form-group">
              <label>New Password</label>
              <input v-model="passwordForm.next" type="password" autocomplete="new-password" class="form-control" placeholder="At least 6 characters" />
            </div>
            <div class="form-group">
              <label>Confirm New Password</label>
              <input v-model="passwordForm.confirm" type="password" autocomplete="new-password" class="form-control" placeholder="Re-enter new password" />
            </div>
            <div class="form-actions">
              <button class="btn btn-primary" :disabled="savingPassword" @click="changePassword">
                {{ savingPassword ? 'Updating…' : 'Update Password' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0, unread - 1)" />
  </div>
</template>

<script setup>
/**
 * Citizen self-service profile page: edit name/phone/ward, and change password.
 * Ward is stored only on the user's own row — editing it here never touches
 * ward values already recorded on the citizen's complaints, bookings, or posts.
 */
import { ref, computed, onMounted } from "vue"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import { useAuthStore } from "../../stores/auth"
import api from "../../api"

const auth = useAuthStore()

const showNotif = ref(false)
const unread = ref(0)
const userInitial = computed(() => auth.user?.name?.charAt(0)?.toUpperCase() || "U")

function fmtJoined(d) {
  return new Date(d).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", month: "long", year: "numeric" })
}

// Matches the ward options offered at registration (RegisterView.vue) — no
// "Central", since that's the city's own designation, not one citizens pick.
const wards = ["Ward-1", "Ward-2", "Ward-3"]

// Same patterns the backend enforces (NAME_RE / PHONE_RE in api.py) — checked
// here too so a bad value is caught instantly instead of after a round trip.
const NAME_RE = /^[A-Za-z][A-Za-z\s.'-]{1,79}$/
const PHONE_RE = /^[6-9]\d{9}$/

const profileForm = ref({ name: "", phone: "", ward: "" })
const savingProfile = ref(false)
const profileError = ref("")
const profileSuccess = ref("")

const passwordForm = ref({ current: "", next: "", confirm: "" })
const savingPassword = ref(false)
const passwordError = ref("")
const passwordSuccess = ref("")

onMounted(async () => {
  profileForm.value = {
    name: auth.user?.name || "",
    phone: auth.user?.phone || "",
    ward: auth.user?.ward || wards[0],
  }
  try {
    const nRes = await api.get("/notifications")
    unread.value = nRes.data.unread_count
  } catch (e) {
    console.error(e)
  }
})

async function saveProfile() {
  profileError.value = ""
  profileSuccess.value = ""
  const name = profileForm.value.name.trim()
  if (!NAME_RE.test(name)) {
    profileError.value = "Please enter a valid name — letters only, numbers are not a name"
    return
  }
  const phone = profileForm.value.phone.trim()
  if (phone && !PHONE_RE.test(phone)) {
    profileError.value = "Phone must be a valid 10-digit mobile number"
    return
  }
  savingProfile.value = true
  try {
    await api.put("/auth/me", {
      name: profileForm.value.name.trim(),
      phone: profileForm.value.phone.trim(),
      ward: profileForm.value.ward,
    })
    await auth.refreshMe()
    profileSuccess.value = "Profile updated successfully"
  } catch (e) {
    profileError.value = e.response?.data?.message || "Could not update profile"
  } finally {
    savingProfile.value = false
  }
}

async function changePassword() {
  passwordError.value = ""
  passwordSuccess.value = ""
  if (!passwordForm.value.current) {
    passwordError.value = "Enter your current password"
    return
  }
  if (passwordForm.value.next.length < 6) {
    passwordError.value = "New password must be at least 6 characters"
    return
  }
  if (passwordForm.value.next !== passwordForm.value.confirm) {
    passwordError.value = "New password and confirmation don't match"
    return
  }
  savingPassword.value = true
  try {
    await api.put("/auth/change-password", {
      current_password: passwordForm.value.current,
      new_password: passwordForm.value.next,
    })
    passwordSuccess.value = "Password updated successfully"
    passwordForm.value = { current: "", next: "", confirm: "" }
  } catch (e) {
    passwordError.value = e.response?.data?.message || "Could not update password"
  } finally {
    savingPassword.value = false
  }
}
</script>

<style scoped>
.profile-hero {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  max-width: 900px;
  padding: 1.75rem 2rem;
  margin-bottom: 1.25rem;
  border-radius: var(--radius-lg);
  background: var(--gradient-accent);
  box-shadow: var(--shadow-accent-lg);
}
.profile-hero-avatar {
  flex-shrink: 0;
  width: 68px; height: 68px;
  border-radius: 50%;
  background: rgba(255,255,255,0.18);
  border: 2px solid rgba(255,255,255,0.5);
  color: #fff;
  font-size: 1.6rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}
.profile-hero-name { font-size: 1.35rem; font-weight: 700; color: #fff; line-height: 1.25; }
.profile-hero-email { font-size: 0.85rem; color: rgba(255,255,255,0.85); margin-top: 0.15rem; }
.profile-hero-chips { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin-top: 0.7rem; }
.profile-chip {
  background: rgba(255,255,255,0.2);
  color: #fff;
  font-size: 0.72rem; font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 100px;
}
.profile-hero-since { font-size: 0.75rem; color: rgba(255,255,255,0.8); }

.profile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1.25rem;
  max-width: 900px;
}
.profile-card { padding: 1.5rem; }
.profile-card-title {
  display: flex; align-items: center; gap: 0.55rem;
  font-size: 1rem; font-weight: 700; color: var(--text);
  margin-bottom: 1.1rem;
}
.profile-card-icon {
  width: 30px; height: 30px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border-radius: 8px;
  background: var(--accent);
  color: var(--primary);
}
.profile-card-icon svg { width: 16px; height: 16px; }
.field-hint { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.35rem; }
.form-actions { margin-top: 0.5rem; }
</style>
