<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import BrainIcon from '@/components/icons/BrainIcon.vue';
import TrendingUpIcon from '@/components/icons/TrendingUpIcon.vue';
import TrendingDownIcon from '@/components/icons/TrendingDownIcon.vue';
import MinusIcon from '@/components/icons/MinusIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';
import CpuIcon from '@/components/icons/CpuIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import UploadIcon from '@/components/icons/UploadIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const selectedAsset = ref('');
const timeRange = ref('3y');
const isLoading = ref(false);
const error = ref('');
const chartContainer = ref<HTMLDivElement | null>(null);
let chartInstance: any = null;

// 从store获取持仓列表
const portfolioAssets = computed(() => {
  return portfolioStore.portfolio.assets.map(asset => ({
    code: asset.code,
    name: asset.name,
    type: asset.type,
  }));
});

// 是否有持仓
const hasAssets = computed(() => portfolioAssets.value.length > 0);

// 周期分析数据
interface CycleData {
  ts_code: string;
  name: string;
  current_pe: number;
  current_pb: number;
  pe_30_percentile: number;
  pe_70_percentile: number;
  pb_30_percentile: number;
  pb_70_percentile: number;
  interval: string;
  suggestion: string;
  pe_history: Array<{ date: string; value: number }>;
  pb_history: Array<{ date: string; value: number }>;
  is_mock?: boolean;
}

const cycleData = ref<CycleData | null>(null);

// 计算PE分位数
const pePercentile = computed(() => {
  if (!cycleData.value) return 0;
  const { current_pe, pe_30_percentile, pe_70_percentile } = cycleData.value;
  if (current_pe <= pe_30_percentile) return 15;
  if (current_pe >= pe_70_percentile) return 85;
  const range = pe_70_percentile - pe_30_percentile;
  const position = current_pe - pe_30_percentile;
  return Math.round(30 + (position / range) * 40);
});

// 计算PB分位数
const pbPercentile = computed(() => {
  if (!cycleData.value) return 0;
  const { current_pb, pb_30_percentile, pb_70_percentile } = cycleData.value;
  if (current_pb <= pb_30_percentile) return 15;
  if (current_pb >= pb_70_percentile) return 85;
  const range = pb_70_percentile - pb_30_percentile;
  const position = current_pb - pb_30_percentile;
  return Math.round(30 + (position / range) * 40);
});

// 周期分析展示数据
const cycleAnalysis = computed(() => {
  if (!cycleData.value) {
    return {
      currentPhase: '加载中',
      phaseColor: 'blue',
      valuation: { pe: 0, pb: 0, pePercentile: 0, pbPercentile: 0 },
      recommendation: '加载中',
    };
  }
  return {
    currentPhase: cycleData.value.interval,
    phaseColor: getPhaseColor(cycleData.value.interval),
    valuation: {
      pe: cycleData.value.current_pe,
      pb: cycleData.value.current_pb,
      pePercentile: pePercentile.value,
      pbPercentile: pbPercentile.value,
    },
    recommendation: cycleData.value.suggestion,
  };
});

const getPhaseColor = (phase: string) => {
  if (phase.includes('低估')) return 'emerald';
  if (phase.includes('高估')) return 'red';
  return 'blue';
};

const getPhaseBg = (phase: string) => {
  const color = getPhaseColor(phase);
  return `bg-${color}-50 border-${color}-200`;
};

const getPhaseText = (phase: string) => {
  const color = getPhaseColor(phase);
  return `text-${color}-600`;
};

// 时间范围 → 回溯天数（日历日）
const LOOKBACK_DAYS: Record<string, number> = {
  '1m': 30,
  '3m': 90,
  '6m': 180,
  '1y': 365,
  '3y': 1095,
};

const lookbackDays = computed(() => LOOKBACK_DAYS[timeRange.value] ?? 365);

const timeRangeLabel = computed(() => {
  const map: Record<string, string> = {
    '1m': '近1个月',
    '3m': '近3个月',
    '6m': '近6个月',
    '1y': '近1年',
    '3y': '近3年',
  };
  return map[timeRange.value] ?? '近1年';
});

