// Real API client — talks to the Flask backend under backend/.
// baseURL is a relative "/api" so calls go through the Vite dev-server proxy
// (see vite.config.js), which forwards them to http://localhost:5000 and
// keeps everything same-origin (no CORS setup needed for local dev). In
// production, build the frontend with the real backend's origin reachable
// at this same "/api" path (e.g. behind the same reverse proxy), or set an
// absolute baseURL via an environment variable if it's hosted separately.
import axios from "axios"

const api = axios.create({ baseURL: "/api" })

// Every authenticated endpoint expects "Authorization: Bearer <token>" —
// attach it from the same localStorage key auth/login already writes to.
// Also bust the browser's HTTP cache on every GET: Flask's dev server sends
// no Cache-Control header at all, so the browser is free to reuse a stale
// response for a repeated identical URL (e.g. GET /requests after a status
// change elsewhere) — which looks exactly like "the app needs a hard reload
// to show new data" everywhere a list is re-fetched without its query
// params changing. A unique timestamp per request makes the URL never
// collide with a previous one, so every GET always hits the network fresh.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("civic_token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  if ((config.method || "get").toLowerCase() === "get") {
    config.params = { ...(config.params || {}), _: Date.now() }
  }
  return config
})

// A 401 on an *authenticated* request means the token is missing/expired/
// invalid — clear the stale session and send the user back to login, same
// as the mock did. But /auth/login and /auth/register themselves also
// return 401/other errors for perfectly normal reasons (wrong password,
// disabled account) that have nothing to do with an existing session — for
// those, let the error fall through so the login/register form's own
// try/catch can show the real message instead of hard-navigating away
// before it ever gets to render.
const AUTH_ENDPOINTS = ["/auth/login", "/auth/register"]
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => error?.config?.url?.includes(path))
    if (error?.response?.status === 401 && !isAuthEndpoint) {
      localStorage.removeItem("civic_token")
      localStorage.removeItem("civic_user")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

export default api
