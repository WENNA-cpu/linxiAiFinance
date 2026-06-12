<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
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
import RefreshIcon from '@/components/icons/RefreshIcon.vue';
import EducationChatPanel from '@/components/EducationChatPanel.vue';
import EducationPremiumModals, { type PremiumView } from '@/components/EducationPremiumModals.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

interface CourseContent {
  id: number;
  title: string;
  category: string;
  categoryName?: string;
  level: string;
  duration: string;
  completed: boolean;
  recommended: boolean;
  description: string;
  section_count?: number;
}

const selectedCategory = ref('all');
const courses = ref<CourseContent[]>([]);
const completedCourses = ref<Set<number>>(new Set());
const isLoading = ref(true);
const loadError = ref('');
const coursesUpdatedAt = ref('');
const activePremiumView = ref<PremiumView>(null);

const categories = [
  { id: 'all', name: '全部' },
  { id: 'stock', name: '股票投资' },
  { id: 'fund', name: '基金投资' },
  { id: 'bond', name: '债券投资' },
  { id: 'portfolio', name: '资产配置' },
  { id: 'risk', name: '风险管理' },
];

const premiumServices = [
  {
    id: 'report' as const,
    title: '深度研报解读',
    price: '99元/月',
    features: ['每日3篇精选研报', 'AI智能摘要', '核心观点提取'],
    icon: BookIcon,
  },
  {
    id: 'rebalance' as const,
    title: '持仓再平衡建议',
    price: '199元/次',
    features: ['个性化调仓方案', '风险评估报告', '执行步骤指导'],
    icon: GraduationCapIcon,
  },
  {
    id: 'expert' as const,
    title: '专家复核',
    price: '299元/次',
    features: ['资深投顾1对1', '视频诊断报告', '持续跟踪服务'],
    icon: StarIcon,
  },
];

const userHoldings = computed(() => {
  const types = new Set<string>();
  portfolioStore.portfolio.assets.forEach((asset) => {
    if (asset.type === 'stock') types.add('股票');
    if (asset.type === 'fund') types.add('基金');
    if (asset.type === 'bond') types.add('债券');
  });
  return types.size > 0 ? Array.from(types) : ['股票', '基金'];
});

const loadCompletedStatus = () => {
  const saved = localStorage.getItem('completed_courses');
  if (saved) {
    completedCourses.value = new Set(JSON.parse(saved));
  }
  courses.value.forEach((course) => {
    course.completed = completedCourses.value.has(course.id);
  });
};

const applyCourses = (list: CourseContent[]) => {
  courses.value = list;
  loadCompletedStatus();
};

const fetchCourses = async () => {
  isLoading.value = true;
  loadError.value = '';

  try {
    const response = await fetch('/api/education/courses');
    if (!response.ok) {
      throw new Error(`加载失败 (${response.status})`);
    }
    const data = await response.json();
    const apiCourses: CourseContent[] = (data.courses || []).map((c: CourseContent) => ({
      ...c,
      completed: completedCourses.value.has(c.id),
    }));
    if (apiCourses.length === 0) {
      throw new Error('课程库为空');
    }
    applyCourses(apiCourses);
    coursesUpdatedAt.value = data.updated_at || '';
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : '课程加载失败';
    courses.value = [];
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  portfolioStore.loadPortfolio();
  fetchCourses();
});

const filteredCourses = computed(() => {
  if (selectedCategory.value === 'all') return courses.value;
  return courses.value.filter((c) => c.category === selectedCategory.value);
});

const recommendedCourses = computed(() => courses.value.filter((c) => c.recommended));

const getLevelColor = (level: string) => {
  switch (level) {
    case '入门':
      return 'bg-emerald-100 text-emerald-700';
    case '进阶':
      return 'bg-blue-100 text-blue-700';
    case '高阶':
      return 'bg-purple-100 text-purple-700';
    default:
      return 'bg-slate-100 text-slate-700';
  }
};

const startCourse = (courseId: number) => {
  router.push(`/course/${courseId}`);
};

const openPremiumService = (view: PremiumView) => {
  activePremiumView.value = view;
};

