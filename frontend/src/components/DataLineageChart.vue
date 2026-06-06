<script setup lang="ts">
import { computed } from 'vue';

interface Node {
  id: string;
  label: string;
  type: 'source' | 'process' | 'output';
}

interface Edge {
  from: string;
  to: string;
}

const nodes: Node[] = [
  { id: 'tushare', label: 'Tushare API', type: 'source' },
  { id: 'market', label: '市场行情数据', type: 'source' },
  { id: 'sentiment', label: '舆情数据', type: 'source' },
  { id: 'clean', label: '数据清洗', type: 'process' },
  { id: 'encrypt', label: 'AES-256加密', type: 'process' },
  { id: 'lstm', label: 'LSTM模型', type: 'process' },
  { id: 'rf', label: '随机森林', type: 'process' },
  { id: 'llm', label: 'LLM分析', type: 'process' },
  { id: 'risk', label: '风控规则', type: 'process' },
  { id: 'output', label: 'AI诊断结果', type: 'output' },
];

const edges: Edge[] = [
  { from: 'tushare', to: 'clean' },
  { from: 'market', to: 'clean' },
  { from: 'sentiment', to: 'clean' },
  { from: 'clean', to: 'encrypt' },
  { from: 'encrypt', to: 'lstm' },
  { from: 'encrypt', to: 'rf' },
  { from: 'encrypt', to: 'llm' },
  { from: 'lstm', to: 'risk' },
  { from: 'rf', to: 'risk' },
  { from: 'llm', to: 'risk' },
  { from: 'risk', to: 'output' },
];

const getNodeColor = (type: string) => {
  switch (type) {
    case 'source':
      return 'bg-blue-100 border-blue-300 text-blue-800';
    case 'process':
      return 'bg-amber-100 border-amber-300 text-amber-800';
    case 'output':
      return 'bg-emerald-100 border-emerald-300 text-emerald-800';
    default:
      return 'bg-slate-100 border-slate-300 text-slate-800';
  }
};

const nodePositions = computed(() => {
  const positions: Record<string, { x: number; y: number }> = {};
  const levels: Record<number, string[]> = {
    0: ['tushare', 'market', 'sentiment'],
    1: ['clean'],
    2: ['encrypt'],
    3: ['lstm', 'rf', 'llm'],
    4: ['risk'],
    5: ['output'],
  };

  Object.entries(levels).forEach(([level, nodeIds]) => {
    const y = parseInt(level) * 80 + 40;
    const spacing = 200;
    const startX = 400 - ((nodeIds.length - 1) * spacing) / 2;
    nodeIds.forEach((id, index) => {
      positions[id] = { x: startX + index * spacing, y };
    });
  });

  return positions;
});
</script>

<template>
  <div class="w-full overflow-x-auto">
    <svg viewBox="0 0 800 520" class="w-full max-w-4xl mx-auto">
      <defs>
        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
        </marker>
      </defs>

      <g v-for="edge in edges" :key="`${edge.from}-${edge.to}`">
        <line
          :x1="nodePositions[edge.from]?.x"
          :y1="nodePositions[edge.from]?.y + 20"
          :x2="nodePositions[edge.to]?.x"
          :y2="nodePositions[edge.to]?.y - 20"
          stroke="#94a3b8"
          stroke-width="2"
          marker-end="url(#arrowhead)"
        />
      </g>

      <g v-for="node in nodes" :key="node.id">
        <rect
          :x="(nodePositions[node.id]?.x || 0) - 70"
          :y="(nodePositions[node.id]?.y || 0) - 20"
          width="140"
          height="40"
          rx="8"
          :class="getNodeColor(node.type)"
          class="border-2"
        />
        <text
          :x="nodePositions[node.id]?.x"
          :y="(nodePositions[node.id]?.y || 0) + 5"
          text-anchor="middle"
          class="text-sm font-medium"
          fill="currentColor"
        >
          {{ node.label }}
        </text>
      </g>
    </svg>
  </div>
</template>
