<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import { coursesData, type CourseContent } from '@/data/courses';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import BookIcon from '@/components/icons/BookIcon.vue';
import GraduationCapIcon from '@/components/icons/GraduationCapIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import StarIcon from '@/components/icons/StarIcon.vue';
import LockIcon from '@/components/icons/LockIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import PlayIcon from '@/components/icons/PlayIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const selectedCategory = ref('all');
const courses = ref<CourseContent[]>([]);
const completedCourses = ref<Set<number>>(new Set());

const categories = [
  { id: 'all', name: '全部' },
  { id: 'stock', name: '股票投资' },
  { id: 'fund', name: '基金投资' },
  { id: 'bond', name: '债券投资' },
  { id: 'portfolio', name: '资产配置' },
  { id: 'risk', name: '风险管理' },
];

// 从持仓推断用户持有的资产类型
const userHoldings = computed(() => {
  const types = new Set<string>();
  portfolioStore.portfolio.assets.forEach(asset => {
    if (asset.type === 'stock') types.add('股票');
    if (asset.type === 'fund') types.add('基金');
    if (asset.type === 'bond') types.add('债券');
  });
  return types.size > 0 ? Array.from(types) : ['股票', '基金'];
});

// 加载课程完成状态
const loadCompletedStatus = () => {
  const saved = localStorage.getItem('completed_courses');
  if (saved) {
    completedCourses.value = new Set(JSON.parse(saved));
  }
  // 同时更新课程数据中的完成状态
  courses.value.forEach(course => {
    course.completed = completedCourses.value.has(course.id);
  });
};

// 保存完成状态
const saveCompletedStatus = () => {
  localStorage.setItem('completed_courses', JSON.stringify(Array.from(completedCourses.value)));
};

onMounted(() => {
  portfolioStore.loadPortfolio();
  courses.value = coursesData;
  loadCompletedStatus();
});

const filteredCourses = computed(() => {
  if (selectedCategory.value === 'all') return courses.value;
  return courses.value.filter(c => c.category === selectedCategory.value);
});

const recommendedCourses = computed(() => {
  return courses.value.filter(c => c.recommended);
});

const getLevelColor = (level: string) => {
  switch (level) {
    case '入门': return 'bg-emerald-100 text-emerald-700';
    case '进阶': return 'bg-blue-100 text-blue-700';
    case '高阶': return 'bg-purple-100 text-purple-700';
    default: return 'bg-slate-100 text-slate-700';
  }
};

const startCourse = (courseId: number) => {
  router.push(`/course/${courseId}`);
};

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
            @click="startCourse(course.id)"
            class="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-lg transition-all cursor-pointer group"
          >
            <div class="flex items-start justify-between mb-3">
              <div
                class="px-2 py-1 rounded text-xs font-medium"
                :class="getLevelColor(course.level)"
              >
                {{ course.level }}
              </div>
              <div v-if="completedCourses.has(course.id)" class="text-emerald-500">
                <CheckCircleIcon class="w-5 h-5" />
              </div>
            </div>
            <h3 class="font-semibold text-slate-900 mb-2 group-hover:text-indigo-600 transition-colors">
              {{ course.title }}
            </h3>
            <p class="text-sm text-slate-500 mb-4 line-clamp-2">{{ course.description }}</p>
            <div class="flex items-center gap-4 text-xs text-slate-400">
              <span class="flex items-center gap-1">
                <ClockIcon class="w-4 h-4" />
                {{ course.duration }}
              </span>
              <span class="px-2 py-0.5 bg-amber-100 text-amber-700 rounded">推荐</span>
            </div>
            <div class="mt-4 pt-4 border-t border-slate-100">
              <button class="w-full flex items-center justify-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition-colors text-sm font-medium">
                <PlayIcon class="w-4 h-4" />
                {{ completedCourses.has(course.id) ? '重新学习' : '开始学习' }}
              </button>
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
            @click="startCourse(course.id)"
            class="flex items-center gap-4 p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer group"
          >
            <div
              class="w-10 h-10 rounded-lg flex items-center justify-center"
              :class="completedCourses.has(course.id) ? 'bg-emerald-100' : 'bg-slate-200'"
            >
              <BookIcon
                class="w-5 h-5"
                :class="completedCourses.has(course.id) ? 'text-emerald-600' : 'text-slate-500'"
              />
            </div>
            <div class="flex-1">
              <h4 class="font-medium text-slate-900 group-hover:text-indigo-600 transition-colors">{{ course.title }}</h4>
              <p class="text-sm text-slate-500 line-clamp-1">{{ course.description }}</p>
            </div>
            <div class="flex items-center gap-4">
              <span class="text-xs text-slate-400">{{ course.duration }}</span>
              <span
                class="px-2 py-1 rounded text-xs font-medium"
                :class="getLevelColor(course.level)"
              >
                {{ course.level }}
              </span>
              <CheckCircleIcon
                v-if="completedCourses.has(course.id)"
                class="w-5 h-5 text-emerald-500"
              />
              <button class="px-3 py-1 bg-indigo-100 text-indigo-600 rounded text-xs font-medium hover:bg-indigo-200 transition-colors">
                学习
              </button>
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
