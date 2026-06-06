<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import BookIcon from '@/components/icons/BookIcon.vue';
import GraduationCapIcon from '@/components/icons/GraduationCapIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import StarIcon from '@/components/icons/StarIcon.vue';
import LockIcon from '@/components/icons/LockIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';

const router = useRouter();

const userHoldings = ref(['股票', '基金']);
const selectedCategory = ref('all');

const categories = [
  { id: 'all', name: '全部' },
  { id: 'stock', name: '股票投资' },
  { id: 'fund', name: '基金投资' },
  { id: 'bond', name: '债券投资' },
  { id: 'portfolio', name: '资产配置' },
  { id: 'risk', name: '风险管理' },
];

const courses = [
  {
    id: 1,
    title: '股票估值基础：PE/PB指标详解',
    category: 'stock',
    level: '入门',
    duration: '15分钟',
    completed: true,
    recommended: true,
    description: '学习市盈率(PE)和市净率(PB)的基本概念及应用场景',
  },
  {
    id: 2,
    title: '基金定投策略实战',
    category: 'fund',
    level: '进阶',
    duration: '25分钟',
    completed: false,
    recommended: true,
    description: '掌握定投的核心逻辑，学会制定适合自己的定投计划',
  },
  {
    id: 3,
    title: '资产配置的四个维度',
    category: 'portfolio',
    level: '进阶',
    duration: '30分钟',
    completed: false,
    recommended: false,
    description: '从风险、收益、流动性、时间四个维度构建投资组合',
  },
  {
    id: 4,
    title: '如何识别投资陷阱',
    category: 'risk',
    level: '入门',
    duration: '20分钟',
    completed: false,
    recommended: true,
    description: '识别常见的投资骗局和风险信号，保护您的资产安全',
  },
  {
    id: 5,
    title: '债券投资入门指南',
    category: 'bond',
    level: '入门',
    duration: '18分钟',
    completed: false,
    recommended: false,
    description: '了解债券的基本类型、收益来源和风险特征',
  },
  {
    id: 6,
    title: '行为金融学：克服投资心理偏差',
    category: 'risk',
    level: '高阶',
    duration: '35分钟',
    completed: false,
    recommended: false,
    description: '深入理解投资者常见的心理偏差及应对策略',
  },
];

const premiumServices = [
  {
    title: '深度研报解读',
    price: '99元/月',
    features: ['每日3篇精选研报', 'AI智能摘要', '核心观点提取'],
    icon: BookIcon,
  },
  {
    title: '持仓再平衡建议',
    price: '199元/次',
    features: ['个性化调仓方案', '风险评估报告', '执行步骤指导'],
    icon: GraduationCapIcon,
  },
  {
    title: '专家复核',
    price: '299元/次',
    features: ['资深投顾1对1', '视频诊断报告', '持续跟踪服务'],
    icon: StarIcon,
  },
];

const filteredCourses = computed(() => {
  if (selectedCategory.value === 'all') return courses;
  return courses.filter(c => c.category === selectedCategory.value);
});

