<template>
  <div class="chatbot-root">
    <transition name="chatbot-panel">
      <div v-if="isOpen" class="chatbot-panel">
        <div class="chatbot-header">
          <div class="chatbot-header-title">
            <ChatbotIcon class="chatbot-logo" />
            <span>Cyber Panchayat Assistant</span>
          </div>
          <button class="chatbot-close" @click="close" aria-label="Close chat">✕</button>
        </div>

        <div ref="scrollEl" class="chatbot-body">
          <div v-for="(msg, i) in transcript" :key="i" :class="['chatbot-msg', `chatbot-msg-${msg.kind}`]">
            <ChatbotIcon v-if="msg.kind === 'bot'" class="chatbot-msg-logo" />
            <div class="chatbot-msg-bubble">
              {{ msg.text }}
              <router-link v-if="msg.action" :to="msg.action.path" class="chatbot-action-btn" @click="close">
                {{ msg.action.label }} →
              </router-link>
            </div>
          </div>
        </div>

        <div class="chatbot-options">
          <div v-if="currentOptions.length" class="chatbot-options-label">You might also ask:</div>
          <div class="chatbot-chips">
            <button v-for="id in currentOptions" :key="id" class="chatbot-chip" @click="select(id)">
              {{ faqNodes[id]?.question }}
            </button>
            <button class="chatbot-chip chatbot-chip-reset" @click="restart">🏠 Main Menu</button>
            <!-- A way out of the chat. Picking questions is quick when the
                 guess is right, but a dead end when it is not. The FAQ page
                 shows every answer at once. -->
            <router-link to="/faq" class="chatbot-chip chatbot-chip-reset" @click="close">Browse all FAQs</router-link>
          </div>
        </div>

        <form class="chatbot-input-row" @submit.prevent="submitTyped">
          <input
            v-model="typedQuestion"
            type="text"
            class="chatbot-input"
            placeholder="Don't see your question? Type it here..."
            maxlength="200"
          />
          <button type="submit" class="chatbot-send" :disabled="!typedQuestion.trim()" aria-label="Send question">➤</button>
        </form>
      </div>
    </transition>

    <transition name="chatbot-hint">
      <div v-if="showHint" class="chatbot-hint" @click="toggle">
        👋 Need help? Ask me anything!
      </div>
    </transition>

    <button
      class="chatbot-bubble"
      :class="{ 'chatbot-bubble-open': isOpen, 'chatbot-bubble-pulse': !hasOpened }"
      @click="toggle"
      aria-label="Open chat assistant"
    >
      <ChatbotIcon v-if="!isOpen" class="chatbot-bubble-logo" />
      <span v-else>✕</span>
    </button>
  </div>
</template>

<script setup>
/**
 * ChatbotWidget - Guided (non-AI) help assistant.
 * Click-through decision tree: pick a question, read the answer, get a fresh
 * set of related follow-up questions. Content lives in data/chatbotFaq.js.
 */
import { nextTick, onMounted, ref, watch } from "vue"
import ChatbotIcon from "./ChatbotIcon.vue"
import { useChatbot } from "../composables/useChatbot"

// Rendered wherever App.vue mounts it, signed in or not: the Help and FAQ page
// is public, and a visitor with no account is exactly the reader who gives up
// on a long help page. Which pages show it is App.vue's call, and useChatbot's
// syncSession() handles closing and reseeding the panel across a sign-in or
// sign-out.
const { isOpen, hasOpened, transcript, currentOptions, faqNodes, open, close, select: selectNode, ask: askQuestion, restart } = useChatbot()
const scrollEl = ref(null)
const showHint = ref(false)
const typedQuestion = ref("")

function toggle() {
  showHint.value = false
  if (isOpen.value) close()
  else open()
}

function select(id) {
  selectNode(id)
}

function submitTyped() {
  if (!typedQuestion.value.trim()) return
  askQuestion(typedQuestion.value)
  typedQuestion.value = ""
}

