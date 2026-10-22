<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-content">
      <AppTopbar title="Community Management" />
      <div class="content-area">
        <div class="page-header">
          <div class="page-header-left">
            <p>Monitor and moderate community posts</p>
          </div>
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
          :result-count="displayPosts.length"
          @clear-all="clearAll"
          @remove-chip="clearFilter"
        />

        <div v-if="loading" class="spinner"></div>

        <!-- A failed load must not read as an empty feed. Without this, a
             network error fell through to "No posts found" and quietly told
             the admin there was nothing to moderate. -->
        <div v-else-if="loadError" class="empty-state">
          <div class="empty-icon">&#9888;</div>
          <p>{{ loadError }}</p>
          <button class="btn btn-sm btn-secondary" @click="loadPosts">Try Again</button>
        </div>

        <div v-else class="posts-list">
          <div v-if="!displayPosts.length && hasActiveFilters" class="empty-state">
            <div class="empty-icon">&#128269;</div>
            <p>No posts match your search</p>
            <button class="btn btn-sm btn-secondary" @click="clearAll">Clear Filters</button>
          </div>
          <div v-else-if="!displayPosts.length" class="empty-state">
            <div class="empty-icon">&#9998;</div>
            <p>No posts found</p>
          </div>
          <div v-for="post in displayPosts" :key="post.id" class="post-card card">
            <div class="post-header">
              <div class="post-author-info">
                <div class="avatar avatar-sm">{{ post.author_name?.charAt(0) }}</div>
                <div>
                  <div class="author-name">
                    {{ post.author_name }}
                    <span v-if="post.is_official" class="badge badge-official badge-inline">Official</span>
                    <span v-if="post.author_department" class="dept-tag">{{ post.author_department }}</span>
                  </div>
                  <div class="post-meta">{{ post.location }} &bull; {{ timeAgo(post.created_at) }}</div>
                </div>
              </div>
              <div class="post-header-right">
                <!-- Same click-to-filter chip the citizen feed shows. Every post
                     already carries a category and this page already filters on
                     it, so leaving it off meant admins were filtering on a field
                     they could not see. -->
                <button
                  v-if="post.category"
                  type="button"
                  class="post-category"
                  :title="`Show only ${fmtCategory(post.category)} posts`"
                  @click="category = post.category"
                >{{ fmtCategory(post.category) }}</button>
                <button class="btn btn-xs btn-danger" @click="deletePost(post)">&#128465; Delete</button>
              </div>
            </div>
            <!-- v-html is safe: highlight() escapes the post text before adding
                 its own <mark> tags. See highlightTerms() in utils/postFilters. -->
            <div v-if="post.title" class="post-title" v-html="highlight(post.title)"></div>
            <div class="post-content" v-html="highlight(post.content)"></div>
            <ImageGallery v-if="post.image_urls?.length" :images="post.image_urls" alt="Post image" />

            <div class="post-actions">
              <button class="action-btn" :class="{ liked: post.liked_by_me }" @click="toggleLike(post)">
                &#9829; {{ post.likes_count }}
              </button>
              <button class="action-btn" @click="toggleComments(post)">
                &#9997; {{ post.comments_count }} Comments
              </button>
            </div>

            <div v-if="expandedPost === post.id" class="comments-section">
              <div v-if="!commentData[post.id]" class="spinner p-4"></div>
              <template v-else>
                <div v-for="c in commentData[post.id]" :key="c.id" class="comment-item" :class="{ 'official-comment': c.is_official }">
                  <div class="comment-author">
                    {{ c.author_name }}
                    <span v-if="c.is_official" class="official-tag">{{ c.author_department || 'Admin' }}</span>
                    <button class="comment-delete-btn" aria-label="Delete comment" title="Delete comment" @click="deleteComment(post, c)">&#x2715;</button>
                  </div>
                  <div class="comment-text">{{ c.content }}</div>
                  <div class="comment-time">{{ timeAgo(c.created_at) }}</div>
                </div>
              </template>
              <div class="comment-input">
                <input v-model="commentTexts[post.id]" class="form-control" placeholder="Reply as admin..." :disabled="postingComment[post.id]" @keydown.enter="addComment(post)" />
                <button class="btn btn-sm btn-primary" :disabled="postingComment[post.id]" @click="addComment(post)">Reply</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Community Management - Admin moderation of community feed posts
 * Features: delete posts, delete comments, add admin replies, moderate content
 * Admins can reply with official department information
 * Posts can be viewed and moderated from this admin-only view
 */
import { ref, computed, onMounted } from 'vue'
import AppSidebar from '../../components/AppSidebar.vue'
import AppTopbar from '../../components/AppTopbar.vue'
import ImageGallery from '../../components/ImageGallery.vue'
import PostFilterBar from '../../components/PostFilterBar.vue'
import { usePostFilters } from '../../composables/usePostFilters'
import { fmtCategory } from '../../utils/postFilters'
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
const posts = ref([]) // All community posts
const tab = ref('all') // Filter: all or own posts
const expandedPost = ref(null) // Currently expanded post for comments
const commentData = ref({}) // Cached comments per post
const commentTexts = ref({}) // Admin reply input per post
const postingComment = ref({}) // Loading state for replies

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

