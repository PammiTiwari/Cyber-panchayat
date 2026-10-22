<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar :title="sub ? `${sub.citizen_name} — Subscription` : 'Subscription Details'" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="detail-topbar">
          <router-link to="/admin/subscriptions" class="back-link">&larr; Back to Subscriptions</router-link>
        </div>

        <div v-if="loading" class="spinner"></div>
        <div v-else-if="!sub" class="empty-state">
          <p>Subscription not found.</p>
        </div>

        <template v-else>
          <div class="card mt-4">
            <div class="flex gap-2 mb-4 items-center">
              <span :class="['badge', statusBadge(sub).cls]">{{ statusBadge(sub).label }}</span>
              <span v-if="sub.status === 'cancelled'" class="td-sub">Expired {{ fmtDateOnly(sub.next_billing_date) }}</span>
            </div>

            <div class="lifetime-callout">
              <div class="lifetime-val">₹{{ lifetimePaid(sub) }}</div>
              <div class="lifetime-lbl">Total Paid · {{ (sub.payments || []).filter(p => p.status === 'paid').length }} cycle(s)</div>
            </div>

            <div class="detail-row"><div class="detail-label">Citizen</div><div class="detail-value">{{ sub.citizen_name }} ({{ sub.citizen_email }})</div></div>
            <div class="detail-row"><div class="detail-label">Monthly Fee</div><div class="detail-value">₹{{ sub.monthly_fee }}/month</div></div>
            <div class="detail-row"><div class="detail-label">Payment Method</div><div class="detail-value capitalize">{{ methodLabel(sub.payment_method) }}</div></div>
            <div class="detail-row"><div class="detail-label">Member Since</div><div class="detail-value">{{ fmtDate(sub.started_at) }}</div></div>
            <div class="detail-row" v-if="lastRejoinedAt(sub)"><div class="detail-label">Last Rejoined</div><div class="detail-value">{{ fmtDate(lastRejoinedAt(sub)) }}</div></div>
            <div class="detail-row" v-if="sub.status === 'active'">
              <div class="detail-label">Active Until</div>
              <div class="detail-value">{{ fmtDateOnly(sub.next_billing_date) }}</div>
            </div>
            <div class="detail-row" v-else>
              <div class="detail-label">Expired On</div>
              <div class="detail-value">{{ fmtDateOnly(sub.next_billing_date) }}</div>
            </div>

            <div class="billing-header mt-4 mb-2">
              <div class="section-title">Payment History</div>
              <button class="btn btn-sm btn-outline" :disabled="!(sub.payments || []).length" @click="downloadPaymentHistoryCsv">
                ⬇ Download Payment History
              </button>
            </div>
            <div v-if="!(sub.payments || []).length" class="empty-state">
              <p>No payments yet.</p>
            </div>
            <div v-else class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Period</th><th>Payment Method</th><th>Transaction Ref</th>
                    <th class="text-right">Amount</th><th>Status</th><th>Paid On</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="p in sub.payments" :key="p.id">
                    <td class="text-sm">{{ fmtDateOnly(p.period_start) }} – {{ fmtDateOnly(p.period_end) }}</td>
                    <td class="text-sm capitalize">{{ methodLabel(p.method) }}</td>
                    <td class="td-txn">{{ p.transaction_ref || '—' }}</td>
                    <td class="text-sm text-right font-semibold">₹{{ p.amount }}</td>
                    <td><span :class="['badge', `badge-${p.status}`]">{{ p.status }}</span></td>
                    <td class="text-sm">{{ p.paid_at ? fmtDateTime(p.paid_at) : '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />
  </div>
</template>

<script setup>
/**
 * Subscription Detail - Full-page admin view of one citizen's Premium
 * subscription: status, lifetime revenue, and a simple payment history
 * table (with CSV export) — one row per paid month, with date, time,
 * amount, and payment method. Reached from the "View" action on Manage
 * Subscriptions (was a modal there; broken out to its own page/route so it
 * can hold a citizen's full billing history without cramping the list).
 */
import { ref, onMounted } from "vue"
import { useRoute } from "vue-router"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import api from "../../api"

const route = useRoute()
const loading = ref(true)
const sub = ref(null)
const showNotif = ref(false)
const unread = ref(0)

function statusBadge(s) {
  if (s.status === "active") return { label: "Active", cls: "badge-confirmed" }
  return { label: "Expired", cls: "badge-cancelled" }
}

function methodLabel(m) {
  return { upi: "UPI", card: "Card", netbanking: "Net Banking", online: "Online" }[m] || "—"
}

// Total actually collected from this citizen across every cycle they've ever
// paid for — a single "last invoice" badge says nothing useful since it's
// "Paid" for nearly everyone; this varies meaningfully citizen to citizen.
function lifetimePaid(s) {
  return (s.payments || []).filter(p => p.status === "paid").reduce((sum, p) => sum + p.amount, 0)
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}
function fmtDateTime(iso) {
  return new Date(iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true })
}
function fmtDateOnly(d) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}

// Most recent "rejoined" event — the full history (every cycle) shows in the activity log below.
function lastRejoinedAt(s) {
  const rejoins = (s.history || []).filter(h => h.type === "rejoined")
  return rejoins.length ? rejoins[rejoins.length - 1].at : null
}

// Lets an admin export a citizen's full payment history as a CSV file —
// every cycle they've ever paid for, with method/status/transaction ref.
function downloadPaymentHistoryCsv() {
  const header = ["Period Start", "Period End", "Amount (Rs.)", "Payment Method", "Status", "Transaction Ref", "Paid On"]
  const rows = (sub.value.payments || []).map(p => [
    p.period_start, p.period_end, p.amount, methodLabel(p.method), p.status, p.transaction_ref || "",
    p.paid_at ? fmtDateTime(p.paid_at) : "",
  ])
  const csv = [header, ...rows]
    .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(","))
    .join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${sub.value.citizen_name.replace(/\s+/g, "_")}_payment_history.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try {
    const [subRes, notifRes] = await Promise.all([
      api.get(`/admin/subscriptions/${route.params.id}`),
      api.get("/notifications"),
    ])
    sub.value = subRes.data
    unread.value = notifRes.data.unread_count
  } catch {
    sub.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.detail-topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.back-link { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); display: inline-flex; align-items: center; gap: 0.3rem; }
.back-link:hover { color: var(--text); }

.badge-confirmed { background: rgba(21,128,61,0.14); color: var(--success); }
.badge-cancelled { background: rgba(148,163,184,0.2); color: #64748B; }
.td-sub { font-size: 0.75rem; color: var(--text-muted); }
.td-txn { font-family: monospace; font-size: 0.72rem; color: var(--text-muted); }

.lifetime-callout {
  display: flex; align-items: baseline; gap: 0.5rem;
  background: var(--accent); border-radius: 8px;
  padding: 0.7rem 1rem; margin-bottom: 1.1rem;
}
.lifetime-val { font-size: 1.3rem; font-weight: 800; color: var(--primary); }
.lifetime-lbl { font-size: 0.78rem; color: var(--text-muted); }

.billing-header { display: flex; align-items: center; justify-content: space-between; }
.billing-header .section-title { margin: 0; }
</style>
