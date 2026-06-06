<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import AlertTriangleIcon from './icons/AlertTriangleIcon.vue';

const messages = [
  'AI分析仅供参考，不构成投资建议',
  '历史收益不代表未来表现',
  '投资有风险，入市需谨慎',
];

const currentIndex = ref(0);
let interval: number | null = null;

onMounted(() => {
  interval = window.setInterval(() => {
    currentIndex.value = (currentIndex.value + 1) % messages.length;
  }, 4000);
});

onUnmounted(() => {
  if (interval) {
    clearInterval(interval);
  }
});
</script>

<template>
  <div class="bg-amber-50 border-b border-amber-200 py-2 px-4">
    <div class="max-w-7xl mx-auto flex items-center justify-center gap-2">
      <AlertTriangleIcon class="w-4 h-4 text-amber-600 flex-shrink-0" />
      <span class="text-sm text-amber-800 font-medium">
        {{ messages[currentIndex] }}
      </span>
    </div>
  </div>
</template>
