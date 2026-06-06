<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getCourseById } from '@/data/courses';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import BookIcon from '@/components/icons/BookIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import ChevronRightIcon from '@/components/icons/ChevronRightIcon.vue';
import ChevronLeftIcon from '@/components/icons/ChevronLeftIcon.vue';
import CheckIcon from '@/components/icons/CheckIcon.vue';
import ArrowLeftIcon from '@/components/icons/ArrowLeftIcon.vue';

const router = useRouter();
const route = useRoute();

interface CourseSection {
  id: string;
  title: string;
  content: string;
  keyPoints?: string[];
  example?: { title: string; content: string };
}

interface CourseContent {
  id: number;
  title: string;
  category: string;
  categoryName?: string;
  level: string;
  duration: string;
  description: string;
  sections: CourseSection[];
}

const course = ref<CourseContent | null>(null);
const isLoading = ref(true);
const loadError = ref('');
const currentSectionIndex = ref(0);
const completedSections = ref<Set<string>>(new Set());
const isCompleted = ref(false);

// 从localStorage读取学习进度
const loadProgress = () => {
  const courseId = route.params.id as string;
  const saved = localStorage.getItem(`course_progress_${courseId}`);
  if (saved) {
    const progress = JSON.parse(saved);
    completedSections.value = new Set(progress.completedSections || []);
    currentSectionIndex.value = progress.currentSection || 0;
    isCompleted.value = progress.isCompleted || false;
  }
};

// 保存学习进度
const saveProgress = () => {
  const courseId = route.params.id as string;
  localStorage.setItem(`course_progress_${courseId}`, JSON.stringify({
    completedSections: Array.from(completedSections.value),
    currentSection: currentSectionIndex.value,
    isCompleted: isCompleted.value,
  }));
};

const fetchCourse = async (courseId: number) => {
  isLoading.value = true;
  loadError.value = '';
  try {
    const response = await fetch(`/api/education/courses/${courseId}`);
    if (response.ok) {
      course.value = await response.json();
      loadProgress();
      return;
    }
    throw new Error(`API ${response.status}`);
  } catch (err) {
    console.warn('[CourseDetail] API 失败，使用本地数据:', err);
    const local = getCourseById(courseId);
    if (local) {
      course.value = local;
      loadProgress();
    } else {
      loadError.value = '未找到该课程';
      course.value = null;
    }
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  const courseId = parseInt(route.params.id as string);
  if (Number.isNaN(courseId)) {
    loadError.value = '无效的课程 ID';
    isLoading.value = false;
    return;
  }
  fetchCourse(courseId);
});

const currentSection = computed(() => {
  if (!course.value) return null;
  return course.value.sections[currentSectionIndex.value];
});

const progressPercent = computed(() => {
  if (!course.value) return 0;
  return Math.round((completedSections.value.size / course.value.sections.length) * 100);
});

const goToSection = (index: number) => {
  currentSectionIndex.value = index;
  saveProgress();
};

const nextSection = () => {
  if (!course.value) return;
  if (currentSection.value) {
    completedSections.value.add(currentSection.value.id);
  }
  if (currentSectionIndex.value < course.value.sections.length - 1) {
    currentSectionIndex.value++;
  } else {
    isCompleted.value = true;
  }
  saveProgress();
};

const prevSection = () => {
  if (currentSectionIndex.value > 0) {
    currentSectionIndex.value--;
    saveProgress();
  }
};

const markAsCompleted = () => {
  if (!course.value) return;
  course.value.sections.forEach(section => {
    completedSections.value.add(section.id);
  });
  isCompleted.value = true;
  saveProgress();
};

