<script setup lang="ts">
import { ref, nextTick } from 'vue';
import SparklesIcon from '@/components/icons/SparklesIcon.vue';
import MessageSquareIcon from '@/components/icons/MessageSquareIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import CloseIcon from '@/components/icons/CloseIcon.vue';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

const isOpen = ref(false);

const messages = ref<ChatMessage[]>([
  {
    role: 'assistant',
    content: '你好！我是投教 AI 助手，可以解答市盈率、定投、资产配置等理财问题。有什么想了解的吗？',
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
    const history = messages.value.slice(0, -1).map(m => ({
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

<template>
  <Teleport to="body">
    <!-- 浮动聊天按钮 -->
    <button
      v-if="!isOpen"
      type="button"
      @click="openChat"
      class="fixed bottom-6 right-6 z-[9990] w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg shadow-indigo-500/30 hover:bg-indigo-700 hover:scale-105 transition-all flex items-center justify-center"
      aria-label="打开 AI 问答助手"
    >
      <MessageSquareIcon class="w-6 h-6" />
      <span class="absolute -top-1 -right-1 w-4 h-4 bg-emerald-400 rounded-full border-2 border-white" />
    </button>

    <!-- 遮罩 + 聊天窗口 -->
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
        class="fixed inset-0 z-[9998] bg-black/20 backdrop-blur-[1px]"
        @click="closeChat"
      />
    </Transition>

    <Transition
      enter-active-class="transition-all duration-200 ease-out"
      enter-from-class="opacity-0 translate-y-4 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition-all duration-150 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 translate-y-4 scale-95"
    >
      <div
        v-if="isOpen"
        class="fixed z-[9999] flex flex-col bg-white shadow-2xl border border-slate-200 overflow-hidden
               bottom-0 right-0 left-0 h-[min(85vh,640px)] rounded-t-2xl
               sm:bottom-6 sm:right-6 sm:left-auto sm:w-[400px] sm:h-[min(70vh,600px)] sm:rounded-2xl"
        @click.stop
      >
        <!-- 标题栏 -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-gradient-to-r from-indigo-50 to-purple-50 flex-shrink-0">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <SparklesIcon class="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 class="font-semibold text-slate-900 text-sm">AI 问答助手</h3>
              <p class="text-xs text-slate-500">Powered by DeepSeek</p>
            </div>
          </div>
          <button
            type="button"
            @click="closeChat"
            class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white/80 transition-colors"
            aria-label="关闭"
          >
            <CloseIcon class="w-5 h-5" />
          </button>
        </div>

        <!-- 消息区 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
          <div
            v-for="(msg, index) in messages"
            :key="index"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[88%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed"
              :class="msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-md'
                : 'bg-slate-100 text-slate-800 rounded-bl-md'"
            >
              <p class="whitespace-pre-wrap">{{ msg.content }}</p>
            </div>
          </div>

          <div v-if="isLoading" class="flex justify-start">
            <div class="bg-slate-100 rounded-2xl rounded-bl-md px-4 py-3 text-sm text-slate-500">
              <span class="inline-flex gap-1">
                <span class="animate-bounce">·</span>
                <span class="animate-bounce" style="animation-delay: 0.1s">·</span>
                <span class="animate-bounce" style="animation-delay: 0.2s">·</span>
              </span>
              正在思考...
            </div>
          </div>
          <div ref="messagesEnd" />
        </div>

        <!-- 快捷问题 -->
        <div v-if="messages.length <= 1" class="px-4 pb-2 flex flex-wrap gap-2 flex-shrink-0">
          <button
            v-for="q in suggestedQuestions"
            :key="q"
            type="button"
            @click="sendQuestion(q)"
            :disabled="isLoading"
            class="text-xs px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-full hover:bg-indigo-100 transition-colors disabled:opacity-50"
          >
            {{ q }}
          </button>
        </div>

        <div v-if="error" class="px-4 pb-2 flex-shrink-0">
          <p class="text-xs text-red-600 bg-red-50 rounded-lg px-3 py-2">{{ error }}</p>
        </div>

        <!-- 输入区 -->
        <div class="p-4 border-t border-slate-200 flex-shrink-0">
          <div class="flex items-end gap-2">
            <textarea
              v-model="input"
              rows="2"
              placeholder="输入你的问题，如「什么是市盈率？」"
              class="flex-1 px-3 py-2.5 text-sm border border-slate-200 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              :disabled="isLoading"
              @keydown="onKeydown"
            />
            <button
              type="button"
              @click="sendQuestion()"
              :disabled="!input.trim() || isLoading"
              class="p-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
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
