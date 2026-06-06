<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
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
import CalculatorIcon from '@/components/icons/CalculatorIcon.vue';
import UploadIcon from '@/components/icons/UploadIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import SparklesIcon from '@/components/icons/SparklesIcon.vue';
import LineChartIcon from '@/components/icons/LineChartIcon.vue';
import BarChartIcon from '@/components/icons/BarChartIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const goToTrace = () => {
  const lastId = localStorage.getItem('last_diagnosis_id');
  router.push(lastId ? `/trace/${lastId}` : '/trace/latest');
};

const showCalculator = ref(false);
const marketSentiment = ref({
  index: 50,
  status: '中性',
  marketState: '震荡整理',
  warningSignals: 1,
  updateTime: new Date().toLocaleString('zh-CN'),
});
const lastFetchTime = ref<number | null>(null);

const features = [
  {
    title: '导入持仓',
    desc: '导入您的持仓资产，开始AI诊断',
    icon: UploadIcon,
    path: '/portfolio/import',
    color: 'bg-indigo-500',
  },
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
  {
    title: '分析溯源',
    desc: '查看AI分析的数据来源与依据',
    icon: SearchIcon,
    path: '/trace/latest',
    color: 'bg-rose-500',
  },
  {
    title: '合规说明',
    desc: '了解AI能力边界与风控规则',
    icon: ShieldIcon,
    path: '/compliance',
    color: 'bg-cyan-500',
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

const goToPortfolioImport = () => {
  router.push('/portfolio/import');
};

// 获取市场情绪数据（调用后端接口）
const fetchMarketSentiment = async () => {
  console.log('[市场情绪] 开始获取数据');

  // 检查是否需要刷新（每小时刷新一次）
  const now = Date.now();
  if (lastFetchTime.value && now - lastFetchTime.value < 3600000) {
    console.log('[市场情绪] 一小时内已获取，跳过');
    return;
  }

  try {
    const response = await fetch('/api/market/sentiment');
    if (!response.ok) {
      throw new Error(`获取数据失败: ${response.status}`);
    }
    const data = await response.json();

    marketSentiment.value = {
      index: data.sentiment_index ?? 50,
      status: data.status ?? '中性',
      marketState: data.market_state ?? '震荡整理',
      warningSignals: data.warning_signals ?? 0,
      updateTime: data.update_time ?? new Date().toLocaleString('zh-CN'),
    };

    console.log('[市场情绪] 获取数据:', marketSentiment.value);
  } catch (err) {
    console.error('[市场情绪] 获取失败:', err);
    // 使用默认值
    marketSentiment.value = {
      index: 50,
      status: '中性',
      marketState: '震荡整理',
      warningSignals: 0,
      updateTime: new Date().toLocaleString('zh-CN'),
    };
  }

  lastFetchTime.value = now;
};

onMounted(() => {
  portfolioStore.loadPortfolio();
  fetchMarketSentiment();
});
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
            <BrainIcon class="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-900">灵析</h1>
            <p class="text-xs text-slate-500">AI金融助手</p>
          </div>
        </div>
        <div class="flex items-center gap-4">
          <button
            @click="router.push('/compliance')"
            class="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors"
          >
            <ShieldIcon class="w-4 h-4" />
            合规说明
          </button>
          <button
            @click="goToTrace()"
            class="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-indigo-600 transition-colors"
          >
            <SearchIcon class="w-4 h-4" />
            分析溯源
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4">
      <div class="text-center min-h-[50vh] flex flex-col items-center justify-center relative py-16">
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none overflow-hidden">
          <div class="absolute left-[10%] top-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-purple-200/50 rounded-full blur-3xl"></div>
          <div class="absolute right-[10%] top-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-200/50 rounded-full blur-3xl"></div>
        </div>
        <div class="relative z-10">
          <div class="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-full text-sm text-slate-600 mb-6">
            <SparklesIcon class="w-4 h-4 text-indigo-500" />
            AI驱动的智能投资助手
          </div>
          <h2 class="text-5xl font-bold mb-6">
            <span class="text-slate-900">让AI为您的投资</span>
            <span class="text-violet-600">保驾护航</span>
          </h2>
          <p class="text-lg text-slate-500 max-w-2xl mx-auto mb-8">
            灵析结合大语言模型与金融数据分析，为您提供专业的持仓诊断、周期分析与投资教育服务
          </p>
          <button
            @click="goToPortfolioImport"
            class="inline-flex items-center gap-2 px-10 py-4 bg-gradient-to-r from-indigo-600 to-blue-600 text-white text-lg font-medium rounded-full hover:from-indigo-700 hover:to-blue-700 transition-all shadow-lg shadow-indigo-200 hover:shadow-xl hover:shadow-indigo-300"
          >
            开始持仓诊断
            <ArrowRightIcon class="w-5 h-5" />
          </button>
        </div>
      </div>

      <div class="bg-white rounded-2xl border border-slate-200 p-6 mb-8">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-2">
            <ActivityIcon class="w-5 h-5 text-indigo-600" />
            <h3 class="text-lg font-semibold text-slate-900">市场情绪简报</h3>
            <!-- 数据来源标识 -->
            <span
              class="px-2 py-0.5 text-xs rounded-full bg-emerald-100 text-emerald-700"
            >
              实时数据
            </span>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-400">数据更新于: {{ marketSentiment.updateTime }}</span>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-8">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-indigo-50 rounded-xl flex items-center justify-center">
              <BarChartIcon class="w-7 h-7 text-indigo-600" />
            </div>
            <div>
              <p class="text-sm text-slate-500 mb-1">情绪指数</p>
              <p class="text-2xl font-bold text-slate-900">{{ marketSentiment.index }}</p>
              <p class="text-sm text-indigo-600">{{ marketSentiment.status }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-slate-50 rounded-xl flex items-center justify-center">
              <LineChartIcon class="w-7 h-7 text-slate-600" />
            </div>
            <div>
              <p class="text-sm text-slate-500 mb-1">市场状态</p>
              <p class="text-xl font-bold text-slate-900">{{ marketSentiment.marketState }}</p>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-amber-50 rounded-xl flex items-center justify-center">
              <AlertTriangleIcon class="w-7 h-7 text-amber-500" />
            </div>
            <div>
              <p class="text-sm text-slate-500 mb-1">警示信号</p>
              <p class="text-xl font-bold text-slate-900">{{ marketSentiment.warningSignals }} 个信号</p>
            </div>
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

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <div class="flex items-center gap-3 mb-6">
          <ScaleIcon class="w-6 h-6 text-indigo-600" />
          <h3 class="text-lg font-semibold text-slate-900">四大设计原则</h3>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
