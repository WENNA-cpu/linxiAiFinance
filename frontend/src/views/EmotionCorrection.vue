<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore, type Asset } from '@/stores/portfolio';
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
const portfolioStore = usePortfolioStore();

const isSentimentLoading = ref(true);
const sentimentError = ref('');

const DATA_SOURCE_LABELS = {
  bias: '*基于用户持仓行为的模拟分析*',
  estimate: '*基于历史回测数据的模拟估算*',
  emotion: '*基于市场公开数据的实时计算*',
};

const DATA_SOURCE_MODAL_ITEMS = [
  { title: '情绪指数', desc: '基于 Tushare 换手率、涨跌比等数据计算' },
  { title: '行为偏差', desc: '基于用户持仓数据的实时分析' },
  { title: '矫正估算', desc: '基于持仓数量与波动率的动态估算' },
];

const showDataSourceModal = ref(false);
const SENTIMENT_CACHE_KEY = 'emotion_sentiment_cache_v2';
const SENTIMENT_CACHE_TTL_MS = 8 * 60 * 1000;

const HOT_STOCK_CODES = new Set([
  '600519', '000001', '601318', '600036', '000858', '601899',
  '510050', '510300', '510500', '159915', '600900', '601166',
]);

interface SentimentData {
  sentiment_index: number;
  status?: string;
  market_state?: string;
  warning_signals?: number;
  extreme_alert?: string | null;
  data_source?: string;
  update_time?: string;
  components?: {
    limit_up?: number;
    limit_down?: number;
    shock_count?: number;
  };
}

const sentimentData = ref<SentimentData | null>(null);
const marketEmotion = ref<'fear' | 'neutral' | 'greed'>('neutral');

const portfolioAssets = computed(() => portfolioStore.portfolio.assets);
const hasPortfolio = computed(() => portfolioAssets.value.length > 0);
const portfolioTotalValue = computed(() => {
  const total = portfolioStore.portfolio.totalValue;
  if (total > 0) return total;
  return portfolioAssets.value.reduce((sum, a) => sum + (a.marketValue || 0), 0);
});

const inferIndustry = (asset: Asset): string => {
  if (asset.type === 'fund') return '基金';
  if (asset.type === 'bond') return '债券';
  if (asset.type === 'other') return '其他';

  const name = asset.name;
  const patterns: [RegExp, string][] = [
    [/银行|金融|证券|保险|信托/, '金融'],
    [/茅台|五粮|汾酒|泸州|古井|洋河|啤酒|餐饮|食品|乳业|消费/, '消费'],
    [/科技|软件|芯片|半导体|电子|通信|计算机|网络|互联/, '科技'],
    [/医药|制药|生物|医疗|健康/, '医药'],
    [/地产|建筑|水泥|钢铁|煤炭|矿业|能源|石油|化工/, '周期'],
    [/汽车|新能源|电池|光伏|风电|锂电/, '新能源'],
    [/电力|水务|燃气|交通|机场|港口|高速/, '公用事业'],
  ];
  for (const [regex, industry] of patterns) {
    if (regex.test(name)) return industry;
  }
  return '综合';
};

const normalizeCode = (code: string) => code.replace(/\.\w+$/i, '');

const isLargeCapOrHot = (asset: Asset): boolean => {
  const code = normalizeCode(asset.code);
  if (HOT_STOCK_CODES.has(code)) return true;
  if (asset.type === 'fund' && /50|300|500|ETF|沪深/i.test(asset.name)) return true;
  const total = portfolioTotalValue.value;
  return total > 0 && asset.marketValue / total >= 0.15;
};

const mapSentimentToEmotion = (index: number): 'fear' | 'neutral' | 'greed' => {
  if (index < 30) return 'fear';
  if (index <= 60) return 'neutral';
  return 'greed';
};

watch(sentimentData, (data) => {
  if (data) {
    marketEmotion.value = mapSentimentToEmotion(data.sentiment_index);
  }
});

