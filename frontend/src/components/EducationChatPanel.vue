<script setup lang="ts">
import { ref, nextTick } from 'vue';
import SparklesIcon from '@/components/icons/SparklesIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import CloseIcon from '@/components/icons/CloseIcon.vue';
import UserIcon from '@/components/icons/UserIcon.vue';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const isOpen = ref(false);

const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好！我是投教 AI 助手 🤖\n可以解答市盈率、定投、资产配置等理财问题，有什么想了解的吗？',
  },
]);

const input = ref('');
const isLoading = ref(false);
const error = ref('');
const messagesEnd = ref<HTMLElement | null>(null);

const suggestedQuestions = [
  '什么是市盈率？',
  '定投是什么？',
  '如何分散投资风险？',
];

const openChat = () => {
  isOpen.value = true;
  scrollToBottom();
};

const closeChat = () => {
  isOpen.value = false;
};

const scrollToBottom = async () => {
  await nextTick();
  messagesEnd.value?.scrollIntoView({ behavior: 'smooth' });
};

const sendQuestion = async (question?: string) => {
  const text = (question ?? input.value).trim();
  if (!text || isLoading.value) return;

  error.value = '';
  messages.value.push({ role: 'user', content: text });
  input.value = '';
  isLoading.value = true;
  await scrollToBottom();

  try {
    const history = messages.value.slice(0, -1).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const response = await fetch('/api/education/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: text, history }),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `请求失败 (${response.status})`);
    }

    messages.value.push({ role: 'assistant', content: data.answer });
  } catch (err) {
    error.value = err instanceof Error ? err.message : '发送失败，请稍后重试';
  } finally {
    isLoading.value = false;
    await scrollToBottom();
  }
};

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendQuestion();
  }
};
</script>

<style scoped>
.fab-float {
  animation: fab-float 3s ease-in-out infinite;
}

.fab-float:hover {
  animation: none;
}

@keyframes fab-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}
</style>

<template>
  <Teleport to="body">
    <!-- AI 助手入口：胶囊形，区别于普通客服图标 -->
    <button
      v-if="!isOpen"
      type="button"
      @click="openChat"
      class="fixed bottom-6 right-6 z-[9990] group flex items-center gap-2.5 pl-2 pr-4 py-2 rounded-full
             bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 text-white
             shadow-xl shadow-indigo-500/35 hover:shadow-indigo-500/50 hover:scale-[1.03]
             transition-all duration-300 fab-float"
      aria-label="打开 AI 投教助手"
    >
      <span class="relative flex-shrink-0 w-10 h-10 rounded-full bg-white/15 ring-2 ring-white/30 flex items-center justify-center backdrop-blur-sm">
        <SparklesIcon class="w-5 h-5 text-amber-200" />
        <span class="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 rounded-full border-2 border-indigo-600" />
      </span>
      <span class="flex flex-col items-start leading-tight pr-1">
        <span class="text-sm font-semibold tracking-wide">AI 投教助手</span>
        <span class="text-[10px] text-indigo-100/90 font-normal">理财问题 · 随时解答</span>
      </span>
    </button>

    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-[9998] bg-black/30 backdrop-blur-sm"
        @click="closeChat"
      />
    </Transition>

    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-6 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition-all duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-6 scale-95"
    >
      <div
        v-if="isOpen"
        class="fixed z-[9999] flex flex-col bg-white shadow-2xl border border-slate-200/80 overflow-hidden
               bottom-0 right-0 left-0 h-[min(88vh,680px)] rounded-t-3xl
               sm:bottom-6 sm:right-6 sm:left-auto sm:w-[420px] sm:h-[min(72vh,640px)] sm:rounded-3xl"
        @click.stop
      >
        <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-gradient-to-r from-indigo-600 to-purple-600 flex-shrink-0">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-white/20 backdrop-blur flex items-center justify-center ring-2 ring-white/30">
              <SparklesIcon class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="font-semibold text-white text-sm">投教 AI 助手</h3>
              <p class="text-xs text-indigo-100 flex items-center gap-1">
                <span class="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                在线 · DeepSeek
              </p>
            </div>
          </div>
          <button
            type="button"
            @click="closeChat"
            class="p-2 rounded-full text-white/70 hover:text-white hover:bg-white/10 transition-colors"
            aria-label="关闭"
          >
            <CloseIcon class="w-5 h-5" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-4 py-5 space-y-5 min-h-0 bg-gradient-to-b from-slate-50 to-white">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex gap-2.5"
            :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
          >
            <div
              class="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm"
              :class="msg.role === 'user'
                ? 'bg-indigo-100 text-indigo-600'
                : 'bg-gradient-to-br from-indigo-500 to-purple-600 text-white'"
            >
              <UserIcon v-if="msg.role === 'user'" class="w-4 h-4" />
              <span v-else class="text-sm leading-none">🤖</span>
            </div>

            <div
              class="max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm"
              :class="msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-tr-sm'
                : 'bg-white text-slate-800 border border-slate-100 rounded-tl-sm'"
            >
              <p class="whitespace-pre-wrap">{{ msg.content }}</p>
            </div>
          </div>

          <div v-if="isLoading" class="flex gap-2.5 flex-row">
            <div class="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-sm">
              <span class="text-sm">🤖</span>
            </div>
            <div class="bg-white border border-slate-100 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm">
              <div class="flex items-center gap-2 text-sm text-slate-500">
                <span class="flex gap-1">
                  <span class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" />
                  <span class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.15s" />
                  <span class="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0.3s" />
                </span>
                正在输入...
              </div>
            </div>
          </div>

          <div ref="messagesEnd" />
        </div>

        <div v-if="messages.length <= 1" class="px-4 pb-2 flex flex-wrap gap-2 flex-shrink-0 bg-white">
          <button
            v-for="q in suggestedQuestions"
            :key="q"
            type="button"
            @click="sendQuestion(q)"
            :disabled="isLoading"
            class="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 border border-indigo-100 transition-colors disabled:opacity-50"
          >
            {{ q }}
          </button>
        </div>

        <div v-if="error" class="px-4 pb-2 flex-shrink-0 bg-white">
          <p class="text-xs text-red-600 bg-red-50 rounded-xl px-3 py-2 border border-red-100">{{ error }}</p>
        </div>

        <div class="p-4 border-t border-slate-100 flex-shrink-0 bg-white">
          <div class="flex items-end gap-2">
            <textarea
              v-model="input"
              rows="1"
              placeholder="输入你的问题..."
              class="flex-1 px-4 py-3 text-sm bg-slate-50 border border-slate-200 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent focus:bg-white transition-colors"
              :disabled="isLoading"
              @keydown="onKeydown"
            />
            <button
              type="button"
              @click="sendQuestion()"
              :disabled="!input.trim() || isLoading"
              class="p-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-2xl hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0 shadow-md shadow-indigo-500/25"
              aria-label="发送"
            >
              <ArrowRightIcon class="w-5 h-5" />
            </button>
          </div>
          <p class="text-[10px] text-slate-400 mt-2 text-center">
            AI 回答仅供参考，不构成投资建议
          </p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
