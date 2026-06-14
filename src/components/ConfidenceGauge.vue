<script setup lang="ts">
interface Props {
  value: number;
  label?: string;
}

const props = withDefaults(defineProps<Props>(), {
  label: '置信度',
});

const getColor = (val: number) => {
  if (val >= 80) return 'text-emerald-600';
  if (val >= 60) return 'text-blue-600';
  if (val >= 40) return 'text-amber-600';
  return 'text-red-600';
};

const getBgColor = (val: number) => {
  if (val >= 80) return 'bg-emerald-500';
  if (val >= 60) return 'bg-blue-500';
  if (val >= 40) return 'bg-amber-500';
  return 'bg-red-500';
};
</script>

<template>
  <div class="flex flex-col items-center">
    <div class="relative w-32 h-16 overflow-hidden">
      <div class="absolute top-0 left-0 w-32 h-32 rounded-full border-8 border-slate-200"></div>
      <div
        class="absolute top-0 left-0 w-32 h-32 rounded-full border-8 transition-all duration-1000"
        :class="getBgColor(props.value)"
        :style="{
          clipPath: `polygon(50% 50%, 50% 0%, ${50 + 50 * Math.sin((props.value / 100) * Math.PI)}% ${50 - 50 * Math.cos((props.value / 100) * Math.PI)}%)`
        }"
      ></div>
      <div class="absolute bottom-0 left-1/2 -translate-x-1/2 text-2xl font-bold" :class="getColor(props.value)">
        {{ props.value }}%
      </div>
    </div>
    <span class="text-sm text-slate-600 mt-1">{{ props.label }}</span>
  </div>
</template>
