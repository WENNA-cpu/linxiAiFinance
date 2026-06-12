<script setup lang="ts">
import { ref, computed } from 'vue';
import { usePortfolioStore } from '@/stores/portfolio';
import BookIcon from '@/components/icons/BookIcon.vue';
import GraduationCapIcon from '@/components/icons/GraduationCapIcon.vue';
import StarIcon from '@/components/icons/StarIcon.vue';
import CloseIcon from '@/components/icons/CloseIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';

export type PremiumView = 'report' | 'rebalance' | 'expert' | null;

const props = defineProps<{
  activeView: PremiumView;
}>();

const emit = defineEmits<{
  close: [];
}>();

const portfolioStore = usePortfolioStore();

const expertForm = ref({
  name: '',
  phone: '',
  email: '',
  date: '',
  concern: '',
});
const expertSubmitted = ref(false);

const sampleReport = {
  title: '2026年Q2 消费行业深度研报',
  institution: '灵犀 AI 研究院',
  date: '2026-06-01',
  rating: '增持',
  summary:
    '消费板块估值处于近五年中低位，政策端促消费措施持续落地，龙头公司渠道改革成效显现，建议关注高端白酒、医美及必选消费细分龙头。',
  highlights: [
    { label: '行业 PE（TTM）', value: '22.4x', trend: '低于历史中位数 28x' },
    { label: '社零同比', value: '+5.8%', trend: '环比改善 0.6pct' },
    { label: '北向净流入', value: '42.3 亿', trend: '近 20 日持续流入' },
  ],
  sections: [
    {
      title: '核心观点',
      content:
        '1. 高端消费复苏节奏快于大众消费，品牌力强的龙头份额持续提升。\n2. 必选消费防御属性凸显，现金流稳定，适合作为底仓配置。\n3. 需警惕部分赛道库存去化不及预期带来的业绩波动。',
    },
    {
      title: '推荐标的逻辑（示例）',
      content:
        '• 高端白酒：渠道库存健康，批价企稳回升\n• 医美龙头：渗透率提升空间大，复购率高\n• 乳制品：成本端原奶价格下行，毛利率有望修复',
    },
    {
      title: '风险提示',
      content: '宏观经济复苏不及预期；消费信心恢复缓慢；行业竞争加剧导致价格战。',
    },
  ],
};

const rebalancePlan = computed(() => {
  const assets = portfolioStore.portfolio.assets;
  if (!assets.length) return null;

  const total =
    portfolioStore.portfolio.totalValue ||
    assets.reduce((sum, a) => sum + (a.marketValue || 0), 0);

  const targetEach = 100 / assets.length;

  return {
    total,
    items: assets.map((asset) => {
      const current = total > 0 ? (asset.marketValue / total) * 100 : 0;
      const diff = targetEach - current;
      let action = '持有观望';
      let actionColor = 'text-slate-600 bg-slate-100';
      if (diff > 8) {
        action = '建议增配';
        actionColor = 'text-emerald-700 bg-emerald-100';
      } else if (diff < -8) {
        action = '建议减配';
        actionColor = 'text-amber-700 bg-amber-100';
      }
      return {
        name: asset.name,
        code: asset.code,
        type: asset.type,
        current: current.toFixed(1),
        target: targetEach.toFixed(1),
        diff: diff.toFixed(1),
        action,
        actionColor,
      };
    }),
    summary:
      '基于等权重再平衡模型，对偏离目标配置超过 8% 的标的给出增配/减配建议，仅供参考。',
  };
});

const submitExpertForm = () => {
  if (!expertForm.value.name.trim() || !expertForm.value.phone.trim()) return;
  expertSubmitted.value = true;
};

const resetExpertForm = () => {
  expertForm.value = { name: '', phone: '', email: '', date: '', concern: '' };
  expertSubmitted.value = false;
};

const handleClose = () => {
  resetExpertForm();
  emit('close');
};

