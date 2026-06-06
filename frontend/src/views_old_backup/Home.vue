<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import ChartIcon from '@/components/icons/ChartIcon.vue';
import BrainIcon from '@/components/icons/BrainIcon.vue';
import BookIcon from '@/components/icons/BookIcon.vue';
import SearchIcon from '@/components/icons/SearchIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';
import UsersIcon from '@/components/icons/UsersIcon.vue';
import CpuIcon from '@/components/icons/CpuIcon.vue';
import ScaleIcon from '@/components/icons/ScaleIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import TrendingUpIcon from '@/components/icons/TrendingUpIcon.vue';
import TrendingDownIcon from '@/components/icons/TrendingDownIcon.vue';
import ActivityIcon from '@/components/icons/ActivityIcon.vue';
import ChevronDownIcon from '@/components/icons/ChevronDownIcon.vue';
import ChevronUpIcon from '@/components/icons/ChevronUpIcon.vue';
import CalculatorIcon from '@/components/icons/CalculatorIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const showPrinciples = ref(false);
const showCalculator = ref(false);

const features = [
  {
    title: 'AI持仓诊断',
    desc: '智能分析持仓资产，识别风险点',
    icon: ChartIcon,
    path: '/portfolio/diagnosis',
    color: 'bg-blue-500',
  },
  {
    title: '资产周期分析',
    desc: 'LSTM模型判断估值周期阶段',
    icon: BrainIcon,
    path: '/cycle',
    color: 'bg-purple-500',
  },
  {
    title: '情绪纠偏',
    desc: '实时监测市场情绪，理性引导',
    icon: ActivityIcon,
    path: '/emotion',
    color: 'bg-amber-500',
  },
  {
    title: '场景化投教',
    desc: '基于持仓的个性化理财知识',
    icon: BookIcon,
    path: '/education',
    color: 'bg-emerald-500',
  },
];

const principles = [
  {
    title: '人机协同原则',
    desc: 'AI负责数据处理与信息提炼，用户做最终决策',
    icon: UsersIcon,
  },
  {
    title: 'AI边界管控原则',
    desc: 'AI不做预测、不推荐具体标的、不承诺收益',
    icon: ShieldIcon,
  },
  {
    title: '可解释性原则',
    desc: '所有结论附带数据来源、分析维度、规则校验',
    icon: SearchIcon,
  },
  {
    title: '分层风控原则',
    desc: '数据层、AI输出层、交互层三重防护',
    icon: ScaleIcon,
  },
];

const marketSentiment = {
  index: 42,
  status: '中性偏谨慎',
  trend: 'down',
  updateTime: '2024-01-15 14:30',
};

const complianceStats = [
  { label: '拦截违规内容', value: '2,847', unit: '次', icon: ShieldIcon },
  { label: 'AI幻觉修正率', value: '94.2', unit: '%', icon: CpuIcon },
  { label: '数据泄露事件', value: '0', unit: '起', icon: CheckCircleIcon },
];

const calculator = ref({
  timeSaved: 0,
  holdingDays: 0,
  lossAvoided: 0,
});

const calculateValue = () => {
  calculator.value = {
    timeSaved: 156,
    holdingDays: 23,
    lossAvoided: 8500,
  };
};

