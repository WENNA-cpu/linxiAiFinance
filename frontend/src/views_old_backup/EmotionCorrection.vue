<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import ActivityIcon from '@/components/icons/ActivityIcon.vue';
import TrendingUpIcon from '@/components/icons/TrendingUpIcon.vue';
import TrendingDownIcon from '@/components/icons/TrendingDownIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import BrainIcon from '@/components/icons/BrainIcon.vue';
import HeartIcon from '@/components/icons/HeartIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';
import CalculatorIcon from '@/components/icons/CalculatorIcon.vue';

const router = useRouter();

const emotionIndex = ref(68);
const userEmotion = ref('neutral');

const marketSentiment = {
  fearGreedIndex: 68,
  status: '贪婪',
  trend: 'up',
  extremeNews: [
    { title: '某板块暴涨，散户蜂拥入场', type: 'greed', time: '2小时前' },
    { title: '机构大幅减仓，市场恐慌情绪蔓延', type: 'fear', time: '5小时前' },
    { title: '政策利好刺激，相关板块涨停', type: 'greed', time: '8小时前' },
  ],
};

const userBias = {
  confirmationBias: 75,
  lossAversion: 82,
  herdMentality: 60,
  overconfidence: 45,
};

const correctionAdvice = [
  {
    title: '避免追涨杀跌',
    desc: '当前市场情绪偏热，建议保持冷静，避免追高热门板块。',
    icon: TrendingUpIcon,
    color: 'amber',
  },
  {
    title: '坚持定投策略',
    desc: '市场波动时，定投可以平滑成本，降低择时压力。',
    icon: CheckCircleIcon,
    color: 'emerald',
  },
  {
    title: '关注长期价值',
    desc: '短期情绪扰动不应影响对资产长期价值的判断。',
    icon: BrainIcon,
    color: 'blue',
  },
];