watch([transcript, currentOptions], async () => {
  await nextTick()
  if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
})

// One-time attention hint on first visit, so the widget doesn't blend into
// the corner unnoticed. Auto-dismisses, and never reappears once opened.
onMounted(() => {
  if (hasOpened.value) return
  const showTimer = setTimeout(() => {
    if (!hasOpened.value) showHint.value = true
  }, 1500)
  const hideTimer = setTimeout(() => { showHint.value = false }, 8000)
  watch(hasOpened, (v) => { if (v) { showHint.value = false; clearTimeout(showTimer); clearTimeout(hideTimer) } })
})
</script>

<style scoped>
.chatbot-root {
  position: fixed;
  /* Toast.vue's notifications anchor at this exact same corner (bottom:24px/
     right:24px). They're transient (a few seconds) while this bubble is
     permanent, so it stays flush in the corner rather than floating up into
     the page content to dodge them. */
  bottom: 24px;
  right: 24px;
  z-index: 1400;
  font-family: var(--font-body);
}

.chatbot-bubble {
  width: 60px; height: 60px; border-radius: 50%; border: none;
  background: var(--gradient-accent);
  color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 27px;
  box-shadow: 0 6px 20px rgba(0,82,255,0.35);
  transition: transform 0.15s, box-shadow 0.15s;
  position: relative;
  /* Deliberately no overflow:hidden — .chatbot-bubble-pulse::before below is
     an expanding ring at inset:-6px, which a clipping parent would swallow. */
}
.chatbot-bubble:hover { transform: scale(1.08); box-shadow: 0 8px 24px rgba(0,82,255,0.45); }
.chatbot-bubble-open { background: linear-gradient(135deg, var(--text-muted) 0%, var(--secondary) 100%); }
.chatbot-bubble-logo { width: 34px; height: 34px; color: #fff; }

.chatbot-bubble-pulse::before {
  content: "";
  position: absolute; inset: -6px;
  border-radius: 50%;
  border: 2px solid var(--primary);
  animation: chatbot-pulse-ring 2.2s ease-out infinite;
}
@keyframes chatbot-pulse-ring {
  0% { transform: scale(0.9); opacity: 0.7; }
  70% { transform: scale(1.35); opacity: 0; }
  100% { transform: scale(1.35); opacity: 0; }
}

.chatbot-hint {
  position: absolute;
  bottom: 8px; right: 72px;
  white-space: nowrap;
  background: #fff; color: var(--text);
  font-size: 0.82rem; font-weight: 600;
  padding: 0.6rem 1rem;
  border-radius: 100px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.18);
  cursor: pointer;
}
.chatbot-hint::after {
  content: "";
  position: absolute; top: 50%; right: -5px; transform: translateY(-50%);
  width: 10px; height: 10px; background: #fff;
  clip-path: polygon(0 0, 0% 100%, 100% 50%);
}
.chatbot-hint-enter-active, .chatbot-hint-leave-active { transition: opacity 0.25s, transform 0.25s; }
.chatbot-hint-enter-from, .chatbot-hint-leave-to { opacity: 0; transform: translateX(8px); }

.chatbot-panel {
  position: absolute;
  bottom: 70px; right: 0;
  width: 360px; max-width: calc(100vw - 32px);
  height: 520px; max-height: 70vh;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 36px rgba(0,0,0,0.22);
  display: flex; flex-direction: column;
  overflow: hidden;
}

