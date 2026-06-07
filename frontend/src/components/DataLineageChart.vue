<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';

export interface LineageStep {
  step_name: string;
  step_status: 'success' | 'running' | 'failed' | string;
  step_detail: string;
  duration_ms?: number;
}

const props = defineProps<{
  steps: LineageStep[] | null;
  isDemo?: boolean;
}>();

const chartRef = ref<HTMLElement | null>(null);
let chartInstance: import('echarts').ECharts | null = null;
let pulseTimer: ReturnType<typeof setInterval> | null = null;
let runningNodeIds: string[] = [];

const PIPELINE_LABELS = [
  '用户输入', '数据获取', '数据清洗',
  'LSTM模型', '随机森林', '规则引擎', '结果生成',
] as const;

/** 菱形 DAG 布局：3→1→1→3→1→1 */
const DIAMOND_NODES = [
  { id: 'input', label: '用户输入', stepKey: '用户输入', x: 250, y: 55 },
  { id: 'fetch', label: '数据获取', stepKey: '数据获取', x: 500, y: 55 },
  { id: 'tushare', label: 'Tushare', stepKey: '数据获取', x: 750, y: 55 },
  { id: 'clean', label: '数据清洗', stepKey: '数据清洗', x: 500, y: 145 },
  { id: 'prep', label: '预处理', stepKey: '数据清洗', x: 500, y: 235 },
  { id: 'lstm', label: 'LSTM模型', stepKey: 'LSTM模型', x: 250, y: 325 },
  { id: 'rf', label: '随机森林', stepKey: '随机森林', x: 500, y: 325 },
  { id: 'merge', label: '模型融合', stepKey: '随机森林', x: 750, y: 325 },
  { id: 'rule', label: '规则引擎', stepKey: '规则引擎', x: 500, y: 415 },
  { id: 'output', label: '结果生成', stepKey: '结果生成', x: 500, y: 505 },
] as const;

const DIAMOND_LINKS: Array<[string, string]> = [
  ['input', 'clean'], ['fetch', 'clean'], ['tushare', 'clean'],
  ['clean', 'prep'],
  ['prep', 'lstm'], ['prep', 'rf'], ['prep', 'merge'],
  ['lstm', 'rule'], ['rf', 'rule'], ['merge', 'rule'],
  ['rule', 'output'],
];

const CHART_HEIGHT = 580;
const NODE_WIDTH = 118;
const NODE_HEIGHT = 42;

const STEP_ALIASES: Record<string, string[]> = {
  '用户输入': ['请求接收', '用户输入'],
  '数据获取': ['数据获取'],
  '数据清洗': ['数据清洗'],
  'LSTM模型': ['LSTM模型预测', 'LSTM模型', 'LSTM'],
  '随机森林': ['随机森林风险评估', '随机森林'],
  '规则引擎': ['规则引擎校验', '规则引擎'],
  '结果生成': ['结果生成', '报告'],
};

const STATUS_COLORS = {
  success: '#262626',
  running: '#1890ff',
  failed: '#f5222d',
  pending: '#bdbdbd',
} as const;

const MOCK_LINEAGE_STEPS: LineageStep[] = [
  { step_name: '用户输入', step_status: 'success', step_detail: '用户发起持仓诊断请求', duration_ms: 15 },
  { step_name: '数据获取', step_status: 'success', step_detail: '从 Tushare 获取 3 只资产行情数据', duration_ms: 420 },
  { step_name: '数据清洗', step_status: 'success', step_detail: '缺失值填充、归一化处理', duration_ms: 180 },
  { step_name: 'LSTM模型预测', step_status: 'success', step_detail: '时序趋势预测完成', duration_ms: 320 },
  { step_name: '随机森林风险评估', step_status: 'success', step_detail: '风险等级分类：中等', duration_ms: 95 },
  { step_name: '规则引擎校验', step_status: 'success', step_detail: '合规文案校验通过', duration_ms: 40 },
  { step_name: '结果生成', step_status: 'success', step_detail: '生成诊断报告', duration_ms: 60 },
];

function matchStepToLabel(stepName: string): string | null {
  for (const label of PIPELINE_LABELS) {
    if (STEP_ALIASES[label].some((alias) => stepName.includes(alias) || alias.includes(stepName))) {
      return label;
    }
  }
  return null;
}

function normalizeStepStatus(status: string): keyof typeof STATUS_COLORS {
  const s = status.toLowerCase();
  if (s === 'failed' || status === '失败') return 'failed';
  if (s === 'running' || status === '进行中') return 'running';
  if (s === 'success' || status === '成功' || status === '警告') return 'success';
  return 'pending';
}

function statusLabel(status: string) {
  if (status === 'success') return '成功';
  if (status === 'running') return '进行中';
  if (status === 'failed') return '失败';
  return '待执行';
}

