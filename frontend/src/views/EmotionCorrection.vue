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
import RefreshIcon from '@/components/icons/RefreshIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const isSentimentLoading = ref(true);
const sentimentError = ref('');

const DATA_SOURCE_LABELS = {
  bias: '*基于用户真实持仓与 Tushare 行业分类数据计算*',
  estimate: '*基于持仓风险系数与盈亏状态的动态估算*',
  emotion: '*基于市场公开数据的实时计算*',
};

const DATA_SOURCE_MODAL_ITEMS = [
  { title: '情绪指数', desc: '基于 Tushare 换手率、涨跌比等数据计算' },
  { title: '行为偏差', desc: '基于用户真实持仓的行业集中度、亏损数量与分散程度计算' },
  { title: '矫正估算', desc: '基于持仓风险系数、持仓数量与当前盈亏百分比估算' },
];

const showDataSourceModal = ref(false);
const SENTIMENT_CACHE_KEY = 'emotion_sentiment_cache_v2';
const SENTIMENT_CACHE_TTL_MS = 8 * 60 * 1000;

interface PortfolioIndustryRow {
  code: string;
  name: string;
  type: string;
  industry: string;
}

interface PortfolioContext {
  asset_industries: PortfolioIndustryRow[];
}

const portfolioContext = ref<PortfolioContext | null>(null);
const isPortfolioContextLoading = ref(false);
const isRefreshingQuotes = ref(false);
const quoteRefreshMessage = ref('');
const lastQuoteRefreshTime = ref('');

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

const portfolioTotalCost = computed(() => {
  const total = portfolioStore.portfolio.totalCost;
  if (total > 0) return total;
  return portfolioAssets.value.reduce((sum, a) => sum + (a.costPrice || 0) * (a.quantity || 0), 0);
});

const normalizeTsCode = (code: string) => {
  const trimmed = code.trim().toUpperCase();
  if (trimmed.includes('.')) return trimmed;
  if (trimmed.startsWith('6') || trimmed.startsWith('5')) return `${trimmed}.SH`;
  return `${trimmed}.SZ`;
};

const bareCode = (code: string) => normalizeTsCode(code).replace(/\.(SH|SZ|BJ)$/i, '');

type RawAsset = Asset & {
  cost?: number;
  cost_price?: number;
  current_price?: number;
};

type AssetPnlStatus = 'profit' | 'loss' | 'missing' | 'breakeven';

interface AssetPnlRow {
  name: string;
  code: string;
  cost: number | null;
  currentPrice: number | null;
  status: AssetPnlStatus;
  statusLabel: string;
}

const readAssetCost = (asset: RawAsset): number | null => {
  const raw = asset as Record<string, unknown>;
  const candidates = [asset.costPrice, asset.cost, asset.cost_price, raw.cost, raw.cost_price];
  for (const value of candidates) {
    const num = Number(value);
    if (Number.isFinite(num) && num > 0) return num;
  }
  return null;
};

const readAssetCurrentPrice = (asset: RawAsset): number | null => {
  const raw = asset as Record<string, unknown>;
  const candidates = [asset.currentPrice, asset.current_price, raw.current_price];
  for (const value of candidates) {
    const num = Number(value);
    if (Number.isFinite(num) && num > 0) return num;
  }
  return null;
};

const getAssetPnlRow = (asset: RawAsset): AssetPnlRow => {
  const cost = readAssetCost(asset);
  const currentPrice = readAssetCurrentPrice(asset);

  if (cost == null || currentPrice == null) {
    return {
      name: asset.name,
      code: asset.code,
      cost,
      currentPrice,
      status: 'missing',
      statusLabel: '数据缺失',
    };
  }
  if (currentPrice < cost) {
    return {
      name: asset.name,
      code: asset.code,
      cost,
      currentPrice,
      status: 'loss',
      statusLabel: '亏损',
    };
  }
  if (currentPrice > cost) {
    return {
      name: asset.name,
      code: asset.code,
      cost,
      currentPrice,
      status: 'profit',
      statusLabel: '盈利',
    };
  }
  return {
    name: asset.name,
    code: asset.code,
    cost,
    currentPrice,
    status: 'breakeven',
    statusLabel: '持平',
  };
};

const assetPnlRows = computed(() => portfolioAssets.value.map(getAssetPnlRow));

