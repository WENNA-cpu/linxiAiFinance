<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
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

const router = useRouter();

const selectedAsset = ref('000001');
const timeRange = ref('1y');

const assets = [
  { code: '000001', name: '平安银行', type: 'stock' },
  { code: '000002', name: '万科A', type: 'stock' },
  { code: '510300', name: '沪深300ETF', type: 'fund' },
];

const cycleAnalysis = ref({
  currentPhase: '合理区间',
  phaseColor: 'blue',
  valuation: {
    pe: 8.5,
    pb: 0.85,
    pePercentile: 45,
    pbPercentile: 38,
  },
  recommendation: '持有观望',
  confidence: 78,
  lstmForecast: {
    trend: '震荡',
    confidence: 72,
    support: 12.5,
    resistance: 15.8,
  },
});

const chartData = ref({
  dates: ['2023-01', '2023-03', '2023-05', '2023-07', '2023-09', '2023-11', '2024-01'],
  prices: [13.2, 14.5, 13.8, 15.2, 14.1, 13.5, 14.2],
  pe: [7.8, 8.5, 8.1, 8.9, 8.3, 7.9, 8.5],
  upper: [15.5, 16.8, 16.2, 17.5, 16.5, 15.8, 16.5],
  lower: [11.2, 12.5, 11.8, 13.2, 12.1, 11.5, 12.2],
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
            基于LSTM深度学习模型分析历史估值数据，判断资产所处周期阶段。仅提供状态分析，不构成买卖建议。
          </p>
        </div>
      </div>

      <div class="flex flex-wrap gap-4 mb-8">
        <select
          v-model="selectedAsset"
          class="px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option v-for="asset in assets" :key="asset.code" :value="asset.code">
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

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
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

            <div class="h-64 bg-slate-50 rounded-lg mb-6 flex items-center justify-center">
              <div class="text-center">
                <div class="w-16 h-16 bg-slate-200 rounded-full mx-auto mb-4 flex items-center justify-center">
                  <TrendingUpIcon class="w-8 h-8 text-slate-400" />
                </div>
                <p class="text-slate-500">估值曲线图 (ECharts)</p>
                <p class="text-xs text-slate-400 mt-1">显示PE/PB历史走势与LSTM预测区间</p>
              </div>
            </div>

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
              <h2 class="text-lg font-semibold text-slate-900">LSTM模型预测</h2>
            </div>
            <div class="grid grid-cols-3 gap-4">
              <div class="p-4 bg-purple-50 rounded-lg text-center">
                <p class="text-sm text-slate-500 mb-1">趋势预测</p>
                <p class="text-xl font-bold text-purple-600">{{ cycleAnalysis.lstmForecast.trend }}</p>
                <p class="text-xs text-slate-500">置信度 {{ cycleAnalysis.lstmForecast.confidence }}%</p>
              </div>
              <div class="p-4 bg-emerald-50 rounded-lg text-center">
                <p class="text-sm text-slate-500 mb-1">支撑位</p>
                <p class="text-xl font-bold text-emerald-600">{{ cycleAnalysis.lstmForecast.support }}</p>
                <p class="text-xs text-slate-500">LSTM预测下限</p>
              </div>
              <div class="p-4 bg-red-50 rounded-lg text-center">
                <p class="text-sm text-slate-500 mb-1">阻力位</p>
                <p class="text-xl font-bold text-red-600">{{ cycleAnalysis.lstmForecast.resistance }}</p>
                <p class="text-xs text-slate-500">LSTM预测上限</p>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">周期判定</h2>
            <div class="space-y-4">
              <div class="flex items-center gap-3 p-3 bg-emerald-50 rounded-lg border border-emerald-200">
                <div class="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
                  <TrendingDownIcon class="w-4 h-4 text-emerald-600" />
                </div>
                <div class="flex-1">
                  <p class="font-medium text-emerald-900">低估区间</p>
                  <p class="text-xs text-emerald-700">PE/PB处于历史低位30%以下</p>
                </div>
              </div>
              <div class="flex items-center gap-3 p-3 bg-blue-50 rounded-lg border-2 border-blue-500">
                <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <MinusIcon class="w-4 h-4 text-blue-600" />
                </div>
                <div class="flex-1">
                  <p class="font-medium text-blue-900">合理区间</p>
                  <p class="text-xs text-blue-700">PE/PB处于历史30%-70%分位</p>
                </div>
                <div class="px-2 py-1 bg-blue-600 text-white text-xs rounded">当前</div>
              </div>
              <div class="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                <div class="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                  <TrendingUpIcon class="w-4 h-4 text-red-600" />
                </div>
                <div class="flex-1">
                  <p class="font-medium text-red-900">高估区间</p>
                  <p class="text-xs text-red-700">PE/PB处于历史高位70%以上</p>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">建议区间</h2>
            <div class="p-4 bg-amber-50 rounded-lg">
              <div class="flex items-center gap-2 mb-2">
                <AlertTriangleIcon class="w-5 h-5 text-amber-600" />
                <span class="font-medium text-amber-900">{{ cycleAnalysis.recommendation }}</span>
              </div>
              <p class="text-sm text-amber-800">
                当前估值处于合理区间，建议持有观望。如需调整仓位，建议小幅操作。
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
                <span class="text-slate-600">数据区间: 2021-01 至 2024-01</span>
              </div>
              <div class="flex items-center gap-2">
                <DatabaseIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">数据来源: Tushare历史估值</span>
              </div>
              <div class="flex items-center gap-2">
                <CpuIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">模型: LSTM时序预测</span>
              </div>
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
  </div>
</template>