onMounted(() => {
  portfolioStore.loadPortfolio();
});
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <RiskBanner />

    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
            <BrainIcon class="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">灵析</h1>
            <p class="text-xs text-slate-500">AI智能投顾助手</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <button
            @click="showCalculator = true"
            class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <CalculatorIcon class="w-4 h-4" />
            价值计算器
          </button>
          <button
            @click="router.push('/compliance')"
            class="flex items-center gap-2 px-4 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 rounded-lg hover:bg-indigo-100 transition-colors"
          >
            <ShieldIcon class="w-4 h-4" />
            合规说明
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 mb-8 text-white">
        <h2 class="text-3xl font-bold mb-4">灵析帮您</h2>
        <div class="flex flex-wrap gap-4 text-lg">
          <span class="flex items-center gap-2">
            <CheckCircleIcon class="w-5 h-5" />
            3分钟读懂持仓
          </span>
          <span class="text-indigo-200">→</span>
          <span class="flex items-center gap-2">
            <AlertTriangleIcon class="w-5 h-5" />
            识别追涨杀跌风险
          </span>
          <span class="text-indigo-200">→</span>
          <span class="flex items-center gap-2">
            <BookIcon class="w-5 h-5" />
            系统化理财学习
          </span>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold text-slate-900">市场情绪简报</h3>
          <span class="text-xs text-slate-500">更新于 {{ marketSentiment.updateTime }}</span>
        </div>
        <div class="flex items-center gap-6">
          <div class="flex items-center gap-3">
            <div
              class="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold"
              :class="marketSentiment.index >= 50 ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'"
            >
              {{ marketSentiment.index }}
            </div>
            <div>
              <p class="text-sm text-slate-500">情绪指数</p>
              <p class="font-medium" :class="marketSentiment.index >= 50 ? 'text-red-600' : 'text-emerald-600'">
                {{ marketSentiment.status }}
              </p>
            </div>
          </div>
          <div class="flex-1 h-2 bg-slate-100 rounded-full">
            <div
              class="h-full rounded-full transition-all"
              :class="marketSentiment.index >= 50 ? 'bg-red-500' : 'bg-emerald-500'"
              :style="{ width: `${marketSentiment.index}%` }"
            ></div>
          </div>
          <div class="flex items-center gap-2">
            <component
              :is="marketSentiment.trend === 'up' ? TrendingUpIcon : TrendingDownIcon"
              class="w-5 h-5"
              :class="marketSentiment.trend === 'up' ? 'text-red-500' : 'text-emerald-500'"
            />
            <span class="text-sm text-slate-600">较昨日{{ marketSentiment.trend === 'up' ? '上升' : '下降' }}</span>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div
          v-for="feature in features"
          :key="feature.title"
          @click="router.push(feature.path)"
          class="bg-white rounded-xl border border-slate-200 p-6 cursor-pointer hover:shadow-lg hover:border-indigo-300 transition-all group"
        >
          <div
            class="w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform"
            :class="feature.color"
          >
            <component :is="feature.icon" class="w-6 h-6 text-white" />
          </div>
          <h3 class="text-lg font-semibold text-slate-900 mb-2">{{ feature.title }}</h3>
          <p class="text-sm text-slate-500">{{ feature.desc }}</p>
          <div class="mt-4 flex items-center text-indigo-600 text-sm font-medium">
            进入功能
            <ArrowRightIcon class="w-4 h-4 ml-1 group-hover:translate-x-1 transition-transform" />
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 mb-8">
        <button
          @click="showPrinciples = !showPrinciples"
          class="w-full px-6 py-4 flex items-center justify-between"
        >
          <div class="flex items-center gap-3">
            <ScaleIcon class="w-6 h-6 text-indigo-600" />
            <h3 class="text-lg font-semibold text-slate-900">四大设计原则</h3>
          </div>
          <component :is="showPrinciples ? ChevronUpIcon : ChevronDownIcon" class="w-5 h-5 text-slate-400" />
        </button>
        <div v-if="showPrinciples" class="px-6 pb-6 border-t border-slate-100">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div
              v-for="principle in principles"
              :key="principle.title"
              class="flex gap-4 p-4 bg-slate-50 rounded-lg"
            >
              <div class="w-10 h-10 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
                <component :is="principle.icon" class="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <h4 class="font-medium text-slate-900 mb-1">{{ principle.title }}</h4>
                <p class="text-sm text-slate-500">{{ principle.desc }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <h3 class="text-lg font-semibold text-slate-900 mb-4">合规价值量化展示</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div
            v-for="stat in complianceStats"
            :key="stat.label"
            class="flex items-center gap-4 p-4 bg-slate-50 rounded-lg"
          >
            <div class="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
              <component :is="stat.icon" class="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <p class="text-sm text-slate-500">{{ stat.label }}</p>
              <p class="text-2xl font-bold text-slate-900">
                {{ stat.value }}<span class="text-sm font-normal text-slate-500">{{ stat.unit }}</span>
              </p>
            </div>
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

    <div
      v-if="showCalculator"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showCalculator = false"
    >
      <div class="bg-white rounded-xl p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-semibold text-slate-900 mb-4">商业价值计算器</h3>
        <div v-if="calculator.timeSaved === 0" class="text-center py-8">
          <p class="text-slate-500 mb-4">点击计算，查看灵析为您带来的价值</p>
          <button
            @click="calculateValue"
            class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            开始计算
          </button>
        </div>
        <div v-else class="space-y-4">
          <div class="p-4 bg-slate-50 rounded-lg">
            <p class="text-sm text-slate-500">预计节省时间</p>
            <p class="text-2xl font-bold text-indigo-600">{{ calculator.timeSaved }}小时/年</p>
          </div>
          <div class="p-4 bg-slate-50 rounded-lg">
            <p class="text-sm text-slate-500">预计持仓时长提升</p>
            <p class="text-2xl font-bold text-emerald-600">{{ calculator.holdingDays }}天</p>
          </div>
          <div class="p-4 bg-slate-50 rounded-lg">
            <p class="text-sm text-slate-500">避免潜在损失</p>
            <p class="text-2xl font-bold text-amber-600">{{ calculator.lossAvoided.toLocaleString() }}元</p>
          </div>
          <button
            @click="showCalculator = false"
            class="w-full py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