// 初始化 ECharts 图表
const initChart = async () => {
  if (!chartContainer.value || !cycleData.value) return;

  const echarts = await import('echarts');

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value);

  const peHistory = cycleData.value.pe_history;
  const pbHistory = cycleData.value.pb_history;

  if (peHistory.length === 0) return;

  // 计算趋势线（简单线性回归）
  const n = peHistory.length;
  const x = Array.from({ length: n }, (_, i) => i);
  const y = peHistory.map(item => item.value);
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((acc, xi, i) => acc + xi * y[i], 0);
  const sumXX = x.reduce((acc, xi) => acc + xi * xi, 0);
  const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;

  const trendLine = x.map(xi => slope * xi + intercept);
  const upperBand = trendLine.map(v => v * 1.1);
  const lowerBand = trendLine.map(v => v * 0.9);

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['PE历史', 'PB历史', '趋势线', '上轨', '下轨'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: peHistory.map(item => item.date.slice(5)),
      axisLabel: { rotate: 45, fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      name: '估值',
      splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
    },
    series: [
      {
        name: 'PE历史',
        type: 'line',
        data: peHistory.map(item => item.value),
        smooth: true,
        lineStyle: { color: '#6366f1', width: 2 },
        itemStyle: { color: '#6366f1' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
              { offset: 1, color: 'rgba(99, 102, 241, 0.05)' },
            ],
          },
        },
      },
      {
        name: 'PB历史',
        type: 'line',
        data: pbHistory.map(item => item.value),
        smooth: true,
        lineStyle: { color: '#22c55e', width: 2 },
        itemStyle: { color: '#22c55e' },
      },
      {
        name: '趋势线',
        type: 'line',
        data: trendLine,
        smooth: true,
        lineStyle: { color: '#a855f7', width: 2, type: 'dashed' },
        symbol: 'none',
      },
      {
        name: '上轨',
        type: 'line',
        data: upperBand,
        smooth: true,
        lineStyle: { color: '#a855f7', width: 1, type: 'dotted' },
        symbol: 'none',
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(168, 85, 247, 0.1)' },
              { offset: 1, color: 'rgba(168, 85, 247, 0.02)' },
            ],
          },
        },
      },
      {
        name: '下轨',
        type: 'line',
        data: lowerBand,
        smooth: true,
        lineStyle: { color: '#a855f7', width: 1, type: 'dotted' },
        symbol: 'none',
      },
    ],
  };

  chartInstance.setOption(option);
};

const normalizeTsCode = (code: string) => {
  if (code.includes('.')) return code;
  return code.startsWith('6') ? `${code}.SH` : `${code}.SZ`;
};

// 获取周期分析数据
const fetchCycleAnalysis = async () => {
  if (!selectedAsset.value) return;

  isLoading.value = true;
  error.value = '';

  try {
    const tsCode = normalizeTsCode(selectedAsset.value);
    const response = await fetch('/api/cycle/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        asset_code: tsCode,
        time_range: timeRange.value,
        lookback_days: lookbackDays.value,
      }),
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `获取周期分析失败 (${response.status})`);
    }

    cycleData.value = await response.json();
    setTimeout(() => initChart(), 100);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取周期分析数据失败';
    cycleData.value = null;
  } finally {
    isLoading.value = false;
  }
};

// 监听资产变化
watch(selectedAsset, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal) {
    fetchCycleAnalysis();
  }
});

// 监听时间范围变化
watch(timeRange, () => {
  fetchCycleAnalysis();
});

