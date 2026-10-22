<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Dashboard" :unread-count="unread" />
      <NotificationBell />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <h1>Hello, {{ auth.user?.name?.split(' ')[0] }} &#9728;</h1>
            <p>Here's what's happening with your complaints</p>
          </div>
          <router-link to="/submit" class="btn btn-primary">+ Submit Complaint</router-link>
        </div>

        <div v-if="loading" class="skeleton-dashboard">
          <div class="stats-grid">
            <SkeletonLoader v-for="i in 4" :key="i" type="card" />
          </div>
          <SkeletonLoader type="table" :count="5" />
        </div>
        <template v-else>
          <div v-if="subBanner" class="sub-banner">
            <div class="sub-banner-icon">⭐</div>
            <div class="sub-banner-text">
              <strong>{{ subBanner.title }}</strong>
              <p>{{ subBanner.desc }}</p>
            </div>
            <router-link to="/subscription" class="btn btn-primary btn-sm">{{ subBanner.cta }}</router-link>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon icon-blue">&#9776;</div>
              <div class="stat-num">{{ stats.requests?.total || 0 }}</div>
              <div class="stat-label">Total Complaints</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-orange">&#9654;</div>
              <div class="stat-num">{{ stats.requests?.pending || 0 }}</div>
              <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-blue">&#9685;</div>
              <div class="stat-num">{{ stats.requests?.in_progress || 0 }}</div>
              <div class="stat-label">In Progress</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-green">&#10003;</div>
              <div class="stat-num">{{ stats.requests?.resolved || 0 }}</div>
              <div class="stat-label">Resolved</div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-orange">&#9729;</div>
              <div class="stat-num">{{ stats.requests?.on_hold_weather || 0 }}</div>
              <div class="stat-label">On Hold - Weather</div>
            </div>
          </div>

          <!-- Analytics summary -->
          <div class="card analytics-header-card">
            <div class="card-header">
              <div class="section-title">Your Analytics</div>
              <div class="date-range-bar">
                <input v-model="analyticsFrom" type="date" class="form-control form-control-sm" />
                <span class="range-sep">to</span>
                <input v-model="analyticsTo" type="date" class="form-control form-control-sm" />
                <button v-if="analyticsFrom || analyticsTo" class="btn btn-xs btn-outline" @click="clearRange">Clear</button>
              </div>
            </div>
            <div class="analytics-stats-grid">
              <div class="mini-stat">
                <div class="mini-stat-num">{{ rangeRequests.length }}</div>
                <div class="mini-stat-label">Complaints <span class="mini-stat-sub">({{ rangeResolvedCount }} resolved · {{ rangePendingCount }} pending)</span></div>
              </div>
              <div class="mini-stat">
                <div class="mini-stat-num">
                  ₹{{ rangeSpend }}
                  <span v-if="spendTrend !== 0" :class="['spend-trend', spendTrend > 0 ? 'trend-up' : 'trend-down']" title="This month vs last month">
                    {{ spendTrend > 0 ? '▲' : '▼' }} ₹{{ Math.abs(spendTrend) }}
                  </span>
                </div>
                <div class="mini-stat-label">Total Spent</div>
              </div>
              <div class="mini-stat">
                <div class="mini-stat-num">{{ rangeBookings.length }}</div>
                <div class="mini-stat-label">Total Bookings</div>
              </div>
            </div>
          </div>

          <!-- Analytics charts -->
          <div class="card analytics-card">
            <div class="charts-grid">
              <!-- Pie: complaints by category -->
              <div class="chart-panel">
                <div class="chart-title">Complaints by Category</div>
                <div v-if="categoryBreakdown.length" class="pie-wrap">
                  <div class="pie-chart" :style="{ background: pieGradient }"></div>
                  <div class="pie-legend">
                    <button
                      v-for="(c, i) in categoryBreakdown" :key="c.category"
                      type="button" class="legend-item"
                      :title="`Show only ${fmtCategory(c.category)} complaints`"
                      @click="drillCategory(c.category)"
                    >
                      <span class="legend-dot" :style="{ background: pieColors[i % pieColors.length] }"></span>
                      {{ fmtCategory(c.category) }} ({{ c.count }})
                    </button>
                  </div>
                </div>
                <p v-else class="chart-empty">No complaints in this range</p>
              </div>

              <!-- Line: submissions over last 30 days -->
              <div class="chart-panel">
                <div class="chart-title">Submissions — Last 30 Days</div>
                <div class="line-chart">
                  <svg :viewBox="`0 0 ${svgW} ${svgH}`" class="line-svg" preserveAspectRatio="none">
                    <line v-for="i in 4" :key="i"
                      :x1="padL" :y1="padT + (i - 1) * ((svgH - padT - padB) / 3)"
                      :x2="svgW - padR" :y2="padT + (i - 1) * ((svgH - padT - padB) / 3)"
                      stroke="var(--border)" stroke-width="1"
                    />
                    <path :d="lineChartArea" fill="var(--primary)" opacity="0.12" />
                    <polyline :points="lineChartPoints" fill="none" stroke="var(--primary)" stroke-width="2.5" stroke-linejoin="round" />
                    <circle v-for="(pt, i) in linePoints30" :key="i" :cx="pt.x" :cy="pt.y" r="2.5" fill="var(--primary)" />
                  </svg>
                  <div class="line-labels">
                    <span v-for="(d, i) in lineChartLabels" :key="i">{{ d }}</span>
                  </div>
                </div>
              </div>

              <!-- Bar: bookings by facility type -->
              <div class="chart-panel">
                <div class="chart-title">Bookings by Facility Type</div>
                <div v-if="bookingsByType.length" class="type-bar-list">
                  <button
                    v-for="(t, i) in bookingsByType" :key="t.type"
                    type="button" class="type-bar-item"
                    title="View all bookings"
                    @click="drillBookings"
                  >
                    <div class="type-bar-header">
                      <span class="type-bar-name">{{ t.type }}</span>
                      <span class="type-bar-count">{{ t.count }}</span>
                    </div>
                    <div class="type-bar-track">
                      <div class="type-bar-fill" :style="{ width: (t.count / maxBookingTypeCount * 100) + '%', background: pieColors[i % pieColors.length] }"></div>
                    </div>
                  </button>
                </div>
                <p v-else class="chart-empty">No bookings in this range</p>
              </div>
            </div>
          </div>

          <!-- Hidden until the list has actually loaded, so a slow or failed
               fetch never claims that nothing is saved.
               It used to be hidden when empty as well, on the grounds that a
               blank panel takes up room to say nothing. But that also meant a
               citizen who had never saved a venue was never told the feature
               existed. The empty version is one line, not a blank panel, so it
               earns its space by explaining itself. -->
          <div v-if="favouritesLoaded" class="card fav-card">
            <div class="card-header">
              <div class="section-title">
                My Favourites
                <span v-if="favourites.length" class="fav-count">{{ favourites.length }}</span>
              </div>
              <router-link
                :to="favourites.length ? '/facilities?fav=1' : '/facilities'"
                class="btn btn-sm btn-primary"
              >{{ favourites.length ? 'View All' : 'Browse Facilities' }}</router-link>
            </div>

            <p v-if="!favourites.length" class="fav-empty">
              No saved venues yet. Tap the heart on any facility to keep it here
              for the next time you book.
            </p>

            <div v-else class="fav-list">
              <router-link
                v-for="f in favourites.slice(0, 4)"
                :key="f.id"
                to="/facilities?fav=1"
                class="fav-item"
              >
                <div class="fav-item-main">
                  <div class="fav-item-name">{{ f.name }}</div>
                  <div class="fav-item-meta">
                    {{ f.facility_type }} · {{ f.ward || 'City' }} ·
                    {{ f.fee_per_hour > 0 ? `₹${f.fee_per_hour}/hr` : 'Free' }}
                  </div>
                </div>
                <div v-if="f.rating_count > 0" class="fav-item-rating">
                  {{ f.avg_rating }} / 5
                </div>
              </router-link>
            </div>
            <p v-if="favourites.length > 4" class="fav-more">
              and {{ favourites.length - 4 }} more
            </p>
          </div>

          <div class="card">
            <div class="card-header">
              <div class="section-title">Recent Complaints</div>
              <router-link to="/complaints" class="btn btn-sm btn-primary">View All</router-link>
            </div>
            <div v-if="requests.length" class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Complaint ID</th>
                    <th>Category</th>
                    <th>Title</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in requests.slice(0, 5)" :key="r.id">
                    <td><code class="cmp-id">{{ r.cmp_id }}</code></td>
                    <td><span class="cat-badge">{{ r.category }}</span></td>
                    <td class="td-title">{{ r.title }}</td>
                    <td>{{ fmtDate(r.created_at) }}</td>
                    <td><span :class="['badge', `badge-${r.status}`]">{{ fmtStatus(r.status) }}</span></td>
                    <td>
                      <router-link :to="`/complaints/${r.id}`" class="btn btn-xs btn-primary">View</router-link>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <EmptyState
              v-else
              type="complaints"
              title="No Complaints Yet"
              description="You haven't submitted any complaints. Start helping your community by reporting an issue."
              buttonText="Submit Your First Complaint"
              @action="router.push('/submit')"
            />
          </div>
        </template>
      </div>
    </div>

    <FloatingActionButton @action="handleFabAction" />
  </div>
