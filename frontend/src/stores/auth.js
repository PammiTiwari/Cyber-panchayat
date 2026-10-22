// Authentication store using Pinia
// Manages user authentication state, token, user data, and role-based access
// Persists auth data to localStorage and provides methods for login/logout/registration

import { defineStore } from "pinia"
import { ref, computed } from "vue"
import api from "../api"

// Helper function to safely parse stored user data from localStorage
function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("civic_user") || "null")
  } catch {
    return null
  }
}

export const useAuthStore = defineStore("auth", () => {
  // Reactive state: authentication token and user data
  const token = ref(localStorage.getItem("civic_token") || null)
  const user = ref(readStoredUser())

  // Computed properties for checking authentication status and user role
  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => user.value?.role || null)
  const isCitizen = computed(() => role.value === "citizen")
  const isStaff = computed(() => role.value === "staff")
  const isAdmin = computed(() => role.value === "admin")

  // Authenticate user with email and password
  // Stores token and user data in both state and localStorage for persistence
  async function login(email, password) {
    const { data } = await api.post("/auth/login", { email, password })
    token.value = data.token
    user.value = data.user
    localStorage.setItem("civic_token", data.token)
    localStorage.setItem("civic_user", JSON.stringify(data.user))
    return data.user
  }

  // Register a new user with provided information
  // Automatically logs in after successful registration
  async function register(payload) {
    const { data } = await api.post("/auth/register", payload)
    token.value = data.token
    user.value = data.user
    localStorage.setItem("civic_token", data.token)
    localStorage.setItem("civic_user", JSON.stringify(data.user))
    return data.user
  }

  // Clear authentication data from state and localStorage
  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem("civic_token")
    localStorage.removeItem("civic_user")
  }

  // Refresh current user data from the server
  // Useful for syncing latest user information after updates
  async function refreshMe() {
    const { data } = await api.get("/auth/me")
    user.value = data
    localStorage.setItem("civic_user", JSON.stringify(data))
  }

  return { token, user, isLoggedIn, role, isCitizen, isStaff, isAdmin, login, register, logout, refreshMe }
})