onMounted(() => {
  // 加载持仓数据
  portfolioStore.loadPortfolio();

  // 如果有持仓，默认选中第一个
  if (hasAssets.value && portfolioAssets.value.length > 0) {
    selectedAsset.value = portfolioAssets.value[0].code;
    fetchCycleAnalysis();
  }

  window.addEventListener('resize', () => {
    chartInstance?.resize();
  });
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
        <h1 class="text-xl font-bold text-slate-900">资产周期分析</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-8">
        <div class="flex items-center gap-3">
          <BrainIcon class="w-6 h-6 text-indigo-600" />
          <p class="text-sm text-indigo-800">
            基于历史估值数据分析资产所处周期阶段。仅提供状态分析，不构成买卖建议。
          </p>
        </div>
      </div>

      <!-- 无持仓状态 -->
      <div v-if="!hasAssets" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <UploadIcon class="w-8 h-8 text-slate-400" />
        </div>
        <h3 class="text-lg font-semibold text-slate-900 mb-2">暂无持仓数据</h3>
        <p class="text-slate-500 mb-6">请前往「持仓导入」页面导入资产，即可查看资产周期分析</p>
        <button
          @click="router.push('/portfolio/import')"
          class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          前往导入持仓
        </button>
      </div>

      <!-- 有持仓状态 -->
      <template v-else>
        <div class="flex flex-wrap gap-4 mb-8">
          <select
            v-model="selectedAsset"
            class="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option v-for="asset in portfolioAssets" :key="asset.code" :value="asset.code">
              {{ asset.name }} ({{ asset.code }})
            </option>
          </select>
          <div class="flex gap-2">
            <button
              v-for="range in ['1m', '3m', '6m', '1y', '3y']"
              :key="range"
              @click="timeRange = range"
              class="px-4 py-2 rounded-lg font-medium transition-colors"
              :class="timeRange === range ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-50'"
            >
              {{ range === '1m' ? '1个月' : range === '3m' ? '3个月' : range === '6m' ? '6个月' : range === '1y' ? '1年' : '3年' }}
            </button>
          </div>
        </div>

        <!-- 加载状态 -->
        <div v-if="isLoading" class="flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <span class="ml-3 text-slate-600">加载估值数据...</span>
        </div>

        <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
          <p class="text-red-800 font-medium mb-2">加载失败</p>
          <p class="text-sm text-red-600">{{ error }}</p>
          <button
            @click="fetchCycleAnalysis"
            class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm"
          >
            重试
          </button>
        </div>

        <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div class="lg:col-span-2 space-y-6">
            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center justify-between mb-6">
                <h2 class="text-lg font-semibold text-slate-900">估值周期分析</h2>
                <div
                  class="px-4 py-2 rounded-lg border font-medium"
                  :class="getPhaseBg(cycleAnalysis.currentPhase)"
                >
                  <span :class="getPhaseText(cycleAnalysis.currentPhase)">
                    当前阶段: {{ cycleAnalysis.currentPhase }}
                  </span>
                </div>
              </div>

              <!-- ECharts 图表容器 -->
              <div ref="chartContainer" class="h-80 w-full mb-6"></div>

              <div class="grid grid-cols-2 gap-4">
                <div class="p-4 bg-slate-50 rounded-lg">
                  <p class="text-sm text-slate-500 mb-1">市盈率 (PE)</p>
                  <p class="text-2xl font-bold text-slate-900">{{ cycleAnalysis.valuation.pe }}</p>
                  <p class="text-xs text-slate-500">历史分位: {{ cycleAnalysis.valuation.pePercentile }}%</p>
                  <div class="mt-2 h-2 bg-slate-200 rounded-full">
                    <div
                      class="h-full bg-indigo-500 rounded-full"
                      :style="{ width: `${cycleAnalysis.valuation.pePercentile}%` }"
                    ></div>
                  </div>
                </div>
                <div class="p-4 bg-slate-50 rounded-lg">
                  <p class="text-sm text-slate-500 mb-1">市净率 (PB)</p>
                  <p class="text-2xl font-bold text-slate-900">{{ cycleAnalysis.valuation.pb }}</p>
                  <p class="text-xs text-slate-500">历史分位: {{ cycleAnalysis.valuation.pbPercentile }}%</p>
                  <div class="mt-2 h-2 bg-slate-200 rounded-full">
                    <div
                      class="h-full bg-indigo-500 rounded-full"
                      :style="{ width: `${cycleAnalysis.valuation.pbPercentile}%` }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <CpuIcon class="w-5 h-5 text-purple-600" />
                <h2 class="text-lg font-semibold text-slate-900">估值分析</h2>
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div class="p-4 bg-purple-50 rounded-lg text-center">
                  <p class="text-sm text-slate-500 mb-1">当前PE</p>
                  <p class="text-xl font-bold text-purple-600">{{ cycleAnalysis.valuation.pe }}</p>
                  <p class="text-xs text-slate-500">历史分位 {{ cycleAnalysis.valuation.pePercentile }}%</p>
                </div>
                <div class="p-4 bg-indigo-50 rounded-lg text-center">
                  <p class="text-sm text-slate-500 mb-1">当前PB</p>
                  <p class="text-xl font-bold text-indigo-600">{{ cycleAnalysis.valuation.pb }}</p>
                  <p class="text-xs text-slate-500">历史分位 {{ cycleAnalysis.valuation.pbPercentile }}%</p>
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-6">
            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <h2 class="text-lg font-semibold text-slate-900 mb-4">周期判定</h2>
              <div class="space-y-4">
                <div
                  class="flex items-center gap-3 p-3 rounded-lg border"
                  :class="cycleAnalysis.currentPhase === '低估区间' ? 'bg-emerald-50 border-2 border-emerald-500' : 'bg-emerald-50 border-emerald-200'"
                >
                  <div class="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
                    <TrendingDownIcon class="w-4 h-4 text-emerald-600" />
                  </div>
                  <div class="flex-1">
                    <p class="font-medium text-emerald-900">低估区间</p>
                    <p class="text-xs text-emerald-700">PE/PB处于历史低位30%以下</p>
                  </div>
                  <div v-if="cycleAnalysis.currentPhase === '低估区间'" class="px-2 py-1 bg-emerald-600 text-white text-xs rounded">当前</div>
                </div>
                <div
                  class="flex items-center gap-3 p-3 rounded-lg border"
                  :class="cycleAnalysis.currentPhase === '合理区间' ? 'bg-blue-50 border-2 border-blue-500' : 'bg-blue-50 border-blue-200'"
                >
                  <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <MinusIcon class="w-4 h-4 text-blue-600" />
                  </div>
                  <div class="flex-1">
                    <p class="font-medium text-blue-900">合理区间</p>
                    <p class="text-xs text-blue-700">PE/PB处于历史30%-70%分位</p>
                  </div>
                  <div v-if="cycleAnalysis.currentPhase === '合理区间'" class="px-2 py-1 bg-blue-600 text-white text-xs rounded">当前</div>
                </div>
                <div
                  class="flex items-center gap-3 p-3 rounded-lg border"
                  :class="cycleAnalysis.currentPhase === '高估区间' ? 'bg-red-50 border-2 border-red-500' : 'bg-red-50 border-red-200'"
                >
                  <div class="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                    <TrendingUpIcon class="w-4 h-4 text-red-600" />
                  </div>
                  <div class="flex-1">
                    <p class="font-medium text-red-900">高估区间</p>
                    <p class="text-xs text-red-700">PE/PB处于历史高位70%以上</p>
                  </div>
                  <div v-if="cycleAnalysis.currentPhase === '高估区间'" class="px-2 py-1 bg-red-600 text-white text-xs rounded">当前</div>
                </div>
              </div>
            </div>

            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <h2 class="text-lg font-semibold text-slate-900 mb-4">建议区间</h2>
              <div class="p-4 rounded-lg" :class="getPhaseBg(cycleAnalysis.currentPhase)">
                <div class="flex items-center gap-2 mb-2">
                  <AlertTriangleIcon class="w-5 h-5" :class="getPhaseText(cycleAnalysis.currentPhase)" />
                  <span class="font-medium" :class="getPhaseText(cycleAnalysis.currentPhase)">{{ cycleAnalysis.recommendation }}</span>
                </div>
                <p class="text-sm" :class="getPhaseText(cycleAnalysis.currentPhase)">
                  当前估值处于{{ cycleAnalysis.currentPhase }}，{{ cycleAnalysis.recommendation }}。
                  {{ cycleAnalysis.currentPhase === '低估区间' ? '可考虑逐步建仓或加仓。' : cycleAnalysis.currentPhase === '高估区间' ? '可考虑适当减仓或止盈。' : '建议保持现有仓位，持续关注。' }}
                </p>
              </div>
              <div class="mt-4 text-xs text-slate-500">
                <p>此建议仅基于估值周期分析，不构成买卖指令。</p>
                <p>请结合您的风险偏好和投资目标综合决策。</p>
              </div>
            </div>

            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <h2 class="text-lg font-semibold text-slate-900 mb-4">分析依据</h2>
              <div class="space-y-2 text-sm">
                <div class="flex items-center gap-2">
                  <ClockIcon class="w-4 h-4 text-slate-400" />
                  <span class="text-slate-600">数据区间: {{ timeRangeLabel }}历史数据</span>
                </div>
                <div class="flex items-center gap-2">
                  <DatabaseIcon class="w-4 h-4 text-slate-400" />
                  <span class="text-slate-600">数据来源: Tushare历史估值</span>
                </div>
                <div class="flex items-center gap-2">
                  <CpuIcon class="w-4 h-4 text-slate-400" />
                  <span class="text-slate-600">模型: PE/PB分位数规则判断</span>
                </div>
                <div v-if="cycleData" class="mt-3 pt-3 border-t border-slate-100">
                  <p class="text-xs text-slate-500">PE 30%分位: {{ cycleData.pe_30_percentile }}</p>
                  <p class="text-xs text-slate-500">PE 70%分位: {{ cycleData.pe_70_percentile }}</p>
                  <p class="text-xs text-slate-500">PB 30%分位: {{ cycleData.pb_30_percentile }}</p>
                  <p class="text-xs text-slate-500">PB 70%分位: {{ cycleData.pb_70_percentile }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
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
