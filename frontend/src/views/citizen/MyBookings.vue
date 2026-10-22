<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="My Bookings" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header flex-between">
          <div>
            <p>Track all your facility booking requests and their status</p>
          </div>
          <router-link to="/facilities" class="btn btn-primary">+ New Booking</router-link>
        </div>

        <div class="stats-row">
          <div class="stat-card stat-ok">
            <div class="stat-val">₹{{ totalPaid }}</div>
            <div class="stat-lbl">Total Paid</div>
          </div>
          <div class="stat-card stat-warn">
            <div class="stat-val">{{ pendingPaymentsCount }}</div>
            <div class="stat-lbl">Pending Payments</div>
          </div>
          <div class="stat-card stat-muted">
            <div class="stat-val">{{ refundedCount }}</div>
            <div class="stat-lbl">Refunds</div>
          </div>
        </div>

        <div class="filter-bar card mb-6">
          <select v-model="filter" class="form-control w-auto">
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="cancelled">Cancelled</option>
            <option value="completed">Completed</option>
              <option value="expired">Expired</option>
            <option value="refund_requested">Refund Requested</option>
            <option value="refunded">Refunded</option>
          </select>
        </div>

        <div v-if="loading" class="bookings-list">
          <SkeletonLoader v-for="i in 3" :key="i" type="card" />
        </div>
        <EmptyState
          v-else-if="filtered.length === 0"
          type="bookings"
          title="No Bookings Found"
          description="You haven't booked any facilities yet. Browse what's available and reserve a slot."
          buttonText="Browse Facilities"
          @action="$router.push('/facilities')"
        />

        <div v-else class="bookings-list">
          <div v-for="b in filtered" :key="b.id" class="booking-card card">
            <div class="booking-top">
              <div>
                <span :class="`badge badge-${statusBadge(b).cls}`">{{ statusBadge(b).label }}</span>
                <span class="facility-type ml-3">{{ b.facility_type }}</span>
              </div>
              <div class="text-xs text-muted">Booking #{{ b.id }}</div>
            </div>
            <h3 class="booking-facility">{{ b.facility_name }}</h3>
            <div class="booking-details">
              <div class="detail">📅 {{ fmtDate(b.booking_date) }}</div>
              <div class="detail">⏰ {{ b.start_time }} – {{ b.end_time }}</div>
              <div class="detail">👥 {{ b.attendees }} attendees</div>
              <div class="detail" v-if="b.fee > 0">💰 ₹{{ b.fee }}</div>
              <div class="detail" v-else>🆓 Free</div>
            </div>
            <div class="booking-purpose">Purpose: {{ b.purpose }}</div>

            <!-- Payment section -->
            <div v-if="b.payment && b.payment.status === 'pending' && b.status === 'confirmed'" class="payment-alert">
              <div>
                <strong>Payment Due:</strong> ₹{{ b.payment.amount }}
                <span class="text-xs text-muted"> — Please pay to complete your booking</span>
              </div>
              <button class="btn btn-success btn-sm" @click="payNow(b)">
                💳 Pay Now
              </button>
            </div>

            <!-- Shown for every pending booking, free or paid — a free
                 facility has no payment object at all, so gating this on
                 b.payment existing left those bookings with no status
                 indicator once the initial "Booking Requested!" success
                 modal was dismissed. -->
            <div v-if="b.status === 'pending'" class="payment-wait">
              ⏳ Waiting for admin approval
              <span v-if="b.payment && b.payment.status === 'pending'" class="text-xs text-muted"> — payment will be available once approved</span>
            </div>

            <div v-if="b.payment && b.payment.status === 'paid'" class="payment-done">
              ✅ Paid ₹{{ b.payment.amount }}
              <span class="text-xs">via {{ b.payment.method }} · {{ b.payment.transaction_ref }}</span>
            </div>

            <div v-if="b.payment && b.payment.status === 'refund_requested'" class="payment-refund-requested">
              <div>🕐 Refund Requested — awaiting admin review</div>
              <p class="refund-request-reason-text">"{{ b.payment.refund_request_reason }}"</p>
            </div>

            <div v-if="isRefundRejected(b)" class="payment-refund-rejected">
              <div>✕ Refund Request Rejected</div>
              <p class="refund-request-reason-text">{{ b.payment.refund_reason || 'No reason was given.' }}</p>
            </div>

            <div v-if="b.payment && b.payment.status === 'refunded'" class="payment-refunded">
              <div>
                ↩ Refunded ₹{{ b.payment.amount }}
                <span class="refund-origin">{{ refundOrigin(b.payment) }}</span>
              </div>
              <button class="btn btn-outline btn-sm" @click="viewRefund(b)">View</button>
            </div>

            <div v-if="b.admin_notes && b.status !== 'cancelled'" class="admin-note mt-3">
              <strong>Note:</strong> {{ b.admin_notes }}
            </div>

            <div v-if="b.status === 'completed'" class="rate-row">
              <template v-if="myRatings[b.facility_id]">
                <StarRating :model-value="myRatings[b.facility_id].rating" readonly size="sm" />
                <button class="btn btn-outline btn-sm" @click="openRateModal(b)">Edit Rating</button>
              </template>
              <button v-else class="btn btn-primary btn-sm" @click="openRateModal(b)">⭐ Rate this Facility</button>
            </div>

            <div class="booking-actions">
              <button v-if="b.payment && ['paid','refunded','refund_requested'].includes(b.payment.status)" class="btn btn-outline btn-sm" @click="viewInvoice(b)">🧾 Invoice</button>
              <button v-if="b.payment && b.payment.status === 'paid' && b.status !== 'completed' && !isRefundRejected(b)" class="btn btn-outline btn-sm" @click="openRefundRequestModal(b)">↩ Request Refund</button>
              <button v-if="canCancel(b)" class="btn btn-danger btn-sm" @click="cancelBooking(b)">✕ Cancel</button>
              <button v-if="canMarkComplete(b)" class="btn btn-primary btn-sm" @click="markComplete(b)">✓ Mark as Complete</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Payment modal -->
    <div v-if="payModal.show" class="modal-overlay" @click.self="payModal.show = false">
      <div class="modal modal-w-md text-center">
        <div class="modal-header">
          <h2>Complete Payment</h2>
          <button class="modal-close" aria-label="Close" @click="payModal.show = false">✕</button>
        </div>
        <div class="pay-icon">💳</div>
        <p class="text-muted mb-4">
          Pay ₹{{ payModal.booking?.payment?.amount }} for {{ payModal.booking?.facility_name }}
        </p>
        <div class="form-group text-left mb-5">
          <label>Payment Method</label>
          <select v-model="payModal.method" class="form-control">
            <option value="upi">UPI</option>
            <option value="card">Credit/Debit Card</option>
            <option value="netbanking">Net Banking</option>
            <option value="online">Online Transfer</option>
          </select>
        </div>
        <div v-if="payModal.error" class="alert alert-error text-left mb-4">{{ payModal.error }}</div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="payModal.show = false">Cancel</button>
          <button class="btn btn-success" :disabled="payModal.loading" @click="confirmPayment">
            {{ payModal.loading ? 'Processing…' : '✅ Pay ₹' + payModal.booking?.payment?.amount }}
          </button>
        </div>
      </div>
    </div>

    <!-- Invoice Modal -->
    <div v-if="invoice" class="modal-overlay" @click.self="invoice = null">
      <div class="modal invoice-modal">
        <div class="modal-header">
          <h2>Booking Invoice</h2>
          <button class="modal-close" aria-label="Close" @click="invoice = null">✕</button>
        </div>
        <div class="invoice-body">
          <div class="inv-row"><span>Invoice No</span><strong>{{ invoice.invoice_number }}</strong></div>
          <div class="inv-row"><span>Date Issued</span><span>{{ invoice.issued_at }}</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row"><span>Citizen</span><span>{{ invoice.citizen_name }}</span></div>
          <div class="inv-row"><span>Phone</span><span>{{ invoice.citizen_phone || '—' }}</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row"><span>Facility</span><strong>{{ invoice.facility_name }}</strong></div>
          <div class="inv-row"><span>Address</span><span>{{ invoice.facility_address }}</span></div>
          <div class="inv-row"><span>Date</span><span>{{ invoice.booking_date }}</span></div>
          <div class="inv-row"><span>Time</span><span>{{ invoice.start_time }} – {{ invoice.end_time }} ({{ invoice.hours }}h)</span></div>
          <div class="inv-row"><span>Purpose</span><span>{{ invoice.purpose }}</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row"><span>Rate</span><span>₹{{ invoice.fee_per_hour }}/hr × {{ invoice.hours }}h</span></div>
          <div class="inv-divider"></div>
          <div class="inv-row inv-total"><span>Total</span><strong>₹{{ invoice.total }}</strong></div>
          <div class="inv-row mt-2">
            <span>Payment</span>
            <span :class="['inv-payment-status', ['paid','refunded','refund_requested'].includes(invoice.payment_status) ? 'is-paid' : 'is-due']">
              {{ invoicePaymentLabel(invoice.payment_status) }}
            </span>
          </div>
          <template v-if="['paid','refunded','refund_requested'].includes(invoice.payment_status)">
            <div class="inv-row"><span>Paid Via</span><span class="capitalize">{{ invoice.payment_method || '—' }}</span></div>
            <div class="inv-row"><span>Paid On</span><span>{{ invoice.paid_at ? fmtDate(invoice.paid_at) : '—' }}</span></div>
            <div class="inv-row" v-if="invoice.transaction_ref"><span>Txn Ref</span><span class="td-txn">{{ invoice.transaction_ref }}</span></div>
          </template>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="downloadInvoice(invoice)">⬇ Download</button>
          <button class="btn btn-secondary" @click="invoice = null">Close</button>
        </div>
      </div>
    </div>

    <!-- Rate facility modal -->
    <div v-if="rateModal.show" class="modal-overlay" @click.self="rateModal.show = false">
      <div class="modal modal-w-sm text-center">
        <div class="modal-header">
          <h2>Rate {{ rateModal.booking?.facility_name }}</h2>
          <button class="modal-close" aria-label="Close" @click="rateModal.show = false">✕</button>
        </div>
        <div class="form-group">
          <StarRating v-model="rateModal.rating" size="lg" />
        </div>
        <div class="form-group text-left">
          <label>Comment <span class="optional-label">(optional)</span></label>
          <textarea v-model="rateModal.comment" class="form-control" rows="3" placeholder="How was your experience?"></textarea>
        </div>
        <div v-if="rateModal.error" class="alert alert-error mb-4">{{ rateModal.error }}</div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="rateModal.show = false">Cancel</button>
          <button class="btn btn-success" :disabled="!rateModal.rating || rateModal.loading" @click="submitRating">
            {{ rateModal.loading ? 'Saving…' : 'Submit Rating' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Request refund modal -->
    <div v-if="refundRequestModal.show" class="modal-overlay" @click.self="refundRequestModal.show = false">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Request Refund</h2>
          <button class="modal-close" aria-label="Close" @click="refundRequestModal.show = false">✕</button>
        </div>
        <p class="text-sm text-muted mb-4">
          {{ refundRequestModal.booking?.facility_name }} — ₹{{ refundRequestModal.booking?.payment?.amount }}
        </p>
        <div class="form-group">
          <label>Reason <span class="req">*</span></label>
          <textarea v-model="refundRequestModal.reason" class="form-control" rows="3"
                    placeholder="e.g. Facility was under construction when I arrived"></textarea>
        </div>
        <div v-if="refundRequestModal.error" class="alert alert-error mb-4">{{ refundRequestModal.error }}</div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="refundRequestModal.show = false">Cancel</button>
          <button class="btn btn-danger" :disabled="!refundRequestModal.reason.trim() || refundRequestModal.loading" @click="submitRefundRequest">
            {{ refundRequestModal.loading ? 'Submitting…' : 'Submit Request' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Refund detail modal -->
    <div v-if="refundDetail" class="modal-overlay" @click.self="refundDetail = null">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Refund Details</h2>
          <button class="modal-close" aria-label="Close" @click="refundDetail = null">✕</button>
        </div>
        <div class="inv-row"><span>Facility</span><strong>{{ refundDetail.facility_name }}</strong></div>
        <div class="inv-row"><span>Booking Date</span><span>{{ fmtDate(refundDetail.booking_date) }}</span></div>
        <div class="inv-divider"></div>
        <div class="inv-row"><span>Amount Refunded</span><strong>₹{{ refundDetail.payment.amount }}</strong></div>
        <div class="inv-row"><span>Originally Paid Via</span><span class="capitalize">{{ refundDetail.payment.method || '—' }}</span></div>
        <!-- Who started it. Both paths end at the same "refunded" payment, so
             without saying this the citizen cannot tell their own approved
             request apart from the admin cancelling it on their own. The
             citizen's stated reason is only ever set on the request path,
             which is what makes the two distinguishable. -->
        <div class="inv-row">
          <span>Refund started by</span>
          <strong>{{ refundDetail.payment.refund_rejected_at ? 'The admin'
                     : (refundDetail.payment.refund_request_reason ? 'Your request' : 'The admin') }}</strong>
        </div>
        <div class="inv-divider"></div>
        <div v-if="refundDetail.payment.refund_request_reason" class="refund-reason-block">
          <div class="refund-reason-label">Your reason</div>
          <div class="refund-reason-text">{{ refundDetail.payment.refund_request_reason }}</div>
        </div>
        <div v-if="refundDetail.payment.refund_rejected_at" class="refund-reason-block">
          <div class="refund-reason-label">Rejected first &mdash; reason</div>
          <div class="refund-reason-text">{{ refundDetail.payment.refund_rejected_reason || 'No reason was given.' }}</div>
        </div>
        <div class="refund-reason-block">
          <div class="refund-reason-label">
            {{ refundDetail.payment.refund_rejected_at ? 'Refunded later — reason'
               : (refundDetail.payment.refund_request_reason ? 'Accepted — reason'
                  : 'Refunded by admin — reason') }}
          </div>
          <div class="refund-reason-text">{{ refundDetail.payment.refund_reason || 'No reason was provided.' }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="refundDetail = null">Close</button>
        </div>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import StarRating from "../../components/StarRating.vue"
import EmptyState from "../../components/EmptyState.vue"
import SkeletonLoader from "../../components/SkeletonLoader.vue"
import api from "../../api"
import { downloadInvoicePdf } from "../../utils/invoicePdf"
import { useAuthStore } from "../../stores/auth"
import { useToast } from "../../composables/useToast"

const { success: toastSuccess, error: toastError } = useToast()
const loading = ref(true)
const bookings = ref([])
const showNotif = ref(false)
const unread = ref(0)
const filter = ref("")
const payModal = ref({ show: false, booking: null, method: "upi", loading: false, error: "" })
const invoice = ref(null)
const myRatings = ref({}) // facility_id -> this citizen's rating for it
const rateModal = ref({ show: false, booking: null, rating: 0, comment: "", loading: false, error: "" })

function todayIST() {
  return new Date().toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" })
}
const refundDetail = ref(null)
const refundRequestModal = ref({ show: false, booking: null, reason: "", loading: false, error: "" })

function openRefundRequestModal(b) {
  refundRequestModal.value = { show: true, booking: b, reason: "", loading: false, error: "" }
}

async function submitRefundRequest() {
  refundRequestModal.value.loading = true
  refundRequestModal.value.error = ""
  try {
    const b = refundRequestModal.value.booking
    const { data } = await api.put(`/bookings/${b.id}/request-refund`, { reason: refundRequestModal.value.reason.trim() })
    const idx = bookings.value.findIndex(x => x.id === b.id)
    if (idx >= 0) bookings.value[idx] = data
    bookings.value = [...bookings.value]
    refundRequestModal.value.show = false
    toastSuccess("Refund request submitted")
  } catch (e) {
    refundRequestModal.value.error = e.response?.data?.message || "Could not submit refund request."
    toastError("Could not submit refund request")
  } finally {
    refundRequestModal.value.loading = false
  }
}

async function viewInvoice(b) {
  try {
    const { data } = await api.get(`/bookings/${b.id}/invoice`)
    invoice.value = data
  } catch {
    toastError("Could not load invoice")
  }
}

function viewRefund(b) {
  refundDetail.value = b
}

// A payment can only be "paid" with a refund_request_reason already set once
// a request on it has been rejected — approval moves status to "refunded"
// instead, so this combination is otherwise unreachable.
// Who the refund actually came from. A request that was rejected did not
// cause the refund — whatever happened afterwards was the admin's own
// decision, so crediting it to the citizen's request would be a lie.
function refundOrigin(p) {
  if (p?.refund_rejected_at) return "· by admin"
  return p?.refund_request_reason ? "· on your request" : "· by admin"
}

// Marked by the timestamp, not the note — a rejection with no reason typed
// is still a rejection.
function isRefundRejected(b) {
  return b.payment?.status === "paid" && !!b.payment?.refund_rejected_at
}

// An invoice is a receipt for the payment itself, not the booking's current
// state — a later refund doesn't undo that the citizen paid, so it always
// reads "PAID" and never mentions the refund.
function invoicePaymentLabel(status) {
  if (status === "free") return "Free"
  if (["paid", "refunded", "refund_requested"].includes(status)) return "PAID"
  return status.toUpperCase()
}

function downloadInvoice(inv) {
  const paymentLabel = invoicePaymentLabel(inv.payment_status)
  const rows = [
    ["Citizen", inv.citizen_name, { bold: true }],
    ["Phone", inv.citizen_phone || "—"],
    ["Facility", inv.facility_name, { divider: true, bold: true }],
    ["Address", inv.facility_address],
    ["Date", inv.booking_date],
    ["Time", `${inv.start_time} – ${inv.end_time} (${inv.hours}h)`],
    ["Purpose", inv.purpose],
    ["Rate", `₹${inv.fee_per_hour}/hr × ${inv.hours}h`, { divider: true }],
    ["Total", `₹${inv.total}`, { divider: true, bold: true }],
    ["Payment", paymentLabel],
  ]
  if (["paid", "refunded", "refund_requested"].includes(inv.payment_status)) {
    rows.push(["Paid Via", inv.payment_method || "—"])
    rows.push(["Paid On", inv.paid_at ? fmtDate(inv.paid_at) : "—"])
    if (inv.transaction_ref) rows.push(["Txn Ref", inv.transaction_ref])
  }
  downloadInvoicePdf({
    title: "Cyber Panchayat — Booking Invoice",
    invoiceNumber: inv.invoice_number,
    issuedAt: inv.issued_at,
    filename: `${inv.invoice_number}.pdf`,
    rows,
  })
}

const filtered = computed(() => {
  let list = bookings.value
  // "Refunded" isn't a booking status (those stay "cancelled") — it's about
  // the payment, so it needs its own check instead of matching b.status.
  if (filter.value === "refunded") list = list.filter(b => b.payment?.status === "refunded")
  else if (filter.value) list = list.filter(b => b.status === filter.value)
  // Newest booking first — the API returns them in creation order, oldest
  // first, which read backwards to a citizen checking on something they just booked.
  return [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

const totalPaid = computed(() =>
  bookings.value.filter(b => b.payment?.status === "paid").reduce((s, b) => s + b.payment.amount, 0)
)
const pendingPaymentsCount = computed(() => bookings.value.filter(b => b.payment?.status === "pending").length)
const refundedCount = computed(() => bookings.value.filter(b => b.payment?.status === "refunded").length)

onMounted(async () => {
  const [bRes, nRes] = await Promise.all([api.get("/bookings"), api.get("/notifications")])
  bookings.value = bRes.data
  unread.value = nRes.data.unread_count
  loading.value = false
  await loadMyRatings()
})

/**
 * Fetch this citizen's own rating (if any) for every facility they've
 * completed a booking at, so completed cards can show "Edit Rating" instead
 * of "Rate this Facility" without a per-click round trip.
 */
async function loadMyRatings() {
  const auth = useAuthStore()
  const facilityIds = [...new Set(bookings.value.filter(b => b.status === "completed").map(b => b.facility_id))]
  const results = await Promise.all(
    facilityIds.map(id => api.get(`/facilities/${id}/ratings`).then(res => ({ id, res })).catch(() => null))
  )
  const map = {}
  for (const r of results) {
    if (!r) continue
    const mine = r.res.data.ratings.find(x => x.citizen_id === auth.user?.id)
    if (mine) map[r.id] = mine
  }
  myRatings.value = map
}

// A cancelled booking whose payment was already refunded is more useful shown
// as "Refunded" than a generic "Cancelled" — it tells the citizen they got
// their money back, not just that the booking didn't happen.
function statusBadge(b) {
  // One status covers both ways a slot lapses — admin never confirmed it, or
  // the citizen never paid. The outcome is identical either way (date gone,
  // no money taken, nothing left to do), so one short word says it.
  if (b.status === "expired") {
    return { label: "Expired", cls: "expired" }
  }
  if (b.payment?.status === "refund_requested") {
    return { label: "Refund Requested", cls: "refund_requested" }
  }
  if (b.status === "cancelled" && b.payment?.status === "refunded") {
    return { label: "Refunded", cls: "refunded" }
  }
  if (isRefundRejected(b)) {
    return { label: "Refund Rejected", cls: "refund_rejected" }
  }
  if (b.status === "cancelled" && b.cancelled_by) {
    return { label: b.cancelled_by === "citizen" ? "Cancelled by You" : "Cancelled by Admin", cls: "cancelled" }
  }
  return { label: b.status, cls: b.status }
}

// Cancellable any time before payment — pending (awaiting admin) or confirmed
// but not yet paid, and not while a refund request is already pending review.
function canCancel(b) {
  // "expired" is deliberately absent: the date has already gone, so there is
  // nothing left to call off — the API refuses it too.
  return ["pending", "confirmed"].includes(b.status) &&
    !["paid", "refund_requested"].includes(b.payment?.status)
}

async function cancelBooking(b) {
  if (!confirm("Cancel this booking?")) return
  try {
    // DELETE /bookings/<id> only returns {"message": ...}, not the updated
    // booking — the real backend has nothing to echo back here, so the local
    // copy has to be updated by hand to match what the server just did.
    await api.delete(`/bookings/${b.id}`)
    b.status = "cancelled"
    b.cancelled_by = "citizen"
    if (b.payment?.status === "pending") b.payment.status = "cancelled"
    bookings.value = [...bookings.value]
    toastSuccess("Booking cancelled")
  } catch (e) {
    toastError(e.response?.data?.message || "Could not cancel booking")
  }
}

// Self-reported completion — only once the date has actually passed, so a
// citizen can't rate a facility for a visit that hasn't happened yet, and
// only while the payment is actually just "paid" — a free booking has no
// payment at all, so that's allowed through too. A pending or requested
// refund means the citizen is already saying they want their money back,
// which doesn't square with also completing and rating the facility, so
// both block this same as an unpaid booking would.
function canMarkComplete(b) {
  return b.status === "confirmed" && b.booking_date <= todayIST() &&
    (!b.payment || b.payment.status === "paid")
}

async function markComplete(b) {
  if (!confirm("Mark this booking as complete? You'll be able to rate the facility.")) return
  try {
    const { data } = await api.put(`/bookings/${b.id}/complete`)
    const idx = bookings.value.findIndex(x => x.id === b.id)
    if (idx >= 0) bookings.value[idx] = data
    bookings.value = [...bookings.value]
    toastSuccess("Booking marked as complete")
    openRateModal(data)
  } catch (e) {
    toastError(e.response?.data?.message || "Could not mark booking complete")
  }
}

function openRateModal(b) {
  const existing = myRatings.value[b.facility_id]
  rateModal.value = {
    show: true, booking: b,
    rating: existing?.rating || 0,
    comment: existing?.comment || "",
    loading: false, error: "",
  }
}

async function submitRating() {
  rateModal.value.loading = true
  rateModal.value.error = ""
  try {
    const b = rateModal.value.booking
    const { data } = await api.post(`/facilities/${b.facility_id}/ratings`, {
      rating: rateModal.value.rating,
      comment: rateModal.value.comment.trim(),
      booking_id: b.id,
    })
    myRatings.value = { ...myRatings.value, [b.facility_id]: data }
    rateModal.value.show = false
    toastSuccess("Rating submitted — thanks for your feedback!")
  } catch (e) {
    rateModal.value.error = e.response?.data?.message || "Could not save rating."
    toastError("Could not save rating")
  } finally {
    rateModal.value.loading = false
  }
}

function payNow(b) {
  payModal.value = { show: true, booking: b, method: "upi", loading: false, error: "" }
}

async function confirmPayment() {
  payModal.value.loading = true
  payModal.value.error = ""
  try {
    const paymentId = payModal.value.booking?.payment?.id
    if (!paymentId) { payModal.value.error = "Payment record not found."; return }
    const { data } = await api.post(`/payments/${paymentId}/pay`,
      { method: payModal.value.method })
    const b = bookings.value.find(x => x.id === payModal.value.booking.id)
    if (b && b.payment) {
      b.payment.status = "paid"
      b.payment.transaction_ref = data.transaction_ref
      b.payment.method = data.method
      b.status = "confirmed"
      bookings.value = [...bookings.value]
    }
    payModal.value.show = false
    toastSuccess("Payment successful — booking confirmed!")
  } catch (e) {
    payModal.value.error = e.response?.data?.message || "Payment failed."
    toastError("Payment failed")
  } finally {
    payModal.value.loading = false
  }
}

function fmtDate(d) {
  return new Date(d).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "2-digit", month: "short", year: "numeric" })
}
</script>

<style scoped>
.refund-origin { font-weight: 600; color: var(--text-muted); font-size: 0.82rem; }

/* Expired: the slot simply ran out of time unpaid. Muted rather than red —
   nobody did anything wrong, so it should not read like a rejection. */
.badge-expired, .status-expired {
  background: rgba(148, 163, 184, 0.18);
  color: #64748B;
  border: 1px dashed rgba(100, 116, 139, 0.45);
}

.stats-row { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 150px;
  background: #fff; border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem 1.1rem;
}
.stat-val { font-size: 1.5rem; font-weight: 800; color: var(--text); line-height: 1; }
.stat-lbl { font-size: 0.7rem; color: var(--text-muted); margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.04em; }
.stat-ok   .stat-val { color: var(--success); }
.stat-warn .stat-val { color: var(--warning); }
.stat-muted .stat-val { color: var(--text-muted); }

.bookings-list { display: flex; flex-direction: column; gap: 1rem; }
.booking-card { padding: 1.5rem; }
.booking-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
.facility-type { font-size: 0.78rem; color: var(--text-muted); font-weight: 600; }
.booking-facility { font-size: 1.05rem; font-weight: 800; color: var(--navy); margin-bottom: 0.75rem; }
.booking-details { display: flex; gap: 1.25rem; flex-wrap: wrap; margin-bottom: 0.5rem; }
.detail { font-size: 0.85rem; color: var(--text-muted); font-weight: 500; }
.booking-purpose { font-size: 0.85rem; color: var(--text); margin-top: 0.25rem; }
.payment-alert {
  display: flex; justify-content: space-between; align-items: center;
  background: #FBF6EE; border-left: 4px solid var(--warning);
  padding: 0.75rem 1rem; border-radius: 8px; margin-top: 0.75rem;
  font-size: 0.88rem;
}
.payment-done {
  background: #E3EADE; color: #0E7A4F;
  padding: 0.5rem 0.85rem; border-radius: 8px;
  font-size: 0.85rem; margin-top: 0.75rem;
  display: flex; align-items: center; gap: 0.5rem;
}
.payment-wait {
  background: var(--accent); color: var(--text-muted);
  padding: 0.5rem 0.85rem; border-radius: 8px;
  font-size: 0.83rem; margin-top: 0.75rem;
}
.payment-refunded {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--accent); color: var(--text-muted);
  padding: 0.5rem 0.85rem; border-radius: 8px;
  font-size: 0.85rem; margin-top: 0.75rem;
}
.payment-refund-requested {
  background: rgba(180,83,9,0.1); border-left: 4px solid var(--warning);
  padding: 0.6rem 0.85rem; border-radius: 8px;
  font-size: 0.85rem; color: var(--text); margin-top: 0.75rem;
}
.payment-refund-rejected {
  background: rgba(220,38,38,0.08); border-left: 4px solid var(--danger);
  padding: 0.6rem 0.85rem; border-radius: 8px;
  font-size: 0.85rem; color: var(--text); margin-top: 0.75rem;
}
.refund-request-reason-text { font-size: 0.82rem; color: var(--text-muted); font-style: italic; margin: 0.3rem 0 0; }
.req { color: var(--danger); }
.admin-note {
  padding: 0.6rem 0.85rem; background: var(--accent); border-radius: 6px;
  font-size: 0.83rem; color: var(--text-muted);
}
.booking-actions { margin-top: 0.85rem; display: flex; gap: 0.5rem; }
.rate-row { margin-top: 0.85rem; display: flex; align-items: center; gap: 0.6rem; }
.optional-label { font-weight: 400; color: var(--text-muted); }
.invoice-modal { max-width: 420px; }
.invoice-body { padding: 0 0.25rem; }
.inv-row { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.3rem 0; color: var(--text); }
.inv-row span:first-child { color: var(--text-muted); }
.inv-divider { border-top: 1px solid var(--border); margin: 0.5rem 0; }
.inv-total { font-size: 1rem; font-weight: 800; padding-top: 0.4rem; }
.inv-payment-status { font-weight: 700; }
.inv-payment-status.is-paid { color: var(--success); }
.inv-payment-status.is-due { color: var(--warning); }
.td-txn { font-family: monospace; font-size: 0.8rem; }
.filter-bar { padding: 1rem; display: flex; gap: 0.75rem; }
.pay-icon { font-size: 2.5rem; margin: 1rem 0; }
.refund-reason-block { margin-top: 0.5rem; }
.refund-reason-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin-bottom: 0.3rem; }
.refund-reason-text { font-size: 0.88rem; color: var(--text); background: var(--accent); padding: 0.6rem 0.75rem; border-radius: 6px; }
</style>
