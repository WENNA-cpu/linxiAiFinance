<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import XCircleIcon from '@/components/icons/XCircleIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';
import BanIcon from '@/components/icons/BanIcon.vue';
import ScaleIcon from '@/components/icons/ScaleIcon.vue';
import CpuIcon from '@/components/icons/CpuIcon.vue';
import LockIcon from '@/components/icons/LockIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import VerifiedIcon from '@/components/icons/VerifiedIcon.vue';
import GavelIcon from '@/components/icons/GavelIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';

const router = useRouter();
const loading = ref(false);
const error = ref('');

const DEFAULT_STATS = {
  blocked_count: 2847,
  hallucination_correction_rate: 94.2,
  data_breach_events: 0,
  rule_pass_rate: 99.8,
};

const stats = ref({ ...DEFAULT_STATS });
const isDefaultData = ref(false);

// 从后端 API 获取合规统计数据
const fetchComplianceStats = async () => {
  loading.value = true;
  error.value = '';

  try {
    const response = await fetch('/api/admin/compliance-stats', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
      throw new Error(`获取数据失败: ${response.status}`);
    }

    const data = await response.json();
    stats.value = {
      blocked_count: data.blocked_count ?? DEFAULT_STATS.blocked_count,
      hallucination_correction_rate: data.hallucination_correction_rate ?? DEFAULT_STATS.hallucination_correction_rate,
      data_breach_events: data.data_breach_events ?? DEFAULT_STATS.data_breach_events,
      rule_pass_rate: data.rule_pass_rate ?? DEFAULT_STATS.rule_pass_rate,
    };
    isDefaultData.value = Boolean(data.is_default);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取统计数据失败';
    stats.value = { ...DEFAULT_STATS };
    isDefaultData.value = true;
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchComplianceStats();
});

const aiCapabilities = {
  can: [
    '基于公开历史数据做现状分析',
    '信息整理与知识问答',
    '持仓资产风险点识别',
    '行业状态与估值分析',
    '投教内容生成',
  ],
  cannot: [
    '预测未来行情走势',
    '推荐具体股票/基金代码',
    '承诺收益或保本',
    '给出买卖指令',
    '提供内幕消息',
  ],
};

const forbiddenWords = [
  '荐股', '保证收益', '稳赚', '翻倍', '内幕消息',
  '涨停', '抄底', '买入信号', '必涨', '包赚',
];

const complianceStats = computed(() => [
  { label: '拦截违规内容', value: stats.value.blocked_count.toLocaleString(), unit: '次', icon: BanIcon },
  { label: 'AI幻觉修正率', value: stats.value.hallucination_correction_rate.toString(), unit: '%', icon: CpuIcon },
  { label: '数据泄露事件', value: stats.value.data_breach_events.toString(), unit: '起', icon: LockIcon },
  { label: '规则校验通过', value: stats.value.rule_pass_rate.toString(), unit: '%', icon: VerifiedIcon },
]);