const closePremiumService = () => {
  activePremiumView.value = null;
};
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <RiskBanner />

    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
        <button @click="router.push('/')" class="p-2 hover:bg-slate-100 rounded-lg transition-colors">
          <HomeIcon class="w-5 h-5 text-slate-600" />
        </button>
        <div>
          <h1 class="text-xl font-bold text-slate-900">场景化投教</h1>
          <p v-if="coursesUpdatedAt" class="text-xs text-slate-400">课程库更新于 {{ coursesUpdatedAt }}</p>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div v-if="loadError" class="bg-red-50 border border-red-200 rounded-xl p-4 mb-8 flex items-center justify-between">
        <span class="text-red-700 text-sm">数据获取失败：{{ loadError }}</span>
        <button
          @click="fetchCourses"
          class="flex items-center gap-1 px-3 py-1 text-xs bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
        >
          <RefreshIcon class="w-3 h-3" />
          重试
        </button>
      </div>

      <div v-if="isLoading" class="flex flex-col items-center justify-center py-20 text-slate-500">
        <div class="w-10 h-10 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4" />
        正在从服务器加载课程...
      </div>

      <template v-else-if="courses.length > 0">
        <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-8">
          <div class="flex items-center gap-3">
            <GraduationCapIcon class="w-6 h-6 text-emerald-600" />
            <p class="text-sm text-emerald-800">
              课程数据来自服务端知识库，后台可随时更新。根据您的持仓品类，为您推荐个性化学习内容。
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
          <p class="text-sm text-slate-500 mt-3">基于您的持仓，我们为您推荐了以下学习内容</p>
        </div>

        <div class="mb-8">
          <h2 class="text-lg font-semibold text-slate-900 mb-4">为您推荐</h2>
          <div
            v-if="recommendedCourses.length === 0"
            class="text-sm text-slate-500 py-8 text-center bg-white rounded-xl border border-slate-200"
          >
            暂无推荐课程，请查看下方全部课程
          </div>
          <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div
              v-for="course in recommendedCourses"
              :key="course.id"
              @click="startCourse(course.id)"
              class="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-lg hover:border-indigo-200 transition-all cursor-pointer group"
            >
              <div class="flex items-start justify-between mb-3">
                <div class="px-2 py-1 rounded text-xs font-medium" :class="getLevelColor(course.level)">
                  {{ course.level }}
                </div>
                <CheckCircleIcon v-if="completedCourses.has(course.id)" class="w-5 h-5 text-emerald-500" />
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
                <span v-if="course.section_count">{{ course.section_count }} 章节</span>
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
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-slate-900">全部课程</h2>
            <span class="text-xs text-slate-400">共 {{ courses.length }} 门</span>
          </div>
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
            <div v-if="filteredCourses.length === 0" class="text-sm text-slate-500 py-8 text-center">
              该分类下暂无课程
            </div>
            <div
              v-for="course in filteredCourses"
              :key="course.id"
              @click="startCourse(course.id)"
              class="flex items-center gap-4 p-4 bg-slate-50 rounded-xl hover:bg-indigo-50/50 hover:border-indigo-100 border border-transparent transition-all cursor-pointer group"
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
              <div class="flex-1 min-w-0">
                <h4 class="font-medium text-slate-900 group-hover:text-indigo-600 transition-colors truncate">
                  {{ course.title }}
                </h4>
                <p class="text-sm text-slate-500 line-clamp-1">{{ course.description }}</p>
              </div>
              <div class="flex items-center gap-3 flex-shrink-0">
                <span class="text-xs text-slate-400 hidden sm:inline">{{ course.duration }}</span>
                <span class="px-2 py-1 rounded text-xs font-medium" :class="getLevelColor(course.level)">
                  {{ course.level }}
                </span>
                <CheckCircleIcon v-if="completedCourses.has(course.id)" class="w-5 h-5 text-emerald-500" />
                <button class="px-3 py-1 bg-indigo-100 text-indigo-600 rounded-lg text-xs font-medium hover:bg-indigo-200 transition-colors">
                  学习
                </button>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div class="bg-gradient-to-br from-indigo-600 via-indigo-700 to-purple-700 rounded-2xl p-6 text-white mt-8 shadow-xl shadow-indigo-500/20">
        <div class="flex items-center gap-2 mb-2">
          <LockIcon class="w-5 h-5" />
          <h2 class="text-lg font-semibold">解锁高级功能</h2>
        </div>
        <p class="text-sm text-indigo-100 mb-5">点击查看完整示例内容，体验增值服务</p>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            v-for="service in premiumServices"
            :key="service.id"
            class="bg-white/10 rounded-xl p-5 backdrop-blur border border-white/10 hover:bg-white/20 hover:border-white/20 transition-all"
          >
            <div class="flex items-center gap-2 mb-2">
              <component :is="service.icon" class="w-5 h-5" />
              <h3 class="font-medium">{{ service.title }}</h3>
            </div>
            <p class="text-2xl font-bold mb-3">{{ service.price }}</p>
            <ul class="space-y-1.5 text-sm text-indigo-100 mb-5">
              <li v-for="feature in service.features" :key="feature" class="flex items-center gap-2">
                <CheckCircleIcon class="w-3.5 h-3.5 flex-shrink-0 text-emerald-300" />
                {{ feature }}
              </li>
            </ul>
            <button
              @click="openPremiumService(service.id)"
              class="w-full py-2.5 bg-white text-indigo-700 rounded-xl font-medium hover:bg-indigo-50 transition-colors flex items-center justify-center gap-1 shadow-sm"
            >
              查看示例
              <ArrowRightIcon class="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </main>

    <EducationPremiumModals :active-view="activePremiumView" @close="closePremiumService" />
    <EducationChatPanel />

    <footer class="bg-white border-t border-slate-200 py-6">
      <div class="max-w-7xl mx-auto px-4 text-center">
        <p class="text-sm text-slate-500">
          历史收益不代表未来表现 · AI无法预测市场 · 本内容仅为投资参考，不构成任何投资建议
        </p>
      </div>
    </footer>
  </div>
</template>