const behaviorEstimate = {
  potentialLoss: 8500,
  savedTrades: 12,
  improvedReturn: 3.2,
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
        <h1 class="text-xl font-bold text-slate-900">投资情绪纠偏</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-8">
        <div class="flex items-center gap-3">
          <HeartIcon class="w-6 h-6 text-purple-600" />
          <p class="text-sm text-purple-800">
            基于Tushare舆情数据实时监测市场情绪，结合行为金融学原理，帮助您识别并纠正投资情绪偏差。
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-6">市场情绪指数</h2>
            <div class="flex items-center gap-8">
              <div class="relative">
                <div class="w-32 h-32 rounded-full border-8 border-slate-200 flex items-center justify-center">
                  <div class="text-center">
                    <p class="text-3xl font-bold" :class="emotionIndex > 70 ? 'text-red-600' : emotionIndex > 30 ? 'text-amber-600' : 'text-emerald-600'">
                      {{ emotionIndex }}
                    </p>
                    <p class="text-xs text-slate-500">恐惧贪婪指数</p>
                  </div>
                </div>
                <div
                  class="absolute -top-2 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-sm font-medium"
                  :class="emotionIndex > 70 ? 'bg-red-100 text-red-700' : emotionIndex > 30 ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'"
                >
                  {{ marketSentiment.status }}
                </div>
              </div>
              <div class="flex-1">
                <div class="h-4 bg-gradient-to-r from-emerald-500 via-amber-500 to-red-500 rounded-full mb-2"></div>
                <div class="flex justify-between text-xs text-slate-500">
                  <span>极度恐惧</span>
                  <span>中性</span>
                  <span>极度贪婪</span>
                </div>
                <div class="mt-4 p-3 bg-amber-50 rounded-lg">
                  <div class="flex items-center gap-2">
                    <AlertTriangleIcon class="w-4 h-4 text-amber-600" />
                    <span class="text-sm text-amber-800 font-medium">市场情绪提示</span>
                  </div>
                  <p class="text-sm text-amber-700 mt-1">
                    当前市场情绪偏{{ marketSentiment.status }}，建议保持理性，避免盲目跟风。
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">极端舆情监测</h2>
            <div class="space-y-3">
              <div
                v-for="(news, index) in marketSentiment.extremeNews"
                :key="index"
                class="flex items-center gap-3 p-3 rounded-lg"
                :class="news.type === 'greed' ? 'bg-red-50' : 'bg-emerald-50'"
              >
                <component
                  :is="news.type === 'greed' ? TrendingUpIcon : TrendingDownIcon"
                  class="w-5 h-5"
                  :class="news.type === 'greed' ? 'text-red-500' : 'text-emerald-500'"
                />
                <div class="flex-1">
                  <p class="text-sm font-medium" :class="news.type === 'greed' ? 'text-red-900' : 'text-emerald-900'">
                    {{ news.title }}
                  </p>
                  <p class="text-xs" :class="news.type === 'greed' ? 'text-red-600' : 'text-emerald-600'">
                    {{ news.time }}
                  </p>
                </div>
                <span
                  class="px-2 py-1 text-xs rounded"
                  :class="news.type === 'greed' ? 'bg-red-200 text-red-800' : 'bg-emerald-200 text-emerald-800'"
                >
                  {{ news.type === 'greed' ? '过热' : '恐慌' }}
                </span>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">理性引导建议</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                v-for="advice in correctionAdvice"
                :key="advice.title"
                class="p-4 rounded-lg"
                :class="`bg-${advice.color}-50`"
              >
                <div class="flex items-center gap-2 mb-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center"
                    :class="`bg-${advice.color}-100`"
                  >
                    <component :is="advice.icon" class="w-4 h-4" :class="`text-${advice.color}-600`" />
                  </div>
                  <h4 class="font-medium" :class="`text-${advice.color}-900`">{{ advice.title }}</h4>
                </div>
                <p class="text-sm" :class="`text-${advice.color}-700`">{{ advice.desc }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">行为偏差检测</h2>
            <div class="space-y-4">
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-slate-600">确认偏误</span>
                  <span class="text-sm font-medium" :class="userBias.confirmationBias > 70 ? 'text-red-600' : 'text-slate-900'">
                    {{ userBias.confirmationBias }}%
                  </span>
                </div>
                <div class="h-2 bg-slate-200 rounded-full">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="userBias.confirmationBias > 70 ? 'bg-red-500' : 'bg-indigo-500'"
                    :style="{ width: `${userBias.confirmationBias}%` }"
                  ></div>
                </div>
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-slate-600">损失厌恶</span>
                  <span class="text-sm font-medium" :class="userBias.lossAversion > 70 ? 'text-red-600' : 'text-slate-900'">
                    {{ userBias.lossAversion }}%
                  </span>
                </div>
                <div class="h-2 bg-slate-200 rounded-full">
                  <div
                    class="h-full rounded-full transition-all"
                    :class="userBias.lossAversion > 70 ? 'bg-red-500' : 'bg-indigo-500'"
                    :style="{ width: `${userBias.lossAversion}%` }"
                  ></div>
                </div>
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-slate-600">羊群效应</span>
                  <span class="text-sm font-medium text-slate-900">{{ userBias.herdMentality }}%</span>
                </div>
                <div class="h-2 bg-slate-200 rounded-full">
                  <div
                    class="h-full bg-indigo-500 rounded-full"
                    :style="{ width: `${userBias.herdMentality}%` }"
                  ></div>
                </div>
              </div>
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-sm text-slate-600">过度自信</span>
                  <span class="text-sm font-medium text-slate-900">{{ userBias.overconfidence }}%</span>
                </div>
                <div class="h-2 bg-slate-200 rounded-full">
                  <div
                    class="h-full bg-indigo-500 rounded-full"
                    :style="{ width: `${userBias.overconfidence}%` }"
                  ></div>
                </div>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <CalculatorIcon class="w-5 h-5 text-indigo-600" />
              <h2 class="text-lg font-semibold text-slate-900">行为矫正估算</h2>
            </div>
            <div class="space-y-4">
              <div class="p-4 bg-emerald-50 rounded-lg">
                <p class="text-sm text-emerald-600 mb-1">避免潜在损失</p>
                <p class="text-2xl font-bold text-emerald-700">{{ behaviorEstimate.potentialLoss.toLocaleString() }}元/年</p>
              </div>
              <div class="p-4 bg-blue-50 rounded-lg">
                <p class="text-sm text-blue-600 mb-1">减少冲动交易</p>
                <p class="text-2xl font-bold text-blue-700">{{ behaviorEstimate.savedTrades }}次/年</p>
              </div>
              <div class="p-4 bg-purple-50 rounded-lg">
                <p class="text-sm text-purple-600 mb-1">提升收益率</p>
                <p class="text-2xl font-bold text-purple-700">+{{ behaviorEstimate.improvedReturn }}%</p>
              </div>
            </div>
            <p class="text-xs text-slate-500 mt-4">
              *基于历史数据模拟估算，实际效果因人而异
            </p>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <ShieldIcon class="w-5 h-5 text-indigo-600" />
              <h2 class="text-lg font-semibold text-slate-900">当前情绪状态</h2>
            </div>
            <div class="flex gap-2">
              <button
                v-for="emotion in ['fear', 'neutral', 'greed']"
                :key="emotion"
                @click="userEmotion = emotion"
                class="flex-1 py-2 rounded-lg text-sm font-medium transition-colors"
                :class="userEmotion === emotion
                  ? emotion === 'fear' ? 'bg-emerald-100 text-emerald-700 border-2 border-emerald-500'
                    : emotion === 'neutral' ? 'bg-blue-100 text-blue-700 border-2 border-blue-500'
                    : 'bg-red-100 text-red-700 border-2 border-red-500'
                  : 'bg-slate-100 text-slate-600'"
              >
                {{ emotion === 'fear' ? '恐慌' : emotion === 'neutral' ? '平静' : '贪婪' }}
              </button>
            </div>
            <div class="mt-4 p-3 bg-slate-50 rounded-lg">
              <p class="text-sm text-slate-600">
                {{ userEmotion === 'fear' ? '市场恐慌时往往是布局良机，但需区分系统性风险与情绪性下跌。'
                  : userEmotion === 'neutral' ? '保持当前理性状态，坚持既定投资策略。'
                  : '市场过热时需保持警惕，避免追高热门标的。' }}
              </p>
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
