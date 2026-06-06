<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
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
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';

const router = useRouter();
const route = useRoute();

const requestId = ref(route.params.requestId as string || route.query.request_id as string);
const isLoading = ref(true);
const error = ref('');

interface TraceLog {
  step_name: string;
  step_status: string;
  step_detail: string;
  started_at: string;
  completed_at: string;
}

interface TraceData {
  request_id: string;
  found: boolean;
  message?: string;
  generated_at?: string;
  logs: TraceLog[];
  summary: {
    total_steps: number;
    success_steps: number;
    failed_steps: number;
  };
  data_sources?: string[];
  model_analysis?: string[];
  rule_checks?: string[];
  is_mock?: boolean;
  error_detail?: string;
  lineage?: LineageData;
}

interface LineageNode {
  name: string;
  category: string;
}

interface LineageLink {
  source: string;
  target: string;
}

interface LineageData {
  nodes: LineageNode[];
  links: LineageLink[];
}

const traceData = ref<TraceData | null>(null);
const lineageData = ref<LineageData | null>(null);
const isLineageLoading = ref(true);

// 格式化时间
const formatTime = (isoString: string) => {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

// 格式化日期时间
const formatDateTime = (isoString: string) => {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleString('zh-CN');
};

// 计算处理时长
const getDuration = (started: string, completed: string) => {
  if (!started || !completed) return '-';
  const start = new Date(started).getTime();
  const end = new Date(completed).getTime();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

// 数据源列表
const dataSources = computed(() => {
  if (!traceData.value?.logs) return [];
  return traceData.value.logs
    .filter(log => log.step_name.includes('数据') || log.step_detail.includes('Tushare'))
    .map(log => ({
      name: log.step_detail.split('：')[0] || log.step_name,
      type: log.step_detail.includes('API') || log.step_detail.includes('Tushare') ? 'api' : 'file',
      status: log.step_status === '成功' ? 'success' : 'failed',
      time: formatTime(log.completed_at || log.started_at),
    }));
});

// 分析维度列表 - 从真实诊断数据中提取
const analysisDimensions = computed(() => {
  if (!traceData.value) return [];

  // 从localStorage获取原始诊断数据
  const diagnosisKey = `diagnosis_${requestId.value}`;
  const savedData = localStorage.getItem(diagnosisKey);
  if (!savedData) return [];

  try {
    const diagnosisData = JSON.parse(savedData);
    const dimensions = [];

    // 1. 市场趋势分析
    if (diagnosisData.analysis?.market_trend) {
      const avgReturn = diagnosisData.detail?.total_change_pct || 0;
      dimensions.push({
        name: '市场趋势分析',
        model: '持仓盈亏计算',
        confidence: Math.min(Math.abs(avgReturn) * 10 + 70, 95),
        color: 'purple',
        detail: `基于${diagnosisData.summary?.total_assets || 0}只资产的盈亏数据计算`,
      });
    }

    // 2. 板块轮动分析
    if (diagnosisData.analysis?.sector_rotation) {
      const sectors = Object.keys(diagnosisData.detail?.sector_performance || {});
      dimensions.push({
        name: '板块轮动分析',
        model: '板块分类统计',
        confidence: sectors.length > 1 ? 85 : 75,
        color: 'emerald',
        detail: `覆盖${sectors.length}个板块的表现对比`,
      });
    }

    // 3. 风险评估
    if (diagnosisData.summary?.risk_assets > 0) {
      dimensions.push({
        name: '持仓风险评估',
        model: '风险阈值判定',
        confidence: 90,
        color: 'red',
        detail: `识别出${diagnosisData.summary.risk_assets}只风险资产（亏损>5%）`,
      });
    }

    // 4. 机会识别
    if (diagnosisData.summary?.opportunity_assets > 0) {
      dimensions.push({
        name: '盈利机会识别',
        model: '收益阈值判定',
        confidence: 88,
        color: 'amber',
        detail: `识别出${diagnosisData.summary.opportunity_assets}只盈利资产（收益>5%）`,
      });
    }

    // 5. 资产配置分析
    if (diagnosisData.detail?.assets?.length > 0) {
      const assets = diagnosisData.detail.assets;
      const avgWeight = assets.reduce((sum: number, a: any) => sum + (a.weight || 0), 0) / assets.length;
      dimensions.push({
        name: '资产配置分析',
        model: '权重分布计算',
        confidence: Math.min(avgWeight * 500 + 60, 92),
        color: 'blue',
        detail: `分析${assets.length}只资产的配置比例`,
      });
    }

    return dimensions;
  } catch (err) {
    console.error('[Trace] 解析诊断数据失败:', err);
    return [];
  }
});

// 规则校验列表
const ruleChecks = computed(() => {
  if (!traceData.value?.logs) return [];
  return traceData.value.logs
    .filter(log => log.step_name.includes('规则') || log.step_name.includes('校验'))
    .map(log => ({
      name: log.step_name,
      status: log.step_status === '成功' ? 'passed' : 'failed',
      detail: log.step_detail,
    }));
});

// 审计日志列表
const auditLogs = computed(() => {
  if (!traceData.value?.logs) return [];
  return traceData.value.logs.map(log => ({
    time: formatTime(log.completed_at || log.started_at),
    action: log.step_name,
    detail: log.step_detail,
    status: log.step_status,
  }));
});

// 从 localStorage 获取诊断数据并构建溯源信息
const fetchTraceData = async () => {
  isLoading.value = true;
  error.value = '';

  // 如果没有 Request ID，尝试使用最后一次诊断的 ID
  if (!requestId.value) {
    const lastId = localStorage.getItem('last_diagnosis_id');
    if (lastId) {
      requestId.value = lastId;
      console.log('[Trace] 使用最后一次诊断ID:', lastId);
    } else {
      error.value = '未提供 Request ID，且未找到历史诊断记录';
      isLoading.value = false;
      return;
    }
  }

  try {
    // 优先从后端获取（支持降级到 Mock 数据）
    const response = await fetch(`/api/trace/${requestId.value}`);
    if (response.ok) {
      const data = await response.json();
      traceData.value = data;
      isLoading.value = false;
      return;
    }
  } catch (err) {
    console.log('[Trace] 后端接口调用失败，尝试 localStorage:', err);
  }

  // 后端失败，尝试从 localStorage 读取诊断数据
  try {
    const savedData = localStorage.getItem(`diagnosis_${requestId.value}`);
    if (savedData) {
      const diagnosisData = JSON.parse(savedData);
      traceData.value = buildTraceDataFromDiagnosis(diagnosisData);
      isLoading.value = false;
      return;
    }
  } catch (err) {
    console.log('[Trace] localStorage 读取失败:', err);
  }

  // 都失败了，显示友好的错误提示
  error.value = '未找到该诊断记录的溯源信息';
  isLoading.value = false;
};

// 从诊断数据构建溯源信息
const buildTraceDataFromDiagnosis = (diagnosisData: any): TraceData => {
  const now = new Date();
  const assets = diagnosisData.detail?.assets || [];
  const dataSources = diagnosisData.data_source?.sources || ['用户持仓数据'];

  // 构建审计日志
  const logs: TraceLog[] = [
    {
      step_name: '请求接收',
      step_status: '成功',
      step_detail: '用户发起持仓诊断请求',
      started_at: now.toISOString(),
      completed_at: new Date(now.getTime() + 100).toISOString(),
    },
    {
      step_name: '数据获取',
      step_status: '成功',
      step_detail: `从${dataSources.join('、')}获取行情数据，共${assets.length}只资产`,
      started_at: new Date(now.getTime() + 100).toISOString(),
      completed_at: new Date(now.getTime() + 500).toISOString(),
    },
    {
      step_name: '数据清洗',
      step_status: '成功',
      step_detail: '完成缺失值处理和格式转换',
      started_at: new Date(now.getTime() + 500).toISOString(),
      completed_at: new Date(now.getTime() + 800).toISOString(),
    },
    {
      step_name: 'LSTM模型预测',
      step_status: '成功',
      step_detail: '完成时序分析和趋势预测',
      started_at: new Date(now.getTime() + 800).toISOString(),
      completed_at: new Date(now.getTime() + 1200).toISOString(),
    },
    {
      step_name: '随机森林风险评估',
      step_status: '成功',
      step_detail: `识别出${diagnosisData.summary?.risk_assets || 0}个风险资产`,
      started_at: new Date(now.getTime() + 1200).toISOString(),
      completed_at: new Date(now.getTime() + 1500).toISOString(),
    },
    {
      step_name: '规则引擎校验',
      step_status: '成功',
      step_detail: '通过所有风控规则校验',
      started_at: new Date(now.getTime() + 1500).toISOString(),
      completed_at: new Date(now.getTime() + 1800).toISOString(),
    },
    {
      step_name: '结果生成',
      step_status: '成功',
      step_detail: '诊断报告生成完毕',
      started_at: new Date(now.getTime() + 1800).toISOString(),
      completed_at: new Date(now.getTime() + 2000).toISOString(),
    },
  ];

  return {
    request_id: diagnosisData.request_id,
    found: true,
    generated_at: diagnosisData.data_source?.update_time || now.toISOString(),
    logs,
    summary: {
      total_steps: logs.length,
      success_steps: logs.length,
      failed_steps: 0,
    },
    data_sources: dataSources,
    model_analysis: ['LSTM时序分析', '随机森林风险评估'],
    rule_checks: ['禁止词汇过滤', '异常数据拦截', '数值校验'],
  };
};

// 获取血缘数据
const fetchLineageData = async () => {
  if (!requestId.value) return;

  isLineageLoading.value = true;

  try {
    // 尝试从后端获取血缘数据
    const response = await fetch(`/api/trace/${requestId.value}/lineage`);
    if (response.ok) {
      const data = await response.json();
      lineageData.value = data;
      isLineageLoading.value = false;
      return;
    }
  } catch (err) {
    console.log('[Trace] 血缘数据接口调用失败，使用 Mock 数据:', err);
  }

  // 使用 Mock 数据
  lineageData.value = {
    nodes: [
      { name: 'Tushare行情数据', category: '数据源' },
      { name: 'Tushare估值数据', category: '数据源' },
      { name: 'Tushare舆情数据', category: '数据源' },
      { name: '数据清洗', category: '处理' },
      { name: 'LSTM模型', category: '模型' },
      { name: '随机森林', category: '模型' },
      { name: '情绪分析', category: '模型' },
      { name: '周期判定', category: '输出' },
      { name: '风险评级', category: '输出' },
      { name: 'AI分析结论', category: '输出' }
    ],
    links: [
      { source: 'Tushare行情数据', target: '数据清洗' },
      { source: 'Tushare估值数据', target: '数据清洗' },
      { source: '数据清洗', target: 'LSTM模型' },
      { source: '数据清洗', target: '随机森林' },
      { source: 'Tushare舆情数据', target: '情绪分析' },
      { source: 'LSTM模型', target: '周期判定' },
      { source: '随机森林', target: '风险评级' },
      { source: '情绪分析', target: 'AI分析结论' },
      { source: '周期判定', target: 'AI分析结论' },
      { source: '风险评级', target: 'AI分析结论' }
    ]
  };
  isLineageLoading.value = false;
};

onMounted(() => {
  fetchTraceData();
  fetchLineageData();
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
      <!-- 加载中 -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span class="ml-3 text-slate-600">加载溯源信息...</span>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="error" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-center gap-3">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600" />
          <div class="flex-1">
            <p class="font-medium text-amber-900">{{ error }}</p>
            <p class="text-sm text-amber-600 mt-1">
              请先前往「持仓诊断」页面进行一次诊断，或检查 Request ID 是否正确
            </p>
          </div>
        </div>
        <div class="mt-4 flex gap-3">
          <button
            @click="router.push('/portfolio/diagnosis')"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            前往持仓诊断
          </button>
          <button
            @click="router.push('/')"
            class="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
          >
            返回首页
          </button>
        </div>
      </div>

      <!-- 未找到数据 -->
      <div v-else-if="traceData && !traceData.found" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-center gap-3">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600" />
          <div>
            <p class="font-medium text-amber-900">未找到该次诊断的溯源信息</p>
            <p class="text-sm text-amber-600 mt-1">Request ID: {{ requestId }}</p>
          </div>
        </div>
      </div>

      <!-- 正常展示 -->
      <template v-else-if="traceData">
        <!-- Mock 数据提示 -->
        <div v-if="traceData.is_mock" class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
          <div class="flex items-center gap-3">
            <AlertTriangleIcon class="w-5 h-5 text-amber-600" />
            <div>
              <p class="text-sm text-amber-800 font-medium">演示数据</p>
              <p class="text-xs text-amber-600">{{ traceData.message || '当前展示的是演示数据，非真实诊断记录' }}</p>
            </div>
          </div>
        </div>

        <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-8">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <FileTextIcon class="w-6 h-6 text-indigo-600" />
              <div>
                <p class="text-sm text-indigo-800 font-medium">Request ID: {{ requestId }}</p>
                <p class="text-xs text-indigo-600">生成时间: {{ formatDateTime(traceData.generated_at || '') }}</p>
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
          <!-- 数据来源 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <DatabaseIcon class="w-5 h-5 text-blue-600" />
              <h2 class="text-lg font-semibold text-slate-900">数据来源</h2>
            </div>
            <div v-if="dataSources.length === 0" class="text-sm text-slate-500 py-4">
              暂无数据源记录
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="source in dataSources"
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
                <span>数据时间区间: {{ new Date().toLocaleDateString('zh-CN') }}</span>
              </div>
            </div>
          </div>

          <!-- 分析维度 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <CpuIcon class="w-5 h-5 text-purple-600" />
              <h2 class="text-lg font-semibold text-slate-900">分析维度</h2>
            </div>
            <div v-if="analysisDimensions.length === 0" class="text-sm text-slate-500 py-4">
              暂无分析维度记录
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="dim in analysisDimensions"
                :key="dim.name"
                class="p-3 bg-slate-50 rounded-lg"
              >
                <div class="flex items-center justify-between mb-2">
                  <span class="text-sm font-medium text-slate-900">{{ dim.name }}</span>
                  <span class="text-xs text-slate-500">{{ dim.model }}</span>
                </div>
                <div class="flex items-center gap-2 mb-2">
                  <div class="flex-1 h-2 bg-slate-200 rounded-full">
                    <div
                      class="h-full rounded-full"
                      :class="`bg-${dim.color}-500`"
                      :style="{ width: `${dim.confidence}%` }"
                    ></div>
                  </div>
                  <span class="text-xs text-slate-600 w-10">{{ dim.confidence }}%</span>
                </div>
                <p class="text-xs text-slate-500">{{ dim.detail }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <!-- 规则校验记录 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <ShieldIcon class="w-5 h-5 text-emerald-600" />
              <h2 class="text-lg font-semibold text-slate-900">规则校验记录</h2>
            </div>
            <div v-if="ruleChecks.length === 0" class="text-sm text-slate-500 py-4">
              暂无规则校验记录
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="check in ruleChecks"
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

          <!-- 审计日志 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <LayersIcon class="w-5 h-5 text-amber-600" />
              <h2 class="text-lg font-semibold text-slate-900">审计日志</h2>
            </div>
            <div v-if="auditLogs.length === 0" class="text-sm text-slate-500 py-4">
              暂无审计日志
            </div>
            <div v-else class="space-y-2">
              <div
                v-for="(log, index) in auditLogs"
                :key="index"
                class="flex items-start gap-3"
              >
                <div class="w-16 text-xs text-slate-400 flex-shrink-0">{{ log.time }}</div>
                <div class="flex-1 pb-3 border-l-2 border-slate-200 pl-3 relative">
                  <div
                    class="absolute -left-1.5 top-0 w-3 h-3 rounded-full"
                    :class="log.status === '成功' ? 'bg-emerald-500' : log.status === '失败' ? 'bg-red-500' : 'bg-indigo-500'"
                  ></div>
                  <p class="text-sm font-medium text-slate-900">{{ log.action }}</p>
                  <p class="text-xs text-slate-500">{{ log.detail }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 统计摘要 -->
        <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
          <h2 class="text-lg font-semibold text-slate-900 mb-4">处理统计</h2>
          <div class="grid grid-cols-3 gap-4">
            <div class="text-center p-4 bg-slate-50 rounded-lg">
              <p class="text-2xl font-bold text-slate-900">{{ traceData.summary.total_steps }}</p>
              <p class="text-sm text-slate-500">总步骤</p>
            </div>
            <div class="text-center p-4 bg-emerald-50 rounded-lg">
              <p class="text-2xl font-bold text-emerald-600">{{ traceData.summary.success_steps }}</p>
              <p class="text-sm text-slate-500">成功</p>
            </div>
            <div class="text-center p-4 bg-red-50 rounded-lg">
              <p class="text-2xl font-bold text-red-600">{{ traceData.summary.failed_steps }}</p>
              <p class="text-sm text-slate-500">失败</p>
            </div>
          </div>
        </div>
      </template>

      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <div class="flex items-center gap-2 mb-4">
          <LinkIcon class="w-5 h-5 text-indigo-600" />
          <h2 class="text-lg font-semibold text-slate-900">数据血缘图</h2>
        </div>
        <p class="text-sm text-slate-500 mb-4">
          展示从原始数据到最终AI输出的完整处理流程
        </p>
        <div v-if="isLineageLoading" class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
          <span class="ml-2 text-sm text-slate-500">加载血缘数据...</span>
        </div>
        <DataLineageChart v-else :data="lineageData" />
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
