<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Premium Subscription" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header">
          <p>A simple pay-per-month membership that supports faster civic services</p>
        </div>

        <div v-if="loading" class="subscription-skeleton">
          <SkeletonLoader type="card" />
          <SkeletonLoader type="text" :count="4" />
        </div>

        <template v-else>
          <!-- Not subscribed -->
          <div v-if="!info.subscription" class="premium-showcase">
            <div class="hero-card">
              <span class="hero-badge">PREMIUM MEMBERSHIP</span>
              <h1 class="hero-title">Cyber Panchayat Premium</h1>
              <p class="hero-sub">Everything you need to get civic issues resolved faster</p>
              <div class="hero-price">₹{{ info.monthly_fee }}<span>/month</span></div>
              <button class="btn-hero" :disabled="acting" @click="openSubscribeModal">
                {{ acting ? 'Processing…' : 'Subscribe Now' }}
              </button>
              <p class="hero-note">One month of access · No auto-renewal · Resubscribe whenever you like</p>
            </div>

            <div class="benefits-grid">
              <div class="benefit-card">
                <div class="benefit-icon icon-blue">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                </div>
                <h3>File Complaints</h3>
                <p>Submit and track civic complaints in your area</p>
              </div>
              <div class="benefit-card">
                <div class="benefit-icon icon-purple">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                </div>
                <h3>Community Feed</h3>
                <p>Post, comment, and like on the community feed</p>
              </div>
              <div class="benefit-card">
                <div class="benefit-icon icon-green">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                </div>
                <h3>Pay As You Go</h3>
                <p>One payment covers exactly one month — no recurring charges</p>
              </div>
              <div class="benefit-card">
                <div class="benefit-icon icon-gray">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>
                </div>
                <h3>No Lock-In</h3>
                <p>No auto-renewal — your month ends and you resubscribe only when you want to</p>
              </div>
            </div>
          </div>

          <!-- Subscribed (active this month, or expired) -->
          <template v-else>
          <div class="subscribed-layout">
            <!-- Active — this month is still running, nothing to do until it ends -->
            <div v-if="isTrulyActive" class="card status-card">
              <div class="plan-header">
                <div class="plan-header-left">
                  <div class="plan-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                  </div>
                  <div>
                    <div class="plan-title-row">
                      <span class="badge badge-confirmed">Active</span>
                    </div>
                    <div class="plan-tenure">Member since {{ fmtDate(info.subscription.started_at) }}</div>
                  </div>
                </div>
                <div class="plan-price-block">
                  <div class="plan-price-val">₹{{ info.monthly_fee }}</div>
                  <div class="plan-price-unit">per month</div>
                </div>
              </div>

              <div class="divider"></div>

              <div class="billing-meta">
                <div class="meta-line">
                  <span class="meta-label">Active until</span>
                  <strong>{{ fmtDateOnly(info.subscription.next_billing_date) }}</strong>
                </div>
                <div class="meta-line" v-if="info.subscription.payment_method">
                  <span class="meta-label">Payment method</span>
                  <strong>{{ methodLabel(info.subscription.payment_method) }}</strong>
                </div>
              </div>

              <p class="status-note">
                No auto-renewal — access ends on {{ fmtDateOnly(info.subscription.next_billing_date) }}. Resubscribe anytime after that.
              </p>

              <div class="divider"></div>

              <div class="perks-section">
                <div class="perks-heading">Your Premium Benefits</div>
                <ul class="perks-list">
                  <li>File complaints</li>
                  <li>Community feed — post, comment &amp; like</li>
                  <li>No auto-renewal — pay only for the month you use</li>
                  <li>Resubscribe whenever you like</li>
                </ul>
              </div>
            </div>

            <!-- Expired — the one paid month ran out; same Subscribe card a
                 never-subscribed citizen sees, button always enabled. -->
            <div v-else class="card status-card status-card-hero is-cancelled">
              <span class="hero-badge">EXPIRED</span>
              <div class="hero-title">Cyber Panchayat Premium</div>
              <p class="hero-sub">Everything you need to get civic issues resolved faster</p>
              <div class="hero-price">₹{{ info.monthly_fee }}<span>/month</span></div>
              <button class="btn-hero" :disabled="acting" @click="openSubscribeModal">
                {{ acting ? 'Processing…' : 'Subscribe Now' }}
              </button>
              <p class="hero-note">
                Your subscription ended on {{ fmtDateOnly(info.subscription.next_billing_date) }}. Subscribe again anytime.
              </p>

              <div class="divider"></div>

              <div class="hero-perks-grid">
                <div class="hero-perk">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                  <span>File Complaints</span>
                </div>
                <div class="hero-perk">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                  <span>Community Feed</span>
                </div>
                <div class="hero-perk">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
                  <span>Pay As You Go</span>
                </div>
                <div class="hero-perk">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>
                  <span>No Lock-In</span>
                </div>
              </div>
            </div>

            <div class="card billing-card">
              <div class="section-title">Billing History</div>
              <div v-if="!payments.length" class="empty-state">
                <p>No invoices yet.</p>
              </div>
              <div v-else class="invoice-list">
                <div v-for="p in payments" :key="p.id" class="invoice-row">
                  <div class="invoice-col-period">
                    <div class="invoice-period-main">{{ fmtDateOnly(p.period_start) }} – {{ fmtDateOnly(p.period_end) }}</div>
                    <div class="invoice-period-sub">{{ methodLabel(p.method) }}</div>
                  </div>
                  <div class="invoice-col-amount">
                    <div class="invoice-amount-val">₹{{ p.amount }}</div>
                    <span :class="['badge', `badge-${p.status}`]">{{ p.status }}</span>
                  </div>
                  <div class="invoice-col-action">
                    <button v-if="p.status === 'paid'" class="btn btn-xs btn-outline" @click="viewInvoice(p)">Invoice</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </template>
        </template>
      </div>
    </div>

    <!-- Subscribe modal — picks the payment method, charges once for one month -->
    <div v-if="subscribeModal.show" class="modal-overlay" @click.self="subscribeModal.show = false">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Subscribe — ₹{{ info.monthly_fee }}/month</h2>
          <button class="modal-close" aria-label="Close" @click="subscribeModal.show = false">✕</button>
        </div>
        <div v-if="subscribeModal.error" class="alert alert-error mb-4">{{ subscribeModal.error }}</div>
        <p class="text-sm text-muted mb-4">
          You'll be charged ₹{{ info.monthly_fee }} now for one month of Premium access. No auto-renewal — subscribe again whenever you like after it ends.
        </p>
        <div class="form-group">
          <label>Payment Method</label>
          <select v-model="subscribeModal.method" class="form-control">
            <option value="upi">UPI</option>
            <option value="card">Credit / Debit Card</option>
            <option value="netbanking">Net Banking</option>
            <option value="online">Online Transfer</option>
          </select>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="subscribeModal.show = false">Cancel</button>
          <button class="btn btn-success" :disabled="subscribeModal.loading" @click="confirmSubscribe">
            {{ subscribeModal.loading ? 'Processing…' : `Subscribe & Pay ₹${info.monthly_fee}` }}
          </button>
        </div>
      </div>
    </div>

    <!-- Invoice modal -->
    <div v-if="invoice" class="modal-overlay" @click.self="invoice = null">
      <div class="modal invoice-modal">
        <div class="modal-header">
          <h2>Subscription Invoice</h2>
          <button class="modal-close" aria-label="Close" @click="invoice = null">✕</button>
        </div>
        <div class="invoice-body">
          <div class="inv-row"><span>Invoice No</span><strong>{{ invoice.invoice_number }}</strong></div>
          <div class="inv-row"><span>Date Issued</span><span>{{ invoice.issued_at }}</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row"><span>Citizen</span><span>{{ invoice.citizen_name }}</span></div>
          <div class="inv-row"><span>Email</span><span>{{ invoice.citizen_email || '—' }}</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row"><span>Plan</span><strong>{{ invoice.plan }}</strong></div>
          <div class="inv-row"><span>Billing Period</span><span>{{ invoice.period_start }} – {{ invoice.period_end }}</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row inv-total"><span>Amount</span><strong>₹{{ invoice.amount }}</strong></div>
          <div class="inv-row mt-2">
            <span>Payment</span>
            <span :class="['inv-payment-status', invoice.status === 'paid' ? 'is-paid' : 'is-due']">
              {{ invoice.status.toUpperCase() }}
            </span>
          </div>
          <div v-if="invoice.transaction_ref" class="inv-row"><span>Txn Ref</span><span class="td-txn">{{ invoice.transaction_ref }}</span></div>
        </div>
        <div class="modal-footer">
          <button v-if="invoice.status === 'paid'" class="btn btn-outline" @click="downloadInvoice(invoice)">⬇ Download</button>
          <button class="btn btn-secondary" @click="invoice = null">Close</button>
        </div>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0, unread - 1)" />
  </div>