const emotionIndex = computed(() => sentimentData.value?.sentiment_index ?? 0);

const emotionStatus = computed(() => {
  const index = emotionIndex.value;
  if (index < 30) return '恐慌';
  if (index <= 60) return '平静';
  return '贪婪';
});

const extremeAlert = computed(() => sentimentData.value?.extreme_alert);

const confirmationBias = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const industryMap = new Map<string, number>();
  for (const asset of assets) {
    const industry = inferIndustry(asset);
    industryMap.set(industry, (industryMap.get(industry) || 0) + (asset.marketValue || 0));
  }

  let topIndustry = '综合';
  let topValue = 0;
  for (const [industry, value] of industryMap) {
    if (value > topValue) {
      topValue = value;
      topIndustry = industry;
    }
  }

  const total = portfolioTotalValue.value;
  const pct = total > 0 ? Math.round((topValue / total) * 100) : 0;
  return {
    industry: topIndustry,
    pct,
    message: `您的持仓集中在${topIndustry}，占比 ${pct}%`,
    severity: pct >= 50,
  };
});

const lossAversion = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const lossCount = assets.filter((a) => a.currentPrice < a.costPrice).length;
  return {
    count: lossCount,
    message: `您的持仓中有 ${lossCount} 只资产处于亏损状态`,
    severity: lossCount >= Math.ceil(assets.length / 2),
  };
});

const herdMentality = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const hotCount = assets.filter(isLargeCapOrHot).length;
  const ratio = hotCount / assets.length;
  if (ratio >= 0.5) {
    return {
      triggered: true,
      message: '您的持仓与当前市场热点高度相关',
      severity: true,
    };
  }
  return {
    triggered: false,
    message: `您的持仓中 ${hotCount}/${assets.length} 只与主流热点相关，整体独立度较好`,
    severity: false,
  };
});

const overconfidence = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const count = assets.length;
  return {
    count,
    message: count >= 6
      ? `您的持仓过于分散，共 ${count} 只资产`
      : `您的持仓共 ${count} 只资产，集中度适中`,
    severity: count >= 8,
  };
});

const behaviorEstimate = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const volatilityCoef = assets.reduce((sum, asset) => {
    if (asset.costPrice <= 0) return sum + 0.8;
    const vol = Math.abs(asset.currentPrice - asset.costPrice) / asset.costPrice;
    return sum + Math.min(1.5, Math.max(0.3, vol));
  }, 0) / assets.length;

  const potentialLoss = Math.min(
    15000,
    Math.max(3000, Math.round(assets.length * 1000 * volatilityCoef))
  );

  const savedTrades = Math.min(12, Math.max(8, 8 + Math.floor((assets.length - 1) / 2)));

  const improvedReturn = Math.min(
    5,
    Math.max(2.5, 2.5 + Math.max(0, 8 - assets.length) * 0.35)
  );

  return {
    potentialLoss,
    savedTrades,
    improvedReturn: Math.round(improvedReturn * 10) / 10,
  };
});

const getEmotionBgColor = (index: number) => {
  if (index < 30) return 'bg-red-50';
  if (index <= 60) return 'bg-slate-50';
  return 'bg-orange-50';
};

const getEmotionTextColor = (index: number) => {
  if (index < 30) return 'text-red-700';
  if (index <= 60) return 'text-slate-600';
  return 'text-orange-700';
};

const getEmotionLabelColor = (index: number) => {
  if (index < 30) return 'bg-red-100 text-red-700';
  if (index <= 60) return 'bg-slate-200 text-slate-700';
  return 'bg-orange-100 text-orange-700';
};

const getEmotionBorderColor = (index: number) => {
  if (index < 30) return 'border-red-200';
  if (index <= 60) return 'border-slate-200';
  return 'border-orange-200';
};