</template>

<script setup>
/**
 * Citizen Dashboard - Main landing page for citizens
 * Displays complaint statistics, recent complaints, and subscription status banner
 * Enforces Premium subscription requirement for filing complaints via banner messaging
 */
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import NotificationBell from '../../components/NotificationBell.vue'
import EmptyState from '../../components/EmptyState.vue'
import FloatingActionButton from '../../components/FloatingActionButton.vue'
import SkeletonLoader from '../../components/SkeletonLoader.vue'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'
import api from '../../api'
import { fmtStatus } from '../../utils/status'

const auth = useAuthStore()
const router = useRouter()
const { success, error } = useToast()
const loading = ref(true)
const stats = ref({})
const requests = ref([])
const unread = ref(0)
const subInfo = ref(null)
// Facilities this citizen saved. Empty until the lookup returns, and left empty
// if it fails, so the section simply does not appear rather than erroring.
const favourites = ref([])
const favouritesLoaded = ref(false)
const bookings = ref([])
const subPayments = ref([]) // Premium subscription billing history — the other half of "Total Spent" alongside bookings

// ── Analytics: date range (affects quick stats, pie, and bar chart — the line
// chart is always a fixed last-30-days view regardless of this range) ──
const analyticsFrom = ref('')
const analyticsTo = ref('')
function clearRange() { analyticsFrom.value = ''; analyticsTo.value = '' }

