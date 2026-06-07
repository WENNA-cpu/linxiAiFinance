<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import ConfidenceGauge from '@/components/ConfidenceGauge.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import SearchIcon from '@/components/icons/SearchIcon.vue';
import ThumbsUpIcon from '@/components/icons/ThumbsUpIcon.vue';
import ThumbsDownIcon from '@/components/icons/ThumbsDownIcon.vue';
import TrendingUpIcon from '@/components/icons/TrendingUpIcon.vue';
import TrendingDownIcon from '@/components/icons/TrendingDownIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import PieChartIcon from '@/components/icons/PieChartIcon.vue';
import ActivityIcon from '@/components/icons/ActivityIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const showDisclaimer = ref(true);
const feedbackType = ref<'positive' | 'negative' | null>(null);
const feedbackReason = ref('');
const feedbackSubmitted = ref(false);
const feedbackSubmitting = ref(false);
const isLoading = ref(false);
const diagnosisError = ref('');
const diagnosisData = ref<any>(null);

const normalizeDiagnosis = (raw: any) => {
  if (!raw) return null;
  const summary = raw.summary || {};
  const analysis = raw.analysis || {};
  const dataSource = raw.data_source || raw.dataSource || {};
  return {
    request_id: raw.request_id || raw.requestId || `diag_${Date.now()}`,
    confidence: raw.confidence ?? 85,
    summary: {
      total_assets: summary.total_assets ?? summary.totalAssets ?? 0,
      risk_assets: summary.risk_assets ?? summary.riskAssets ?? 0,
      opportunity_assets: summary.opportunity_assets ?? summary.opportunityAssets ?? 0,
      time_saved: summary.time_saved ?? summary.timeSaved ?? 0,
    },
    analysis: {
      market_trend: analysis.market_trend ?? analysis.marketTrend ?? '当前市场处于震荡整理阶段',
      sector_rotation: analysis.sector_rotation ?? analysis.sectorRotation ?? '资金从高估值流向低估值板块',
      risk_points: analysis.risk_points ?? analysis.riskPoints ?? [],
      opportunities: analysis.opportunities ?? [],
    },
    data_source: {
      time_range: dataSource.time_range ?? dataSource.timeRange ?? '2026-01-01 至 2026-06-01',
      sources: dataSource.sources ?? ['Tushare 行情数据', '行业研报'],
      update_time: dataSource.update_time ?? dataSource.updateTime ?? new Date().toLocaleString('zh-CN'),
    },
    detail: raw.detail || { assets: [] },
    audit_logs: raw.audit_logs || [],
  };
};

const buildFallbackDiagnosis = () => {
  const assets = portfolioStore.portfolio.assets;
  const totalValue = portfolioStore.portfolio.totalValue || 1;
  const riskCount = assets.filter((a) => {
    if (!a.costPrice || !a.currentPrice) return false;
    return ((a.currentPrice - a.costPrice) / a.costPrice) * 100 < -5;
  }).length;
  const oppCount = assets.filter((a) => {
    if (!a.costPrice || !a.currentPrice) return false;
    return ((a.currentPrice - a.costPrice) / a.costPrice) * 100 > 5;
  }).length;

  return normalizeDiagnosis({
    request_id: `diag_fallback_${Date.now()}`,
    confidence: 85,
    summary: {
      total_assets: assets.length,
      risk_assets: riskCount,
      opportunity_assets: oppCount,
      time_saved: assets.length * 5,
    },
    analysis: {
      market_trend: '当前市场处于震荡整理阶段，建议关注持仓结构与风险分散。',
      sector_rotation: '资金从高估值流向低估值板块，可关注板块轮动机会。',
      risk_points: riskCount
        ? [`${riskCount} 只资产处于亏损状态，建议关注风险控制`]
        : ['当前持仓风险可控，建议持续关注市场变化'],
      opportunities: oppCount
        ? [`${oppCount} 只资产盈利较好，可考虑适当止盈`]
        : ['建议关注低估值优质资产的配置机会'],
    },
    data_source: {
      time_range: '2026-01-01 至 2026-06-01',
      sources: ['Tushare 行情数据', '行业研报'],
      update_time: new Date().toLocaleString('zh-CN'),
    },
    detail: {
      assets: assets.map((a) => ({
        code: a.code,
        name: a.name,
        weight: a.marketValue / totalValue,
        cost_price: a.costPrice,
        current_price: a.currentPrice,
        profit_pct: a.costPrice > 0
          ? ((a.currentPrice - a.costPrice) / a.costPrice) * 100
          : 0,
        data_source: '用户导入数据',
      })),
    },
  });
};

