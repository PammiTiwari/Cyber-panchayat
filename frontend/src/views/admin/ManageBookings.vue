<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Manage Bookings" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header">
          <p>Review and manage all facility booking requests</p>
        </div>

        <div class="stats-row">
          <div class="stat-card">
            <div class="stat-val">{{ bookings.length }}</div>
            <div class="stat-lbl">Total</div>
          </div>
          <div class="stat-card stat-warn">
            <div class="stat-val">{{ countByStatus('pending') }}</div>
            <div class="stat-lbl">Pending</div>
          </div>
          <div class="stat-card stat-ok">
            <div class="stat-val">{{ countByStatus('confirmed') }}</div>
            <div class="stat-lbl">Confirmed</div>
          </div>
          <div class="stat-card stat-muted">
            <div class="stat-val">{{ countByStatus('completed') }}</div>
            <div class="stat-lbl">Completed</div>
          </div>
          <div class="stat-card stat-danger">
            <div class="stat-val">{{ countByStatus('cancelled') }}</div>
            <div class="stat-lbl">Cancelled</div>
          </div>
          <div class="stat-card stat-warn">
            <div class="stat-val">{{ refundRequestCount }}</div>
            <div class="stat-lbl">Refund Requests</div>
          </div>
        </div>

        <div class="card">
          <div class="filter-bar">
            <input v-model="search" class="form-control" placeholder="Search by citizen or facility..." />
            <select v-model="statusFilter" class="form-control filter-select">
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

          <div v-if="loading" class="spinner"></div>
          <div v-else-if="!paged.length" class="empty-state">
            <div class="empty-icon">📅</div>
            <p>No bookings found</p>
          </div>
          <template v-else>
            <div class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>ID</th><th>Facility</th><th>Citizen</th>
                    <th>Date & Time</th><th>Purpose</th><th>Attendees</th><th>Fee</th>
                    <th>Payment</th><th>Status</th><th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="b in paged" :key="b.id">
                    <td><code class="td-id">{{ b.id }}</code></td>
                    <td>
                      <div class="font-bold">{{ b.facility_name }}</div>
                      <div class="td-sub">{{ b.facility_type }}</div>
                    </td>
                    <td class="text-sm">{{ b.citizen_name }}</td>
                    <td>
                      <div class="td-date-main">{{ fmtDate(b.booking_date) }}</div>
                      <div class="td-sub">{{ b.start_time }} – {{ b.end_time }}</div>
                    </td>
                    <td>
                      <!-- The citizen writes this when booking, and it is what an
                           admin actually judges the request on. Up to 300 chars —
                           far too much for a table cell, so it lives in the card. -->
                      <button class="btn btn-xs btn-outline" @click="openPurposeModal(b)">View</button>
                    </td>
                    <td class="text-sm">{{ b.attendees }}</td>
                    <td class="font-bold">{{ b.fee > 0 ? `₹${b.fee}` : 'Free' }}</td>
                    <td>
                      <span v-if="b.payment" :class="`badge badge-${paymentBadge(b).cls}`">{{ paymentBadge(b).label }}</span>
                      <span v-else class="td-dash">—</span>
                    </td>
                    <td><span :class="`badge badge-${statusBadge(b).cls}`">{{ statusBadge(b).label }}</span></td>
                    <td>
                      <div v-if="b.payment?.status === 'refund_requested'" class="action-btns">
                        <button class="btn btn-xs btn-warning" @click="openReviewModal(b)">View</button>
                        <button class="btn btn-xs btn-outline" @click="viewInvoice(b)">🧾 Invoice</button>
                      </div>
                      <div v-else-if="b.status === 'pending'" class="action-btns">
                        <button class="btn btn-xs btn-success" @click="updateStatus(b, 'confirmed')">Confirm</button>
                        <button class="btn btn-xs btn-danger" @click="updateStatus(b, 'cancelled')">Cancel</button>
                      </div>
                      <!-- Confirmed, but the fee never came in. There is nothing to
                           refund, yet the booking is still live and holding its slot —
                           the admin has to be able to call it off. The API allows this
                           (only cancelled/completed/expired are terminal); without this
                           branch the row fell through to "No action needed" and the
                           admin had no way to cancel it at all. -->
                      <div v-else-if="b.status === 'confirmed' && b.payment?.status === 'pending'" class="action-btns">
                        <button class="btn btn-xs btn-danger" @click="updateStatus(b, 'cancelled')">Cancel</button>
                      </div>
                      <div v-else-if="['confirmed','completed'].includes(b.status) && b.payment?.status === 'paid'" class="action-btns">
                        <button v-if="b.payment?.refund_request_reason" class="btn btn-xs btn-outline" @click="openRefundDetailModal(b)">View</button>
                        <!-- Once the booking is completed the slot has been used, so
                             there is nothing left to cancel and nothing to refund —
                             the API refuses both ("A completed booking can no longer
                             be changed"). Offering the button anyway just walks the
                             admin into an error, so it only shows while the booking
                             can still actually be cancelled. -->
                        <button v-if="b.status !== 'completed'" class="btn btn-xs btn-danger" @click="openRefundModal(b)">Cancel &amp; Refund</button>
                        <button class="btn btn-xs btn-outline" @click="viewInvoice(b)">🧾 Invoice</button>
                      </div>
                      <div v-else-if="b.payment?.status === 'refunded'" class="action-btns">
                        <button class="btn btn-xs btn-outline" @click="openRefundDetailModal(b)">View</button>
                        <button class="btn btn-xs btn-outline" @click="viewInvoice(b)">🧾 Invoice</button>
                      </div>
                      <!-- Cancelled and expired bookings are closed business:
                           no money to move, no slot to free, nothing left for the
                           admin to decide. Saying so beats a bare dash, which reads
                           like the row failed to load. -->
                      <span v-else class="no-action">No action needed</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="pagination" v-if="totalPages > 1">
              <button class="page-btn" aria-label="Previous page" :disabled="page === 1" @click="page--">&lt;</button>
              <button v-for="p in totalPages" :key="p" class="page-btn" :class="{ active: page === p }" @click="page = p">{{ p }}</button>
              <button class="page-btn" aria-label="Next page" :disabled="page === totalPages" @click="page++">&gt;</button>
            </div>
          </template>
        </div>
      </div>
    </div>
    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />

    <!-- Cancel & Refund modal -->
    <div v-if="refundModal.show" class="modal-overlay" @click.self="refundModal.show = false">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Cancel &amp; Refund</h2>
          <button class="modal-close" aria-label="Close" @click="refundModal.show = false">✕</button>
        </div>
        <p class="text-sm text-muted mb-4">
          Cancelling <strong>{{ refundModal.booking?.facility_name }}</strong> for
          {{ refundModal.booking?.citizen_name }} and refunding ₹{{ refundModal.booking?.payment?.amount }}.
        </p>
        <!-- Rejecting a refund request settles one question — whether the
             citizen's own reason earns their money back. It does not freeze the
             booking, so cancelling it later for a different reason (the hall
             floods) stays allowed. But the admin should be told they already
             said no here, so they are not undoing their own decision by
             accident. -->
        <div v-if="isRefundRejected(refundModal.booking)" class="prior-reject">
          <strong>⚠ You already rejected a refund request on this booking.</strong>
          <div class="prior-reject-line">
            <span class="prior-reject-label">Citizen asked:</span>
            {{ refundModal.booking.payment.refund_request_reason }}
          </div>
          <div class="prior-reject-line">
            <span class="prior-reject-label">You replied:</span>
            {{ refundModal.booking.payment.refund_rejected_reason || 'No reason was given.' }}
          </div>
          <div class="prior-reject-note">Going ahead now refunds the money anyway.</div>
        </div>
        <div class="form-group">
          <label>Reason for refund (optional)</label>
          <textarea v-model="refundModal.reason" class="form-control" rows="3"
                    placeholder="e.g. Facility unavailable due to maintenance"></textarea>
        </div>
        <div v-if="refundModal.error" class="alert alert-error mb-4">{{ refundModal.error }}</div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="refundModal.show = false">Close</button>
          <button class="btn btn-danger" :disabled="refundModal.loading" @click="submitRefund">
            {{ refundModal.loading ? 'Processing…' : 'Cancel & Refund' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Refund request review modal -->
    <div v-if="reviewModal.show" class="modal-overlay" @click.self="reviewModal.show = false">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Refund Request</h2>
          <button class="modal-close" aria-label="Close" @click="reviewModal.show = false">✕</button>
        </div>
        <p class="text-sm text-muted mb-2">
          <strong>{{ reviewModal.booking?.citizen_name }}</strong> — {{ reviewModal.booking?.facility_name }} · ₹{{ reviewModal.booking?.payment?.amount }}
        </p>
        <div class="refund-reason-block">
          <div class="refund-reason-label">Citizen's Reason</div>
          <div class="refund-reason-text">{{ reviewModal.booking?.payment?.refund_request_reason }}</div>
        </div>
        <div class="form-group">
          <label>Your Note <span class="optional-label">(optional)</span></label>
          <textarea v-model="reviewModal.note" class="form-control" rows="2"
                    placeholder="e.g. Approved as requested / Not eligible — event already took place"></textarea>
        </div>
        <div v-if="reviewModal.error" class="alert alert-error mt-4">{{ reviewModal.error }}</div>
        <div class="modal-footer">
          <button class="btn btn-secondary" :disabled="!!reviewModal.loading" @click="rejectRefundRequest">
            {{ reviewModal.loading === 'reject' ? 'Rejecting…' : 'Reject Request' }}
          </button>
          <button class="btn btn-danger" :disabled="!!reviewModal.loading" @click="approveRefundRequest">
            {{ reviewModal.loading === 'approve' ? 'Refunding…' : '✓ Refund It' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Resolved refund detail — what the citizen asked for, and how it was resolved -->
    <!-- Purpose of booking -->
    <div v-if="purposeModal.show" class="modal-overlay" @click.self="purposeModal.show = false">
      <div class="modal booking-modal">
        <div class="modal-header">
          <h2>Booking Details</h2>
          <button class="modal-close" aria-label="Close" @click="purposeModal.show = false">&#10005;</button>
        </div>

        <template v-if="purposeModal.booking">
          <!-- Who booked it, and where -->
          <div class="bk-who">
            <div class="bk-avatar">{{ initialsOf(purposeModal.booking.citizen_name) }}</div>
            <div class="bk-who-text">
              <div class="bk-name">{{ purposeModal.booking.citizen_name }}</div>
              <div class="bk-facility">{{ purposeModal.booking.facility_name }}</div>
            </div>
            <span :class="`badge badge-${statusBadge(purposeModal.booking).cls}`">
              {{ statusBadge(purposeModal.booking).label }}
            </span>
          </div>

          <!-- The three things an admin actually reads off this card -->
          <div class="bk-grid">
            <div class="bk-cell">
              <div class="bk-cell-label">Date</div>
              <div class="bk-cell-value">{{ fmtDateLong(purposeModal.booking.booking_date) }}</div>
              <div class="bk-cell-sub">{{ dayOffset(purposeModal.booking.booking_date) }}</div>
            </div>
            <div class="bk-cell">
              <div class="bk-cell-label">Time</div>
              <div class="bk-cell-value">
                {{ timeRange(purposeModal.booking.start_time, purposeModal.booking.end_time) }}
              </div>
              <div class="bk-cell-sub">
                {{ slotLength(purposeModal.booking.start_time, purposeModal.booking.end_time) }}
              </div>
            </div>
            <div class="bk-cell">
              <div class="bk-cell-label">Attendees</div>
              <div class="bk-cell-value">{{ purposeModal.booking.attendees }}</div>
              <div class="bk-cell-sub">&#8377;{{ purposeModal.booking.fee }} fee</div>
            </div>
          </div>

          <!-- The refund story belongs on the booking's own card: an admin
               opening this to decide something needs the whole history, not
               just what the hall was booked for. -->
          <div v-if="purposeModal.booking.payment?.refund_request_reason" class="bk-purpose">
            <div class="bk-cell-label">Refund history</div>
            <p class="bk-purpose-text">
              <strong>{{ refundOutcome(purposeModal.booking) }}</strong><br>
              <span class="bk-refund-line">Citizen&rsquo;s reason: {{ purposeModal.booking.payment.refund_request_reason }}</span><br>
              <span v-if="purposeModal.booking.payment.refund_rejected_at" class="bk-refund-line">
                Rejected first: {{ purposeModal.booking.payment.refund_rejected_reason || 'no reason given' }}<br>
              </span>
              <span v-if="purposeModal.booking.payment.status === 'refunded'" class="bk-refund-line">
                {{ purposeModal.booking.payment.refund_rejected_at ? 'Refunded later:' : 'Accepted:' }}
                {{ purposeModal.booking.payment.refund_reason || 'No reason was given.' }}
              </span>
            </p>
          </div>

          <div class="bk-purpose">
            <div class="bk-cell-label">Citizen&rsquo;s purpose</div>
            <p class="bk-purpose-text" :class="{ 'is-empty': !purposeModal.booking.purpose }">
              {{ purposeModal.booking.purpose || 'No purpose was given.' }}
            </p>
          </div>
        </template>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="purposeModal.show = false">Close</button>
        </div>
      </div>
    </div>

    <div v-if="refundDetailModal.show" class="modal-overlay" @click.self="refundDetailModal.show = false">
      <div class="modal modal-w-sm">
        <div class="modal-header">
          <h2>Refund Details</h2>
          <button class="modal-close" aria-label="Close" @click="refundDetailModal.show = false">✕</button>
        </div>
        <p class="text-sm text-muted mb-2">
          <strong>{{ refundDetailModal.booking?.citizen_name }}</strong> — {{ refundDetailModal.booking?.facility_name }} ·
          ₹{{ refundDetailModal.booking?.payment?.amount }}
        </p>
        <!-- Only the refund's own story, in the order it happened. What the
             hall was booked for is not part of it — that lives on the booking
             card. A rejection that is later overturned needs a third block,
             because the two notes explain different decisions. -->
        <!-- The citizen's block only exists when a citizen actually asked. A
             refund the admin decided on their own has no request behind
             it, so showing an empty "Citizen's reason" invented a step that
             never happened — and calling it "Accepted" implied a request had
             been granted when there was none. -->
        <div v-if="refundDetailModal.booking?.payment?.refund_request_reason" class="refund-reason-block">
          <div class="refund-reason-label">Citizen&rsquo;s reason</div>
          <div class="refund-reason-text">{{ refundDetailModal.booking.payment.refund_request_reason }}</div>
        </div>
        <div v-if="refundDetailModal.booking?.payment?.refund_rejected_at" class="refund-reason-block">
          <div class="refund-reason-label">Rejected first &mdash; reason</div>
          <div class="refund-reason-text">{{ refundDetailModal.booking.payment.refund_rejected_reason || 'No reason was given.' }}</div>
        </div>
        <div v-if="refundDetailModal.booking?.payment?.status === 'refunded'" class="refund-reason-block">
          <div class="refund-reason-label">{{ refundLabel(refundDetailModal.booking) }}</div>
          <div class="refund-reason-text">{{ refundDetailModal.booking?.payment?.refund_reason || 'No note was given.' }}</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="refundDetailModal.show = false">Close</button>
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
            <div class="inv-row"><span>Paid On</span><span>{{ invoice.paid_at ? fmtPaidAt(invoice.paid_at) : '—' }}</span></div>
            <div class="inv-row" v-if="invoice.transaction_ref"><span>Txn Ref</span><span class="td-txn">{{ invoice.transaction_ref }}</span></div>
          </template>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline" @click="downloadInvoice(invoice)">⬇ Download</button>
          <button class="btn btn-secondary" @click="invoice = null">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue"
/**
 * Manage Bookings - Admin workflow for facility booking approvals
 * Workflow: pending → confirmed or cancelled (final, by admin only)
 * Citizens can only pay for a booking once it's confirmed here
 */
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import api from "../../api"
import { downloadInvoicePdf } from "../../utils/invoicePdf"
import { useToast } from "../../composables/useToast"
import { useDebouncedValue } from "../../composables/useDebounce"

const { success: toastSuccess, error: toastError } = useToast()

const loading = ref(true)
const bookings = ref([]) // All facility bookings
const showNotif = ref(false)
const unread = ref(0)
const statusFilter = ref("") // Filter by pending/confirmed/cancelled/completed
const search = ref("")
const debouncedSearch = useDebouncedValue(search, 300)
const refundModal = ref({ show: false, booking: null, reason: "", loading: false, error: "" })
const reviewModal = ref({ show: false, booking: null, note: "", loading: false, error: "" })
const purposeModal = ref({ show: false, booking: null })
function openPurposeModal(b) {
  purposeModal.value = { show: true, booking: b }
}

const refundDetailModal = ref({ show: false, booking: null })
const invoice = ref(null)

function openRefundDetailModal(b) {
  refundDetailModal.value = { show: true, booking: b }
}
const page = ref(1)
watch([search, statusFilter], () => { page.value = 1 })
const perPage = 10

function countByStatus(s) {
  return bookings.value.filter(b => b.status === s).length
}

// A payment can only be "paid" with a refund_request_reason already set once
// a request on it has been rejected — approval moves status to "refunded"
// instead, so this combination is otherwise unreachable.
// The rejection is marked by its timestamp, not by whether a note was typed —
// an admin who declines without a reason still rejected it.
function isRefundRejected(b) {
  return b.payment?.status === "paid" && !!b.payment?.refund_rejected_at
}

// A cancelled booking whose payment was already refunded reads better as
// "Refunded" than a generic "Cancelled" in the status column, and a pending
// refund request should be visible here too, whatever the booking itself
// happens to be doing (confirmed or completed).
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
    return { label: b.cancelled_by === "citizen" ? "Cancelled by Citizen" : "Cancelled by Admin", cls: "cancelled" }
  }
  return { label: b.status, cls: b.status }
}

// Same "paid" underlying status, but the Payment column should distinguish a
// booking that's simply paid from one whose refund request was rejected —
// otherwise that history disappears the moment status reverts to "paid".
// Names the final block for what actually happened, so it never claims a
// request was "accepted" when nobody made one.
function refundLabel(b) {
  const p = b?.payment
  if (p?.refund_rejected_at) return "Refunded later — reason"
  if (p?.refund_request_reason) return "Accepted — reason"
  return "Refunded by admin — reason"
}

// What actually happened to the refund request, in one line.
function refundOutcome(b) {
  const p = b?.payment
  if (p?.status === "refund_requested") return "Requested — awaiting your decision"
  if (p?.status === "refunded" && !p.refund_request_reason) {
    return "Refunded by admin — the citizen never asked"
  }
  if (p?.status === "refunded") {
    // The request was turned down; the money went back later for a reason of
    // the admin's own, not because the citizen asked.
    return p.refund_rejected_at
      ? "Rejected, then refunded by admin"
      : "Approved — money returned"
  }
  if (p?.status === "paid") return "Rejected — the citizen kept the booking"
  return "Requested"
}

function paymentBadge(b) {
  if (isRefundRejected(b)) {
    return { label: "refund rejected", cls: "refund_rejected" }
  }
  return { label: b.payment.status.replace("_", " "), cls: b.payment.status }
}

const refundRequestCount = computed(() =>
  bookings.value.filter(b => b.payment?.status === "refund_requested").length
)

const filtered = computed(() => {
  let list = bookings.value
  // Neither of these is a real booking status (those stay "confirmed" /
  // "cancelled") — both are about the payment, so they need their own checks
  // instead of matching b.status.
  if (statusFilter.value === "refunded") list = list.filter(b => b.payment?.status === "refunded")
  else if (statusFilter.value === "refund_requested") list = list.filter(b => b.payment?.status === "refund_requested")
  else if (statusFilter.value) list = list.filter(b => b.status === statusFilter.value)
  if (debouncedSearch.value) {
    const q = debouncedSearch.value.toLowerCase()
    list = list.filter(b =>
      b.citizen_name?.toLowerCase().includes(q) ||
      b.facility_name?.toLowerCase().includes(q)
    )
  }
  return list
})

const totalPages = computed(() => Math.ceil(filtered.value.length / perPage))
const paged = computed(() => filtered.value.slice((page.value - 1) * perPage, page.value * perPage))

onMounted(async () => {
  const [bRes, nRes] = await Promise.all([api.get("/bookings"), api.get("/notifications")])
  bookings.value = bRes.data
  unread.value = nRes.data.unread_count
  loading.value = false
})

async function updateStatus(b, status) {
  const action = status === "confirmed" ? "confirm" : "cancel"
  if (!confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} this booking?`)) return
  try {
    const { data } = await api.put(`/bookings/${b.id}/status`, { status })
    const idx = bookings.value.findIndex(x => x.id === b.id)
    if (idx >= 0) bookings.value[idx] = data
    bookings.value = [...bookings.value]
    toastSuccess(status === "confirmed" ? "Booking confirmed" : "Booking cancelled")
  } catch (e) {
    toastError(e.response?.data?.message || `Could not ${action} booking`)
  }
}

function openRefundModal(b) {
  refundModal.value = { show: true, booking: b, reason: "", loading: false, error: "" }
}

async function submitRefund() {
  refundModal.value.loading = true
  refundModal.value.error = ""
  try {
    const { data } = await api.put(`/bookings/${refundModal.value.booking.id}/status`,
      { status: "cancelled", refund_reason: refundModal.value.reason.trim() })
    const idx = bookings.value.findIndex(x => x.id === refundModal.value.booking.id)
    if (idx >= 0) bookings.value[idx] = data
    bookings.value = [...bookings.value]
    refundModal.value.show = false
    toastSuccess("Booking cancelled and refund processed")
  } catch (e) {
    refundModal.value.error = e.response?.data?.message || "Could not process refund."
    toastError("Could not process refund")
  } finally {
    refundModal.value.loading = false
  }
}

function openReviewModal(b) {
  reviewModal.value = { show: true, booking: b, note: "", loading: false, error: "" }
}

async function approveRefundRequest() {
  reviewModal.value.loading = "approve"
  reviewModal.value.error = ""
  try {
    const b = reviewModal.value.booking
    const { data } = await api.put(`/bookings/${b.id}/status`,
      { status: "cancelled", refund_reason: reviewModal.value.note.trim() })
    const idx = bookings.value.findIndex(x => x.id === b.id)
    if (idx >= 0) bookings.value[idx] = data
    bookings.value = [...bookings.value]
    reviewModal.value.show = false
    toastSuccess("Refund approved")
  } catch (e) {
    reviewModal.value.error = e.response?.data?.message || "Could not process refund."
    toastError("Could not process refund")
  } finally {
    reviewModal.value.loading = false
  }
}

async function rejectRefundRequest() {
  reviewModal.value.loading = "reject"
  reviewModal.value.error = ""
  try {
    const { data } = await api.put(`/bookings/${reviewModal.value.booking.id}/reject-refund`,
      { reason: reviewModal.value.note.trim() })
    const idx = bookings.value.findIndex(x => x.id === reviewModal.value.booking.id)
    if (idx >= 0) bookings.value[idx] = data
    bookings.value = [...bookings.value]
    reviewModal.value.show = false
    toastSuccess("Refund request rejected")
  } catch (e) {
    reviewModal.value.error = e.response?.data?.message || "Could not reject the request."
    toastError("Could not reject the request")
  } finally {
    reviewModal.value.loading = false
  }
}

function initialsOf(name) {
  return (name || "?").split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2)
}

// The API sends a plain "HH:MM" wall-clock string. Indian users read booking
// slots in 12-hour time, so render it that way rather than showing 07:00.
function fmtTime12(t) {
  if (!t) return "--"
  const [h, m] = String(t).split(":")
  const hour = Number(h)
  const suffix = hour < 12 ? "am" : "pm"
  const h12 = hour % 12 === 0 ? 12 : hour % 12
  return `${h12}:${m} ${suffix}`
}

// "7:00 – 9:00 am" rather than "7:00 am – 9:00 am": when both ends share a
// meridiem, repeating it only makes the range wrap onto a second line.
function timeRange(start, end) {
  if (!start || !end) return "--"
  const a = fmtTime12(start), b = fmtTime12(end)
  const [at, as] = a.split(" "), [bt, bs] = b.split(" ")
  return as === bs ? `${at} – ${bt} ${bs}` : `${a} – ${b}`
}

function slotLength(start, end) {
  if (!start || !end) return ""
  const [sh, sm] = String(start).split(":").map(Number)
  const [eh, em] = String(end).split(":").map(Number)
  const mins = (eh * 60 + em) - (sh * 60 + sm)
  if (mins <= 0) return ""
  const h = Math.floor(mins / 60), m = mins % 60
  const parts = []
  if (h) parts.push(`${h} hour${h === 1 ? "" : "s"}`)
  if (m) parts.push(`${m} min`)
  return parts.join(" ")
}

function fmtDateLong(d) {
  if (!d) return "--"
  const dt = new Date(d + "T00:00:00")
  const p = Object.fromEntries(
    new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata", weekday: "short", day: "2-digit", month: "short", year: "numeric",
    }).formatToParts(dt).map(x => [x.type, x.value])
  )
  // Assembled by hand because en-IN renders "Fri, 07 Aug, 2026" — the comma
  // before the year pushes the date onto a second line in a narrow cell.
  return `${p.weekday}, ${p.day} ${p.month} ${p.year}`
}

// "in 3 days" / "5 days ago" reads faster than a second date when an admin is
// scanning a queue to decide what still needs approving.
function dayOffset(d) {
  if (!d) return ""
  const today = new Date(); today.setHours(0, 0, 0, 0)
  const target = new Date(d + "T00:00:00"); target.setHours(0, 0, 0, 0)
  const days = Math.round((target - today) / 86400000)
  if (days === 0) return "Today"
  if (days === 1) return "Tomorrow"
  if (days === -1) return "Yesterday"
  return days > 0 ? `in ${days} days` : `${Math.abs(days)} days ago`
}

function fmtDate(d) {
  return new Date(d + "T00:00:00").toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", day: "2-digit", month: "short", year: "numeric" })
}

function fmtPaidAt(d) {
  return new Date(d).toLocaleDateString("en-IN", { timeZone: "Asia/Kolkata", weekday: "short", day: "2-digit", month: "short", year: "numeric" })
}

// An invoice is a receipt for the payment itself, not the booking's current
// state — a later refund doesn't undo that the citizen paid, so it always
// reads "PAID" and never mentions the refund.
function invoicePaymentLabel(status) {
  if (status === "free") return "Free"
  if (["paid", "refunded", "refund_requested"].includes(status)) return "PAID"
  return status.replace("_", " ").toUpperCase()
}

async function viewInvoice(b) {
  try {
    const { data } = await api.get(`/bookings/${b.id}/invoice`)
    invoice.value = data
  } catch {
    toastError("Could not load invoice")
  }
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
    rows.push(["Paid On", inv.paid_at ? fmtPaidAt(inv.paid_at) : "—"])
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
</script>

<style scoped>
.prior-reject {
  border: 1px solid var(--warning, #d97706);
  background: rgba(217, 119, 6, 0.07);
  border-radius: var(--radius-sm);
  padding: 0.7rem 0.8rem;
  margin-bottom: 1rem;
  font-size: 0.82rem;
  line-height: 1.5;
}
.prior-reject-line { margin-top: 0.35rem; color: var(--text); }
.prior-reject-label { color: var(--text-muted); font-weight: 600; }
.prior-reject-note { margin-top: 0.5rem; color: var(--text-muted); font-size: 0.78rem; }
.bk-refund-line { font-size: 0.83rem; color: var(--text-muted); }

/* Shown where a booking has no admin action left. Deliberately quiet — it is
   a statement of fact, not a control. */
.no-action {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
  color: var(--text-muted);
  background: var(--accent);
  border: 1px dashed var(--border);
  border-radius: 999px;
  padding: 0.26rem 0.55rem;
}

/* Expired: the slot simply ran out of time unpaid. Muted rather than red —
   nobody did anything wrong, so it should not read like a rejection. */
.badge-expired, .status-expired {
  background: rgba(148, 163, 184, 0.18);
  color: #64748B;
  border: 1px dashed rgba(100, 116, 139, 0.45);
}

.stats-row { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
.stat-card {
  flex: 1; min-width: 110px;
  background: #fff; border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem 1.1rem;
}
.stat-val { font-size: 1.5rem; font-weight: 800; color: var(--text); line-height: 1; }
.stat-lbl { font-size: 0.7rem; color: var(--text-muted); margin-top: 0.3rem; text-transform: uppercase; letter-spacing: 0.04em; }
.stat-ok   .stat-val { color: var(--success); }
.stat-warn .stat-val { color: var(--warning); }
.stat-muted .stat-val { color: var(--text-muted); }
.stat-danger .stat-val { color: var(--danger); }
.action-btns { display: flex; gap: 0.35rem; flex-wrap: wrap; }
.td-id { font-family: var(--font-mono); font-size: 0.8rem; color: var(--accent-foreground); background: var(--accent); padding: 0.15rem 0.45rem; border-radius: 4px; }
.td-sub { font-size: 0.75rem; color: var(--text-muted); }
.td-date-main { font-weight: 600; font-size: 0.88rem; }
.td-dash { color: var(--text-muted); font-size: 0.82rem; }
/* ── Booking details modal ─────────────────────────────────────────── */
.booking-modal { max-width: 520px; }

.bk-who {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--accent);
  margin-bottom: 0.9rem;
}
.bk-avatar {
  width: 38px; height: 38px; flex-shrink: 0;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.78rem; font-weight: 700; letter-spacing: 0.02em;
}
.bk-who-text { min-width: 0; flex: 1; }
.bk-name { font-weight: 700; font-size: 0.92rem; color: var(--text); }
.bk-facility {
  font-size: 0.8rem; color: var(--text-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.bk-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.9rem;
}
.bk-cell {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.6rem 0.65rem;
  background: var(--card);
  min-width: 0;
}
.bk-cell-label {
  font-size: 0.66rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--text-muted); margin-bottom: 0.3rem;
}
.bk-cell-value {
  font-size: 0.85rem; font-weight: 700; color: var(--text);
  line-height: 1.35; white-space: nowrap;
}
.bk-cell-sub { font-size: 0.72rem; color: var(--text-muted); margin-top: 0.15rem; }

.bk-purpose { margin-bottom: 0.25rem; }
.bk-purpose-text {
  font-size: 0.88rem; line-height: 1.55; color: var(--text);
  background: var(--accent);
  border-left: 3px solid var(--primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  padding: 0.65rem 0.8rem;
  margin: 0;
}
.bk-purpose-text.is-empty { color: var(--text-muted); font-style: italic; border-left-color: var(--border); }

/* Below this the three stat cells are too narrow to read, so they stack. */
@media (max-width: 420px) {
  .bk-grid { grid-template-columns: 1fr; }
}

.refund-reason-block { margin: 1rem 0; }
.refund-reason-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin-bottom: 0.3rem; }
.refund-reason-text { font-size: 0.88rem; color: var(--text); background: var(--accent); padding: 0.6rem 0.75rem; border-radius: 6px; }
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
</style>