function inRange(dateStr) {
  const d = dateStr.slice(0, 10)
  if (analyticsFrom.value && d < analyticsFrom.value) return false
  if (analyticsTo.value && d > analyticsTo.value) return false
  return true
}

const rangeRequests = computed(() => requests.value.filter(r => inRange(r.created_at)))
const rangeBookings = computed(() => bookings.value.filter(b => inRange(b.created_at)))
const rangeSubPayments = computed(() => subPayments.value.filter(p => inRange(p.created_at)))

const rangeResolvedCount = computed(() => rangeRequests.value.filter(r => r.status === 'resolved' || r.status === 'closed').length)
const rangePendingCount = computed(() => rangeRequests.value.filter(r => !['resolved', 'closed', 'rejected'].includes(r.status)).length)

// Net actually-spent amount from a list of payments: paid adds, refunded
// subtracts (money that came back isn't still "spent"), pending/failed
// payments never moved money so they don't count either way.
function netSpend(payments) {
  return payments.reduce((sum, p) => {
    if (p?.status === 'paid') return sum + (p.amount || 0)
    if (p?.status === 'refunded') return sum - (p.amount || 0)
    return sum
  }, 0)
}

// "Total Spent" covers everything that moves money for this citizen —
// facility booking payments AND Premium subscription payments — not just
// bookings alone.
const rangeSpend = computed(() =>
  netSpend(rangeBookings.value.map(b => b.payment)) + netSpend(rangeSubPayments.value)
)