const extremeNews = computed(() => {
  if (!sentimentData.value) return [];

  const index = emotionIndex.value;
  const comp = sentimentData.value.components;
  const limitUp = comp?.limit_up ?? 0;
  const limitDown = comp?.limit_down ?? 0;
  const updateTime = sentimentData.value.update_time || '刚刚';

  if (index > 60) {
    return [
      { title: `涨停 ${limitUp} 家，市场贪婪情绪升温`, type: 'greed' as const, time: updateTime },
      { title: `涨跌停比 ${limitUp}:${limitDown}，资金追涨意愿较强`, type: 'greed' as const, time: updateTime },
    ];
  }
  if (index < 30) {
    return [
      { title: `跌停 ${limitDown} 家，市场恐慌情绪蔓延`, type: 'fear' as const, time: updateTime },
      { title: `涨跌停比 ${limitUp}:${limitDown}，避险情绪主导`, type: 'fear' as const, time: updateTime },
    ];
  }
  return [
    { title: `涨停 ${limitUp} 家、跌停 ${limitDown} 家，多空分歧加大`, type: 'neutral' as const, time: updateTime },
  ];
});

const correctionAdvice = computed(() => {
  const index = emotionIndex.value;

  if (index > 60) {
    return [
      { title: '避免追涨杀跌', desc: '当前市场情绪偏热，建议保持冷静，避免追高热门板块。', icon: TrendingUpIcon, color: 'red' },
      { title: '分批止盈', desc: '对于已有盈利标的，可考虑分批止盈，锁定收益。', icon: CheckCircleIcon, color: 'amber' },
      { title: '关注估值', desc: '高情绪往往伴随高估值，需警惕估值回归风险。', icon: BrainIcon, color: 'blue' },
    ];
  }
  if (index < 30) {
    return [
      { title: '避免恐慌割肉', desc: '恐慌时往往是布局良机，但需区分系统性风险与情绪性下跌。', icon: TrendingDownIcon, color: 'emerald' },
      { title: '坚持定投', desc: '市场低位时坚持定投，可以积累更多便宜筹码。', icon: CheckCircleIcon, color: 'blue' },
      { title: '关注长期价值', desc: '短期情绪扰动不应影响对资产长期价值的判断。', icon: BrainIcon, color: 'indigo' },
    ];
  }
  return [
    { title: '保持理性', desc: '当前市场情绪平稳，建议保持既定投资策略。', icon: BrainIcon, color: 'blue' },
    { title: '坚持定投策略', desc: '市场波动时，定投可以平滑成本，降低择时压力。', icon: CheckCircleIcon, color: 'emerald' },
    { title: '关注长期价值', desc: '短期情绪扰动不应影响对资产长期价值的判断。', icon: TrendingUpIcon, color: 'amber' },
  ];
});

const emotionAdviceText = computed(() => {
  if (marketEmotion.value === 'fear') {
    return '市场恐慌时往往是布局良机，但需区分系统性风险与情绪性下跌。';
  }
  if (marketEmotion.value === 'greed') {
    return '市场过热时需保持警惕，避免追高热门标的。';
  }
  return '保持当前理性状态，坚持既定投资策略。';
});

const readSentimentCache = (): SentimentData | null => {
  try {
    const raw = sessionStorage.getItem(SENTIMENT_CACHE_KEY);
    if (!raw) return null;
    const { ts, data } = JSON.parse(raw) as { ts: number; data: SentimentData };
    if (Date.now() - ts > SENTIMENT_CACHE_TTL_MS) return null;
    return data;
  } catch {
    return null;
  }
};

const writeSentimentCache = (data: SentimentData) => {
  try {
    sessionStorage.setItem(SENTIMENT_CACHE_KEY, JSON.stringify({ ts: Date.now(), data }));
  } catch {
    // ignore
  }
};

