import { fileURLToPath, URL } from "node:url"
import { defineConfig } from "vite"
import vue from "@vitejs/plugin-vue"

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      // Forwards /api/* to the real Flask backend so the browser sees it as
      // same-origin — no CORS setup needed for local dev.
      "/api": {
        target: "http://localhost:5001",
        changeOrigin: true,
      },
    },
  },
})
