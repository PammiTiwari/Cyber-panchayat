<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Book a Facility" :unread-count="unread" @notifications="showNotif = true" />
      <div class="content-area">
        <div class="page-header">
          <p>Browse and book community halls, sports grounds, parks and more.</p>
        </div>

        <div v-if="loading" class="facilities-grid">
          <SkeletonLoader v-for="i in 6" :key="i" type="card" />
        </div>
        <div v-else>
          <div class="filter-bar">
            <div class="search-wrapper">
              <input
                ref="searchInput"
                v-model="searchQuery"
                type="search"
                class="form-control"
                aria-label="Search facilities by name, type, or location"
                placeholder="🔍 Search by name, type, or location...  (press /)"
              />
              <button
                v-if="searchQuery"
                type="button"
                class="search-clear"
                aria-label="Clear search"
                @click="clearSearch"
              >✕</button>
            </div>
            <select v-model="facilityTypeFilter" class="form-control filter-select">
              <option value="">Type: All</option>
              <option value="Community Hall">Community Hall</option>
              <option value="Sports Ground">Sports Ground</option>
              <option value="Park">Park</option>
              <option value="Conference Room">Conference Room</option>
              <option value="Auditorium">Auditorium</option>
              <option value="Library Hall">Library Hall</option>
              <option value="Swimming Pool">Swimming Pool</option>
              <option value="Other">Other</option>
            </select>
            <select v-model="priceFilter" class="form-control filter-select">
              <option value="">Price: All</option>
              <option value="free">Free</option>
              <option value="budget">Under ₹500/hr</option>
              <option value="mid">₹500-1000/hr</option>
              <option value="premium">Above ₹1000/hr</option>
            </select>
            <select v-model="capacityFilter" class="form-control filter-select">
              <option value="">Capacity: Any</option>
              <option value="25">Fits 25+</option>
              <option value="50">Fits 50+</option>
              <option value="100">Fits 100+</option>
              <option value="200">Fits 200+</option>
            </select>
            <select v-model="ratingFilter" class="form-control filter-select">
              <option value="">Rating: Any</option>
              <option value="5">5 ⭐ only</option>
              <option value="4">4 ⭐ &amp; up</option>
              <option value="3">3 ⭐ &amp; up</option>
              <option value="2">2 ⭐ &amp; up</option>
              <option value="1">1 ⭐ &amp; up</option>
            </select>
            <!-- Offered once something is saved, so it is never a filter that
                 guarantees an empty grid. Also kept while the filter is on even
                 if the count drops to zero, otherwise un-favouriting your last
                 one would remove the control that turns the filter back off and
                 leave you staring at an empty page. -->
            <button
              v-if="favouriteCount || favouritesOnly"
              type="button"
              class="fav-filter-btn"
              :class="{ 'is-on': favouritesOnly }"
              :aria-pressed="String(favouritesOnly)"
              @click="favouritesOnly = !favouritesOnly"
            >
              <svg viewBox="0 0 24 24" class="fav-icon" aria-hidden="true">
                <path d="M12 21s-7.5-4.7-9.6-9A5.3 5.3 0 0 1 12 6.1 5.3 5.3 0 0 1 21.6 12c-2.1 4.3-9.6 9-9.6 9z" />
              </svg>
              Favourites
              <span class="fav-filter-n">{{ favouriteCount }}</span>
            </button>
            <select v-if="wards.length > 1" v-model="wardFilter" class="form-control filter-select">
              <option value="">Ward: All</option>
              <option v-for="w in wards" :key="w" :value="w">{{ w }}</option>
            </select>
            <label class="date-label">
              Free on
              <input v-model="availableOnDate" type="date" class="form-control date-input" :min="today" />
            </label>
            <button
              v-if="hasActiveFilters"
              class="btn btn-outline btn-sm clear-filters"
              @click="clearAllFilters"
            >
              Clear Filters
            </button>
          </div>

          <FilterChips :filters="activeChips" @remove="clearFilter" />

          <div v-if="hasActiveFilters" class="filter-info">
            <span class="result-count" aria-live="polite">📊 {{ filtered.length }} facilit{{ filtered.length !== 1 ? 'ies' : 'y' }} found</span>
            <span v-if="availabilityLoading" class="availability-note">checking availability…</span>
            <span v-else-if="availableOnDate" class="availability-note">free all day on {{ availableOnDate }}</span>
          </div>

          <div v-if="filtered.length > 0" class="facilities-grid">
            <div v-for="f in filtered" :key="f.id" class="facility-card card">
              <ImageGallery v-if="f.image_urls?.length" :images="f.image_urls" alt="Facility photo" class="facility-gallery" />
              <div class="facility-header">
                <div class="facility-type-icon">{{ typeIcon(f.facility_type) }}</div>
                <span class="facility-type-badge">{{ f.facility_type }}</span>
                <!-- An SVG rather than an emoji heart so it can be filled,
                     coloured and animated from CSS. aria-pressed tells a screen
                     reader this is a toggle and which way it is currently set. -->
                <button
                  type="button"
                  class="fav-btn"
                  :class="{ 'is-fav': isFavourite(f.id) }"
                  :aria-pressed="String(isFavourite(f.id))"
                  :title="isFavourite(f.id) ? 'Remove from favourites' : 'Save to favourites'"
                  :aria-label="isFavourite(f.id) ? `Remove ${f.name} from favourites` : `Save ${f.name} to favourites`"
                  @click.stop="toggleFavourite(f)"
                >
                  <svg viewBox="0 0 24 24" class="fav-icon" aria-hidden="true">
                    <path d="M12 21s-7.5-4.7-9.6-9A5.3 5.3 0 0 1 12 6.1 5.3 5.3 0 0 1 21.6 12c-2.1 4.3-9.6 9-9.6 9z" />
                  </svg>
                </button>
              </div>
              <h3 class="facility-name">{{ f.name }}</h3>
              <p class="facility-desc">{{ f.description }}</p>
              <div class="facility-info">
                <div class="info-chip">👥 Capacity: {{ f.capacity }}</div>
                <div class="info-chip">📍 {{ f.ward || 'City' }}</div>
                <div class="info-chip">{{ f.fee_per_hour > 0 ? `💰 ₹${f.fee_per_hour}/hr` : '🆓 Free' }}</div>
              </div>
              <button
                v-if="f.rating_count > 0"
                type="button"
                class="facility-rating-row"
                :title="`See all ${f.rating_count} review${f.rating_count !== 1 ? 's' : ''} for ${f.name}`"
                :aria-label="`See all ${f.rating_count} review${f.rating_count !== 1 ? 's' : ''} for ${f.name}`"
                @click="openRatings(f)"
              >
                <StarRating :model-value="f.avg_rating" readonly size="sm" />
                <span class="rating-score">{{ f.avg_rating }}</span>
                <span class="rating-dot" aria-hidden="true">·</span>
                <span class="rating-summary">{{ f.rating_count }} review{{ f.rating_count !== 1 ? 's' : '' }}</span>
                <span class="rating-chevron" aria-hidden="true">&rsaquo;</span>
              </button>
              <div v-else class="facility-rating-row facility-rating-empty">
                <span class="rating-summary">No ratings yet</span>
              </div>
              <div v-if="f.amenities" class="amenities">
                <span v-for="a in f.amenities.split(',')" :key="a" class="amenity-chip">{{ a.trim() }}</span>
              </div>
              <div class="facility-address">📍 {{ f.address }}</div>
              <button class="btn btn-primary w-full mt-4" @click="openBooking(f)">
                📅 Book Now
              </button>
            </div>
          </div>
          <EmptyState
            v-else
            type="search"
            title="No Facilities Found"
            description="Try adjusting your search filters or browse all available facilities."
            buttonText="Clear Filters"
            @action="clearAllFilters"
          />
        </div>
      </div>
    </div>

    <!-- Booking modal -->
    <div v-if="bookingModal.show" class="modal-overlay" @click.self="bookingModal.show = false">
      <div class="modal modal-w-lg">
        <div class="modal-header">
          <h2>Book {{ bookingModal.facility?.name }}</h2>
          <button class="modal-close" aria-label="Close" @click="bookingModal.show = false">✕</button>
        </div>

        <ImageGallery v-if="bookingModal.facility?.image_urls?.length" :images="bookingModal.facility.image_urls" alt="Facility photo" class="mb-4" />
        <div class="facility-booking-info">
          <span>👥 Capacity: {{ bookingModal.facility?.capacity }}</span>
          <span>{{ bookingModal.facility?.fee_per_hour > 0 ? `💰 ₹${bookingModal.facility?.fee_per_hour}/hr` : '🆓 Free' }}</span>
          <span>📍 {{ bookingModal.facility?.ward }}</span>
        </div>

        <div v-if="bookingModal.error" class="alert alert-error mb-4">{{ bookingModal.error }}</div>

        <form @submit.prevent="submitBooking" class="flex-col gap-4">
          <div class="form-group">
            <label>Booking Date *</label>
            <input v-model="bookingForm.booking_date" type="date" class="form-control"
                   :min="today" required @change="loadAvailability" />
          </div>

          <!-- Already booked slots for selected date -->
          <div v-if="slotsLoading" class="text-sm text-muted">Checking availability...</div>
          <div v-else-if="bookedSlots.length > 0" class="booked-slots-info">
            <div class="booked-slots-title">⚠️ Already booked on this date:</div>
            <div v-for="slot in bookedSlots" :key="slot.start" class="booked-slot">
              {{ slot.start }} – {{ slot.end }}
              <span :class="`badge badge-${slot.status}`" class="ml-2">{{ slot.status }}</span>
            </div>
          </div>
          <div v-else-if="bookingForm.booking_date" class="alert alert-success m-0 slot-available-alert">
            ✅ No existing bookings on this date — all slots available
          </div>

          <div class="grid-2">
            <div class="form-group">
              <label>Start Time *</label>
              <input v-model="bookingForm.start_time" type="time" class="form-control"
                     min="06:00" max="21:00" required />
            </div>
            <div class="form-group">
              <label>End Time *</label>
              <input v-model="bookingForm.end_time" type="time" class="form-control"
                     min="07:00" max="22:00" required />
            </div>
          </div>
          <div v-if="estimatedFee > 0" class="fee-preview">
            Estimated fee: <strong>₹{{ estimatedFee }}</strong>
            <span class="text-xs text-muted"> (₹{{ bookingModal.facility?.fee_per_hour }}/hr × {{ hours }} hr)</span>
          </div>
          <div class="form-group">
            <label>Number of Attendees *</label>
            <input v-model.number="bookingForm.attendees" type="number" class="form-control"
                   min="1" :max="bookingModal.facility?.capacity" required />
          </div>
          <div class="form-group">
            <label>Purpose of Booking *</label>
            <input v-model="bookingForm.purpose" type="text" class="form-control"
                   placeholder="e.g., Community meeting, Birthday celebration, Sports event" required />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-outline" @click="bookingModal.show = false">Cancel</button>
            <button type="submit" class="btn btn-primary" :disabled="bookingModal.loading">
              {{ bookingModal.loading ? 'Booking…' : '✅ Confirm Booking' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Success modal -->
    <div v-if="successModal" class="modal-overlay">
      <div class="modal modal-w-sm text-center">
        <div class="success-icon">🎉</div>
        <h2 class="navy-text">Booking Requested!</h2>
        <p class="text-muted success-msg">
          Your booking is pending confirmation. You'll be notified once approved.
          {{ successModal.fee > 0 ? `Payment of ₹${successModal.fee} will be due after confirmation.` : '' }}
        </p>
        <div class="flex gap-3 justify-center mt-4">
          <router-link to="/bookings" class="btn btn-primary">View My Bookings</router-link>
          <button class="btn btn-outline" @click="successModal = null">Book Another</button>
        </div>
      </div>
    </div>

    <!-- Ratings modal: distribution + individual reviews -->
    <div v-if="ratingsModal.show" class="modal-overlay" @click.self="ratingsModal.show = false">
      <div class="modal modal-w-lg">
        <div class="modal-header">
          <h2>Ratings — {{ ratingsModal.facility?.name }}</h2>
          <button class="modal-close" aria-label="Close" @click="ratingsModal.show = false">✕</button>
        </div>

        <SkeletonLoader v-if="ratingsModal.loading" type="list" :count="3" />
        <template v-else-if="ratingsModal.data">
          <div class="rating-overview">
            <div class="rating-overview-score">{{ ratingsModal.data.avg }}</div>
            <div>
              <StarRating :model-value="ratingsModal.data.avg" readonly size="md" />
              <div class="rating-overview-count">{{ ratingsModal.data.count }} review{{ ratingsModal.data.count !== 1 ? 's' : '' }}</div>
            </div>
          </div>

          <div class="rating-distribution">
            <div v-for="n in [5,4,3,2,1]" :key="n" class="dist-row">
              <span class="dist-star">{{ n }} ⭐</span>
              <div class="dist-bar-track">
                <div class="dist-bar-fill" :style="{ width: distPercent(n) + '%' }"></div>
              </div>
              <span class="dist-count">{{ ratingsModal.data.distribution[n] }}</span>
            </div>
          </div>

          <div class="divider"></div>

          <div v-if="!ratingsWithComments.length" class="empty-state">
            <p>No written reviews yet.</p>
          </div>
          <div v-else class="review-list">
            <div v-for="r in ratingsWithComments" :key="r.id" class="review-row">
              <div class="review-head">
                <strong>{{ r.citizen_name }}</strong>
                <StarRating :model-value="r.rating" readonly size="sm" />
              </div>
              <p class="review-comment">{{ r.comment }}</p>
            </div>
          </div>
        </template>

        <div class="modal-footer">
          <button class="btn btn-secondary" @click="ratingsModal.show = false">Close</button>
        </div>
      </div>
    </div>

    <NotificationsPanel v-if="showNotif" @close="showNotif = false" @read="unread = Math.max(0,unread-1)" />

    <FloatingActionButton
      :actions="[{ icon: '📅', label: 'My Bookings' }, { icon: '📝', label: 'New Complaint' }]"
      @action="handleFabAction"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import AppSidebar from "../../components/AppSidebar.vue"
import AppTopbar from "../../components/AppTopbar.vue"
import NotificationsPanel from "../../components/NotificationsPanel.vue"
import ImageGallery from "../../components/ImageGallery.vue"
import EmptyState from "../../components/EmptyState.vue"
import FilterChips from "../../components/FilterChips.vue"
import SkeletonLoader from "../../components/SkeletonLoader.vue"
import FloatingActionButton from "../../components/FloatingActionButton.vue"
import StarRating from "../../components/StarRating.vue"
import { useToast } from "../../composables/useToast"
import { useDebouncedValue } from "../../composables/useDebounce"
import api from "../../api"

const { success: toastSuccess, error: toastError } = useToast()
const loading = ref(true)
const facilities = ref([])
const showNotif = ref(false)
const unread = ref(0)
const successModal = ref(null)
const today = new Date().toISOString().split("T")[0]

const route = useRoute()
const router = useRouter()
const searchInput = ref(null)

// Seeded from the URL so a refresh or back-navigation restores the same view
// rather than flashing the unfiltered grid first.
const searchQuery = ref(route.query.q || '')
// The input itself stays instantly responsive (v-model binds directly to
// searchQuery); it's the filtering and URL sync that wait for a pause in
// typing, so the grid doesn't re-filter and the URL doesn't churn on every
// keystroke.
const debouncedSearchQuery = useDebouncedValue(searchQuery, 300)
const facilityTypeFilter = ref(route.query.type || '')
const priceFilter = ref(route.query.price || '')
const capacityFilter = ref(route.query.capacity || '')
const ratingFilter = ref(route.query.rating || '')
const wardFilter = ref(route.query.ward || '')
const availableOnDate = ref(route.query.date || '')
// "fav" in the URL so a favourites-only view survives a refresh and can be
// shared or bookmarked, same as every other filter on this page.
const favouritesOnly = ref(route.query.fav === '1')

// Two things drive this filter: the page's own Favourites button, and the
// dashboard's "My Favourites" card, which links to /facilities?fav=1. Keep the
// button and the URL in step in both directions, so arriving with ?fav=1 turns
// the filter on and turning it off drops the query. A router-only query change
// reuses this component, so a watcher is the only thing that notices;
// `replace` keeps the back button meaningful.
watch(favouritesOnly, (on) => {
  const has = route.query.fav === '1'
  if (on === has) return
  const query = { ...route.query }
  if (on) query.fav = '1'
  else delete query.fav
  router.replace({ path: route.path, query })
})

watch(() => route.query.fav, (fav) => {
  const on = fav === '1'
  if (favouritesOnly.value !== on) favouritesOnly.value = on
})

// Facility ids this citizen has saved. A Set because the grid asks "is this one
// favourited" for every card on every render.
const favouriteIds = ref(new Set())
// Ids with a toggle in flight, so a double click cannot fire two requests.
const favouritePending = ref(new Set())
// Facility ids with no pending/confirmed booking on availableOnDate. Null means
// "not looked up yet", which is different from an empty set (= nothing free).
const freeFacilityIds = ref(null)
const availabilityLoading = ref(false)
// Monotonic counter used to discard out-of-order availability responses.
let availabilityRun = 0
let availabilityTimer = null

const bookingModal = ref({ show: false, facility: null, loading: false, error: "" })
const bookingForm = ref({ booking_date: "", start_time: "", end_time: "", attendees: 1, purpose: "" })
const bookedSlots = ref([])
const slotsLoading = ref(false)

const ratingsModal = ref({ show: false, facility: null, loading: false, data: null })

// Star-only ratings (no comment) still count toward the average and the
// distribution bars above — they just aren't listed as individual reviews,
// since a bare star row with nothing written reads as empty filler.
const ratingsWithComments = computed(() => (ratingsModal.value.data?.ratings || []).filter(r => r.comment))

async function openRatings(f) {
  ratingsModal.value = { show: true, facility: f, loading: true, data: null }
  try {
    const { data } = await api.get(`/facilities/${f.id}/ratings`)
    ratingsModal.value.data = data
  } finally {
    ratingsModal.value.loading = false
  }
}

function distPercent(star) {
  const d = ratingsModal.value.data
  if (!d || !d.count) return 0
  return Math.round((d.distribution[star] / d.count) * 100)
}

const hours = computed(() => {
  if (!bookingForm.value.start_time || !bookingForm.value.end_time) return 0
  const [sh, sm] = bookingForm.value.start_time.split(":").map(Number)
  const [eh, em] = bookingForm.value.end_time.split(":").map(Number)
  return Math.max(0, (eh * 60 + em - sh * 60 - sm) / 60)
})

const estimatedFee = computed(() => {
  if (!bookingModal.value.facility) return 0
  return Math.round(bookingModal.value.facility.fee_per_hour * hours.value * 100) / 100
})

const filtered = computed(() => {
  let result = facilities.value

  // Search across name, facility_type, ward, address
  if (debouncedSearchQuery.value) {
    const q = debouncedSearchQuery.value.toLowerCase()
    result = result.filter(f =>
      f.name?.toLowerCase().includes(q) ||
      f.facility_type?.toLowerCase().includes(q) ||
      f.ward?.toLowerCase().includes(q) ||
      f.address?.toLowerCase().includes(q) ||
      f.description?.toLowerCase().includes(q)
    )
  }

  // Filter by facility type
  if (facilityTypeFilter.value) {
    result = result.filter(f => f.facility_type === facilityTypeFilter.value)
  }

  // Filter by price range
  if (priceFilter.value) {
    result = result.filter(f => {
      if (priceFilter.value === 'free') return f.fee_per_hour === 0
      if (priceFilter.value === 'budget') return f.fee_per_hour > 0 && f.fee_per_hour <= 500
      if (priceFilter.value === 'mid') return f.fee_per_hour > 500 && f.fee_per_hour <= 1000
      if (priceFilter.value === 'premium') return f.fee_per_hour > 1000
      return true
    })
  }

  // Minimum capacity — "will it fit my group?" is the useful question here, so
  // each option is a floor rather than a band.
  if (capacityFilter.value) {
    const min = Number(capacityFilter.value)
    result = result.filter(f => (f.capacity || 0) >= min)
  }

  // Filter by ward
  if (wardFilter.value) {
    result = result.filter(f => f.ward === wardFilter.value)
  }

  // Minimum average rating — unrated facilities have no avg_rating and drop
  // out here, same as they would against any star-based floor.
  if (ratingFilter.value) {
    const min = Number(ratingFilter.value)
    result = result.filter(f => (f.avg_rating || 0) >= min)
  }

  // Filter by availability on the chosen date. Until the lookup resolves,
  // freeFacilityIds is null and the list is left alone rather than briefly
  // emptying out.
  if (availableOnDate.value && freeFacilityIds.value) {
    result = result.filter(f => freeFacilityIds.value.has(f.id))
  }

  // Only the ones this citizen saved.
  if (favouritesOnly.value) {
    result = result.filter(f => favouriteIds.value.has(f.id))
  }

  return result
})

// Ward options come from the data rather than a hardcoded list, so a new ward
// added to a facility shows up here without a code change.
const wards = computed(() =>
  [...new Set(facilities.value.map(f => f.ward).filter(Boolean))].sort()
)

// Counted against the facilities actually on the page, not the raw saved ids.
// An admin can deactivate a facility after someone favourited it; that card is
// filtered out of the grid, so counting it here would promise more results than
// the filter can deliver.
const favouriteCount = computed(() =>
  facilities.value.reduce((n, f) => n + (favouriteIds.value.has(f.id) ? 1 : 0), 0)
)

function isFavourite(id) {
  return favouriteIds.value.has(id)
}

async function loadFavourites() {
  try {
    const res = await api.get('/facilities/favorites')
    favouriteIds.value = new Set(res.data || [])
  } catch {
    // Signed out, or the call failed. An empty set just means no hearts are
    // filled in; the rest of the page behaves exactly as before.
    favouriteIds.value = new Set()
  }
}

async function toggleFavourite(facility) {
  if (favouritePending.value.has(facility.id)) return
  favouritePending.value = new Set(favouritePending.value).add(facility.id)

  // Flip it straight away so the heart responds to the click, then reconcile
  // with the server's answer. Waiting on the request first makes a one-click
  // control feel broken.
  const optimistic = new Set(favouriteIds.value)
  const wasFavourite = optimistic.has(facility.id)
  wasFavourite ? optimistic.delete(facility.id) : optimistic.add(facility.id)
  favouriteIds.value = optimistic

  try {
    const res = await api.post('/facilities/favorites', { facility_id: facility.id })
    const confirmed = new Set(favouriteIds.value)
    res.data.favourited ? confirmed.add(facility.id) : confirmed.delete(facility.id)
    favouriteIds.value = confirmed
    toastSuccess(res.data.favourited
      ? `${facility.name} saved to your favourites`
      : `${facility.name} removed from your favourites`)
  } catch (e) {
    // Put it back, so the heart never claims something that did not save.
    const reverted = new Set(favouriteIds.value)
    wasFavourite ? reverted.add(facility.id) : reverted.delete(facility.id)
    favouriteIds.value = reverted
    toastError(e.response?.data?.message || 'Could not update your favourites')
  } finally {
    const done = new Set(favouritePending.value)
    done.delete(facility.id)
    favouritePending.value = done
  }
}

const hasActiveFilters = computed(() =>
  searchQuery.value || facilityTypeFilter.value || priceFilter.value ||
  capacityFilter.value || wardFilter.value || availableOnDate.value ||
  favouritesOnly.value || ratingFilter.value
)

/**
 * Look up which facilities are free on the selected date.
 *
 * "Free" here means the facility has no pending or confirmed booking that day
 * at all. That is deliberately coarse — a hall booked 10:00-11:00 is still
 * bookable in the afternoon — but the filter's job is narrowing a grid of
 * cards, and the booking modal already shows exact slot-level availability
 * once a facility is opened.
 */
async function refreshAvailability(date) {
  // Each run claims a token. Changing the date quickly leaves earlier lookups
  // in flight, and without this an older response landing last would overwrite
  // the newer date's results — showing availability for a date the user has
  // already moved off.
  const token = ++availabilityRun

  if (!date) {
    freeFacilityIds.value = null
    availabilityLoading.value = false
    return
  }
  availabilityLoading.value = true
  try {
    const results = await Promise.all(
      facilities.value.map(f =>
        api.get(`/facilities/${f.id}/availability`, { params: { date } })
          .then(res => ({ id: f.id, booked: res.data.booked_slots || [] }))
          // A failed lookup shouldn't hide an otherwise valid facility, so treat
          // it as free and let the booking form reject it if it isn't.
          .catch(() => ({ id: f.id, booked: [] }))
      )
    )
    if (token !== availabilityRun) return
    freeFacilityIds.value = new Set(results.filter(r => !r.booked.length).map(r => r.id))
  } finally {
    // Only the newest run owns the spinner, otherwise a stale run finishing
    // first would clear it while the current lookup is still going.
    if (token === availabilityRun) availabilityLoading.value = false
  }
}

// Debounced, because one date change costs a request per facility — stepping
// through a date picker would otherwise fire a burst of them per click.
// Clearing is applied immediately since it needs no requests.
watch(availableOnDate, (date) => {
  clearTimeout(availabilityTimer)
  if (!date) {
    refreshAvailability('')
    return
  }
  // Held on through the debounce window so the grid doesn't look settled while
  // a lookup is still pending.
  availabilityLoading.value = true
  availabilityTimer = setTimeout(() => refreshAvailability(date), 250)
})

onBeforeUnmount(() => clearTimeout(availabilityTimer))

onMounted(async () => {
  window.addEventListener("keydown", onKeydown)
  // Favourites are not awaited alongside these two: the grid should not wait on
  // them, and a signed-out or failed lookup just leaves the hearts empty.
  loadFavourites()
  const [facRes, notifRes] = await Promise.all([api.get("/facilities"), api.get("/notifications")])
  facilities.value = facRes.data.filter(f => f.is_active)
  unread.value = notifRes.data.unread_count
  loading.value = false
  // A date seeded from the URL never fired the watch, and the lookup needs the
  // facility list anyway — so resolve it here, once the list exists.
  if (availableOnDate.value) refreshAvailability(availableOnDate.value)
})

/**
 * "/" jumps to the search box, the convention from GitHub, Slack, and friends.
 * Ignored while another field has focus so it doesn't swallow a literal slash,
 * and ignored alongside modifiers so it never shadows a browser shortcut.
 */
function onKeydown(e) {
  if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return
  const el = e.target
  if (el?.tagName === "INPUT" || el?.tagName === "TEXTAREA" || el?.tagName === "SELECT" || el?.isContentEditable) return
  e.preventDefault()
  searchInput.value?.focus()
}

onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown))