</template>

<script setup>
/**
 * My Subscription - Citizen Premium subscription management
 * Features: subscribe (one month, pay-per-cycle), view billing history and invoices
 * Premium unlocks: file complaints, community feed posting
 * Payment workflow: subscribe → charged once → active for exactly one month →
 * expires automatically, no auto-renewal and no manual "cancel" step. The
 * citizen subscribes again whenever they want back in, which starts a brand
 * new month from that day (no makeup billing for time they were away).
 */
import { ref, computed, onMounted } from "vue"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import SkeletonLoader from "../../components/SkeletonLoader.vue"
import api from "../../api"
import { downloadInvoicePdf } from "../../utils/invoicePdf"
import { useToast } from "../../composables/useToast"

const { success: toastSuccess, error: toastError } = useToast()
const loading = ref(true)
const acting = ref(false) // Prevents duplicate subscribe requests
const showNotif = ref(false)
const unread = ref(0)
const info = ref({ subscribed: false, subscription: null, monthly_fee: 100 })
const payments = ref([]) // Billing history (monthly invoices)
const subscribeModal = ref({ show: false, method: "upi", loading: false, error: "" })
const invoice = ref(null)

const isTrulyActive = computed(() => info.value.subscription?.status === "active")

async function loadAll() {
  const [subRes, notifRes] = await Promise.all([api.get("/subscriptions/me"), api.get("/notifications")])
  info.value = subRes.data
  unread.value = notifRes.data.unread_count
  if (info.value.subscription) {
    const payRes = await api.get("/subscriptions/payments")
    payments.value = payRes.data
  }
}