const logAssetPnlDebug = (rows: AssetPnlRow[]) => {
  if (!rows.length) return;
  console.group('[情绪纠偏] 持仓盈亏判断');
  console.table(
    rows.map((row) => ({
      名称: row.name,
      代码: row.code,
      cost: row.cost,
      current_price: row.currentPrice,
      状态: row.statusLabel,
    })),
  );
  console.groupEnd();
};

watch(assetPnlRows, (rows) => {
  logAssetPnlDebug(rows);
}, { immediate: true, deep: true });

const industryByCode = computed(() => {
  const map = new Map<string, string>();
  for (const row of portfolioContext.value?.asset_industries ?? []) {
    map.set(normalizeTsCode(row.code), row.industry);
    map.set(bareCode(row.code), row.industry);
  }
  return map;
});

const resolveAssetIndustry = (asset: Asset): string => {
  const fromApi = industryByCode.value.get(normalizeTsCode(asset.code))
    ?? industryByCode.value.get(bareCode(asset.code));
  if (fromApi) return fromApi;
  if (asset.type === 'fund') return '基金';
  if (asset.type === 'bond') return '债券';
  if (asset.type === 'other') return '其他';
  return '综合';
};

const buildIndustryValueMap = () => {
  const industryMap = new Map<string, number>();
  for (const asset of portfolioAssets.value) {
    const industry = resolveAssetIndustry(asset);
    industryMap.set(industry, (industryMap.get(industry) || 0) + (asset.marketValue || 0));
  }
  return industryMap;
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

  const industryMap = buildIndustryValueMap();

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
    message: `${topIndustry}占比 ${pct}%`,
    severity: pct >= 50,
  };
});

const lossAversion = computed(() => {
  const rows = assetPnlRows.value;
  if (!rows.length) return null;

  const lossCount = rows.filter((row) => row.status === 'loss').length;
  const missingCount = rows.filter((row) => row.status === 'missing').length;

  return {
    count: lossCount,
    missingCount,
    rows,
    message: missingCount > 0
      ? `${lossCount} 只亏损，${missingCount} 只数据缺失`
      : `${lossCount} 只亏损`,
    severity: lossCount >= Math.ceil(rows.length / 2),
  };
});

const herdMentality = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const industryMap = buildIndustryValueMap();
  const industryCount = industryMap.size;
  const total = portfolioTotalValue.value;

  let maxPct = 0;
  let topIndustry = '';
  if (total > 0) {
    for (const [industry, value] of industryMap) {
      const pct = Math.round((value / total) * 100);
      if (pct > maxPct) {
        maxPct = pct;
        topIndustry = industry;
      }
    }
  }

  if (maxPct > 50) {
    return {
      level: '较高',
      message: `${topIndustry}行业占比 ${maxPct}%，跟风集中风险较高`,
      severity: true,
    };
  }
  if (industryCount >= 3) {
    return {
      level: '较低',
      message: `持仓分散在 ${industryCount} 个行业，羊群效应较低`,
      severity: false,
    };
  }
  return {
    level: '适中',
    message: `持仓覆盖 ${industryCount} 个行业，羊群效应适中`,
    severity: false,
  };
});

const overconfidence = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const count = assets.length;
  let level: '低' | '中' | '高' = '中';
  if (count < 5) level = '低';
  else if (count > 10) level = '高';

  const levelText = level === '低'
    ? '过度自信风险较低'
    : level === '高'
      ? '过度自信风险较高'
      : '过度自信风险适中';

  return {
    count,
    level,
    message: `持仓 ${count} 只，${levelText}`,
    severity: count > 10,
  };
});

const portfolioRiskCoef = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return 0;

  const sum = assets.reduce((acc, asset) => {
    const cost = readAssetCost(asset);
    const current = readAssetCurrentPrice(asset);
    if (cost == null || current == null) return acc;
    return acc + Math.abs(current - cost) / cost;
  }, 0);
  const validCount = assets.filter((asset) => readAssetCost(asset) != null && readAssetCurrentPrice(asset) != null).length;
  return validCount > 0 ? sum / validCount : 0;
});

const emotionIndexPosition = computed(() => Math.min(96, Math.max(4, emotionIndex.value)));

const portfolioPnlPct = computed(() => {
  const cost = portfolioTotalCost.value;
  const value = portfolioTotalValue.value;
  if (cost <= 0) return 0;
  return ((value - cost) / cost) * 100;
});