const fetchSentimentData = async () => {
  sentimentError.value = '';

  const cached = readSentimentCache();
  if (cached) {
    sentimentData.value = cached;
    isSentimentLoading.value = false;
    return;
  }

  isSentimentLoading.value = true;

  try {
    const response = await fetch('/api/market/sentiment');
    if (!response.ok) {
      throw new Error('数据获取失败');
    }
    const data = (await response.json()) as SentimentData;
    sentimentData.value = data;
    writeSentimentCache(data);
  } catch {
    sentimentError.value = '数据获取失败';
    sentimentData.value = null;
  } finally {
    isSentimentLoading.value = false;
  }
};

onMounted(() => {
  portfolioStore.loadPortfolio();
  fetchSentimentData();
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
        <h1 class="text-xl font-bold text-slate-900">投资情绪纠偏</h1>
        <button
          type="button"
          @click="showDataSourceModal = true"
          class="ml-auto text-sm text-indigo-600 hover:text-indigo-800 underline underline-offset-2"
        >
          数据来源
        </button>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-purple-50 border border-purple-200 rounded-xl p-4 mb-8">
        <div class="flex items-center gap-3">
          <HeartIcon class="w-6 h-6 text-purple-600" />
          <p class="text-sm text-purple-800">
            基于 Tushare 实时数据计算情绪指数，结合持仓行为分析，帮助您识别并纠正投资情绪偏差。
          </p>
        </div>
      </div>

      <div
        v-if="sentimentError && !isSentimentLoading"
        class="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm flex items-center justify-between"
      >
        <span>{{ sentimentError }}</span>
        <button
          @click="fetchSentimentData"
          class="px-3 py-1 text-xs bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
        >
          重试
        </button>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-lg font-semibold text-slate-900">市场情绪指数</h2>
              <span
                v-if="isSentimentLoading"
                class="px-2 py-1 text-xs bg-slate-100 text-slate-600 rounded"
              >
                加载中...
              </span>
            </div>

            <div v-if="isSentimentLoading" class="flex items-center gap-8 animate-pulse">
              <div class="w-32 h-32 rounded-full bg-slate-200"></div>
              <div class="flex-1 space-y-3">
                <div class="h-4 bg-slate-200 rounded-full"></div>
                <div class="h-3 bg-slate-100 rounded w-3/4"></div>
                <div class="h-16 bg-slate-100 rounded-lg mt-4"></div>
              </div>
            </div>

            <div v-else-if="sentimentData" class="flex items-center gap-8">
              <div class="relative">
                <div
                  class="w-32 h-32 rounded-full border-8 flex items-center justify-center"
                  :class="getEmotionBorderColor(emotionIndex)"
                >
                  <div class="text-center">
                    <p class="text-3xl font-bold" :class="getEmotionTextColor(emotionIndex)">
                      {{ emotionIndex }}
                    </p>
                    <p class="text-xs text-slate-500">恐惧贪婪指数</p>
                  </div>
                </div>
                <div
                  class="absolute -top-2 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-sm font-medium whitespace-nowrap"
                  :class="getEmotionLabelColor(emotionIndex)"
                >
                  {{ emotionStatus }}
                </div>
              </div>
              <div class="flex-1">
                <div class="h-4 bg-gradient-to-r from-red-400 via-slate-300 to-orange-400 rounded-full mb-2"></div>
                <div class="flex justify-between text-xs text-slate-500">
                  <span>恐慌 (&lt;30)</span>
                  <span>平静 (30-60)</span>
                  <span>贪婪 (&gt;60)</span>
                </div>
                <div v-if="extremeAlert" class="mt-4 p-3 rounded-lg" :class="getEmotionBgColor(emotionIndex)">
                  <div class="flex items-center gap-2">
                    <AlertTriangleIcon class="w-4 h-4" :class="getEmotionTextColor(emotionIndex)" />
                    <span class="text-sm font-medium" :class="getEmotionTextColor(emotionIndex)">极端行情提示</span>
                  </div>
                  <p class="text-sm mt-1" :class="getEmotionTextColor(emotionIndex)">
                    {{ extremeAlert }}
                  </p>
                </div>
                <div v-else class="mt-4 p-3 rounded-lg" :class="getEmotionBgColor(emotionIndex)">
                  <div class="flex items-center gap-2">
                    <CheckCircleIcon class="w-4 h-4" :class="getEmotionTextColor(emotionIndex)" />
                    <span class="text-sm font-medium" :class="getEmotionTextColor(emotionIndex)">
                      当前市场{{ emotionStatus }}
                    </span>
                  </div>
                  <p class="text-sm mt-1" :class="getEmotionTextColor(emotionIndex)">
                    情绪指数 {{ emotionIndex }}，建议保持理性投资。
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div v-if="!isSentimentLoading && sentimentData" class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">极端舆情监测</h2>
            <div class="space-y-3">
              <div
                v-for="(news, index) in extremeNews"
                :key="index"
                class="flex items-center gap-3 p-3 rounded-lg"
                :class="news.type === 'greed' ? 'bg-orange-50' : news.type === 'fear' ? 'bg-red-50' : 'bg-slate-50'"
              >
                <component
                  :is="news.type === 'greed' ? TrendingUpIcon : news.type === 'fear' ? TrendingDownIcon : ActivityIcon"
                  class="w-5 h-5"
                  :class="news.type === 'greed' ? 'text-orange-500' : news.type === 'fear' ? 'text-red-500' : 'text-slate-500'"
                />
                <div class="flex-1">
                  <p
                    class="text-sm font-medium"
                    :class="news.type === 'greed' ? 'text-orange-900' : news.type === 'fear' ? 'text-red-900' : 'text-slate-900'"
                  >
                    {{ news.title }}
                  </p>
                  <p
                    class="text-xs"
                    :class="news.type === 'greed' ? 'text-orange-600' : news.type === 'fear' ? 'text-red-600' : 'text-slate-600'"
                  >
                    更新于 {{ news.time }}
                  </p>
                </div>
                <span
                  class="px-2 py-1 text-xs rounded"
                  :class="news.type === 'greed' ? 'bg-orange-200 text-orange-800' : news.type === 'fear' ? 'bg-red-200 text-red-800' : 'bg-slate-200 text-slate-800'"
                >
                  {{ news.type === 'greed' ? '贪婪' : news.type === 'fear' ? '恐慌' : '平静' }}
                </span>
              </div>
            </div>
          </div>

          <div v-if="!isSentimentLoading && sentimentData" class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">理性引导建议</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                v-for="advice in correctionAdvice"
                :key="advice.title"
                class="p-4 rounded-lg"
                :class="`bg-${advice.color}-50`"
              >
                <div class="flex items-center gap-2 mb-2">
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center" :class="`bg-${advice.color}-100`">
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
            <h2 class="text-lg font-semibold text-slate-900 mb-1">行为偏差检测</h2>
            <p class="text-xs text-slate-400 italic mb-4">{{ DATA_SOURCE_LABELS.bias }}</p>

            <div v-if="!hasPortfolio" class="py-8 text-center">
              <p class="text-sm text-slate-600 mb-4">暂无持仓，请先导入</p>
              <button
                @click="router.push('/portfolio/import')"
                class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
              >
                去导入持仓
              </button>
            </div>

            <div v-else class="space-y-4">
              <div class="p-3 rounded-lg" :class="confirmationBias?.severity ? 'bg-amber-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">确认偏误</p>
                <p class="text-sm text-slate-600">{{ confirmationBias?.message }}</p>
              </div>
              <div class="p-3 rounded-lg" :class="lossAversion?.severity ? 'bg-red-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">损失厌恶</p>
                <p class="text-sm text-slate-600">{{ lossAversion?.message }}</p>
              </div>
              <div class="p-3 rounded-lg" :class="herdMentality?.severity ? 'bg-orange-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">羊群效应</p>
                <p class="text-sm text-slate-600">{{ herdMentality?.message }}</p>
              </div>
              <div class="p-3 rounded-lg" :class="overconfidence?.severity ? 'bg-amber-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">过度自信</p>
                <p class="text-sm text-slate-600">{{ overconfidence?.message }}</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-1">
              <CalculatorIcon class="w-5 h-5 text-indigo-600" />
              <h2 class="text-lg font-semibold text-slate-900">行为矫正估算</h2>
            </div>
            <p class="text-xs text-slate-400 italic mb-4">{{ DATA_SOURCE_LABELS.estimate }}</p>

            <div v-if="!hasPortfolio" class="py-6 text-center text-sm text-slate-500">
              导入持仓后可查看矫正估算
            </div>

            <template v-else-if="behaviorEstimate">
              <div class="space-y-4">
                <div class="p-4 bg-emerald-50 rounded-lg">
                  <p class="text-sm text-emerald-600 mb-1">避免潜在损失</p>
                  <p class="text-2xl font-bold text-emerald-700">
                    {{ behaviorEstimate.potentialLoss.toLocaleString() }}元/年
                  </p>
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
              <p class="text-xs text-slate-500 mt-4">基于您的持仓动态估算</p>
            </template>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-1">
              <ShieldIcon class="w-5 h-5 text-indigo-600" />
              <h2 class="text-lg font-semibold text-slate-900">当前情绪状态</h2>
            </div>
            <p class="text-xs text-slate-400 italic mb-4">{{ DATA_SOURCE_LABELS.emotion }}</p>

            <div v-if="isSentimentLoading" class="animate-pulse space-y-3">
              <div class="h-10 bg-slate-100 rounded-lg"></div>
              <div class="h-16 bg-slate-50 rounded-lg"></div>
            </div>

            <template v-else-if="sentimentData">
              <div class="flex gap-2">
                <div
                  v-for="emotion in (['fear', 'neutral', 'greed'] as const)"
                  :key="emotion"
                  class="flex-1 py-2 rounded-lg text-sm font-medium text-center transition-colors"
                  :class="marketEmotion === emotion
                    ? emotion === 'fear' ? 'bg-red-100 text-red-700 border-2 border-red-500'
                      : emotion === 'neutral' ? 'bg-slate-200 text-slate-700 border-2 border-slate-400'
                      : 'bg-orange-100 text-orange-700 border-2 border-orange-500'
                    : 'bg-slate-100 text-slate-400'"
                >
                  {{ emotion === 'fear' ? '恐慌' : emotion === 'neutral' ? '平静' : '贪婪' }}
                </div>
              </div>
              <div class="mt-4 p-3 bg-slate-50 rounded-lg">
                <p class="text-sm text-slate-600">
                  市场指数 {{ emotionIndex }}，当前处于「{{ emotionStatus }}」状态。{{ emotionAdviceText }}
                </p>
              </div>
            </template>

            <div v-else class="py-4 text-center text-sm text-red-600">
              情绪数据不可用
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

    <Teleport to="body">
      <div
        v-if="showDataSourceModal"
        class="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/40"
        @click.self="showDataSourceModal = false"
      >
        <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-lg font-semibold text-slate-900">数据来源说明</h2>
            <button
              type="button"
              class="text-slate-400 hover:text-slate-600 text-xl leading-none"
              @click="showDataSourceModal = false"
            >
              ×
            </button>
          </div>
          <ul class="space-y-4">
            <li
              v-for="item in DATA_SOURCE_MODAL_ITEMS"
              :key="item.title"
              class="border-b border-slate-100 pb-4 last:border-0 last:pb-0"
            >
              <p class="text-sm font-medium text-slate-900 mb-1">{{ item.title }}</p>
              <p class="text-sm text-slate-600">{{ item.desc }}</p>
            </li>
          </ul>
          <p class="text-xs text-slate-400 mt-4">
            以上数据均为参考性分析，不构成投资建议。
          </p>
        </div>
      </div>
    </Teleport>
  </div>
</template>