.chatbot-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.9rem 1.1rem;
  background: linear-gradient(135deg, var(--primary) 0%, var(--accent-secondary) 100%);
  color: #fff; flex-shrink: 0;
}
.chatbot-header-title { display: flex; align-items: center; gap: 0.5rem; font-size: 0.92rem; font-weight: 700; }
.chatbot-logo {
  width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0;
  background: #fff; color: var(--primary);
  padding: 3px;
}
.chatbot-close { background: rgba(255,255,255,0.2); border: none; color: #fff; width: 26px; height: 26px; border-radius: 50%; cursor: pointer; font-size: 0.8rem; }
.chatbot-close:hover { background: rgba(255,255,255,0.32); }

.chatbot-body {
  flex: 1; overflow-y: auto;
  padding: 1rem;
  display: flex; flex-direction: column; gap: 0.7rem;
  background: var(--bg, #F7F8FA);
  scrollbar-width: thin;
  scrollbar-color: var(--accent-secondary) transparent;
}
.chatbot-body::-webkit-scrollbar { width: 6px; }
.chatbot-body::-webkit-scrollbar-thumb { background: var(--accent-secondary); border-radius: 100px; }
.chatbot-body::-webkit-scrollbar-track { background: transparent; }
.chatbot-msg { display: flex; align-items: flex-start; gap: 0.5rem; }
.chatbot-msg-user { justify-content: flex-end; }
.chatbot-msg-logo {
  width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0; margin-top: 0.1rem;
  background: var(--accent); color: var(--primary);
  padding: 2.5px;
  box-shadow: 0 0 0 1px var(--border);
}
.chatbot-msg-bubble {
  max-width: 82%;
  padding: 0.6rem 0.85rem;
  border-radius: 12px;
  font-size: 0.84rem; line-height: 1.45;
  background: #fff; color: var(--text);
  box-shadow: 0 1px 2px rgba(0,0,0,0.06);
}
.chatbot-msg-user .chatbot-msg-bubble {
  background: var(--primary); color: #fff;
  border-bottom-right-radius: 4px;
}
.chatbot-msg-bot .chatbot-msg-bubble { border-bottom-left-radius: 4px; }

.chatbot-action-btn {
  display: inline-block; margin-top: 0.5rem;
  font-size: 0.78rem; font-weight: 700;
  color: var(--primary);
}

.chatbot-options { border-top: 1px solid var(--border); padding: 0.75rem; flex-shrink: 0; }
.chatbot-options-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.5rem; }
.chatbot-chips { display: flex; flex-wrap: wrap; gap: 0.4rem; max-height: 140px; overflow-y: auto; }
.chatbot-chip {
  background: var(--accent, #EEF2FF); color: var(--primary);
  border: 1px solid transparent;
  border-radius: 100px; padding: 0.4rem 0.8rem;
  font-size: 0.76rem; font-weight: 600; cursor: pointer;
  transition: background 0.15s;
}
.chatbot-chip:hover { background: rgba(0,82,255,0.16); }
.chatbot-chip-reset { background: #fff; border-color: var(--border); color: var(--text-muted); }
.chatbot-chip-reset:hover { background: var(--stone, #F1F5F9); }

.chatbot-input-row {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.7rem 0.75rem;
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.chatbot-input {
  flex: 1;
  border: 1px solid var(--border); border-radius: 100px;
  padding: 0.55rem 0.95rem;
  font-size: 0.82rem;
  outline: none;
  transition: border-color 0.15s;
}
.chatbot-input:focus { border-color: var(--primary); }
.chatbot-send {
  width: 34px; height: 34px; border-radius: 50%; border: none; flex-shrink: 0;
  background: var(--primary); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.9rem;
  transition: opacity 0.15s;
}
.chatbot-send:disabled { opacity: 0.4; cursor: default; }
.chatbot-send:not(:disabled):hover { opacity: 0.85; }

.chatbot-panel-enter-active, .chatbot-panel-leave-active { transition: opacity 0.18s, transform 0.18s; }
.chatbot-panel-enter-from, .chatbot-panel-leave-to { opacity: 0; transform: translateY(12px); }

@media (max-width: 480px) {
  .chatbot-root { right: 12px; bottom: 12px; }
  .chatbot-panel { width: calc(100vw - 24px); height: 65vh; }
  .chatbot-hint { right: 68px; white-space: normal; max-width: 180px; }
}
</style>