const behaviorEstimate = computed(() => {
  const assets = portfolioAssets.value;
  if (!assets.length) return null;

  const potentialLoss = Math.round(portfolioRiskCoef.value * 1000);
  const savedTrades = assets.length * 2;
  const pnl = portfolioPnlPct.value;
  const improvedReturn = pnl > 0
    ? Math.round(Math.min(10, 1 + pnl * 0.2) * 10) / 10
    : Math.round(Math.max(0.5, 1 + pnl * 0.05) * 10) / 10;

  return {
    potentialLoss,
    savedTrades,
    improvedReturn,
  };
});

const getEmotionBgColor = (index: number) => {
  if (index < 30) return 'bg-red-50';
  if (index <= 60) return 'bg-amber-50';
  return 'bg-emerald-50';
};

const getEmotionTextColor = (index: number) => {
  if (index < 30) return 'text-red-700';
  if (index <= 60) return 'text-amber-700';
  return 'text-emerald-700';
};

const getEmotionLabelColor = (index: number) => {
  if (index < 30) return 'bg-red-100 text-red-700';
  if (index <= 60) return 'bg-amber-100 text-amber-800';
  return 'bg-emerald-100 text-emerald-700';
};

const getEmotionBorderColor = (index: number) => {
  if (index < 30) return 'border-red-300';
  if (index <= 60) return 'border-amber-300';
  return 'border-emerald-300';
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

const fetchPortfolioContext = async () => {
  if (!hasPortfolio.value) {
    portfolioContext.value = null;
    return;
  }

  isPortfolioContextLoading.value = true;
  try {
    const response = await fetch('/api/market/emotion-portfolio-context', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        assets: portfolioAssets.value.map((asset) => ({
          code: asset.code,
          name: asset.name,
          type: asset.type,
        })),
      }),
    });
    if (!response.ok) {
      throw new Error('持仓行业数据获取失败');
    }
    const data = await response.json() as PortfolioContext & { hot_industries?: string[] };
    portfolioContext.value = { asset_industries: data.asset_industries };
  } catch {
    portfolioContext.value = {
      asset_industries: portfolioAssets.value.map((asset) => ({
        code: asset.code,
        name: asset.name,
        type: asset.type,
        industry: asset.type === 'fund' ? '基金' : asset.type === 'bond' ? '债券' : asset.type === 'other' ? '其他' : '综合',
      })),
    };
  } finally {
    isPortfolioContextLoading.value = false;
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

const handleRefreshQuotes = async () => {
  if (!hasPortfolio.value || isRefreshingQuotes.value) return;

  isRefreshingQuotes.value = true;
  quoteRefreshMessage.value = '';
  try {
    const result = await portfolioStore.refreshLiveQuotes();
    if (!result.ok || !result.assets?.length) {
      quoteRefreshMessage.value = '刷新现价失败，请稍后重试';
      return;
    }

    lastQuoteRefreshTime.value = result.updateTime || new Date().toLocaleString('zh-CN');
    const preview = result.assets
      .map((row) => `${row.code} ¥${row.current_price ?? '--'}`)
      .join(' · ');
    quoteRefreshMessage.value = `已刷新：${preview}`;
  } finally {
    isRefreshingQuotes.value = false;
  }
};

onMounted(async () => {
  portfolioStore.loadPortfolio();
  fetchSentimentData();
  if (hasPortfolio.value) {
    const quoteResult = await portfolioStore.refreshLiveQuotes();
    if (quoteResult.updateTime) {
      lastQuoteRefreshTime.value = quoteResult.updateTime;
    }
    fetchPortfolioContext();
  }
});

watch(portfolioAssets, () => {
  if (portfolioAssets.value.length > 0) {
    fetchPortfolioContext();
  }
}, { deep: true });
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
        <div class="ml-auto flex items-center gap-3">
          <button
            v-if="hasPortfolio"
            type="button"
            :disabled="isRefreshingQuotes"
            @click="handleRefreshQuotes"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            <RefreshIcon class="w-4 h-4" :class="{ 'animate-spin': isRefreshingQuotes }" />
            {{ isRefreshingQuotes ? '刷新中…' : '刷新现价' }}
          </button>
          <button
            type="button"
            @click="showDataSourceModal = true"
            class="text-sm text-indigo-600 hover:text-indigo-800 underline underline-offset-2"
          >
            数据来源
          </button>
        </div>
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
        v-if="quoteRefreshMessage"
        class="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-sm flex flex-wrap items-center justify-between gap-2"
      >
        <span>{{ quoteRefreshMessage }}</span>
        <span v-if="lastQuoteRefreshTime" class="text-xs text-emerald-600">{{ lastQuoteRefreshTime }}</span>
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
              <div class="flex-1 min-w-0">
                <div class="relative pt-8 pb-1">
                  <div
                    class="emotion-gradient-bar h-5 w-full rounded-full"
                    aria-hidden="true"
                  />
                  <div
                    class="absolute top-0 flex flex-col items-center -translate-x-1/2 transition-all duration-500 ease-out"
                    :style="{ left: `${emotionIndexPosition}%` }"
                  >
                    <div
                      class="emotion-index-marker min-w-[2.25rem] px-2 py-1 text-center text-sm font-bold text-white rounded-full shadow-lg"
                      :class="emotionIndex < 30 ? 'bg-red-500' : emotionIndex <= 60 ? 'bg-amber-500' : 'bg-emerald-500'"
                    >
                      {{ emotionIndex }}
                    </div>
                    <div
                      class="w-0 h-0 border-l-[7px] border-r-[7px] border-t-[8px] border-l-transparent border-r-transparent -mt-px"
                      :class="emotionIndex < 30 ? 'border-t-red-500' : emotionIndex <= 60 ? 'border-t-amber-500' : 'border-t-emerald-500'"
                    />
                  </div>
                </div>
                <div class="flex justify-between text-xs font-medium mt-2">
                  <span class="text-red-500">恐慌 (&lt;30)</span>
                  <span class="text-amber-500">平静 (30-60)</span>
                  <span class="text-emerald-500">贪婪 (&gt;60)</span>
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

            <div v-else-if="isPortfolioContextLoading" class="py-6 text-center text-sm text-slate-500">
              正在加载持仓行业数据...
            </div>

            <div v-else class="space-y-4">
              <div class="p-3 rounded-lg" :class="confirmationBias?.severity ? 'bg-amber-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">确认偏误</p>
                <p class="text-2xl font-bold text-slate-900 mb-1">{{ confirmationBias?.pct }}%</p>
                <p class="text-sm text-slate-600">{{ confirmationBias?.message }}</p>
              </div>
              <div class="p-3 rounded-lg" :class="lossAversion?.severity ? 'bg-red-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">损失厌恶</p>
                <p class="text-2xl font-bold text-slate-900 mb-1">{{ lossAversion?.count }} 只</p>
                <p class="text-sm text-slate-600 mb-3">{{ lossAversion?.message }}</p>
                <ul class="space-y-1.5 text-xs border-t border-slate-200/80 pt-3">
                  <li
                    v-for="row in lossAversion?.rows"
                    :key="row.code"
                    class="flex flex-wrap items-center justify-between gap-x-2 gap-y-0.5 text-slate-600"
                  >
                    <span class="font-medium text-slate-700">{{ row.name }}</span>
                    <span>
                      cost={{ row.cost ?? '—' }} · current_price={{ row.currentPrice ?? '—' }}
                      ·
                      <span
                        :class="row.status === 'loss' ? 'text-red-600' : row.status === 'profit' ? 'text-emerald-600' : row.status === 'missing' ? 'text-amber-600' : 'text-slate-500'"
                      >
                        {{ row.statusLabel }}
                      </span>
                    </span>
                  </li>
                </ul>
              </div>
              <div class="p-3 rounded-lg" :class="herdMentality?.severity ? 'bg-orange-50' : 'bg-slate-50'">
                <p class="text-sm font-medium text-slate-800 mb-1">羊群效应</p>
                <p class="text-2xl font-bold text-slate-900 mb-1">{{ herdMentality?.level }}</p>
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
              <p class="text-xs text-slate-500 mt-4">
                基于真实持仓计算 · 风险系数 {{ portfolioRiskCoef.toFixed(2) }} · 当前盈亏 {{ portfolioPnlPct.toFixed(1) }}%
              </p>
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

<style scoped>
.emotion-gradient-bar {
  background: linear-gradient(
    90deg,
    #ef4444 0%,
    #f97316 28%,
    #fb923c 42%,
    #fbbf24 50%,
    #84cc16 72%,
    #22c55e 100%
  );
  box-shadow:
    inset 0 1px 2px rgba(255, 255, 255, 0.35),
    0 4px 14px rgba(239, 68, 68, 0.18),
    0 2px 6px rgba(34, 197, 94, 0.15);
}

.emotion-index-marker {
  box-shadow:
    0 4px 10px rgba(0, 0, 0, 0.18),
    0 0 0 3px rgba(255, 255, 255, 0.95);
}
</style>