const applyDiagnosis = (raw: any) => {
  const normalized = normalizeDiagnosis(raw);
  if (!normalized) return;
  diagnosisData.value = normalized;
  localStorage.setItem(`diagnosis_${normalized.request_id}`, JSON.stringify(normalized));
  localStorage.setItem('last_diagnosis_id', normalized.request_id);
};

// 调用后端 API 获取诊断结果
const fetchDiagnosis = async () => {
  const assets = portfolioStore.portfolio.assets;
  if (assets.length === 0) return;

  isLoading.value = true;
  diagnosisError.value = '';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 45000);

  try {
    const totalValue = portfolioStore.portfolio.totalValue || 1;
    const payload = {
      assets: assets.map(a => ({
        code: a.code,
        name: a.name,
        weight: a.marketValue / totalValue,
        cost_price: a.costPrice,
        current_price: a.currentPrice,
      })),
      total_value: portfolioStore.portfolio.totalValue,
    };

    const response = await fetch('/api/portfolio/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `诊断请求失败 (${response.status})`);
    }

    const data = await response.json();
    applyDiagnosis(data);
  } catch (err) {
    const isAbort = err instanceof Error && err.name === 'AbortError';
    diagnosisError.value = isAbort
      ? '诊断请求超时，已展示本地降级结果'
      : (err instanceof Error ? err.message : '获取诊断结果失败');
    applyDiagnosis(buildFallbackDiagnosis());
  } finally {
    clearTimeout(timeoutId);
    isLoading.value = false;
  }
};

// 基于store判断是否有持仓数据
const hasRealData = computed(() => portfolioStore.portfolio.assets.length > 0);

// 从store计算真实持仓数据
const storeAssets = computed(() => portfolioStore.portfolio.assets);
const storeAssetCount = computed(() => storeAssets.value.length);

// 诊断结果（优先使用后端 API 数据）
const diagnosisResult = computed(() => {
  if (storeAssetCount.value === 0) {
    return {
      requestId: '-',
      confidence: 0,
      summary: {
        totalAssets: 0,
        riskAssets: 0,
        opportunityAssets: 0,
        timeSaved: 0,
      },
      analysis: {
        marketTrend: '暂无持仓数据，请先导入持仓',
        sectorRotation: '暂无持仓数据，请先导入持仓',
        riskPoints: ['暂无持仓数据，请先导入持仓'],
        opportunities: ['暂无持仓数据，请先导入持仓'],
      },
      dataSource: {
        timeRange: '-',
        sources: [],
        updateTime: '-',
      },
    };
  }

  if (diagnosisData.value) {
    const d = diagnosisData.value;
    return {
      requestId: d.request_id,
      confidence: d.confidence ?? 85,
      summary: {
        totalAssets: d.summary?.total_assets ?? storeAssetCount.value,
        riskAssets: d.summary?.risk_assets ?? 0,
        opportunityAssets: d.summary?.opportunity_assets ?? 0,
        timeSaved: d.summary?.time_saved ?? storeAssetCount.value * 5,
      },
      analysis: {
        marketTrend: d.analysis?.market_trend ?? '当前市场处于震荡整理阶段',
        sectorRotation: d.analysis?.sector_rotation ?? '资金从高估值流向低估值板块',
        riskPoints: d.analysis?.risk_points?.length
          ? d.analysis.risk_points
          : ['当前持仓风险可控，建议持续关注市场变化'],
        opportunities: d.analysis?.opportunities?.length
          ? d.analysis.opportunities
          : ['建议关注低估值优质资产的配置机会'],
      },
      dataSource: {
        timeRange: d.data_source?.time_range ?? '2026-01-01 至 2026-06-01',
        sources: d.data_source?.sources ?? ['Tushare 行情数据', '行业研报'],
        updateTime: d.data_source?.update_time ?? '-',
      },
    };
  }

  return {
    requestId: '-',
    confidence: 0,
    summary: { totalAssets: storeAssetCount.value, riskAssets: 0, opportunityAssets: 0, timeSaved: 0 },
    analysis: {
      marketTrend: isLoading.value ? '正在分析...' : '暂无诊断数据',
      sectorRotation: isLoading.value ? '正在分析...' : '暂无诊断数据',
      riskPoints: [],
      opportunities: [],
    },
    dataSource: { timeRange: '-', sources: [], updateTime: '-' },
  };
});

