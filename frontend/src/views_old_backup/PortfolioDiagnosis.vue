<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import ConfidenceGauge from '@/components/ConfidenceGauge.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import SearchIcon from '@/components/icons/SearchIcon.vue';
import ThumbsUpIcon from '@/components/icons/ThumbsUpIcon.vue';
import ThumbsDownIcon from '@/components/icons/ThumbsDownIcon.vue';
import TrendingUpIcon from '@/components/icons/TrendingUpIcon.vue';
import TrendingDownIcon from '@/components/icons/TrendingDownIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import PieChartIcon from '@/components/icons/PieChartIcon.vue';
import ActivityIcon from '@/components/icons/ActivityIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const showDisclaimer = ref(true);
const showFeedback = ref(false);
const feedbackType = ref<'positive' | 'negative' | null>(null);
const feedbackReason = ref('');

const diagnosisResult = ref({
  requestId: 'REQ-' + Date.now(),
  confidence: 87,
  summary: {
    totalAssets: 5,
    riskAssets: 2,
    opportunityAssets: 3,
    timeSaved: 45,
  },
  analysis: {
    marketTrend: '当前市场处于震荡整理阶段，整体估值处于历史中等偏低水平。',
    sectorRotation: '近期资金从成长股向价值股转移，建议关注低估值蓝筹。',
    riskPoints: [
      '持仓集中度偏高，单只股票占比超过30%',
      '部分资产估值处于历史高位区间',
    ],
    opportunities: [
      '新能源板块估值回调，具备中长期配置价值',
      '消费板块业绩稳健，适合作为底仓配置',
    ],
  },
  dataSource: {
    timeRange: '2024-01-01 至 2024-01-15',
    sources: ['Tushare行情数据', '行业研报数据', '资金流向数据'],
    updateTime: '2024-01-15 15:00',
  },
});

const assetAnalysis = computed(() => {
  return portfolioStore.portfolio.assets.map(asset => ({
    ...asset,
    returnRate: ((asset.currentPrice - asset.costPrice) / asset.costPrice) * 100,
    riskLevel: Math.random() > 0.5 ? 'high' : Math.random() > 0.5 ? 'medium' : 'low',
    trend: Math.random() > 0.5 ? 'up' : 'down',
  }));
});

const submitFeedback = () => {
  showFeedback.value = false;
  feedbackType.value = null;
  feedbackReason.value = '';
};

const viewTraceability = () => {
  router.push(`/trace/${diagnosisResult.value.requestId}`);
};