function formatDuration(ms?: number) {
  if (ms == null || ms < 0) return '-';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function mergeStepsByLabel(steps: LineageStep[]) {
  const merged: Record<string, LineageStep & { fullName: string }> = {};
  for (const step of steps) {
    const label = matchStepToLabel(step.step_name);
    if (label) {
      merged[label] = { ...step, fullName: step.step_name };
    }
  }
  return merged;
}

function getEffectiveSteps(): LineageStep[] {
  return props.steps?.length ? props.steps : MOCK_LINEAGE_STEPS;
}

function buildChartOption(steps: LineageStep[]) {
  const merged = mergeStepsByLabel(steps);
  runningNodeIds = [];

  const nodes = DIAMOND_NODES.map((def) => {
    const data = merged[def.stepKey];
    const status = data ? normalizeStepStatus(String(data.step_status)) : 'pending';
    if (status === 'running') runningNodeIds.push(def.id);

    const isAuxiliary = def.label !== def.stepKey;

    return {
      id: def.id,
      name: def.label,
      x: def.x,
      y: def.y,
      symbol: 'roundRect',
      symbolSize: [NODE_WIDTH, NODE_HEIGHT],
      itemStyle: {
        color: STATUS_COLORS[status],
        borderRadius: NODE_HEIGHT / 2,
        shadowBlur: status === 'running' ? 14 : 0,
        shadowColor: status === 'running' ? 'rgba(24, 144, 255, 0.5)' : 'transparent',
      },
      label: {
        show: true,
        fontSize: 13,
        color: '#ffffff',
        fontWeight: 500,
      },
      stepData: {
        name: isAuxiliary ? `${def.label}（${def.stepKey}）` : (data?.fullName || def.label),
        status,
        detail: data?.step_detail || '暂无该步骤数据',
        duration_ms: data?.duration_ms,
      },
    };
  });

  const links = DIAMOND_LINKS.map(([source, target]) => ({ source, target }));

  return {
    animationDurationUpdate: 300,
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.96)',
      borderColor: '#e2e8f0',
      borderWidth: 1,
      padding: [12, 16],
      textStyle: { color: '#334155', fontSize: 13 },
      extraCssText: 'box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-radius: 8px;',
      formatter: (params: {
        dataType?: string;
        data?: { stepData?: { name: string; status: string; detail: string; duration_ms?: number } };
      }) => {
        if (params.dataType !== 'node' || !params.data?.stepData) return '';
        const d = params.data.stepData;
        const color = STATUS_COLORS[d.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.pending;
        return [
          `<div style="font-weight:600;margin-bottom:6px;color:#1e293b">${d.name}</div>`,
          `<div>执行状态：<span style="color:${color};font-weight:500">${statusLabel(d.status)}</span></div>`,
          `<div style="color:#64748b">耗时：${formatDuration(d.duration_ms)}</div>`,
          `<div style="margin-top:8px;color:#64748b;max-width:260px;line-height:1.5">${d.detail}</div>`,
        ].join('');
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'none',
        roam: false,
        draggable: false,
        focusNodeAdjacency: true,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        data: nodes,
        links,
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 2.5, color: '#64748b' },
          itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,0,0,0.15)' },
        },
        lineStyle: {
          color: '#c8d4e0',
          width: 1.5,
          curveness: 0,
        },
      },
    ],
  };
}

function stopPulseAnimation() {
  if (pulseTimer) {
    clearInterval(pulseTimer);
    pulseTimer = null;
  }
}

function startPulseAnimation() {
  stopPulseAnimation();
  if (!chartInstance || runningNodeIds.length === 0) return;

  let bright = true;
  pulseTimer = setInterval(() => {
    if (!chartInstance) return;
    const option = chartInstance.getOption() as {
      series?: Array<{ data?: Array<{ id: string; itemStyle?: Record<string, unknown> }> }>;
    };
    const seriesData = option.series?.[0]?.data;
    if (!seriesData) return;

    seriesData.forEach((node) => {
      if (runningNodeIds.includes(node.id)) {
        node.itemStyle = {
          ...(node.itemStyle || {}),
          shadowBlur: bright ? 20 : 6,
          opacity: bright ? 1 : 0.7,
        };
      }
    });
    chartInstance.setOption({ series: [{ data: seriesData }] });
    bright = !bright;
  }, 550);
}

async function renderChart() {
  if (!chartRef.value) return;

  const echarts = await import('echarts');
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }

  chartInstance.setOption(buildChartOption(getEffectiveSteps()), true);
  startPulseAnimation();
}

function handleResize() {
  chartInstance?.resize();
}

onMounted(() => {
  nextTick(() => renderChart());
  window.addEventListener('resize', handleResize);
});

watch(
  () => props.steps,
  () => {
    nextTick(() => renderChart());
  },
  { deep: true },
);

onUnmounted(() => {
  stopPulseAnimation();
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
  chartInstance = null;
});
</script>

<template>
  <div class="w-full relative">
    <div
      v-if="isDemo"
      class="pointer-events-none absolute inset-0 flex items-center justify-center z-10"
    >
      <span class="text-5xl font-bold text-slate-200/80 select-none tracking-widest rotate-[-12deg]">
        演示数据
      </span>
    </div>

    <div
      ref="chartRef"
      class="w-full max-w-[900px] mx-auto"
      :style="{ height: `${CHART_HEIGHT}px` }"
    />

    <div class="mt-3 flex flex-wrap items-center justify-center gap-4 text-xs text-slate-500">
      <span class="inline-flex items-center gap-1.5">
        <span class="w-3 h-3 rounded-sm" style="background: #262626" />
        成功
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="w-3 h-3 rounded-sm animate-pulse" style="background: #1890ff" />
        进行中
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="w-3 h-3 rounded-sm" style="background: #f5222d" />
        失败
      </span>
      <span class="inline-flex items-center gap-1.5">
        <span class="w-3 h-3 rounded-sm" style="background: #bdbdbd" />
        待执行
      </span>
    </div>
  </div>
</template>