interface BackendAsset {
  code: string;
  name: string;
  weight: number;
  cost_price?: number;
  current_price?: number;
  profit_pct?: number;  // 基于成本价的盈亏百分比
  trade_date?: string;  // 数据日期
  data_source?: string;
}

const assetAnalysis = computed(() => {
  const assets = portfolioStore.portfolio.assets;
  if (assets.length === 0) {
    return [];
  }

  const backendAssets: BackendAsset[] = diagnosisData.value?.detail?.assets || [];
  const backendAssetsMap = new Map(backendAssets.map((a) => [a.code, a]));

  return assets.map(asset => {
    const backendAsset = backendAssetsMap.get(asset.code);
    const profitPct = backendAsset?.profit_pct ?? (
      asset.costPrice > 0 && asset.currentPrice > 0
        ? ((asset.currentPrice - asset.costPrice) / asset.costPrice) * 100
        : 0
    );

    return {
      ...asset,
      returnRate: profitPct,
      dataSource: backendAsset?.data_source || '用户持仓数据',
      tradeDate: backendAsset?.trade_date || '',
      riskLevel: profitPct < -5 ? 'high' : profitPct > 5 ? 'low' : 'medium',
      trend: profitPct >= 0 ? 'up' : 'down',
    };
  });
});

type ToastType = 'success' | 'error';

const toast = ref({
  visible: false,
  fading: false,
  message: '',
  type: 'success' as ToastType,
});

let toastTimer: ReturnType<typeof setTimeout> | null = null;
let toastFadeTimer: ReturnType<typeof setTimeout> | null = null;

const hideToast = () => {
  if (toastTimer) {
    clearTimeout(toastTimer);
    toastTimer = null;
  }
  if (!toast.value.visible) return;
  toast.value.fading = true;
  if (toastFadeTimer) clearTimeout(toastFadeTimer);
  toastFadeTimer = setTimeout(() => {
    toast.value.visible = false;
    toast.value.fading = false;
  }, 300);
};

const showToast = (message: string, type: ToastType) => {
  if (toastTimer) clearTimeout(toastTimer);
  if (toastFadeTimer) clearTimeout(toastFadeTimer);
  toast.value = { visible: true, fading: false, message, type };
  toastTimer = setTimeout(() => hideToast(), 2500);
};

const handleFeedbackClick = async (type: 'positive' | 'negative') => {
  if (feedbackSubmitting.value) return;
  feedbackType.value = type;
  await submitFeedback(type === 'negative' ? '' : undefined);
};