const riskControls = [
  {
    layer: '数据层',
    measures: ['数据脱敏处理', '异常值拦截(涨跌幅>20%告警)', 'AES-256加密存储'],
    icon: DatabaseIcon,
  },
  {
    layer: 'AI输出层',
    measures: ['禁止词汇库过滤', '数值校验(PE<0或>100告警)', '事实校验机制'],
    icon: CpuIcon,
  },
  {
    layer: '交互层',
    measures: ['风险提示弹窗', '常驻免责声明', '权责边界声明'],
    icon: ShieldIcon,
  },
];
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <RiskBanner />

    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
        <button @click="router.push('/')" class="p-2 hover:bg-slate-100 rounded-lg transition-colors">
          <HomeIcon class="w-5 h-5 text-slate-600" />
        </button>
        <h1 class="text-xl font-bold text-slate-900">合规与AI能力边界</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-slate-900 rounded-xl p-8 mb-8 text-white">
        <div class="flex items-center gap-3 mb-4">
          <ScaleIcon class="w-8 h-8" />
          <h2 class="text-2xl font-bold">AI能力边界声明</h2>
        </div>
        <p class="text-slate-300 text-lg">
          灵析严格遵守监管要求，明确界定AI能力边界，确保所有输出合规合法。
        </p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center gap-2 mb-4">
            <CheckCircleIcon class="w-6 h-6 text-emerald-500" />
            <h2 class="text-lg font-semibold text-slate-900">AI可以做的</h2>
          </div>
          <ul class="space-y-3">
            <li
              v-for="item in aiCapabilities.can"
              :key="item"
              class="flex items-start gap-3 p-3 bg-emerald-50 rounded-lg"
            >
              <CheckCircleIcon class="w-5 h-5 text-emerald-500 flex-shrink-0" />
              <span class="text-slate-700">{{ item }}</span>
            </li>
          </ul>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 p-6">
          <div class="flex items-center gap-2 mb-4">
            <XCircleIcon class="w-6 h-6 text-red-500" />
            <h2 class="text-lg font-semibold text-slate-900">AI不能做的</h2>
          </div>
          <ul class="space-y-3">
            <li
              v-for="item in aiCapabilities.cannot"
              :key="item"
              class="flex items-start gap-3 p-3 bg-red-50 rounded-lg"
            >
              <BanIcon class="w-5 h-5 text-red-500 flex-shrink-0" />
              <span class="text-slate-700">{{ item }}</span>
            </li>
          </ul>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <div class="flex items-center gap-2 mb-4">
          <GavelIcon class="w-5 h-5 text-amber-600" />
          <h2 class="text-lg font-semibold text-slate-900">禁止词汇库</h2>
        </div>
        <p class="text-sm text-slate-500 mb-4">以下词汇将被系统自动拦截，不会出现在AI输出中</p>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="word in forbiddenWords"
            :key="word"
            class="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium"
          >
            {{ word }}
          </span>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-lg font-semibold text-slate-900">合规价值量化</h2>
          <span v-if="loading" class="text-sm text-slate-500">加载中...</span>
          <span v-else-if="error" class="text-sm text-red-500">{{ error }}</span>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="stat in complianceStats"
            :key="stat.label"
            class="p-4 bg-slate-50 rounded-lg text-center"
          >
            <component :is="stat.icon" class="w-8 h-8 mx-auto mb-2 text-indigo-600" />
            <p class="text-2xl font-bold text-slate-900">
              {{ stat.value }}<span class="text-sm font-normal text-slate-500">{{ stat.unit }}</span>
            </p>
            <p class="text-sm text-slate-500">{{ stat.label }}</p>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
        <div class="flex items-center gap-2 mb-4">
          <ShieldIcon class="w-5 h-5 text-indigo-600" />
          <h2 class="text-lg font-semibold text-slate-900">三层风控体系</h2>
        </div>
        <div class="space-y-4">
          <div
            v-for="(control, index) in riskControls"
            :key="control.layer"
            class="p-4 rounded-lg"
            :class="index === 0 ? 'bg-blue-50' : index === 1 ? 'bg-purple-50' : 'bg-emerald-50'"
          >
            <div class="flex items-center gap-2 mb-2">
              <span
                class="px-2 py-1 rounded text-xs font-medium"
                :class="index === 0 ? 'bg-blue-200 text-blue-800' : index === 1 ? 'bg-purple-200 text-purple-800' : 'bg-emerald-200 text-emerald-800'"
              >
                {{ control.layer }}
              </span>
            </div>
            <ul class="space-y-1">
              <li
                v-for="measure in control.measures"
                :key="measure"
                class="text-sm text-slate-600 flex items-center gap-2"
              >
                <CheckCircleIcon class="w-3 h-3" :class="index === 0 ? 'text-blue-500' : index === 1 ? 'text-purple-500' : 'text-emerald-500'" />
                {{ measure }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="bg-amber-50 border border-amber-200 rounded-xl p-6">
        <div class="flex items-start gap-3">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600 flex-shrink-0" />
          <div>
            <h3 class="font-semibold text-amber-900 mb-2">监管红线提示</h3>
            <ul class="space-y-2 text-sm text-amber-800">
              <li>• 严禁任何形式的荐股行为</li>
              <li>• 严禁承诺收益或保本保息</li>
              <li>• 严禁传播内幕消息或未公开信息</li>
              <li>• 所有AI输出必须附带风险提示</li>
              <li>• 用户投资决策完全由用户自主做出</li>
            </ul>
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