/**
 * Mirror the current filters into the query string.
 *
 * `replace` rather than `push`: typing in the search box would otherwise stack
 * a history entry per keystroke. The URL still carries the state when
 * navigating away, so coming back restores the same filtered grid.
 */
watch([debouncedSearchQuery, facilityTypeFilter, priceFilter, capacityFilter, wardFilter, availableOnDate, favouritesOnly, ratingFilter], () => {
  const q = {}
  if (debouncedSearchQuery.value) q.q = debouncedSearchQuery.value
  if (facilityTypeFilter.value) q.type = facilityTypeFilter.value
  if (priceFilter.value) q.price = priceFilter.value
  if (capacityFilter.value) q.capacity = capacityFilter.value
  if (wardFilter.value) q.ward = wardFilter.value
  if (availableOnDate.value) q.date = availableOnDate.value
  if (favouritesOnly.value) q.fav = '1'
  if (ratingFilter.value) q.rating = ratingFilter.value
  router.replace({ query: q }).catch(() => {})
})

function openBooking(facility) {
  bookingModal.value = { show: true, facility, loading: false, error: "" }
  bookingForm.value = { booking_date: "", start_time: "", end_time: "", attendees: 1, purpose: "" }
  bookedSlots.value = []
}

async function loadAvailability() {
  const date = bookingForm.value.booking_date
  const facilityId = bookingModal.value.facility?.id
  if (!date || !facilityId) return
  slotsLoading.value = true
  try {
    const res = await api.get(`/facilities/${facilityId}/availability`, { params: { date } })
    bookedSlots.value = res.data.booked_slots || []
  } catch {
    bookedSlots.value = []
  } finally {
    slotsLoading.value = false
  }
}