const viewMeta = computed(() => {
  switch (props.activeView) {
    case 'report':
      return { title: '深度研报解读', icon: BookIcon, price: '99元/月' };
    case 'rebalance':
      return { title: '持仓再平衡建议', icon: GraduationCapIcon, price: '199元/次' };
    case 'expert':
      return { title: '专家复核', icon: StarIcon, price: '299元/次' };
    default:
      return null;
  }
});
</script>

<template>
  <Teleport to="body">
    <div
      v-if="activeView && viewMeta"
      class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/50"
      @click.self="handleClose"
    >
      <div
        class="bg-white rounded-2xl shadow-2xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        :class="activeView === 'expert' ? 'max-w-lg' : 'max-w-3xl'"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-indigo-50 to-purple-50 flex-shrink-0">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center">
              <component :is="viewMeta.icon" class="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 class="text-lg font-bold text-slate-900">{{ viewMeta.title }}</h3>
              <p class="text-sm text-indigo-600 font-medium">{{ viewMeta.price }}</p>
            </div>
          </div>
          <button
            type="button"
            class="p-2 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white transition-colors"
            @click="handleClose"
          >
            <CloseIcon class="w-5 h-5" />
          </button>
        </div>

        <div class="flex-1 overflow-y-auto p-6">
          <!-- 深度研报 -->
          <div v-if="activeView === 'report'" class="space-y-6">
            <div class="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h4 class="text-xl font-bold text-slate-900">{{ sampleReport.title }}</h4>
                <p class="text-sm text-slate-500 mt-1">
                  {{ sampleReport.institution }} · {{ sampleReport.date }}
                </p>
              </div>
              <span class="px-3 py-1 bg-emerald-100 text-emerald-700 rounded-full text-sm font-semibold">
                评级：{{ sampleReport.rating }}
              </span>
            </div>

            <div class="p-4 bg-indigo-50 border border-indigo-100 rounded-xl">
              <p class="text-sm text-indigo-900 leading-relaxed">{{ sampleReport.summary }}</p>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div
                v-for="item in sampleReport.highlights"
                :key="item.label"
                class="p-4 bg-slate-50 rounded-xl border border-slate-100"
              >
                <p class="text-xs text-slate-500 mb-1">{{ item.label }}</p>
                <p class="text-xl font-bold text-slate-900">{{ item.value }}</p>
                <p class="text-xs text-emerald-600 mt-1">{{ item.trend }}</p>
              </div>
            </div>

            <div class="space-y-4">
              <div
                v-for="section in sampleReport.sections"
                :key="section.title"
                class="border border-slate-200 rounded-xl overflow-hidden"
              >
                <div class="px-4 py-2 bg-slate-50 border-b border-slate-200">
                  <h5 class="font-semibold text-slate-800">{{ section.title }}</h5>
                </div>
                <p class="px-4 py-3 text-sm text-slate-600 whitespace-pre-line leading-relaxed">
                  {{ section.content }}
                </p>
              </div>
            </div>

            <div class="flex items-start gap-2 p-3 bg-amber-50 rounded-lg text-xs text-amber-800">
              <AlertTriangleIcon class="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span>本文为示例研报摘要，仅供学习参考，不构成投资建议。</span>
            </div>
          </div>

          <!-- 持仓再平衡 -->
          <div v-else-if="activeView === 'rebalance'">
            <div v-if="!rebalancePlan" class="py-12 text-center">
              <p class="text-slate-600 mb-4">暂无持仓数据，无法生成再平衡方案</p>
              <p class="text-sm text-slate-400">请先在「持仓导入」页录入您的持仓</p>
            </div>

            <div v-else class="space-y-6">
              <div class="p-4 bg-emerald-50 border border-emerald-100 rounded-xl">
                <p class="text-sm text-emerald-800">{{ rebalancePlan.summary }}</p>
                <p class="text-xs text-emerald-600 mt-2">
                  当前持仓总市值：{{ rebalancePlan.total.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) }} 元
                  · 共 {{ rebalancePlan.items.length }} 只资产
                </p>
              </div>

              <div class="overflow-x-auto rounded-xl border border-slate-200">
                <table class="w-full text-sm">
                  <thead class="bg-slate-50">
                    <tr>
                      <th class="text-left px-4 py-3 font-medium text-slate-600">资产</th>
                      <th class="text-right px-4 py-3 font-medium text-slate-600">当前占比</th>
                      <th class="text-right px-4 py-3 font-medium text-slate-600">目标占比</th>
                      <th class="text-right px-4 py-3 font-medium text-slate-600">偏离</th>
                      <th class="text-center px-4 py-3 font-medium text-slate-600">建议</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="item in rebalancePlan.items"
                      :key="item.code"
                      class="border-t border-slate-100 hover:bg-slate-50"
                    >
                      <td class="px-4 py-3">
                        <p class="font-medium text-slate-900">{{ item.name }}</p>
                        <p class="text-xs text-slate-400">{{ item.code }}</p>
                      </td>
                      <td class="px-4 py-3 text-right text-slate-700">{{ item.current }}%</td>
                      <td class="px-4 py-3 text-right text-indigo-600 font-medium">{{ item.target }}%</td>
                      <td class="px-4 py-3 text-right" :class="Number(item.diff) > 0 ? 'text-emerald-600' : 'text-amber-600'">
                        {{ Number(item.diff) > 0 ? '+' : '' }}{{ item.diff }}%
                      </td>
                      <td class="px-4 py-3 text-center">
                        <span class="px-2 py-1 rounded-full text-xs font-medium" :class="item.actionColor">
                          {{ item.action }}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div class="p-4 bg-blue-50 rounded-xl">
                  <p class="text-xs text-blue-600 mb-1">执行步骤 1</p>
                  <p class="text-sm text-blue-900">卖出超配标的，释放资金</p>
                </div>
                <div class="p-4 bg-blue-50 rounded-xl">
                  <p class="text-xs text-blue-600 mb-1">执行步骤 2</p>
                  <p class="text-sm text-blue-900">分批买入低配标的，降低冲击成本</p>
                </div>
                <div class="p-4 bg-blue-50 rounded-xl">
                  <p class="text-xs text-blue-600 mb-1">执行步骤 3</p>
                  <p class="text-sm text-blue-900">每季度复核一次，动态调整</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 专家复核 -->
          <div v-else-if="activeView === 'expert'">
            <div v-if="expertSubmitted" class="py-12 text-center">
              <CheckCircleIcon class="w-16 h-16 text-emerald-500 mx-auto mb-4" />
              <h4 class="text-lg font-bold text-slate-900 mb-2">预约提交成功</h4>
              <p class="text-sm text-slate-600 mb-6">
                资深投顾将在 1 个工作日内联系您（{{ expertForm.phone }}），请保持电话畅通。
              </p>
              <button
                type="button"
                class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                @click="handleClose"
              >
                完成
              </button>
            </div>

            <div v-else class="space-y-5">
              <div class="p-4 bg-purple-50 border border-purple-100 rounded-xl">
                <h4 class="font-semibold text-purple-900 mb-2">服务介绍</h4>
                <ul class="text-sm text-purple-800 space-y-1">
                  <li>· 资深投顾 1 对 1 视频/电话沟通（30 分钟）</li>
                  <li>· 基于您的持仓出具书面诊断报告</li>
                  <li>· 30 天内免费跟进 1 次</li>
                </ul>
              </div>

              <form class="space-y-4" @submit.prevent="submitExpertForm">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">姓名 *</label>
                  <input
                    v-model="expertForm.name"
                    type="text"
                    required
                    placeholder="请输入您的姓名"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">手机号 *</label>
                  <input
                    v-model="expertForm.phone"
                    type="tel"
                    required
                    placeholder="请输入联系电话"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">邮箱</label>
                  <input
                    v-model="expertForm.email"
                    type="email"
                    placeholder="选填，用于接收报告"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">期望沟通时间</label>
                  <input
                    v-model="expertForm.date"
                    type="date"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">关注问题</label>
                  <textarea
                    v-model="expertForm.concern"
                    rows="3"
                    placeholder="如：持仓过于集中、近期亏损较大等"
                    class="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <button
                  type="submit"
                  class="w-full py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
                >
                  提交预约
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