// Tab narrows first; the shared composable applies search + category + ward on
// top, identically to the citizen /feed and staff views.
const baseList = computed(() =>
  tab.value === 'mine' ? posts.value.filter(p => p.citizen_id === auth.user?.id) : posts.value
)
const {
  search, category, ward, author, department,
  filtered: displayPosts, hasActiveFilters, activeChips,
  clearFilter, clearAll, highlight,
} = usePostFilters(baseList)

async function deletePost(post) {
  if (!confirm('Delete this post?')) return
  try {
    await api.delete(`/posts/${post.id}`)
    posts.value = posts.value.filter(p => p.id !== post.id)
  } catch (e) { toastError(e.response?.data?.message || 'Failed to delete') }
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

async function addComment(post) {
  if (postingComment.value[post.id]) return
  const text = commentTexts.value[post.id]?.trim()
  if (!text) return
  postingComment.value[post.id] = true
  commentTexts.value[post.id] = ''
  try {
    const res = await api.post(`/posts/${post.id}/comments`, { content: text })
    if (!commentData.value[post.id]) commentData.value[post.id] = []
    commentData.value[post.id].push(res.data)
    post.comments_count++
  } catch (e) {
    console.error(e)
    commentTexts.value[post.id] = text
  } finally {
    postingComment.value[post.id] = false
  }
}

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

</script>

<style scoped>
/* Matched search terms inside post text. :deep because the <mark> is injected
   via v-html and so isn't in this component's scoped-style scope. */
:deep(.search-hl) { background: #FEF08A; color: inherit; border-radius: 3px; padding: 0 1px; }
.empty-state .btn { margin-top: 0.75rem; }

.posts-list { display: flex; flex-direction: column; gap: 1rem; max-width: 760px; }
.post-card { padding: 1.1rem 1.25rem; }
.post-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; margin-bottom: 0.75rem; }

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
.post-author-info { display: flex; align-items: flex-start; gap: 0.6rem; }
.author-name { font-size: 0.85rem; font-weight: 700; color: #5C1A41; display: flex; align-items: center; flex-wrap: wrap; gap: 0.25rem; }
.dept-tag { font-size: 0.7rem; color: #B0708F; background: #FFE9F2; padding: 0.1rem 0.35rem; border-radius: 100px; }
.post-meta { font-size: 0.75rem; color: #D69AB8; }
.post-title { font-size: 0.9rem; font-weight: 700; color: #5C1A41; margin-bottom: 0.4rem; }
.post-content { font-size: 0.875rem; color: #5C1A41; line-height: 1.6; margin-bottom: 0.75rem; }
.post-actions { display: flex; gap: 1rem; padding-top: 0.65rem; border-top: 1px solid #FFE9F2; }
.action-btn { background: none; border: none; font-size: 0.8rem; color: #B0708F; cursor: pointer; padding: 0.2rem 0.4rem; border-radius: 5px; }
.action-btn:hover { background: #FFE9F2; }
.action-btn.liked { color: #FF2D6F; }
.comments-section { margin-top: 0.85rem; padding-top: 0.85rem; border-top: 1px solid #FFD1E6; }
.comment-item { padding: 0.5rem 0; border-bottom: 1px solid #FFE9F2; }
.comment-item.official-comment { background: #DFF7EC; border-radius: 6px; padding: 0.5rem 0.75rem; margin-bottom: 0.35rem; }
.comment-author { font-size: 0.78rem; font-weight: 700; color: #5C1A41; display: flex; align-items: center; gap: 0.35rem; }
.official-tag { font-size: 0.65rem; background: #0E7A4F; color: #fff; padding: 0.1rem 0.35rem; border-radius: 100px; }
.comment-text { font-size: 0.82rem; color: #5C1A41; margin-top: 0.15rem; }
.comment-time { font-size: 0.7rem; color: #D69AB8; margin-top: 0.1rem; }
.comment-delete-btn { background: none; border: none; color: #D69AB8; font-size: 0.7rem; cursor: pointer; margin-left: 0.4rem; padding: 0 0.2rem; }
.comment-delete-btn:hover { color: #E0218A; }
.comment-input { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
.badge-count { background: #FF2D6F; color: #fff; border-radius: 50%; padding: 0.05rem 0.3rem; font-size: 0.65rem; margin-left: 0.25rem; }
.btn-xs { padding: 0.22rem 0.6rem; font-size: 0.72rem; border-radius: 4px; font-weight: 600; border: none; cursor: pointer; }
.badge-inline { font-size: 0.6rem; margin-left: 0.35rem; }
</style>