async function submitBooking() {
  bookingModal.value.loading = true
  bookingModal.value.error = ""
  try {
    const { data } = await api.post("/bookings", {
      ...bookingForm.value,
      facility_id: bookingModal.value.facility.id,
    })
    bookingModal.value.show = false
    successModal.value = { fee: data.fee }
  } catch (e) {
    bookingModal.value.error = e.response?.data?.message || "Booking failed."
  } finally {
    bookingModal.value.loading = false
  }
}

function handleFabAction(action) {
  if (action.label === 'My Bookings') router.push('/bookings')
  else if (action.label === 'New Complaint') router.push('/submit')
}

function typeIcon(t) {
  const map = {
    "Community Hall": "🏛️", "Sports Ground": "⚽", "Conference Room": "🏢",
    "Park": "🌳", "Auditorium": "🎭", "Library Hall": "📚", "Swimming Pool": "🏊",
  }
  return map[t] || "🏗️"
}

const CAPACITY_LABELS = { 25: 'Fits 25+', 50: 'Fits 50+', 100: 'Fits 100+', 200: 'Fits 200+' }
const PRICE_LABELS = { free: 'Free', budget: 'Under ₹500/hr', mid: '₹500-1000/hr', premium: 'Above ₹1000/hr' }

// Removable summary of what's currently narrowing the grid.
const activeChips = computed(() => {
  const chips = []
  if (searchQuery.value) chips.push({ key: 'search', label: `Search: "${searchQuery.value}"` })
  if (facilityTypeFilter.value) chips.push({ key: 'type', label: `Type: ${facilityTypeFilter.value}` })
  if (priceFilter.value) chips.push({ key: 'price', label: `Price: ${PRICE_LABELS[priceFilter.value] || priceFilter.value}` })
  if (capacityFilter.value) chips.push({ key: 'capacity', label: CAPACITY_LABELS[capacityFilter.value] || `Fits ${capacityFilter.value}+` })
  if (wardFilter.value) chips.push({ key: 'ward', label: `Ward: ${wardFilter.value}` })
  if (availableOnDate.value) chips.push({ key: 'date', label: `Free on ${availableOnDate.value}` })
  if (favouritesOnly.value) chips.push({ key: 'fav', label: 'My favourites only' })
  if (ratingFilter.value) chips.push({ key: 'rating', label: ratingFilter.value === '5' ? '5 ⭐ only' : `${ratingFilter.value} ⭐ & up` })
  return chips
})