onMounted(async () => {
  try {
    await loadAll()
  } finally {
    loading.value = false
  }
})

function openSubscribeModal() {
  subscribeModal.value = { show: true, method: "upi", loading: false, error: "" }
}

/**
 * Subscribe to Premium (or resubscribe after expiry) — charges the chosen
 * method once, for exactly one month starting today. No auto-renewal.
 */
async function confirmSubscribe() {
  subscribeModal.value.loading = true
  subscribeModal.value.error = ""
  try {
    await api.post("/subscriptions/subscribe", { method: subscribeModal.value.method })
    subscribeModal.value.show = false
    await loadAll()
    toastSuccess("✓ Subscribed to Cyber Panchayat Premium!")
  } catch (e) {
    subscribeModal.value.error = e.response?.data?.message || "Could not subscribe"
    toastError("Could not subscribe")
  } finally {
    subscribeModal.value.loading = false
  }
}

async function viewInvoice(p) {
  try {
    const { data } = await api.get(`/subscriptions/payments/${p.id}/invoice`)
    invoice.value = data
  } catch {
    toastError("Could not load invoice")
  }
}

function downloadInvoice(inv) {
  const rows = [
    ["Citizen", inv.citizen_name, { bold: true }],
    ["Email", inv.citizen_email || "—"],
    ["Plan", inv.plan, { divider: true, bold: true }],
    ["Billing Period", `${inv.period_start} – ${inv.period_end}`],
    ["Amount", `₹${inv.amount}`, { divider: true, bold: true }],
    ["Payment", inv.status.toUpperCase()],
  ]
  if (inv.transaction_ref) rows.push(["Txn Ref", inv.transaction_ref])
  downloadInvoicePdf({
    title: "Cyber Panchayat — Subscription Invoice",
    invoiceNumber: inv.invoice_number,
    issuedAt: inv.issued_at,
    filename: `${inv.invoice_number}.pdf`,
    rows,
  })
}

