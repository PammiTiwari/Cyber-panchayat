<!-- Root component of the Cyber Panchayat application
     Serves as the main container that renders the appropriate view based on the current route.
     All page navigation and routing is handled through router-view. -->

<template>
  <div id="civic-app">
    <Toast />
    <ConfirmDialog />
    <router-view />
    <ChatbotWidget v-if="showChatbot" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Toast from '@/components/Toast.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ChatbotWidget from '@/components/ChatbotWidget.vue'
import { unlockAudio } from '@/utils/notifySound'

// Hidden on the landing/login/register pages — not useful before a user has an account context.
const HIDDEN_ON_ROUTES = ['home', 'login', 'register']
const route = useRoute()
const showChatbot = computed(() => !HIDDEN_ON_ROUTES.includes(route.name))

// Browsers block audio until the page has had one real user gesture. This
// unlocks it the first time anywhere in the app, so the notification sound
// (triggered later by AppTopbar's background polling, not a click) can
// actually play. Registered once here since App.vue never remounts, unlike
// per-page components such as AppTopbar.
document.addEventListener('click', unlockAudio, { once: true })
</script>