// Trend is a fixed this-month-vs-last-month comparison, independent of
// whatever the citizen has the date range picker set to — the range is for
// browsing history, the trend is always "am I spending more lately."
function spendInMonth(monthsAgo) {
  const now = new Date()
  const target = new Date(now.getFullYear(), now.getMonth() - monthsAgo, 1)
  const y = target.getFullYear(), m = target.getMonth()
  const inMonth = (dateStr) => {
    const d = new Date(dateStr)
    return d.getFullYear() === y && d.getMonth() === m
  }
  const bookingPayments = bookings.value.filter(b => inMonth(b.created_at)).map(b => b.payment)
  const subPays = subPayments.value.filter(p => inMonth(p.created_at))
  return netSpend(bookingPayments) + netSpend(subPays)
}
const thisMonthSpend = computed(() => spendInMonth(0))
const lastMonthSpend = computed(() => spendInMonth(1))
const spendTrend = computed(() => thisMonthSpend.value - lastMonthSpend.value)

function fmtCategory(c) {
  if (!c) return 'Other'
  return c.charAt(0).toUpperCase() + c.slice(1).replace(/_/g, ' ')
}

// ── Pie: complaints by category ──
const pieColors = ['#0052FF', '#4D7CFF', '#FFB400', '#E0218A', '#15803D', '#DC2626', '#B45309', '#475569']
const categoryBreakdown = computed(() => {
  const counts = {}
  for (const r of rangeRequests.value) counts[r.category] = (counts[r.category] || 0) + 1
  return Object.entries(counts)
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count)
})
const pieGradient = computed(() => {
  const total = categoryBreakdown.value.reduce((s, c) => s + c.count, 0)
  if (!total) return null
  let cumulative = 0
  const segments = categoryBreakdown.value.map((c, i) => {
    const start = (cumulative / total) * 360
    cumulative += c.count
    const end = (cumulative / total) * 360
    return `${pieColors[i % pieColors.length]} ${start}deg ${end}deg`
  })
  return `conic-gradient(${segments.join(', ')})`
})

// ── Line: complaint submissions over the last 30 days (fixed window) ──
const svgW = 500, svgH = 140, padL = 20, padR = 20, padT = 15, padB = 25
const last30Days = computed(() => {
  const days = []
  const today = new Date()
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    days.push({ date: d.toISOString().split('T')[0], count: 0 })
  }
  for (const r of requests.value) {
    const key = (r.created_at || '').slice(0, 10)
    const day = days.find(d => d.date === key)
    if (day) day.count++
  }
  return days
})
const linePoints30 = computed(() => {
  const maxVal = Math.max(...last30Days.value.map(d => d.count), 1)
  const stepX = (svgW - padL - padR) / Math.max(last30Days.value.length - 1, 1)
  const scaleY = (svgH - padT - padB) / maxVal
  return last30Days.value.map((d, i) => ({
    x: padL + i * stepX,
    y: svgH - padB - d.count * scaleY,
  }))
})
const lineChartPoints = computed(() => linePoints30.value.map(p => `${p.x},${p.y}`).join(' '))
const lineChartArea = computed(() => {
  const pts = linePoints30.value
  if (!pts.length) return ''
  const bottomLeft = `${pts[0].x},${svgH - padB}`
  const bottomRight = `${pts[pts.length - 1].x},${svgH - padB}`
  return `M ${bottomLeft} L ${pts.map(p => `${p.x},${p.y}`).join(' L ')} L ${bottomRight} Z`
})
const lineChartLabels = computed(() =>
  last30Days.value.filter((_, i) => i % 6 === 0).map(d => d.date.slice(5))
)

// ── Bar: bookings by facility type ──
const bookingsByType = computed(() => {
  const counts = {}
  for (const b of rangeBookings.value) counts[b.facility_type] = (counts[b.facility_type] || 0) + 1
  return Object.entries(counts)
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
})
const maxBookingTypeCount = computed(() => Math.max(...bookingsByType.value.map(t => t.count), 1))

// ── Drill-down: land on the filtered page for whatever was clicked ──
function drillCategory(category) { router.push({ path: '/complaints', query: { category } }) }
function drillStatus(status) { router.push({ path: '/complaints', query: { status } }) }
function drillBookings() { router.push('/bookings') }

// Default FAB actions are "New Complaint" and "Browse Facilities" — quick
// shortcuts to the two most common things a citizen does from here.
function handleFabAction(action) {
  if (action.label === 'New Complaint') router.push('/submit')
  else if (action.label === 'Browse Facilities') router.push('/facilities')
}