const getLevelColor = (level: string) => {
  switch (level) {
    case '入门': return 'bg-emerald-100 text-emerald-700';
    case '进阶': return 'bg-blue-100 text-blue-700';
    case '高阶': return 'bg-purple-100 text-purple-700';
    default: return 'bg-slate-100 text-slate-700';
  }
};
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <RiskBanner />

    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
        <button @click="router.push('/education')" class="p-2 hover:bg-slate-100 rounded-lg transition-colors">
          <ArrowLeftIcon class="w-5 h-5 text-slate-600" />
        </button>
        <div class="flex-1">
          <h1 class="text-lg font-bold text-slate-900">{{ course?.title || '课程学习' }}</h1>
          <p class="text-xs text-slate-500">{{ course?.categoryName }}</p>
        </div>
        <div class="flex items-center gap-3">
          <div class="text-sm text-slate-600">
            进度: <span class="font-medium text-indigo-600">{{ progressPercent }}%</span>
          </div>
          <div class="w-32 h-2 bg-slate-200 rounded-full">
            <div
              class="h-full bg-indigo-500 rounded-full transition-all"
              :style="{ width: `${progressPercent}%` }"
            ></div>
          </div>
        </div>
      </div>
    </header>

    <main v-if="course" class="max-w-7xl mx-auto px-4 py-8">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- 左侧课程目录 -->
        <div class="lg:col-span-1">
          <div class="bg-white rounded-xl border border-slate-200 p-4 sticky top-24">
            <div class="flex items-center gap-3 mb-4 pb-4 border-b border-slate-100">
              <div class="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                <BookIcon class="w-6 h-6 text-indigo-600" />
              </div>
              <div>
                <h2 class="font-semibold text-slate-900">{{ course.title }}</h2>
                <div class="flex items-center gap-2 mt-1">
                  <span class="px-2 py-0.5 rounded text-xs font-medium" :class="getLevelColor(course.level)">
                    {{ course.level }}
                  </span>
                  <span class="text-xs text-slate-500 flex items-center gap-1">
                    <ClockIcon class="w-3 h-3" />
                    {{ course.duration }}
                  </span>
                </div>
              </div>
            </div>

            <h3 class="text-sm font-medium text-slate-700 mb-3">课程目录</h3>
            <div class="space-y-1">
              <button
                v-for="(section, index) in course.sections"
                :key="section.id"
                @click="goToSection(index)"
                class="w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors"
                :class="currentSectionIndex === index ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-slate-50'"
              >
                <div
                  class="w-6 h-6 rounded-full flex items-center justify-center text-xs"
                  :class="completedSections.has(section.id) ? 'bg-emerald-500 text-white' : currentSectionIndex === index ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600'"
                >
                  <CheckIcon v-if="completedSections.has(section.id)" class="w-3 h-3" />
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <span
                  class="text-sm flex-1"
                  :class="currentSectionIndex === index ? 'text-indigo-700 font-medium' : 'text-slate-600'"
                >
                  {{ section.title.split('、')[1] || section.title }}
                </span>
              </button>
            </div>

            <div v-if="isCompleted" class="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
              <div class="flex items-center gap-2">
                <CheckCircleIcon class="w-5 h-5 text-emerald-600" />
                <span class="text-sm font-medium text-emerald-700">已完成本课程</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧课程内容 -->
        <div class="lg:col-span-2">
          <div v-if="currentSection" class="bg-white rounded-xl border border-slate-200 p-8">
            <h2 class="text-xl font-bold text-slate-900 mb-6">{{ currentSection.title }}</h2>

            <!-- 主要内容 -->
            <div class="prose prose-slate max-w-none">
              <div class="text-slate-700 leading-relaxed whitespace-pre-line mb-8">
                {{ currentSection.content }}
              </div>

              <!-- 要点总结 -->
              <div v-if="currentSection.keyPoints" class="bg-indigo-50 border border-indigo-200 rounded-lg p-6 mb-8">
                <h3 class="font-semibold text-indigo-900 mb-4 flex items-center gap-2">
                  <CheckCircleIcon class="w-5 h-5" />
                  核心要点
                </h3>
                <ul class="space-y-2">
                  <li
                    v-for="point in currentSection.keyPoints"
                    :key="point"
                    class="flex items-start gap-2 text-indigo-800"
                  >
                    <span class="w-1.5 h-1.5 bg-indigo-500 rounded-full mt-2 flex-shrink-0"></span>
                    <span>{{ point }}</span>
                  </li>
                </ul>
              </div>

              <!-- 实际案例 -->
              <div v-if="currentSection.example" class="bg-amber-50 border border-amber-200 rounded-lg p-6 mb-8">
                <h3 class="font-semibold text-amber-900 mb-3 flex items-center gap-2">
                  <BookIcon class="w-5 h-5" />
                  {{ currentSection.example.title }}
                </h3>
                <p class="text-amber-800 leading-relaxed">{{ currentSection.example.content }}</p>
              </div>
            </div>

            <!-- 导航按钮 -->
            <div class="flex items-center justify-between pt-6 border-t border-slate-200">
              <button
                @click="prevSection"
                :disabled="currentSectionIndex === 0"
                class="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
                :class="currentSectionIndex === 0 ? 'text-slate-400 cursor-not-allowed' : 'text-slate-600 hover:bg-slate-100'"
              >
                <ChevronLeftIcon class="w-5 h-5" />
                上一节
              </button>

              <div class="flex items-center gap-3">
                <button
                  v-if="!isCompleted && currentSectionIndex === course.sections.length - 1"
                  @click="markAsCompleted"
                  class="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors flex items-center gap-2"
                >
                  <CheckCircleIcon class="w-4 h-4" />
                  完成课程
                </button>
                <button
                  v-if="currentSectionIndex < course.sections.length - 1"
                  @click="nextSection"
                  class="flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                  下一节
                  <ChevronRightIcon class="w-5 h-5" />
                </button>
                <button
                  v-else-if="isCompleted"
                  @click="router.push('/education')"
                  class="flex items-center gap-2 px-6 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors"
                >
                  返回课程列表
                  <ChevronRightIcon class="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 课程不存在 -->
    <main v-else class="max-w-7xl mx-auto px-4 py-20 text-center">
      <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <BookIcon class="w-8 h-8 text-slate-400" />
      </div>
      <h2 class="text-lg font-semibold text-slate-900 mb-2">课程不存在</h2>
      <p class="text-slate-500 mb-6">该课程可能已被删除或您访问的链接有误</p>
      <button
        @click="router.push('/education')"
        class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
      >
        返回课程列表
      </button>
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