function clearFilter(key) {
  if (key === 'search') searchQuery.value = ''
  else if (key === 'type') facilityTypeFilter.value = ''
  else if (key === 'price') priceFilter.value = ''
  else if (key === 'capacity') capacityFilter.value = ''
  else if (key === 'ward') wardFilter.value = ''
  else if (key === 'date') availableOnDate.value = ''
  else if (key === 'fav') favouritesOnly.value = false
  else if (key === 'rating') ratingFilter.value = ''
}

function clearSearch() {
  searchQuery.value = ''
}

function clearAllFilters() {
  searchQuery.value = ''
  facilityTypeFilter.value = ''
  priceFilter.value = ''
  capacityFilter.value = ''
  wardFilter.value = ''
  availableOnDate.value = ''
  favouritesOnly.value = false
  ratingFilter.value = ''
}
</script>

<style scoped>
.facilities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}
.facility-card { display: flex; flex-direction: column; }
/* Coloured with --accent, not --bg, on purpose. This card's decorative chips
   (.info-chip, .amenity-chip) are grey on muted text; the app's clickable pills
   (.filter-chip) are accent on accent-foreground. A grey pill here read as one
   more label sitting among labels. Accent puts it in the interactive family at
   a glance, before any hover, which is what touch users get. */
.facility-rating-row {
  display: inline-flex; align-items: center; gap: 0.45rem; margin-bottom: 0.75rem;
  background: var(--accent); border: 1px solid transparent; border-radius: 100px;
  padding: 0.3rem 0.75rem;
  cursor: pointer; text-align: left; width: fit-content; font-family: inherit;
  transition: background var(--transition), border-color var(--transition);
}
/* Scoped to button: the "No ratings yet" variant is a div and must stay inert. */
button.facility-rating-row:hover { background: rgba(0, 82, 255, 0.16); border-color: var(--primary); }
button.facility-rating-row:hover .rating-chevron { transform: translateX(2px); }
button.facility-rating-row:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.rating-score { font-size: 0.84rem; font-weight: 800; color: var(--accent-foreground); }
.rating-dot { color: var(--accent-foreground); opacity: 0.45; }
.facility-rating-row .rating-summary { color: var(--accent-foreground); }
/* An arrow says "this opens something" without spending a word on it. */
.rating-chevron {
  font-size: 1.05rem; font-weight: 700; line-height: 1;
  color: var(--accent-foreground);
  transition: transform var(--transition);
}
.facility-rating-row.facility-rating-empty {
  cursor: default; background: none; border-color: transparent; padding-left: 0;
}
.rating-summary { font-size: 0.82rem; font-weight: 600; color: var(--text-muted); }
.rating-overview { display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem; }
.rating-overview-score { font-size: 2.2rem; font-weight: 800; color: var(--text); line-height: 1; }
.rating-overview-count { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
.rating-distribution { display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1.25rem; }
.dist-row { display: flex; align-items: center; gap: 0.6rem; font-size: 0.8rem; }
.dist-star { width: 42px; color: var(--text-muted); flex-shrink: 0; }
.dist-bar-track { flex: 1; height: 8px; background: var(--border); border-radius: 100px; overflow: hidden; }
.dist-bar-fill { height: 100%; background: #FFC107; border-radius: 100px; }
.dist-count { width: 24px; text-align: right; color: var(--text-muted); flex-shrink: 0; }
.divider { border-top: 1px solid var(--border); margin: 1rem 0; }
.review-list { display: flex; flex-direction: column; gap: 0.85rem; max-height: 280px; overflow-y: auto; }
.review-head { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.2rem; }
.review-comment { font-size: 0.85rem; color: var(--text-muted); }
.facility-gallery.count-1 :deep(img) { max-height: 170px; }
.facility-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.75rem; }

/* Heart toggle. Outline when off, filled when on, with a short pop on the way
   in so saving feels like it registered. margin-left:auto pushes it to the far
   right of the header so it never crowds the facility type badge. */
.fav-btn {
  margin-left: auto;
  display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; flex-shrink: 0;
  background: none; border: 1px solid var(--border); border-radius: 50%;
  cursor: pointer; padding: 0;
  transition: border-color var(--transition), background var(--transition);
}
.fav-btn:hover { border-color: var(--danger); background: rgba(220, 38, 38, 0.06); }
.fav-icon { width: 18px; height: 18px; fill: none; stroke: var(--text-muted); stroke-width: 2; }
.fav-btn:hover .fav-icon { stroke: var(--danger); }
.fav-btn.is-fav { border-color: var(--danger); background: rgba(220, 38, 38, 0.08); }
.fav-btn.is-fav .fav-icon { fill: var(--danger); stroke: var(--danger); animation: fav-pop 0.28s ease; }

@keyframes fav-pop {
  0%   { transform: scale(1); }
  45%  { transform: scale(1.35); }
  100% { transform: scale(1); }
}

/* The colour change already communicates the state, so reduced motion only
   drops the pop rather than losing any meaning. */
@media (prefers-reduced-motion: reduce) {
  .fav-btn.is-fav .fav-icon { animation: none; }
}

/* Favourites filter, styled as a toggle rather than a select because it is on
   or off, unlike the dropdowns beside it. */
.fav-filter-btn {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: var(--card); color: var(--text-muted);
  border: 1px solid var(--outline); border-radius: 100px;
  padding: 0.45rem 0.9rem; font-size: 0.82rem; font-weight: 600;
  font-family: inherit; cursor: pointer; white-space: nowrap;
  transition: background var(--transition), border-color var(--transition), color var(--transition);
}
.fav-filter-btn:hover { border-color: var(--danger); color: var(--danger); }
.fav-filter-btn .fav-icon { width: 15px; height: 15px; }
.fav-filter-btn.is-on {
  background: rgba(220, 38, 38, 0.08);
  border-color: var(--danger);
  color: var(--danger);
}
.fav-filter-btn.is-on .fav-icon { fill: var(--danger); stroke: var(--danger); }
.fav-filter-n { font-weight: 800; }
.facility-type-icon { font-size: 2rem; }
.facility-type-badge {
  background: var(--bg); color: var(--text-muted);
  font-size: 0.75rem; font-weight: 700;
  padding: 0.2rem 0.7rem; border-radius: 100px;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.facility-name { font-size: 1.05rem; font-weight: 800; color: var(--navy); margin-bottom: 0.4rem; }
.facility-desc { font-size: 0.85rem; color: var(--text-muted); line-height: 1.5; margin-bottom: 0.85rem; flex: 1; }
.facility-info { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
.info-chip {
  background: rgba(255,180,0,0.08); color: var(--text);
  border: 1px solid rgba(255,180,0,0.2);
  padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600;
}
.amenities { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.75rem; }
.amenity-chip {
  background: var(--bg); color: var(--text-muted);
  padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.75rem;
}
.facility-address { font-size: 0.82rem; color: var(--text-muted); }
.facility-booking-info {
  display: flex; gap: 1rem; flex-wrap: wrap;
  background: var(--bg); padding: 0.75rem 1rem; border-radius: 8px;
  font-size: 0.85rem; color: var(--text-muted); font-weight: 600;
  margin-bottom: 1.25rem;
}
.fee-preview {
  background: #D7F5E5;
  color: #0E7A4F;
  padding: 0.6rem 0.85rem;
  border-radius: 8px;
  font-size: 0.9rem;
}
.booked-slots-info {
  background: #FFF0F6;
  border: 1px solid #FFB400;
  border-radius: 8px;
  padding: 0.65rem 0.85rem;
  font-size: 0.84rem;
}
.booked-slots-title { font-weight: 700; color: #A66E00; margin-bottom: 0.35rem; }
.booked-slot { color: #8a5800; padding: 0.15rem 0; }
.slot-available-alert { font-size: 0.82rem; padding: 0.5rem 0.85rem; }
.success-icon { font-size: 3rem; margin-bottom: 1rem; }
.navy-text { color: var(--navy); }
.success-msg { margin: 1rem 0; }
.justify-center { justify-content: center; }

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.search-wrapper {
  flex: 1;
  position: relative;
  min-width: 200px;
}

.search-wrapper .form-control {
  padding-right: 32px;
}

/* type="search" earns the right semantics and a better mobile keyboard, but
   WebKit draws its own clear button that would land on top of ours. */
.search-wrapper input[type="search"]::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}

.search-clear {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 0;
  line-height: 1;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 18px;
  font-weight: bold;
  transition: color var(--transition);
}

.search-clear:hover {
  color: var(--text);
}

.filter-select {
  min-width: 140px;
}

.clear-filters {
  white-space: nowrap;
}

.date-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}

.date-input {
  width: auto;
  min-width: 150px;
}

.availability-note {
  margin-left: 10px;
  font-style: italic;
  opacity: 0.85;
}

.filter-info {
  background: var(--accent);
  border-left: 4px solid var(--primary);
  padding: 8px 12px;
  margin-bottom: 16px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--accent-foreground);
}

.result-count {
  font-weight: 500;
}

@media (max-width: 640px) {
  .filter-bar {
    flex-direction: column;
  }

  .search-wrapper,
  .filter-select,
  .date-label {
    width: 100%;
  }

  .date-input {
    flex: 1;
    min-width: 0;
  }

  .filter-info {
    font-size: 12px;
  }

  .facilities-grid {
    grid-template-columns: 1fr;
  }
}
</style>