const submitFeedback = async (reasonOverride?: string) => {
  const requestId = diagnosisResult.value.requestId;
  if (!requestId || requestId === '-') {
    showToast('暂无诊断记录，无法提交反馈', 'error');
    return;
  }
  if (!feedbackType.value) return;

  feedbackSubmitting.value = true;
  try {
    const reason = reasonOverride !== undefined ? reasonOverride : feedbackReason.value;
    const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        request_id: requestId,
        feedback_type: feedbackType.value === 'positive' ? 'helpful' : 'unhelpful',
        reason: reason || '',
      }),
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `反馈提交失败 (${response.status})`);
    }

    const data = await response.json();
    feedbackSubmitted.value = true;
    showToast(data.message || '感谢您的反馈，这能帮助我们做得更好！', 'success');

    if (feedbackType.value === 'positive') {
      feedbackReason.value = '';
    }
  } catch (err) {
    showToast(err instanceof Error ? err.message : '反馈提交失败，请稍后重试', 'error');
  } finally {
    feedbackSubmitting.value = false;
  }
};

const submitNegativeReason = async () => {
  if (!feedbackReason.value.trim()) {
    showToast('请先填写改进建议', 'error');
    return;
  }
  await submitFeedback(feedbackReason.value);
};

// 合规追问助手
const followUpQuestion = ref('');
const followUpLoading = ref(false);
const followUpStatus = ref<'idle' | 'blocked' | 'passed' | 'error'>('idle');
const followUpBlockedReason = ref('');
const followUpAnswer = ref('');

const followUpSuggestions = [
  '这只股票现在能买吗？',
  '风险高怎么办？',
  '当前估值合理吗',
];

const diagnosisContext = computed(() => {
  const primary = assetAnalysis.value[0];
  const riskLabel =
    primary?.riskLevel === 'high' ? '高' : primary?.riskLevel === 'low' ? '低' : '中';

  let interval = '震荡整理';
  const trend = diagnosisResult.value.analysis.marketTrend;
  if (trend.includes('上涨') || trend.includes('偏多')) interval = '偏高估/强势';
  else if (trend.includes('下跌') || trend.includes('偏空')) interval = '偏低估/弱势';

  return {
    asset_name: primary?.name || '综合持仓',
    interval,
    risk_level: riskLabel,
    change_pct: primary?.returnRate ?? 0,
    request_id: diagnosisResult.value.requestId !== '-' ? diagnosisResult.value.requestId : undefined,
    market_trend: diagnosisResult.value.analysis.marketTrend,
    sector_rotation: diagnosisResult.value.analysis.sectorRotation,
  };
});

const sendFollowUp = async (questionText?: string) => {
  const question = (questionText ?? followUpQuestion.value).trim();
  if (!question || followUpLoading.value) return;

  if (!diagnosisData.value) {
    showToast('请先完成诊断后再追问', 'error');
    return;
  }

  followUpLoading.value = true;
  followUpStatus.value = 'idle';
  followUpBlockedReason.value = '';
  followUpAnswer.value = '';
  followUpQuestion.value = question;

  try {
    const checkRes = await fetch('/api/rule/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        request_id: diagnosisContext.value.request_id,
      }),
    });

    const checkData = await checkRes.json().catch(() => ({}));
    if (!checkRes.ok) {
      throw new Error(checkData.detail || `合规检查失败 (${checkRes.status})`);
    }

    if (checkData.is_blocked) {
      followUpStatus.value = 'blocked';
      followUpBlockedReason.value = checkData.blocked_reason || '该问题已被合规规则拦截';
      return;
    }

    followUpStatus.value = 'passed';

    const chatRes = await fetch('/api/diagnose/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        diagnosis_context: diagnosisContext.value,
      }),
    });

    const chatData = await chatRes.json().catch(() => ({}));
    if (!chatRes.ok) {
      if (chatRes.status === 403) {
        followUpStatus.value = 'blocked';
        followUpBlockedReason.value = chatData.detail || '该问题已被合规规则拦截';
        return;
      }
      throw new Error(chatData.detail || `回答生成失败 (${chatRes.status})`);
    }

    followUpAnswer.value = chatData.answer;
  } catch (err) {
    followUpStatus.value = 'error';
    followUpBlockedReason.value = err instanceof Error ? err.message : '追问失败，请稍后重试';
  } finally {
    followUpLoading.value = false;
  }
};

const onFollowUpKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendFollowUp();
  }
};

const viewTraceability = () => {
  router.push(`/trace/${diagnosisResult.value.requestId}`);
};

onMounted(() => {
  portfolioStore.loadPortfolio();

  const lastId = localStorage.getItem('last_diagnosis_id');
  if (lastId) {
    try {
      const cached = localStorage.getItem(`diagnosis_${lastId}`);
      if (cached) {
        applyDiagnosis(JSON.parse(cached));
      }
    } catch {
      // ignore bad cache
    }
  }

  if (!diagnosisData.value && portfolioStore.portfolio.assets.length > 0) {
    applyDiagnosis(buildFallbackDiagnosis());
  }

  fetchDiagnosis();
});

onUnmounted(() => {
  if (toastTimer) clearTimeout(toastTimer);
  if (toastFadeTimer) clearTimeout(toastFadeTimer);
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
        <h1 class="text-xl font-bold text-slate-900">持仓诊断结果</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <!-- 无数据提示 -->
      <div v-if="!hasRealData" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-start gap-4">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600 flex-shrink-0" />
          <div class="flex-1">
            <h3 class="font-semibold text-amber-900 mb-2">暂无持仓数据</h3>
            <p class="text-sm text-amber-800 mb-4">
              您尚未导入持仓数据，当前显示的是示例数据。请先导入您的真实持仓以获取准确的AI诊断分析。
            </p>
            <button
              @click="router.push('/portfolio/import')"
              class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors"
            >
              去导入持仓
            </button>
          </div>
        </div>
      </div>

      <div v-if="showDisclaimer && hasRealData" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-start gap-4">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600 flex-shrink-0" />
          <div class="flex-1">
            <h3 class="font-semibold text-amber-900 mb-2">AI分析免责声明</h3>
            <p class="text-sm text-amber-800 mb-4">
              本人已知晓AI分析仅供参考，不构成投资建议。历史收益不代表未来表现，AI无法预测市场。所有投资决策由我本人做出。
            </p>
            <button
              @click="showDisclaimer = false"
              class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-colors"
            >
              我已知晓并同意
            </button>
          </div>
        </div>
      </div>

      <div v-if="diagnosisError" class="bg-red-50 border border-red-200 rounded-xl p-4 mb-8 text-red-700">
        {{ diagnosisError }}
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div class="lg:col-span-2 space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center justify-between mb-6">
              <h2 class="text-lg font-semibold text-slate-900">诊断概览</h2>
              <ConfidenceGauge :value="diagnosisResult.confidence" />
            </div>
            <div class="grid grid-cols-4 gap-4 mb-6">
              <div class="text-center p-4 bg-slate-50 rounded-lg">
                <p class="text-2xl font-bold text-slate-900">{{ diagnosisResult.summary.totalAssets }}</p>
                <p class="text-sm text-slate-500">持仓资产</p>
              </div>
              <div class="text-center p-4 bg-red-50 rounded-lg">
                <p class="text-2xl font-bold text-red-600">{{ diagnosisResult.summary.riskAssets }}</p>
                <p class="text-sm text-slate-500">风险资产</p>
              </div>
              <div class="text-center p-4 bg-emerald-50 rounded-lg">
                <p class="text-2xl font-bold text-emerald-600">{{ diagnosisResult.summary.opportunityAssets }}</p>
                <p class="text-sm text-slate-500">机会资产</p>
              </div>
              <div class="text-center p-4 bg-indigo-50 rounded-lg">
                <p class="text-2xl font-bold text-indigo-600">{{ diagnosisResult.summary.timeSaved }}分钟</p>
                <p class="text-sm text-slate-500">节省时间</p>
              </div>
            </div>
            <div class="p-4 bg-slate-50 rounded-lg">
              <h3 class="font-medium text-slate-900 mb-2">价值摘要</h3>
              <p class="text-sm text-slate-600">
                本次诊断共分析 {{ diagnosisResult.summary.totalAssets }} 只资产，识别出 {{ diagnosisResult.summary.riskAssets }} 个风险点，
                发现 {{ diagnosisResult.summary.opportunityAssets }} 个潜在机会。预计为您节省 {{ diagnosisResult.summary.timeSaved }} 分钟分析时间。
              </p>
            </div>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-lg font-semibold text-slate-900">AI分析结论</h2>
              <span v-if="isLoading" class="text-xs text-slate-400 flex items-center gap-1">
                <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                分析中...
              </span>
            </div>
            <div class="space-y-4">
              <div class="flex gap-3">
                <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <ActivityIcon class="w-4 h-4 text-blue-600" />
                </div>
                <div class="flex-1">
                  <h4 class="font-medium text-slate-900 mb-1">市场趋势</h4>
                  <p class="text-sm text-slate-600">{{ diagnosisResult.analysis.marketTrend }}</p>
                </div>
              </div>
              <div class="flex gap-3">
                <div class="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center flex-shrink-0">
                  <PieChartIcon class="w-4 h-4 text-purple-600" />
                </div>
                <div class="flex-1">
                  <h4 class="font-medium text-slate-900 mb-1">板块轮动</h4>
                  <p class="text-sm text-slate-600">{{ diagnosisResult.analysis.sectorRotation }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 资产明细分析 - 只在有数据时显示 -->
          <div v-if="assetAnalysis.length > 0" class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-lg font-semibold text-slate-900">资产明细分析</h2>
              <span class="text-xs text-slate-400">持仓盈亏（基于成本价）</span>
            </div>
            <div class="space-y-3">
              <div
                v-for="asset in assetAnalysis"
                :key="asset.code"
                class="flex items-center justify-between p-4 bg-slate-50 rounded-lg"
              >
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 rounded-lg flex items-center justify-center"
                    :class="asset.returnRate >= 0 ? 'bg-red-100' : 'bg-green-100'"
                  >
                    <component
                      :is="asset.returnRate >= 0 ? TrendingUpIcon : TrendingDownIcon"
                      class="w-5 h-5"
                      :class="asset.returnRate >= 0 ? 'text-red-600' : 'text-green-600'"
                    />
                  </div>
                  <div>
                    <p class="font-medium text-slate-900">{{ asset.name }}</p>
                    <p class="text-sm text-slate-500">{{ asset.code }} · {{ asset.type === 'stock' ? '股票' : asset.type === 'fund' ? '基金' : '其他' }}</p>
                  </div>
                </div>
                <div class="text-right">
                  <p class="font-medium" :class="asset.returnRate >= 0 ? 'text-red-600' : 'text-green-600'">
                    {{ asset.returnRate >= 0 ? '▲ +' : '▼ ' }}{{ asset.returnRate.toFixed(2) }}%
                  </p>
                  <p class="text-xs text-slate-400">
                    {{ asset.dataSource }}
                    <span v-if="asset.tradeDate">· {{ asset.tradeDate }}</span>
                    <span v-else-if="asset.dataSource === '用户导入数据'">· 数据截至昨日收盘</span>
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <AlertTriangleIcon class="w-5 h-5 text-red-500" />
                <h2 class="text-lg font-semibold text-slate-900">风险点</h2>
              </div>
              <ul class="space-y-2">
                <li
                  v-for="(risk, index) in diagnosisResult.analysis.riskPoints"
                  :key="index"
                  class="flex items-start gap-2 text-sm text-slate-600"
                >
                  <span class="w-5 h-5 bg-red-100 text-red-600 rounded-full flex items-center justify-center text-xs flex-shrink-0">{{ index + 1 }}</span>
                  {{ risk }}
                </li>
              </ul>
            </div>
            <div class="bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center gap-2 mb-4">
                <CheckCircleIcon class="w-5 h-5 text-emerald-500" />
                <h2 class="text-lg font-semibold text-slate-900">机会点</h2>
              </div>
              <ul class="space-y-2">
                <li
                  v-for="(opp, index) in diagnosisResult.analysis.opportunities"
                  :key="index"
                  class="flex items-start gap-2 text-sm text-slate-600"
                >
                  <span class="w-5 h-5 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center text-xs flex-shrink-0">{{ index + 1 }}</span>
                  {{ opp }}
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">数据来源</h2>
            <div class="space-y-3 text-sm">
              <div class="flex items-center gap-2">
                <ClockIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">时间区间: {{ diagnosisResult.dataSource.timeRange }}</span>
              </div>
              <div class="flex items-center gap-2">
                <DatabaseIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">数据来源: {{ diagnosisResult.dataSource.sources.join('、') }}</span>
              </div>
              <div class="flex items-center gap-2">
                <ShieldIcon class="w-4 h-4 text-slate-400" />
                <span class="text-slate-600">更新时间: {{ diagnosisResult.dataSource.updateTime }}</span>
              </div>
            </div>
            <button
              @click="viewTraceability"
              class="w-full mt-4 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50 transition-colors flex items-center justify-center gap-2"
            >
              <SearchIcon class="w-4 h-4" />
              查看分析依据
            </button>
          </div>

          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <h2 class="text-lg font-semibold text-slate-900 mb-4">AI反馈</h2>
            <p class="text-sm text-slate-500 mb-4">这个分析对您有帮助吗？</p>
            <div v-if="feedbackSubmitted && feedbackType === 'positive'" class="text-sm text-emerald-600 mb-3">
              已收到您的反馈，感谢支持！
            </div>
            <div class="flex gap-3">
              <button
                @click="handleFeedbackClick('positive')"
                :disabled="feedbackSubmitting || (feedbackSubmitted && feedbackType === 'positive')"
                class="flex-1 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                :class="feedbackType === 'positive' ? 'bg-emerald-50 border-emerald-500 text-emerald-600' : ''"
              >
                <ThumbsUpIcon class="w-4 h-4" />
                {{ feedbackSubmitting && feedbackType === 'positive' ? '提交中...' : '有帮助' }}
              </button>
              <button
                @click="handleFeedbackClick('negative')"
                :disabled="feedbackSubmitting"
                class="flex-1 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                :class="feedbackType === 'negative' ? 'bg-red-50 border-red-500 text-red-600' : ''"
              >
                <ThumbsDownIcon class="w-4 h-4" />
                {{ feedbackSubmitting && feedbackType === 'negative' && !feedbackReason ? '提交中...' : '需改进' }}
              </button>
            </div>
            <div v-if="feedbackType === 'negative'" class="mt-4">
              <textarea
                v-model="feedbackReason"
                placeholder="请告诉我们哪里需要改进..."
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                rows="3"
              />
              <button
                @click="submitNegativeReason"
                :disabled="feedbackSubmitting"
                class="w-full mt-2 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {{ feedbackSubmitting ? '提交中...' : '提交改进建议' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 追问助手：全宽底部，有持仓即显示（诊断完成后可提问） -->
      <div v-if="hasRealData" class="mt-8 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div class="flex items-center gap-2 mb-1">
          <span class="text-lg">💬</span>
          <h2 class="text-lg font-semibold text-slate-900">追问助手</h2>
        </div>
        <p class="text-xs text-slate-500 mb-4">基于诊断结果继续提问，会经过合规审核</p>

        <div
          v-if="isLoading || !diagnosisData"
          class="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-600 flex items-center gap-2"
        >
          <svg class="w-4 h-4 animate-spin text-indigo-600 flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          {{ isLoading ? '诊断结果加载中，完成后即可追问…' : '诊断数据不可用，请刷新页面或重新导入持仓' }}
        </div>

        <div class="flex flex-wrap gap-2 mb-3">
          <button
            v-for="q in followUpSuggestions"
            :key="q"
            type="button"
            :disabled="followUpLoading || !diagnosisData"
            @click="sendFollowUp(q)"
            class="text-xs px-3 py-1.5 rounded-full border transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :class="q.includes('能买吗')
              ? 'border-red-200 text-red-600 bg-red-50 hover:bg-red-100'
              : 'border-indigo-200 text-indigo-700 bg-indigo-50 hover:bg-indigo-100'"
          >
            {{ q }}
          </button>
        </div>

        <div class="flex gap-2">
          <input
            v-model="followUpQuestion"
            type="text"
            placeholder="输入追问，如：当前估值合理吗？"
            class="flex-1 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
            :disabled="followUpLoading || !diagnosisData"
            @keydown="onFollowUpKeydown"
          />
          <button
            type="button"
            :disabled="!followUpQuestion.trim() || followUpLoading || !diagnosisData"
            @click="sendFollowUp()"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
          >
            <ArrowRightIcon class="w-4 h-4" />
            发送
          </button>
        </div>

        <div v-if="followUpLoading" class="mt-4 space-y-2">
          <p
            v-if="followUpStatus === 'passed'"
            class="text-xs font-medium text-emerald-600 flex items-center gap-1"
          >
            <CheckCircleIcon class="w-3.5 h-3.5" />
            合规通过，正在回答...
          </p>
          <div class="flex items-center gap-2 text-sm text-slate-500">
            <svg class="w-4 h-4 animate-spin text-indigo-600" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            {{ followUpStatus === 'passed' ? 'AI 生成回答中' : '合规检查中' }}
          </div>
        </div>

        <div
          v-else-if="followUpStatus === 'blocked'"
          class="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg"
        >
          <p class="text-sm font-medium text-red-700">该问题已被合规规则拦截</p>
          <p class="text-xs text-red-600 mt-1">{{ followUpBlockedReason }}</p>
        </div>

        <div
          v-else-if="followUpStatus === 'passed' && followUpAnswer"
          class="mt-4 space-y-2"
        >
          <p class="text-xs font-medium text-emerald-600 flex items-center gap-1">
            <CheckCircleIcon class="w-3.5 h-3.5" />
            合规通过
          </p>
          <div class="p-3 bg-slate-50 border border-slate-200 rounded-lg">
            <p class="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{{ followUpAnswer }}</p>
          </div>
        </div>

        <div
          v-else-if="followUpStatus === 'error'"
          class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800"
        >
          {{ followUpBlockedReason }}
        </div>
      </div>
    </main>

    <footer class="bg-white border-t border-slate-200 py-6">
      <div class="max-w-7xl mx-auto px-4 text-center">
        <p class="text-sm text-slate-500">
          本内容仅为投资参考，不构成任何投资建议 · Request ID: {{ diagnosisResult.requestId }}
        </p>
      </div>
    </footer>

    <Teleport to="body">
      <div
        v-show="toast.visible"
        class="fixed top-6 left-1/2 -translate-x-1/2 z-[9999] transition-opacity duration-300"
        :class="toast.fading ? 'opacity-0' : 'opacity-100'"
      >
        <div
          class="flex items-center gap-3 px-5 py-3 rounded-lg shadow-lg text-white min-w-[280px] max-w-md"
          :class="toast.type === 'success' ? 'bg-emerald-600' : 'bg-red-600'"
        >
          <p class="text-sm flex-1 leading-relaxed">{{ toast.message }}</p>
          <button
            type="button"
            class="text-white/80 hover:text-white text-lg leading-none"
            @click="hideToast"
          >
            ×
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>
