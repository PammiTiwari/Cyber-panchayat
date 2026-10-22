// Main entry point for the Vue application
// Initializes the Vue app instance, sets up Pinia for state management,
// configures Vue Router for navigation, and mounts the app to the DOM

import { createApp } from "vue"
import { createPinia } from "pinia"
import App from "./App.vue"
import router from "./router"
import "./assets/main.css"

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount("#app")