function methodLabel(m) {
  return { upi: 'UPI', card: 'Card', netbanking: 'Net Banking', online: 'Online' }[m] || (m || '—')
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}
function fmtDateOnly(d) {
  if (!d) return '—'
  return new Date(d + "T00:00:00").toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}
</script>

<style scoped>
.subscription-skeleton { display: flex; flex-direction: column; gap: 1.25rem; max-width: 780px; margin: 0 auto; }

/* ── Not-subscribed showcase ─────────────────────────────────────────────── */
.premium-showcase { max-width: 780px; margin: 0 auto; }

.hero-card {
  position: relative;
  overflow: hidden;
  text-align: center;
  padding: 2.75rem 2rem 2.25rem;
  margin-bottom: 1.75rem;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-secondary) 55%, var(--navy) 100%);
  box-shadow: 0 12px 32px rgba(0,82,255,0.28);
}
.hero-badge {
  display: inline-block; background: rgba(255,255,255,0.22); color: #fff;
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em;
  padding: 0.3rem 0.85rem; border-radius: 100px; margin-bottom: 1rem;
}
.hero-title { font-size: 1.5rem; font-weight: 700; color: #fff; margin-bottom: 0.4rem; }
.hero-sub { font-size: 0.88rem; color: rgba(255,255,255,0.85); margin-bottom: 1.5rem; }
.hero-price { font-size: 2.4rem; font-weight: 700; color: #fff; margin-bottom: 1.5rem; }
.hero-price span { font-size: 0.95rem; font-weight: 500; color: rgba(255,255,255,0.75); }
.hero-note { font-size: 0.78rem; color: rgba(255,255,255,0.75); margin-top: 0.85rem; }
.btn-hero {
  background: #fff; color: var(--primary); border: none;
  font-size: 0.9rem; font-weight: 700; padding: 0.8rem 2.25rem;
  border-radius: 100px; cursor: pointer;
  box-shadow: 0 6px 18px rgba(0,0,0,0.18);
  transition: transform 0.15s, box-shadow 0.15s;
}
.btn-hero:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 10px 22px rgba(0,0,0,0.22); }
.btn-hero:disabled { opacity: 0.7; cursor: default; }

.benefits-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
.benefit-card {
  background: #fff; border: 1px solid var(--border); border-radius: 14px;
  padding: 1.4rem 1.5rem; transition: transform 0.15s, box-shadow 0.15s;
}
.benefit-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-hover); }
.benefit-icon {
  width: 40px; height: 40px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 0.75rem;
}
.benefit-icon svg { width: 19px; height: 19px; }
.icon-purple { background: rgba(155,89,182,0.15); color: #9B59B6; }
.benefit-card h3 { font-size: 0.98rem; font-weight: 800; color: var(--text); margin-bottom: 0.35rem; }
.benefit-card p { font-size: 0.83rem; color: var(--text-muted); line-height: 1.5; }

@media (max-width: 640px) {
  .benefits-grid { grid-template-columns: 1fr; }
}

/* ── Subscribed layout: status card + billing history side by side ───────── */
.subscribed-layout { display: grid; grid-template-columns: 1fr 1.05fr; gap: 1.25rem; align-items: start; }
@media (max-width: 900px) {
  .subscribed-layout { grid-template-columns: 1fr; }
}

/* ── Subscribed status card — matches the hero card's blue brand ─────────── */
.status-card {
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-secondary) 55%, var(--navy) 100%);
  box-shadow: 0 12px 32px rgba(0,82,255,0.28);
}
.status-card.is-cancelled {
  background: linear-gradient(135deg, #94A3B8 0%, #64748B 55%, #475569 100%);
  box-shadow: 0 12px 32px rgba(71,85,105,0.22);
}
/* Expired variant reuses the hero card's centered "Subscribe" layout instead
   of the compact plan-header one. */
.status-card-hero { text-align: center; padding: 2.5rem 1.75rem 2.25rem; }

.plan-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.1rem; }
.plan-header-left { display: flex; align-items: flex-start; gap: 0.85rem; }
.plan-icon {
  width: 46px; height: 46px; border-radius: 12px; flex-shrink: 0;
  background: rgba(255,255,255,0.22); border: 1px solid rgba(255,255,255,0.3); color: #fff;
  display: flex; align-items: center; justify-content: center;
}
.plan-icon svg { width: 20px; height: 20px; }
.plan-title-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
.plan-name { font-size: 1.05rem; font-weight: 700; color: #fff; }
.plan-tenure { font-size: 0.78rem; color: rgba(255,255,255,0.75); margin-top: 0.2rem; }
.plan-price-block { text-align: right; flex-shrink: 0; }
.plan-price-val { font-size: 1.4rem; font-weight: 700; color: #fff; line-height: 1.1; }
.plan-price-unit { font-size: 0.72rem; color: rgba(255,255,255,0.75); }

.divider { border-top: 1px solid rgba(255,255,255,0.2); margin: 1.1rem 0; }

.billing-meta { display: flex; gap: 1.75rem; flex-wrap: wrap; margin-bottom: 1rem; }
.meta-line { font-size: 0.86rem; color: rgba(255,255,255,0.9); }
.meta-line strong { color: #fff; margin-left: 0.35rem; }
.meta-label { color: rgba(255,255,255,0.7); }

.badge-confirmed { background: rgba(255,255,255,0.9); color: #15803D; }

.perks-section { margin-top: -0.25rem; }
.perks-heading { font-size: 0.76rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(255,255,255,0.7); margin-bottom: 0.5rem; }
.perks-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.4rem; }
.perks-list li { font-size: 0.85rem; color: #fff; padding-left: 1.3rem; position: relative; }
.perks-list li::before { content: "✓"; position: absolute; left: 0; font-weight: 700; }

.hero-perks-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.85rem 1.25rem; text-align: left; }
.hero-perk { display: flex; align-items: center; gap: 0.6rem; color: #fff; font-size: 0.84rem; font-weight: 600; }
.hero-perk svg { width: 18px; height: 18px; flex-shrink: 0; color: rgba(255,255,255,0.85); }
@media (max-width: 480px) {
  .hero-perks-grid { grid-template-columns: 1fr; }
}

.status-note {
  font-size: 0.86rem; color: #fff; margin: 0 0 0.9rem;
  display: flex; align-items: center; flex-wrap: wrap; gap: 0.6rem;
}

/* ── Billing history card — compact rows for the narrower side column ────── */
.billing-card { display: flex; flex-direction: column; max-height: 560px; }
.invoice-list {
  display: flex; flex-direction: column;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--accent) transparent;
}
.invoice-list::-webkit-scrollbar { width: 6px; }
.invoice-list::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 100px; }
.invoice-list::-webkit-scrollbar-track { background: transparent; }
.invoice-row {
  display: flex; align-items: center; justify-content: space-between; gap: 0.75rem;
  padding: 0.85rem 0.15rem;
  border-bottom: 1px solid var(--border);
}
.invoice-row:last-child { border-bottom: none; }
.invoice-row:hover { background: var(--stone); }
.invoice-period-main { font-size: 0.86rem; font-weight: 700; color: var(--text); }
.invoice-period-sub { font-size: 0.74rem; color: var(--text-muted); margin-top: 0.15rem; }
.invoice-col-amount { text-align: right; flex-shrink: 0; }
.invoice-amount-val { font-size: 0.92rem; font-weight: 800; color: var(--text); }
.invoice-col-amount .badge { display: block; margin-top: 0.25rem; }
.invoice-col-action { display: flex; flex-direction: column; gap: 0.35rem; align-items: flex-end; flex-shrink: 0; }

.td-method { font-size: 0.84rem; color: var(--text-muted); }
.td-txn { font-family: monospace; font-size: 0.8rem; color: var(--text-muted); }
.btn-xs { padding: 0.22rem 0.65rem; font-size: 0.72rem; border-radius: 4px; font-weight: 600; cursor: pointer; }
.invoice-modal { max-width: 420px; }
.invoice-body { padding: 0 0.25rem; }
.inv-row { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.3rem 0; color: var(--text); }
.inv-row span:first-child { color: var(--text-muted); }
.inv-divider { border-top: 1px solid var(--border); margin: 0.5rem 0; }
.inv-total { font-size: 1rem; font-weight: 800; padding-top: 0.4rem; }
.inv-payment-status { font-weight: 700; }
.inv-payment-status.is-paid { color: var(--success); }
.inv-payment-status.is-due { color: var(--warning); }
</style>
