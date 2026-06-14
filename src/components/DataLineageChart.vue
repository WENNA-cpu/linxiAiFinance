<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';

interface LineageNode {
  name: string;
  category: string;
  x?: number;
  y?: number;
}

interface LineageLink {
  source: string;
  target: string;
}

interface LineageData {
  nodes: LineageNode[];
  links: LineageLink[];
}

const props = defineProps<{
  data?: LineageData | null;
}>();

const chartContainer = ref<HTMLDivElement | null>(null);
const chartInstance = ref<any>(null);

// 默认 Mock 数据
const defaultData: LineageData = {
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

// 使用传入的数据或默认数据
const lineageData = computed(() => props.data || defaultData);

// 颜色配置
const categoryColors: Record<string, string> = {
  '数据源': '#3b82f6', // blue-500
  '处理': '#f59e0b',    // amber-500
  '模型': '#8b5cf6',    // violet-500
  '输出': '#10b981',    // emerald-500
};

const initChart = async () => {
  if (!chartContainer.value) return;

  // 确保数据存在
  const data = lineageData.value;
  if (!data || !data.nodes || data.nodes.length === 0) return;

  // 动态导入 echarts
  const echarts = await import('echarts');

  if (chartInstance.value) {
    chartInstance.value.dispose();
    chartInstance.value = null;
  }

  chartInstance.value = echarts.init(chartContainer.value);

  // 为节点分配类别索引
  const categories = ['数据源', '处理', '模型', '输出'];
  const nodes = data.nodes.map(node => ({
    name: node.name,
    category: categories.indexOf(node.category),
    symbolSize: node.category === '输出' ? 60 : 50,
    itemStyle: {
      color: categoryColors[node.category] || '#64748b',
    },
    label: {
      show: true,
      position: 'bottom',
      fontSize: 12,
      color: '#334155',
    },
  }));

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `<div style="font-weight:bold">${params.name}</div><div style="color:#666">${categories[params.data.category]}</div>`;
        }
        return `${params.data.source} → ${params.data.target}`;
      },
    },
    legend: {
      data: categories,
      bottom: 10,
      textStyle: {
        color: '#64748b',
      },
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: data.links,
        categories: categories.map(name => ({ name })),
        roam: true,
        draggable: true,
        focusNodeAdjacency: true,
        force: {
          repulsion: 400,
          gravity: 0.05,
          edgeLength: [100, 180],
          layoutAnimation: true,
        },
        lineStyle: {
          color: '#94a3b8',
          width: 2,
          curveness: 0.2,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: {
            width: 4,
            color: '#6366f1',
          },
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 10],
        label: {
          show: true,
          position: 'bottom',
          fontSize: 11,
          color: '#334155',
          distance: 5,
        },
      },
    ],
    // 添加网格背景
    grid: {
      left: '5%',
      right: '5%',
      top: '10%',
      bottom: '15%',
    },
  };

  chartInstance.value.setOption(option);
  // 自适应容器大小
  chartInstance.value.resize();
};

// 监听数据变化
watch(() => props.data, () => {
  initChart();
}, { deep: true });

onMounted(() => {
  initChart();

  // 响应式调整
  window.addEventListener('resize', () => {
    chartInstance.value?.resize();
  });
});
</script>

<template>
  <div ref="chartContainer" class="w-full h-[500px]"></div>
</template>