/**
 * Subscription banner logic
 * Shows "Subscribe Now" if no subscription exists
 * Shows payment reminder if payment is overdue
 * Null if subscription is active and up-to-date
 * IMPORTANT: Filing complaints and posting to community feed require active Premium subscription
 */
const subBanner = computed(() => {
  if (!subInfo.value) return null
  if (!subInfo.value.subscription) {
    return {
      title: 'Unlock full access to Cyber Panchayat',
      desc: `Subscribe to Premium (₹${subInfo.value.monthly_fee}/month) to file complaints and join the community feed. Browsing and tracking stay free.`,
      cta: 'Subscribe Now',
    }
  }
  if (subInfo.value.due_payment) {
    return {
      title: 'Payment due on your Premium subscription',
      desc: `Pay ₹${subInfo.value.due_payment.amount} to keep filing complaints and posting on the community feed.`,
      cta: 'Pay Now',
    }
  }
  return null
})

/**
 * Fetch dashboard data on mount
 * Subscription info is fetched separately (fire-and-forget) to avoid blocking dashboard
 * Core dashboard data (stats, requests, notifications) is fetched in parallel
 */
onMounted(async () => {
  // Fetch subscription status separately — errors here should not block dashboard display
  api.get('/subscriptions/me').then(res => { subInfo.value = res.data }).catch(() => {})
  // Same treatment for favourites: a nice-to-have panel should never hold up
  // the complaints the dashboard exists to show.
  //
  // favouritesLoaded is only set on success. The panel now says something when
  // the list is empty, so a failed request must leave it hidden rather than
  // telling a citizen with saved venues that they have none.
  api.get('/facilities/favorites/detail').then(res => {
    favourites.value = Array.isArray(res.data) ? res.data : []
    favouritesLoaded.value = true
  }).catch(() => { favourites.value = [] })

  try {
    const [dash, reqs, notifs, bookingsRes, subPaysRes] = await Promise.all([
      api.get('/dashboard'),
      api.get('/requests'),
      api.get('/notifications'),
      api.get('/bookings'),
      api.get('/subscriptions/payments'),
    ])
    stats.value = dash.data
    requests.value = reqs.data
    unread.value = notifs.data.unread_count || 0
    bookings.value = bookingsRes.data
    subPayments.value = subPaysRes.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function fmtDate(d) {
  return new Date(d).toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric' })
}

</script>

<style scoped>
.skeleton-dashboard { display: flex; flex-direction: column; gap: 1.5rem; }
/* One extra card (On Hold - Weather) beyond the shared 4-column .stats-grid
   default — scoped here so other dashboards keep their 4-column layout. */
.stats-grid { grid-template-columns: repeat(5, 1fr); }
@media (max-width: 900px) { .stats-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 640px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.75rem; }
.cmp-id { font-family: monospace; font-size: 0.8rem; background: #FFE9F2; padding: 0.1rem 0.35rem; border-radius: 4px; }
.cat-badge { font-size: 0.75rem; font-weight: 600; color: #9B2C6F; text-transform: capitalize; }

/* Analytics */
.analytics-header-card { margin-bottom: 1.5rem; }
.analytics-card { margin-bottom: 1.5rem; }
.date-range-bar { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.date-range-bar .form-control-sm { width: 150px; padding: 0.4rem 0.6rem; font-size: 0.8rem; }
.range-sep { font-size: 0.78rem; color: var(--text-muted); }

.analytics-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.mini-stat {
  background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 0.9rem 1.1rem;
}
.mini-stat-num { font-size: 1.4rem; font-weight: 800; color: var(--text); display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap; }
.mini-stat-label { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem; }
.mini-stat-sub { font-size: 0.72rem; }
.spend-trend { font-size: 0.72rem; font-weight: 700; }
.trend-up { color: var(--danger); }
.trend-down { color: var(--success); }

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 1.5rem;
  align-items: stretch;
}
.chart-panel {
  background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  padding: 1.5rem;
  display: flex; flex-direction: column;
  min-height: 320px;
}
.chart-title { font-size: 0.9rem; font-weight: 700; color: var(--text); margin-bottom: 1.25rem; }
.chart-empty { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; color: var(--text-muted); text-align: center; }

/* Pie chart */
.pie-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.5rem; }
.pie-chart { width: 190px; height: 190px; border-radius: 50%; flex-shrink: 0; }
/* Capped so a citizen with many complaint categories doesn't blow out this
   panel's height — which, since all three chart panels stretch to match the
   tallest one in the row, would otherwise drag the line and bar panels into
   a lot of empty space along with it. Scrolls instead. */
.pie-legend { display: flex; flex-direction: column; gap: 0.6rem; width: 100%; max-height: 130px; overflow-y: auto; padding-right: 0.25rem; }
.legend-item {
  display: flex; align-items: center; gap: 0.6rem;
  background: none; border: none; padding: 0.2rem 0; cursor: pointer;
  font-size: 0.85rem; color: var(--text); text-align: left;
  transition: color var(--transition);
}
.legend-item:hover { color: var(--primary); }
.legend-dot { width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0; }

/* Line chart */
.line-chart { flex: 1; display: flex; flex-direction: column; justify-content: center; }
.line-svg { width: 100%; height: 210px; }
.line-labels { display: flex; justify-content: space-between; padding: 0.4rem 0.3rem 0; }
.line-labels span { font-size: 0.68rem; color: var(--text-muted); }

/* Bookings by type — horizontal progress bars, same idea as the admin
   Reports page's Department Performance panel. Reads clearly even when
   every type only has one or two bookings, unlike a height-based bar chart
   where small equal counts all look "full". */
.type-bar-list { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 1.4rem; }
.type-bar-item { display: block; width: 100%; background: none; border: none; cursor: pointer; padding: 0; text-align: left; }
.type-bar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.type-bar-name { font-size: 0.88rem; font-weight: 600; color: var(--text); text-transform: capitalize; }
.type-bar-count { font-size: 0.9rem; font-weight: 800; color: var(--text); }
.type-bar-track { background: var(--border); border-radius: 100px; height: 12px; overflow: hidden; }
.type-bar-fill { height: 100%; border-radius: 100px; transition: width 0.5s, opacity var(--transition); }
.type-bar-item:hover .type-bar-fill { opacity: 0.75; }

@media (max-width: 640px) {
  .charts-grid { grid-template-columns: 1fr; }
}

.sub-banner {
  display: flex; align-items: center; gap: 1rem;
  background: linear-gradient(135deg, #FFE9F2, #FFF3FA);
  border: 1px solid #FFD1E6; border-radius: 14px;
  padding: 1rem 1.25rem; margin-bottom: 1.5rem;
}
.sub-banner-icon {
  width: 40px; height: 40px; flex-shrink: 0; border-radius: 10px;
  background: #E0218A; color: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
}
.sub-banner-text { flex: 1; min-width: 0; }
.sub-banner-text strong { font-size: 0.9rem; color: #5C1A41; }
.sub-banner-text p { font-size: 0.8rem; color: #9B2C6F; margin-top: 0.2rem; }
.td-title { max-width: 220px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.85rem; }

/* My Favourites */
.fav-card { margin-bottom: 1.5rem; }
.fav-count {
  display: inline-block; margin-left: 0.45rem;
  background: var(--accent); color: var(--accent-foreground);
  border-radius: 100px; padding: 0.05rem 0.5rem;
  font-size: 0.72rem; font-weight: 800;
}
.fav-list { display: flex; flex-direction: column; gap: 0.4rem; }
.fav-item {
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  padding: 0.65rem 0.85rem; text-decoration: none;
  background: var(--bg); border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: border-color var(--transition), background var(--transition);
}
.fav-item:hover { border-color: var(--primary); background: var(--accent); }
.fav-item-main { min-width: 0; }
.fav-item-name {
  font-size: 0.87rem; font-weight: 700; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fav-item-meta { font-size: 0.76rem; color: var(--text-muted); margin-top: 0.15rem; }
.fav-item-rating {
  flex-shrink: 0; font-size: 0.76rem; font-weight: 700; color: var(--text-muted);
}
.fav-more { font-size: 0.78rem; color: var(--text-muted); margin-top: 0.6rem; }
.fav-empty { font-size: 0.82rem; color: var(--text-muted); margin: 0; line-height: 1.5; }
</style>
