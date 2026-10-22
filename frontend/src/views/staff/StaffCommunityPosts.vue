<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Community Posts" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Monitor and respond to citizen posts in your department</p>
          </div>
          <button class="btn btn-primary" @click="openCreate">+ Create Post</button>
        </div>

        <div class="tabs">
          <button class="tab-btn" :class="{ active: tab === 'all' }" @click="tab = 'all'">All Posts</button>
          <button class="tab-btn" :class="{ active: tab === 'mine' }" @click="tab = 'mine'">My Posts</button>
        </div>

        <PostFilterBar
          v-if="!loading"
          :search="search" @update:search="search = $event"
          :category="category" @update:category="category = $event"
          :ward="ward" @update:ward="ward = $event"
          :author="author" @update:author="author = $event"
          :department="department" @update:department="department = $event"
          :has-active-filters="hasActiveFilters"
          :active-chips="activeChips"
          :result-count="filteredPosts.length"
          @clear-all="clearAll"
          @remove-chip="clearFilter"
        />

        <div v-if="loading" class="spinner"></div>

        <!-- A failed load must not read as an empty feed. Without this, a
             network error fell through to "No posts found" and quietly told
             the user the community had nothing to say. -->
        <div v-else-if="loadError" class="empty-state">
          <div class="empty-icon">&#9888;</div>
          <p>{{ loadError }}</p>
          <button class="btn btn-sm btn-secondary" @click="loadPosts">Try Again</button>
        </div>

        <div v-else class="posts-list">
          <div v-if="!filteredPosts.length && hasActiveFilters" class="empty-state">
            <div class="empty-icon">&#128269;</div>
            <p>No posts match your search</p>
            <button class="btn btn-sm btn-secondary" @click="clearAll">Clear Filters</button>
          </div>
          <div v-else-if="!filteredPosts.length" class="empty-state">
            <div class="empty-icon">&#9998;</div>
            <p>No posts found</p>
          </div>
          <div v-for="post in filteredPosts" :key="post.id" class="post-card card">
            <div class="post-header">
              <div class="post-author">
                <div class="avatar avatar-sm">{{ post.author_name?.charAt(0) }}</div>
                <div>
                  <div class="author-name">
                    {{ post.author_name }}
                    <span v-if="post.is_official" class="badge badge-official badge-inline">Official</span>
                    <span v-if="post.author_department" class="dept-tag">{{ post.author_department }}</span>
                  </div>
                  <div class="post-meta">
                    <span v-if="post.location">{{ post.location }}</span>
                    <span> &bull; {{ timeAgo(post.created_at) }}</span>
                  </div>
                </div>
              </div>
              <div class="post-header-right">
                <!-- Same click-to-filter chip the citizen feed shows. Every post
                     already carries a category and this page already filters on
                     it, so leaving it off meant staff were filtering on a field
                     they could not see. -->
                <button
                  v-if="post.category"
                  type="button"
                  class="post-category"
                  :title="`Show only ${fmtCategory(post.category)} posts`"
                  @click="category = post.category"
                >{{ fmtCategory(post.category) }}</button>
                <button v-if="post.citizen_id === auth.user?.id" class="btn btn-xs btn-danger" @click="deletePost(post)">&#128465; Delete</button>
              </div>
            </div>
            <!-- v-html is safe: highlight() escapes the post text before adding
                 its own <mark> tags. See highlightTerms() in utils/postFilters. -->
            <div v-if="post.title" class="post-title" v-html="highlight(post.title)"></div>
            <div class="post-content" v-html="highlight(post.content)"></div>
            <ImageGallery v-if="post.image_urls?.length" :images="post.image_urls" alt="Post image" />
            <div class="post-actions">
              <button class="action-btn" :class="{ liked: post.liked_by_me }" @click="toggleLike(post)">&#9829; {{ post.likes_count }}</button>
              <button class="action-btn" @click="toggleComments(post)">&#9997; {{ post.comments_count }} Comments</button>
            </div>

            <div v-if="expandedPost === post.id" class="comments-section">
              <div v-if="!commentData[post.id]" class="spinner p-4"></div>
              <template v-else>
                <div v-for="c in commentData[post.id]" :key="c.id" class="comment-item" :class="{ 'official-comment': c.is_official }">
                  <div class="comment-author">
                    {{ c.author_name }}
                    <span v-if="c.is_official" class="official-tag">{{ c.author_department || 'Official' }}</span>
                    <button v-if="c.user_id === auth.user?.id || auth.isAdmin" class="comment-delete-btn" aria-label="Delete comment"
                            title="Delete comment" @click="deleteComment(post, c)">&#x2715;</button>
                  </div>
                  <div class="comment-text">{{ c.content }}</div>
                  <div class="comment-time">{{ timeAgo(c.created_at) }}</div>
                </div>
              </template>
              <div class="comment-input">
                <input v-model="commentTexts[post.id]" class="form-control"
                       placeholder="Add official department response..."
                       :disabled="postingComment[post.id]"
                       @keydown.enter="addComment(post)" />
                <button class="btn btn-sm btn-primary" :disabled="postingComment[post.id]" @click="addComment(post)">Respond</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Post Modal -->
    <div v-if="showCreatePost" class="modal-overlay" @click.self="closeCreate">
      <div class="modal create-modal">
        <div class="create-header">
          <button class="create-nav" @click="closeCreate" aria-label="Close">&#x2715;</button>
          <h2>Create new post</h2>
          <button class="create-action" :disabled="!canShare || postLoading" @click="createPost">
            {{ postLoading ? 'Sharing…' : 'Share' }}
          </button>
        </div>

        <div class="create-body">
          <div class="form-group">
            <label for="staff-post-caption">Caption</label>
            <textarea id="staff-post-caption" v-model="newPost.content" class="form-control" rows="4" placeholder="Share an update with your community…"></textarea>
          </div>
          <div class="form-group">
            <!-- The suggest button is a sibling of the label, not a child: a
                 <button> inside a <label> is invalid nesting, and clicking it
                 would also activate the labelled control. -->
            <div class="label-row">
              <label for="staff-post-category">Category</label>
              <button
                v-if="suggestedCategory && suggestedCategory !== newPost.category"
                type="button"
                class="suggest-btn"
                title="Detected from your caption"
                @click="newPost.category = suggestedCategory"
              >✨ Suggest: {{ fmtCategory(suggestedCategory) }}</button>
            </div>
            <!-- No "None" option, and not optional: the API coerces a missing
                 category to "general", so "None" promised something the post
                 never actually got. Defaulting to General says the same thing
                 honestly. -->
            <select id="staff-post-category" v-model="newPost.category" class="form-control">
              <option v-for="c in CATEGORIES" :key="c.value" :value="c.value">{{ c.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="staff-post-location">Location <span class="optional-label">(optional)</span></label>
            <!-- The "(Ward-N)" shape is not decoration: wardFromLocation parses
                 it to auto-fill the ward below, so the example teaches it. -->
            <!-- 200 matches Post.location's column width in the backend model
                 (backend/apps/models.py), so a location that types fine here
                 can't be rejected or truncated on save. -->
            <input
              id="staff-post-location"
              v-model="newPost.location"
              class="form-control"
              maxlength="200"
              placeholder="e.g. Block A Park, Preetam Nagar (Ward-1)"
            />
          </div>
          <div class="form-group">
            <label for="staff-post-ward">Ward <span class="optional-label">(optional)</span></label>
            <select id="staff-post-ward" v-model="newPost.ward" class="form-control" @change="onWardSelected">
              <option value="">Not specified</option>
              <option v-for="w in WARDS" :key="w" :value="w">{{ w }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>Pin location on map <span class="optional-label">(optional)</span></label>
            <LocationPicker @located="onPostLocated" />
          </div>
          <div class="form-group">
            <label>Photos <span class="optional-label">(optional)</span></label>
            <MultiImageUpload v-model="newPost.image_urls" :max="3" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Staff Community Posts - View and respond to citizen posts in the community feed
 * Features: create official posts, respond to citizen posts, like/comment, view responses
 * Posts by staff are marked "Official" with department tag
 * Staff can respond with official department information
 */
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import ImageGallery from '../../components/ImageGallery.vue'
import MultiImageUpload from '../../components/MultiImageUpload.vue'
import LocationPicker from '../../components/LocationPicker.vue'
import PostFilterBar from '../../components/PostFilterBar.vue'
import { usePostFilters } from '../../composables/usePostFilters'
import { CATEGORIES, WARDS, DEFAULT_CATEGORY, fmtCategory, suggestCategory, wardFromLocation } from '../../utils/postFilters'
import { timeAgo } from '../../utils/timeAgo'
import { useAuthStore } from '../../stores/auth'
import api from '../../api'
import { useToast } from '../../composables/useToast'

const { error: toastError } = useToast()

const auth = useAuthStore()
const loading = ref(true)
// Non-empty only when the feed request itself failed, which is a different
// state from "the feed is genuinely empty" and must render differently.
const loadError = ref('')
const posts = ref([]) // All posts from community feed
const tab = ref('all') // Filter: 'all' or 'mine' (staff's own posts)
const expandedPost = ref(null) // Currently expanded post for comments
const commentData = ref({}) // Cached comments per post
const commentTexts = ref({}) // Input text for each post's comment box
const postingComment = ref({}) // Loading state per post
const showCreatePost = ref(false) // Create post modal visibility
// Category is pre-selected rather than blank: the API coerces a blank category
// to the default anyway, so starting there is what actually gets saved.
const newPost = ref({ content: '', location: '', image_urls: [], category: DEFAULT_CATEGORY, ward: '' })
const postLoading = ref(false)

// Matches the citizen feed: the API accepts a post with images and no caption,
// so requiring a caption here blocked something the backend allows.
const canShare = computed(() => !!(newPost.value.content.trim() || newPost.value.image_urls.length))

const suggestedCategory = computed(() => suggestCategory(newPost.value.content))

// Ward is optional, but auto-fill it from the location string when one can be
// parsed out (e.g. "...(Ward-1)").
//
// The flag tracks whether the ward on the form is our guess or the user's own
// choice, so editing the location only ever revises our guess. Without it, a
// ward parsed from an earlier location stuck around after the location was
// changed or cleared, and the post went out tagged with a ward that no longer
// matched what it said.
const wardAutoFilled = ref(false)

// Reverse direction: picking a ward from the dropdown tags the location text
// with "(Ward-N)" too, same shape as if the citizen had typed it themselves.
// Replaces any existing "(...)" suffix rather than piling one on, so
// switching wards doesn't leave "(Central) (Ward-1)" behind.
function onWardSelected() {
  wardAutoFilled.value = false
  const w = newPost.value.ward
  const base = newPost.value.location.replace(/\s*\([^()]*\)\s*$/, '').trim()
  newPost.value.location = w ? `${base}${base ? ' ' : ''}(${w})` : base
}

watch(() => newPost.value.location, (loc) => {
  const w = wardFromLocation(loc)
  if (w) {
    newPost.value.ward = w
    wardAutoFilled.value = true
  } else if (wardAutoFilled.value) {
    newPost.value.ward = ''
    wardAutoFilled.value = false
  }
})

// Named rather than inline so the error state's "Try Again" can call it.
async function loadPosts() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await api.get('/posts')
    posts.value = res.data
  } catch (e) {
    loadError.value = e.response?.data?.message || 'Could not load posts. Check your connection and try again.'
  } finally {
    loading.value = false
  }
}

onMounted(loadPosts)

// ── Create-post modal chrome ──
// Escape closes it, and the page behind it stops scrolling while it is open —
// otherwise a scroll inside the modal falls through to the feed and leaves you
// somewhere else entirely once the modal closes.
watch(showCreatePost, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

function onModalKeydown(e) {
  if (e.key === 'Escape' && showCreatePost.value) closeCreate()
}

onMounted(() => window.addEventListener('keydown', onModalKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onModalKeydown)
  // Leaving the route with the modal open must not leave the page unscrollable.
  document.body.style.overflow = ''
})

// Tab narrows first; the shared composable applies search + category + ward on
// top, identically to the citizen /feed and admin views.
const baseList = computed(() =>
  tab.value === 'mine' ? posts.value.filter(p => p.citizen_id === auth.user?.id) : posts.value
)
const {
  search, category, ward, author, department,
  filtered: filteredPosts, hasActiveFilters, activeChips,
  clearFilter, clearAll, highlight,
} = usePostFilters(baseList)

function openCreate() {
  resetCreate()
  showCreatePost.value = true
}

function closeCreate() {
  showCreatePost.value = false
  resetCreate()
}

function resetCreate() {
  newPost.value = { content: '', location: '', image_urls: [], category: DEFAULT_CATEGORY, ward: '' }
  wardAutoFilled.value = false
}

function onPostLocated({ address, lat, lng }) {
  // Fill the location box from the map pin, unless the user already typed one.
  if (!newPost.value.location) newPost.value.location = address || `${lat}, ${lng}`
}

/**
 * Delete a post - only author or admin can delete
 * Button is conditionally hidden in template for non-owners
 */
async function deletePost(post) {
  if (!confirm('Delete this post?')) return
  try {
    await api.delete(`/posts/${post.id}`)
    posts.value = posts.value.filter(p => p.id !== post.id)
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to delete post')
  }
}

/**
 * Delete a comment - only author or admin can delete
 * Server validates permission on DELETE endpoint
 */
async function deleteComment(post, comment) {
  if (!confirm('Delete this comment?')) return
  try {
    await api.delete(`/posts/${post.id}/comments/${comment.id}`)
    commentData.value[post.id] = commentData.value[post.id].filter(c => c.id !== comment.id)
    post.comments_count--
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to delete comment')
  }
}

async function toggleLike(post) {
  try {
    const res = await api.post(`/posts/${post.id}/like`)
    post.liked_by_me = res.data.liked
    post.likes_count += res.data.liked ? 1 : -1
  } catch (e) {
    toastError(e.response?.data?.message || 'Failed to update like')
  }
}

async function toggleComments(post) {
  if (expandedPost.value === post.id) { expandedPost.value = null; return }
  expandedPost.value = post.id
  if (!commentData.value[post.id]) {
    try {
      const res = await api.get(`/posts/${post.id}/comments`)
      commentData.value[post.id] = res.data
    } catch (e) { commentData.value[post.id] = [] }
  }
}

/**
 * Add comment (official response) to a post
 * Staff can respond with official department information
 * Comment is marked as "official" if posted by staff member
 */
async function addComment(post) {
  if (postingComment.value[post.id]) return // Prevent duplicate submissions
  const text = commentTexts.value[post.id]?.trim()
  if (!text) return
  postingComment.value[post.id] = true
  commentTexts.value[post.id] = '' // Clear input immediately
  try {
    const res = await api.post(`/posts/${post.id}/comments`, { content: text })
    if (!commentData.value[post.id]) commentData.value[post.id] = []
    commentData.value[post.id].push(res.data)
    post.comments_count++
  } catch (e) {
    console.error(e)
    commentTexts.value[post.id] = text // Restore text on error
  } finally {
    postingComment.value[post.id] = false
  }
}

/**
 * Create official post from staff member
 * Post is marked "Official" with department tag in community feed
 * New post appears at top of feed immediately
 */
async function createPost() {
  if (!canShare.value || postLoading.value) return
  postLoading.value = true
  try {
    const res = await api.post('/posts', {
      content: newPost.value.content,
      // Trimmed so a location of only spaces is stored as absent rather than
      // rendering as a blank location line on the card.
      location: newPost.value.location.trim() || undefined,
      image_urls: newPost.value.image_urls,
      category: newPost.value.category || DEFAULT_CATEGORY,
      ward: newPost.value.ward || undefined,
    })
    posts.value.unshift(res.data) // Add to top of feed
    closeCreate()
  } catch (e) {
    // Was console.error only: a rejected post left the modal open with no
    // explanation, so it looked like the Share button simply did nothing.
    toastError(e.response?.data?.message || 'Failed to share post')
  } finally { postLoading.value = false }
}

</script>

<style scoped>
/* Matched search terms inside post text. :deep because the <mark> is injected
   via v-html and so isn't in this component's scoped-style scope. */
:deep(.search-hl) { background: #FEF08A; color: inherit; border-radius: 3px; padding: 0 1px; }
.empty-state .btn { margin-top: 0.75rem; }

.posts-list { display: flex; flex-direction: column; gap: 1rem; max-width: 700px; }
.post-card { padding: 1.1rem 1.25rem; }
.post-header { display: flex; justify-content: space-between; gap: 0.75rem; align-items: flex-start; margin-bottom: 0.75rem; }

.post-header-right { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }

/* Accent, not grey: this app colours clickable pills with --accent and purely
   decorative ones with --bg, and this chip filters the feed when clicked. */
.post-category {
  background: var(--accent);
  color: var(--accent-foreground);
  border: 1px solid transparent;
  border-radius: 100px;
  padding: 0.2rem 0.65rem;
  font-size: 0.7rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  font-family: inherit;
  transition: background var(--transition), border-color var(--transition);
}
.post-category:hover { background: rgba(0, 82, 255, 0.16); border-color: var(--primary); }
.post-author { display: flex; align-items: flex-start; gap: 0.6rem; }
.author-name { font-size: 0.85rem; font-weight: 700; color: #5C1A41; display: flex; align-items: center; flex-wrap: wrap; gap: 0.25rem; }
.dept-tag { font-size: 0.7rem; color: #B0708F; background: #FFE9F2; padding: 0.1rem 0.35rem; border-radius: 100px; }
.post-meta { font-size: 0.75rem; color: #D69AB8; margin-top: 0.1rem; }
.post-title { font-size: 0.9rem; font-weight: 700; color: #5C1A41; margin-bottom: 0.4rem; }
.post-content { font-size: 0.875rem; color: #5C1A41; line-height: 1.65; margin-bottom: 0.85rem; }
.post-img { width: 100%; max-height: 280px; object-fit: cover; border-radius: 8px; margin-bottom: 0.85rem; border: 1px solid #FFD1E6; display: block; }
.post-actions { display: flex; gap: 1rem; padding-top: 0.65rem; border-top: 1px solid #FFE9F2; }
.action-btn { background: none; border: none; font-size: 0.8rem; color: #B0708F; cursor: pointer; padding: 0.2rem 0.4rem; border-radius: 5px; }
.action-btn:hover { background: #FFE9F2; }
.action-btn.liked { color: #FF2D6F; }
.comments-section { margin-top: 0.85rem; padding-top: 0.85rem; border-top: 1px solid #FFD1E6; }
.comment-item { padding: 0.5rem 0; border-bottom: 1px solid #FFE9F2; }
.comment-item.official-comment { background: #DFF7EC; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.35rem; }
.comment-author { font-size: 0.78rem; font-weight: 700; color: #5C1A41; display: flex; align-items: center; gap: 0.35rem; }
.official-tag { font-size: 0.65rem; background: #5C1A41; color: #fff; padding: 0.1rem 0.35rem; border-radius: 100px; }
.comment-text { font-size: 0.82rem; color: #5C1A41; margin-top: 0.15rem; }
.comment-time { font-size: 0.7rem; color: #D69AB8; margin-top: 0.1rem; }
.comment-delete-btn { background: none; border: none; color: #D69AB8; font-size: 0.7rem; cursor: pointer; margin-left: 0.4rem; padding: 0 0.2rem; }
.comment-delete-btn:hover { color: #E0218A; }
.comment-input { display: flex; gap: 0.5rem; margin-top: 0.75rem; }

.badge-inline { margin-left: 0.4rem; font-size: 0.6rem; }

/* Instagram-style create-post modal — same pattern as the citizen feed */
.create-modal { width: 460px; max-width: 92vw; padding: 0; overflow: hidden; display: flex; flex-direction: column; }
.create-header { display: flex; align-items: center; justify-content: space-between; padding: 0.6rem 0.85rem; border-bottom: 1px solid #FFD1E6; }
.create-header h2 { font-size: 0.95rem; font-weight: 700; margin: 0; color: #5C1A41; }
.create-nav { background: none; border: none; font-size: 1.1rem; color: #5C1A41; cursor: pointer; padding: 0.15rem 0.35rem; line-height: 1; }
.create-action { background: none; border: none; color: #E0218A; font-size: 0.85rem; font-weight: 700; cursor: pointer; padding: 0.15rem 0.35rem; }
.create-action:disabled { color: #FFD1E6; cursor: default; }
.create-body { padding: 1rem; overflow-y: auto; }
.optional-label { font-weight: 400; color: #D69AB8; }
/* Keeps the label and its ✨ Suggest button on one row now that the button is
   no longer nested inside the <label>. */
.label-row { display: flex; align-items: center; }
.suggest-btn {
  margin-left: 0.5rem;
  background: var(--accent);
  color: var(--accent-foreground);
  border: 1px solid transparent;
  border-radius: 100px;
  padding: 0.15rem 0.6rem;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
  transition: background var(--transition);
}
.suggest-btn:hover { background: rgba(0, 82, 255, 0.16); }
</style>
