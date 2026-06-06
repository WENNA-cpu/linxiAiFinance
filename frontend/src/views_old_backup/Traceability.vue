<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import RiskBanner from '@/components/RiskBanner.vue';
import DataLineageChart from '@/components/DataLineageChart.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';
import CpuIcon from '@/components/icons/CpuIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import FileTextIcon from '@/components/icons/FileTextIcon.vue';
import LinkIcon from '@/components/icons/LinkIcon.vue';
import GlobeIcon from '@/components/icons/GlobeIcon.vue';
import LayersIcon from '@/components/icons/LayersIcon.vue';

const router = useRouter();
const route = useRoute();

const requestId = ref(route.params.requestId as string);

const traceData = ref({
  requestId: '',
  timestamp: '',
  dataSources: [
    { name: 'Tushare行情数据', type: 'api', status: 'success', time: '14:00:01' },
    { name: '行业研报数据', type: 'file', status: 'success', time: '14:00:03' },
    { name: '资金流向数据', type: 'api', status: 'success', time: '14:00:05' },
  ],
  analysisDimensions: [
    { name: '技术面分析', model: 'LSTM', confidence: 85 },
    { name: '基本面分析', model: '规则引擎', confidence: 92 },
    { name: '情绪面分析', model: 'LLM', confidence: 78 },
    { name: '风险评估', model: '随机森林', confidence: 88 },
  ],
  ruleChecks: [
    { name: '禁止词汇过滤', status: 'passed', detail: '未检测到违规词汇' },
    { name: '异常数据拦截', status: 'passed', detail: '涨跌幅均在正常范围' },
    { name: '数值校验', status: 'passed', detail: 'PE/PB数值合理' },
    { name: '事实校验', status: 'passed', detail: '数据与源一致' },
  ],
  auditLog: [
    { time: '14:00:00', action: '请求接收', detail: '用户发起诊断请求' },
    { time: '14:00:02', action: '数据获取', detail: '从Tushare获取行情数据' },
    { time: '14:00:04', action: '数据清洗', detail: '完成缺失值处理' },
    { time: '14:00:06', action: '模型分析', detail: 'LSTM模型预测完成' },
    { time: '14:00:08', action: '规则校验', detail: '通过所有风控规则' },
    { time: '14:00:10', action: '结果生成', detail: '诊断报告生成完毕' },
  ],
});

onMounted(() => {
  traceData.value.requestId = requestId.value;
  traceData.value.timestamp = new Date().toLocaleString();
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
        <h1 class="text-xl font-bold text-slate-900">AI分析依据溯源</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-8">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <FileTextIcon class="w-6 h-6 text-indigo-600" />
            <div>
              <p class="text-sm text-indigo-800 font-medium">Request ID: {{ requestId }}</p>
              <p class="text-xs text-indigo-600">生成时间: {{ traceData.timestamp }}</p>
            </div>
          </div>
          <button
            @click="router.back()"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
          >
            <ArrowRightIcon class="w-4 h-4 rotate-180" />
            返回上一页
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center gap-2 mb-4">
            <DatabaseIcon class="w-5 h-5 text-blue-600" />
            <h2 class="text-lg font-semibold text-slate-900">数据来源</h2>
          </div>
          <div class="space-y-3">
            <div
              v-for="source in traceData.dataSources"
              :key="source.name"
              class="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
            >
              <div class="flex items-center gap-3">
                <component
                  :is="source.type === 'api' ? GlobeIcon : FileTextIcon"
                  class="w-4 h-4 text-slate-400"
                />
                <span class="text-sm font-medium text-slate-900">{{ source.name }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-500">{{ source.time }}</span>
                <CheckCircleIcon class="w-4 h-4 text-emerald-500" />
              </div>
            </div>
          </div>
          <div class="mt-4 p-3 bg-blue-50 rounded-lg">
            <div class="flex items-center gap-2 text-sm text-blue-800">
              <ClockIcon class="w-4 h-4" />
              <span>数据时间区间: 2024-01-01 至 2024-01-15</span>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center gap-2 mb-4">
            <CpuIcon class="w-5 h-5 text-purple-600" />
            <h2 class="text-lg font-semibold text-slate-900">分析维度</h2>
          </div>
          <div class="space-y-3">
            <div
              v-for="dim in traceData.analysisDimensions"
              :key="dim.name"
              class="p-3 bg-slate-50 rounded-lg"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-medium text-slate-900">{{ dim.name }}</span>
                <span class="text-xs text-slate-500">{{ dim.model }}</span>
              </div>
              <div class="flex items-center gap-2">
                <div class="flex-1 h-2 bg-slate-200 rounded-full">
                  <div
                    class="h-full bg-purple-500 rounded-full"
                    :style="{ width: `${dim.confidence}%` }"
                  ></div>
                </div>
                <span class="text-xs text-slate-600 w-10">{{ dim.confidence }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center gap-2 mb-4">
            <ShieldIcon class="w-5 h-5 text-emerald-600" />
            <h2 class="text-lg font-semibold text-slate-900">规则校验记录</h2>
          </div>
          <div class="space-y-3">
            <div
              v-for="check in traceData.ruleChecks"
              :key="check.name"
              class="flex items-start gap-3 p-3 bg-slate-50 rounded-lg"
            >
              <CheckCircleIcon class="w-5 h-5 text-emerald-500 flex-shrink-0" />
              <div>
                <p class="text-sm font-medium text-slate-900">{{ check.name }}</p>
                <p class="text-xs text-slate-500">{{ check.detail }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center gap-2 mb-4">
            <LayersIcon class="w-5 h-5 text-amber-600" />
            <h2 class="text-lg font-semibold text-slate-900">审计日志</h2>
          </div>
          <div class="space-y-2">
            <div
              v-for="(log, index) in traceData.auditLog"
              :key="index"
              class="flex items-start gap-3"
            >
              <div class="w-16 text-xs text-slate-400 flex-shrink-0">{{ log.time }}</div>
              <div class="flex-1 pb-3 border-l-2 border-slate-200 pl-3 relative">
                <div class="absolute -left-1.5 top-0 w-3 h-3 bg-indigo-500 rounded-full"></div>
                <p class="text-sm font-medium text-slate-900">{{ log.action }}</p>
                <p class="text-xs text-slate-500">{{ log.detail }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <div class="flex items-center gap-2 mb-4">
          <LinkIcon class="w-5 h-5 text-indigo-600" />
          <h2 class="text-lg font-semibold text-slate-900">数据血缘图</h2>
        </div>
        <p class="text-sm text-slate-500 mb-4">
          展示从原始数据到最终AI输出的完整处理流程
        </p>
        <DataLineageChart />
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