const recommendedCourses = computed(() => {
  return courses.filter(c => c.recommended);
});
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <RiskBanner />

    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
        <button @click="router.push('/')" class="p-2 hover:bg-slate-100 rounded-lg transition-colors">
          <HomeIcon class="w-5 h-5 text-slate-600" />
        </button>
        <h1 class="text-xl font-bold text-slate-900">场景化投教</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-8">
        <div class="flex items-center gap-3">
          <GraduationCapIcon class="w-6 h-6 text-emerald-600" />
          <p class="text-sm text-emerald-800">
            根据您的持仓品类和风险偏好，为您推荐个性化的理财知识。所有内容均经过人工审核。
          </p>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <h2 class="text-lg font-semibold text-slate-900 mb-4">您的持仓场景</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="holding in userHoldings"
            :key="holding"
            class="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium"
          >
            {{ holding }}
          </span>
        </div>
        <p class="text-sm text-slate-500 mt-3">
          基于您的持仓，我们为您推荐了以下学习内容
        </p>
      </div>

      <div class="mb-8">
        <h2 class="text-lg font-semibold text-slate-900 mb-4">为您推荐</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="course in recommendedCourses"
            :key="course.id"
            class="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-lg transition-shadow cursor-pointer group"
          >
            <div class="flex items-start justify-between mb-3">
              <div
                class="px-2 py-1 rounded text-xs font-medium"
                :class="course.level === '入门' ? 'bg-emerald-100 text-emerald-700' : course.level === '进阶' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'"
              >
                {{ course.level }}
              </div>
              <div v-if="course.completed" class="text-emerald-500">
                <CheckCircleIcon class="w-5 h-5" />
              </div>
            </div>
            <h3 class="font-semibold text-slate-900 mb-2 group-hover:text-indigo-600 transition-colors">
              {{ course.title }}
            </h3>
            <p class="text-sm text-slate-500 mb-4">{{ course.description }}</p>
            <div class="flex items-center gap-4 text-xs text-slate-400">
              <span class="flex items-center gap-1">
                <ClockIcon class="w-4 h-4" />
                {{ course.duration }}
              </span>
              <span class="px-2 py-0.5 bg-amber-100 text-amber-700 rounded">推荐</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <h2 class="text-lg font-semibold text-slate-900 mb-4">全部课程</h2>
        <div class="flex flex-wrap gap-2 mb-6">
          <button
            v-for="cat in categories"
            :key="cat.id"
            @click="selectedCategory = cat.id"
            class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            :class="selectedCategory === cat.id ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
          >
            {{ cat.name }}
          </button>
        </div>
        <div class="space-y-3">
          <div
            v-for="course in filteredCourses"
            :key="course.id"
            class="flex items-center gap-4 p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <div
              class="w-10 h-10 rounded-lg flex items-center justify-center"
              :class="course.completed ? 'bg-emerald-100' : 'bg-slate-200'"
            >
              <BookIcon
                class="w-5 h-5"
                :class="course.completed ? 'text-emerald-600' : 'text-slate-500'"
              />
            </div>
            <div class="flex-1">
              <h4 class="font-medium text-slate-900">{{ course.title }}</h4>
              <p class="text-sm text-slate-500">{{ course.description }}</p>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-xs text-slate-400">{{ course.duration }}</span>
              <span
                class="px-2 py-1 rounded text-xs font-medium"
                :class="course.level === '入门' ? 'bg-emerald-100 text-emerald-700' : course.level === '进阶' ? 'bg-blue-100 text-blue-700' : 'bg-purple-100 text-purple-700'"
              >
                {{ course.level }}
              </span>
              <CheckCircleIcon
                v-if="course.completed"
                class="w-5 h-5 text-emerald-500"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-xl p-6 text-white">
        <div class="flex items-center gap-2 mb-4">
          <LockIcon class="w-5 h-5" />
          <h2 class="text-lg font-semibold">解锁高级功能</h2>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            v-for="service in premiumServices"
            :key="service.title"
            class="bg-white/10 rounded-lg p-4 backdrop-blur"
          >
            <div class="flex items-center gap-2 mb-2">
              <component :is="service.icon" class="w-5 h-5" />
              <h3 class="font-medium">{{ service.title }}</h3>
            </div>
            <p class="text-2xl font-bold mb-3">{{ service.price }}</p>
            <ul class="space-y-1 text-sm text-indigo-100">
              <li v-for="feature in service.features" :key="feature" class="flex items-center gap-1">
                <CheckCircleIcon class="w-3 h-3" />
                {{ feature }}
              </li>
            </ul>
            <button class="w-full mt-4 py-2 bg-white text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors flex items-center justify-center gap-1">
              了解详情
              <ArrowRightIcon class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </main>

    <footer class="bg-white border-t border-slate-200 py-6">
      <div class="max-w-7xl mx-auto px-4 text-center">
        <p class="text-sm text-slate-500">
          历史收益不代表未来表现 · AI无法预测市场 · 本内容仅为投资参考，不构成任何投资建议
        </p>
      </div>
    </footer>
  </div>
</template>