onMounted(() => {
  portfolioStore.loadPortfolio();
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
        <h1 class="text-xl font-bold text-slate-900">持仓诊断结果</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div v-if="showDisclaimer" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-start gap-4">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600 flex-shrink-0" />
          <div class="flex-1">
            <h3 class="font-semibold text-amber-900 mb-2">AI分析免责声明</h3>
            <p class="text-sm text-amber-800 mb-4">
              本人已知晓AI分析仅供参考，不构成投资建议。历史收益不代表未来表现，AI无法预测市场。所有投资决策由我本人做出。
            </p>
            <button
              @click="showDisclaimer = false"
              class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors"
            >
              我已知晓并同意
            </button>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-lg font-semibold text-slate-900">诊断概览</h2>
              <ConfidenceGauge :value="diagnosisResult.confidence" />
            </div>
            <div class="grid grid-cols-4 gap-4 mb-6">
              <div class="text-center p-4 bg-slate-50 rounded-lg">
                <p class="text-2xl font-bold text-slate-900">{{ diagnosisResult.summary.totalAssets }}</p>
                <p class="text-sm text-slate-500">持仓资产</p>
              </div>
              <div class="text-center p-4 bg-red-50 rounded-lg">
                <p class="text-2xl font-bold text-red-600">{{ diagnosisResult.summary.riskAssets }}</p>
                <p class="text-sm text-slate-500">风险资产</p>
              </div>
              <div class="text-center p-4 bg-emerald-50 rounded-lg">
                <p class="text-2xl font-bold text-emerald-600">{{ diagnosisResult.summary.opportunityAssets }}</p>
                <p class="text-sm text-slate-500">机会资产</p>
              </div>
              <div class="text-center p-4 bg-indigo-50 rounded-lg">
                <p class="text-2xl font-bold text-indigo-600">{{ diagnosisResult.summary.timeSaved }}分钟</p>
                <p class="text-sm text-slate-500">节省时间</p>
              </div>
            </div>
            <div class="p-4 bg-slate-50 rounded-lg">
              <h3 class="font-medium text-slate-900 mb-2">价值摘要</h3>
              <p class="text-sm text-slate-600">
                本次诊断共分析 {{ diagnosisResult.summary.totalAssets }} 只资产，识别出 {{ diagnosisResult.summary.riskAssets }} 个风险点，
                发现 {{ diagnosisResult.summary.opportunityAssets }} 个潜在机会。预计为您节省 {{ diagnosisResult.summary.timeSaved }} 分钟分析时间。
              </p>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">AI分析结论</h2>
            <div class="space-y-4">
              <div class="flex gap-3">
                <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <ActivityIcon class="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <h4 class="font-medium text-slate-900 mb-1">市场趋势</h4>
                  <p class="text-sm text-slate-600">{{ diagnosisResult.analysis.marketTrend }}</p>
                </div>
              </div>
              <div class="flex gap-3">
                <div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <PieChartIcon class="w-4 h-4 text-purple-600" />
                </div>
                <div>
                  <h4 class="font-medium text-slate-900 mb-1">板块轮动</h4>
                  <p class="text-sm text-slate-600">{{ diagnosisResult.analysis.sectorRotation }}</p>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">资产明细分析</h2>
            <div class="space-y-3">
              <div
                v-for="asset in assetAnalysis"
                :key="asset.code"
                class="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-lg flex items-center justify-center"
                    :class="asset.returnRate >= 0 ? 'bg-emerald-100' : 'bg-red-100'"
                  >
                    <component
                      :is="asset.returnRate >= 0 ? TrendingUpIcon : TrendingDownIcon"
                      class="w-5 h-5"
                      :class="asset.returnRate >= 0 ? 'text-emerald-600' : 'text-red-600'"
                    />
                  </div>
                  <div>
                    <p class="font-medium text-slate-900">{{ asset.name }}</p>
                    <p class="text-sm text-slate-500">{{ asset.code }} · {{ asset.type === 'stock' ? '股票' : asset.type === 'fund' ? '基金' : '其他' }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="font-medium" :class="asset.returnRate >= 0 ? 'text-emerald-600' : 'text-red-600'">
                    {{ asset.returnRate >= 0 ? '+' : '' }}{{ asset.returnRate.toFixed(2) }}%
                  </p>
                  <p class="text-sm text-slate-500">{{ asset.marketValue.toLocaleString() }}元</p>
                </div>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <AlertTriangleIcon class="w-5 h-5 text-red-500" />
                <h2 class="text-lg font-semibold text-slate-900">风险点</h2>
              </div>
              <ul class="space-y-2">
                <li
                  v-for="(risk, index) in diagnosisResult.analysis.riskPoints"
                  :key="index"
                  class="flex items-start gap-2 text-sm text-slate-600"
                >
                  <span class="w-5 h-5 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-xs flex-shrink-0">{{ index + 1 }}</span>
                  {{ risk }}
                </li>
              </ul>
            </div>
            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
                <h2 class="text-lg font-semibold text-slate-900">机会点</h2>
              </div>
              <ul class="space-y-2">
                <li
                  v-for="(opp, index) in diagnosisResult.analysis.opportunities"
                  :key="index"
                  class="flex items-start gap-2 text-sm text-slate-600"
                >
                  <span class="w-5 h-5 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center text-xs flex-shrink-0">{{ index + 1 }}</span>
                  {{ opp }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">数据来源</h2>
            <div class="space-y-3 text-sm">
              <div class="flex items-center gap-2">
                <ClockIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">时间区间: {{ diagnosisResult.dataSource.timeRange }}</span>
              </div>
              <div class="flex items-center gap-2">
                <DatabaseIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">数据来源: {{ diagnosisResult.dataSource.sources.join('、') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <ShieldIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">更新时间: {{ diagnosisResult.dataSource.updateTime }}</span>
              </div>
            </div>
            <button
              @click="viewTraceability"
              class="w-full mt-4 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2"
            >
              <SearchIcon class="w-4 h-4" />
              查看分析依据
            </button>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">AI反馈</h2>
            <p class="text-sm text-slate-500 mb-4">这个分析对您有帮助吗？</p>
            <div class="flex gap-3">
              <button
                @click="feedbackType = 'positive'"
                class="flex-1 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                :class="feedbackType === 'positive' ? 'bg-emerald-50 border-emerald-500 text-emerald-600' : ''"
              >
                <ThumbsUpIcon class="w-4 h-4" />
                有帮助
              </button>
              <button
                @click="feedbackType = 'negative'"
                class="flex-1 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                :class="feedbackType === 'negative' ? 'bg-red-50 border-red-500 text-red-600' : ''"
              >
                <ThumbsDownIcon class="w-4 h-4" />
                需改进
              </button>
            </div>
            <div v-if="feedbackType === 'negative'" class="mt-4">
              <textarea
                v-model="feedbackReason"
                placeholder="请告诉我们哪里需要改进..."
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                rows="3"
              ></textarea>
              <button
                @click="submitFeedback"
                class="w-full mt-2 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm"
              >
                提交反馈
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>

    <footer class="bg-white border-t border-slate-200 py-6">
      <div class="max-w-7xl mx-auto px-4 text-center">
        <p class="text-sm text-slate-500">
          本内容仅为投资参考，不构成任何投资建议 · Request ID: {{ diagnosisResult.requestId }}
        </p>
      </div>
    </footer>
  </div>
</template>
