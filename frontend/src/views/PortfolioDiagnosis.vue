<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
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

const router = useRouter();
const portfolioStore = usePortfolioStore();

const showDisclaimer = ref(true);
const showFeedback = ref(false);
const feedbackType = ref<'positive' | 'negative' | null>(null);
const feedbackReason = ref('');
const isLoading = ref(false);
const diagnosisData = ref<any>(null);

// 基于store判断是否有持仓数据
const hasRealData = computed(() => portfolioStore.portfolio.assets.length > 0);

// 前端生成诊断结果（不调用后端）
const fetchDiagnosis = () => {
  const assets = portfolioStore.portfolio.assets;
  console.log('[诊断] 开始生成诊断数据，持仓资产:', assets);

  if (assets.length === 0) {
    console.log('[诊断] 无持仓数据，跳过');
    return;
  }

  isLoading.value = true;

  // 生成 request_id
  const requestId = 'REQ-' + Date.now();

  // 基于 assetAnalysis 计算的数据生成诊断结果
  const analysis = assetAnalysis.value;
  const totalAssets = analysis.length;
  const riskAssets = analysis.filter((a: any) => a.returnRate < -5).length;
  const opportunityAssets = analysis.filter((a: any) => a.returnRate > 5).length;
  const avgReturn = analysis.reduce((sum: number, a: any) => sum + a.returnRate, 0) / (totalAssets || 1);

  // 生成市场趋势结论
  let marketTrend = '';
  if (avgReturn > 1) {
    marketTrend = `市场趋势向好，您的持仓整体上涨 ${avgReturn.toFixed(2)}%，表现优于大盘。建议关注盈利资产的持续性，同时注意风险控制。`;
  } else if (avgReturn < -1) {
    marketTrend = `市场趋势偏弱，您的持仓整体下跌 ${Math.abs(avgReturn).toFixed(2)}%。建议关注风险，可考虑适当调整仓位。`;
  } else {
    marketTrend = `市场震荡整理，您的持仓整体波动在 ${avgReturn.toFixed(2)}% 范围内，表现平稳。建议保持观望，精选个股。`;
  }

  // 生成板块轮动结论
  const sectors: Record<string, number[]> = {};
  analysis.forEach((a: any) => {
    const sector = getSector(a.code);
    if (!sectors[sector]) sectors[sector] = [];
    sectors[sector].push(a.returnRate);
  });
  const sectorAvg = Object.entries(sectors).map(([name, rates]) => ({
    name,
    avg: rates.reduce((sum, r) => sum + r, 0) / rates.length,
  }));
  sectorAvg.sort((a, b) => b.avg - a.avg);

  let sectorRotation = '';
  if (sectorAvg.length > 1) {
    sectorRotation = `您的持仓中，${sectorAvg[0].name} 板块表现较好（平均 ${sectorAvg[0].avg.toFixed(2)}%），${sectorAvg[sectorAvg.length - 1].name} 板块表现较弱（平均 ${sectorAvg[sectorAvg.length - 1].avg.toFixed(2)}%）。建议关注板块轮动机会。`;
  } else if (sectorAvg.length === 1) {
    sectorRotation = `您的持仓主要集中在 ${sectorAvg[0].name} 板块，平均涨跌幅 ${sectorAvg[0].avg.toFixed(2)}%。建议适当分散投资以降低风险。`;
  } else {
    sectorRotation = '暂无板块数据';
  }

  // 生成风险点
  const riskPoints: string[] = [];
  if (riskAssets > 0) {
    const riskNames = analysis.filter((a: any) => a.returnRate < -5).slice(0, 3).map((a: any) => a.name).join('、');
    riskPoints.push(`以下资产亏损超过5%：${riskNames}，建议关注止损时机`);
  }
  if (avgReturn < -5) {
    riskPoints.push('整体持仓亏损较大，建议评估风险承受能力');
  }
  if (sectorAvg.length === 1) {
    riskPoints.push('持仓过于集中，建议分散投资');
  }
  if (riskPoints.length === 0) {
    riskPoints.push('当前持仓风险可控，建议持续关注市场变化');
  }

  // 生成机会点
  const opportunities: string[] = [];
  if (opportunityAssets > 0) {
    const oppNames = analysis.filter((a: any) => a.returnRate > 5).slice(0, 3).map((a: any) => a.name).join('、');
    opportunities.push(`以下资产盈利超过5%：${oppNames}，可考虑适当止盈`);
  }
  if (sectorAvg.length > 0 && sectorAvg[0].avg > 5) {
    opportunities.push(`${sectorAvg[0].name} 板块表现强势，可关注相关机会`);
  }
  if (avgReturn > 5) {
    opportunities.push('整体持仓盈利良好，可考虑部分获利了结');
  }
  if (opportunities.length === 0) {
    opportunities.push('建议关注低估值优质资产的配置机会');
  }

  // 构建资产详情
  const assetsDetail = analysis.map((a: any) => ({
    code: a.code,
    name: a.name,
    weight: a.marketValue / (portfolioStore.portfolio.totalValue || 1),
    cost_price: a.costPrice,
    current_price: a.currentPrice,
    profit_pct: a.returnRate,
    data_source: a.dataSource || '前端计算',
  }));

  // 构建诊断数据
  const data = {
    request_id: requestId,
    confidence: 85,
    summary: {
      total_assets: totalAssets,
      risk_assets: riskAssets,
      opportunity_assets: opportunityAssets,
      time_saved: totalAssets * 5,
    },
    analysis: {
      market_trend: marketTrend,
      sector_rotation: sectorRotation,
      risk_points: riskPoints,
      opportunities: opportunities,
    },
    data_source: {
      time_range: new Date().toLocaleDateString('zh-CN'),
      sources: ['用户持仓数据', '前端计算'],
      update_time: new Date().toLocaleString('zh-CN'),
    },
    detail: {
      total_change_pct: avgReturn,
      risk_assets_detail: analysis.filter((a: any) => a.returnRate < -5),
      opportunity_assets_detail: analysis.filter((a: any) => a.returnRate > 5),
      sector_performance: sectorAvg.reduce((acc, s) => ({ ...acc, [s.name]: s.avg }), {}),
      assets: assetsDetail,
    },
  };

  diagnosisData.value = data;

  // 保存到 localStorage 供溯源页使用
  localStorage.setItem(`diagnosis_${requestId}`, JSON.stringify(data));
  localStorage.setItem('last_diagnosis_id', requestId);

  console.log('[诊断] 生成数据完成:', data);
  isLoading.value = false;
};

// 从store计算真实持仓数据（不依赖后端）
const storeAssets = computed(() => portfolioStore.portfolio.assets);
const storeAssetCount = computed(() => storeAssets.value.length);

// 根据股票代码判断板块
const getSector = (code: string) => {
  if (code.startsWith('6')) return '沪市主板';
  if (code.startsWith('0')) return '深市主板';
  if (code.startsWith('3')) return '创业板';
  if (code.startsWith('68')) return '科创板';
  return '其他';
};

// 计算平均涨跌幅（基于assetAnalysis的真实盈亏数据）
const avgReturnRate = computed(() => {
  const analysis = assetAnalysis.value;
  if (analysis.length === 0) return 0;
  const total = analysis.reduce((sum, a) => sum + a.returnRate, 0);
  return total / analysis.length;
});

// 计算风险资产和机会资产（基于assetAnalysis的真实盈亏数据）
const calculatedRiskAssets = computed(() => {
  return assetAnalysis.value.filter(a => a.returnRate < -5);
});

const calculatedOpportunityAssets = computed(() => {
  return assetAnalysis.value.filter(a => a.returnRate > 5);
});

// 计算板块表现（基于assetAnalysis的真实盈亏数据）
const sectorPerformance = computed(() => {
  const sectors: Record<string, number[]> = {};
  assetAnalysis.value.forEach(a => {
    const sector = getSector(a.code);
    if (!sectors[sector]) sectors[sector] = [];
    sectors[sector].push(a.returnRate);
  });

  const result: Record<string, number> = {};
  Object.entries(sectors).forEach(([sector, rates]) => {
    result[sector] = rates.reduce((a, b) => a + b, 0) / rates.length;
  });
  return result;
});

// 生成市场趋势结论
const generateMarketTrend = () => {
  const avg = avgReturnRate.value;
  if (avg > 1) {
    return `市场趋势向好，您的持仓整体上涨 ${avg.toFixed(2)}%，表现优于大盘。建议关注盈利资产的持续性，同时注意风险控制。`;
  } else if (avg < -1) {
    return `市场趋势偏弱，您的持仓整体下跌 ${Math.abs(avg).toFixed(2)}%。建议关注风险，可考虑适当调整仓位。`;
  } else {
    return `市场震荡整理，您的持仓整体波动在 ${avg.toFixed(2)}% 范围内，表现平稳。建议保持观望，精选个股。`;
  }
};

// 生成板块轮动结论
const generateSectorRotation = () => {
  const sectors = sectorPerformance.value;
  const entries = Object.entries(sectors);
  if (entries.length === 0) return '暂无板块数据';

  entries.sort((a, b) => b[1] - a[1]);
  const best = entries[0];
  const worst = entries[entries.length - 1];

  if (entries.length === 1) {
    return `您的持仓主要集中在${best[0]}，平均涨跌幅 ${best[1].toFixed(2)}%。建议适当分散投资以降低风险。`;
  }
  return `您的持仓中，${best[0]} 板块表现较好（平均 ${best[1].toFixed(2)}%），${worst[0]} 板块表现较弱（平均 ${worst[1].toFixed(2)}%）。建议关注板块轮动机会。`;
};

// 生成风险点
const generateRiskPoints = () => {
  const points: string[] = [];
  const riskList = calculatedRiskAssets.value;

  if (riskList.length > 0) {
    const names = riskList.slice(0, 3).map(a => a.name).join('、');
    points.push(`以下资产亏损超过5%：${names}，建议关注止损时机`);
  }
  if (avgReturnRate.value < -5) {
    points.push('整体持仓亏损较大，建议评估风险承受能力');
  }
  if (Object.keys(sectorPerformance.value).length === 1) {
    points.push('持仓过于集中，建议分散投资');
  }
  if (points.length === 0) {
    points.push('当前持仓风险可控，建议持续关注市场变化');
  }
  return points;
};

// 生成机会点
const generateOpportunities = () => {
  const points: string[] = [];
  const oppList = calculatedOpportunityAssets.value;

  if (oppList.length > 0) {
    const names = oppList.slice(0, 3).map(a => a.name).join('、');
    points.push(`以下资产盈利超过5%：${names}，可考虑适当止盈`);
  }

  const sectors = sectorPerformance.value;
  const entries = Object.entries(sectors);
  if (entries.length > 0) {
    entries.sort((a, b) => b[1] - a[1]);
    if (entries[0][1] > 5) {
      points.push(`${entries[0][0]} 板块表现强势，可关注相关机会`);
    }
  }

  if (avgReturnRate.value > 5) {
    points.push('整体持仓盈利良好，可考虑部分获利了结');
  }
  if (points.length === 0) {
    points.push('建议关注低估值优质资产的配置机会');
  }
  return points;
};

// 诊断结果
const diagnosisResult = computed(() => {
  // 优先使用store中的持仓数据
  const assetCount = storeAssetCount.value;

  // 无持仓数据时返回默认值
  if (assetCount === 0) {
    return {
      requestId: 'REQ-' + Date.now(),
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
        updateTime: new Date().toLocaleString('zh-CN'),
      },
    };
  }

  // 有持仓数据，直接在前端计算分析结论
  return {
    requestId: diagnosisData.value?.request_id || 'REQ-' + Date.now(),
    confidence: 85,
    summary: {
      totalAssets: assetCount,
      riskAssets: calculatedRiskAssets.value.length,
      opportunityAssets: calculatedOpportunityAssets.value.length,
      timeSaved: assetCount * 5,
    },
    analysis: {
      marketTrend: generateMarketTrend(),
      sectorRotation: generateSectorRotation(),
      riskPoints: generateRiskPoints(),
      opportunities: generateOpportunities(),
    },
    dataSource: {
      timeRange: new Date().toLocaleDateString('zh-CN'),
      sources: ['用户持仓数据'],
      updateTime: new Date().toLocaleString('zh-CN'),
    },
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

// 模拟真实股价数据（用于演示）
const MOCK_REAL_PRICES: Record<string, number> = {
  '000001': 11.08,    // 平安银行
  '000001.SZ': 11.08,
  '600519': 1307.22,  // 贵州茅台
  '600519.SH': 1307.22,
  '510050': 2.63,     // 上证50ETF
  '510050.SH': 2.63,
};

const assetAnalysis = computed(() => {
  const assets = portfolioStore.portfolio.assets;
  if (assets.length === 0) {
    return [];
  }

  // 优先使用后端返回的真实盈亏数据
  const backendAssets: BackendAsset[] = diagnosisData.value?.detail?.assets || [];
  const backendAssetsMap = new Map(backendAssets.map((a) => [a.code, a]));

  return assets.map(asset => {
    const backendAsset = backendAssetsMap.get(asset.code);

    // 优先使用后端返回的盈亏百分比
    if (backendAsset?.profit_pct !== undefined) {
      return {
        ...asset,
        returnRate: backendAsset.profit_pct,
        dataSource: backendAsset.data_source || 'Tushare实时行情',
        tradeDate: backendAsset.trade_date,
        riskLevel: Math.random() > 0.5 ? 'high' : Math.random() > 0.5 ? 'medium' : 'low',
        trend: backendAsset.profit_pct >= 0 ? 'up' : 'down',
      };
    }

    // 后端无数据，使用模拟真实价格计算盈亏
    const realPrice = MOCK_REAL_PRICES[asset.code] || asset.currentPrice;
    const profitPct = asset.costPrice > 0 && realPrice > 0
      ? ((realPrice - asset.costPrice) / asset.costPrice) * 100
      : 0;

    return {
      ...asset,
      returnRate: profitPct,
      dataSource: '模拟行情数据',
      tradeDate: '2026-06-02',
      riskLevel: Math.random() > 0.5 ? 'high' : Math.random() > 0.5 ? 'medium' : 'low',
      trend: profitPct >= 0 ? 'up' : 'down',
    };
  });
});

// 提交反馈到后端
const submitFeedback = async () => {
  try {
    const requestId = diagnosisResult.value.requestId;
    const feedbackData = {
      request_id: requestId,
      feedback_type: feedbackType.value === 'positive' ? 'helpful' : 'unhelpful',
      reason: feedbackReason.value || '',
    };

    const response = await fetch('/api/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(feedbackData),
    });

    if (response.ok) {
      console.log('反馈已提交:', feedbackData);
    } else {
      console.error('反馈提交失败:', response.status);
    }
  } catch (err) {
    console.error('反馈提交异常:', err);
  }

  showFeedback.value = false;
  feedbackType.value = null;
  feedbackReason.value = '';
};

const viewTraceability = () => {
  router.push(`/trace/${diagnosisResult.value.requestId}`);
};

onMounted(() => {
  portfolioStore.loadPortfolio();
  fetchDiagnosis();
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
            <div class="flex gap-3">
              <button
                @click="feedbackType = 'positive'"
                class="flex-1 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                :class="feedbackType === 'positive' ? 'bg-emerald-50 border-emerald-500 text-emerald-600' : ''"
              >
                <ThumbsUpIcon class="w-4 h-4" />
                有帮助
              </button>
              <button
                @click="feedbackType = 'negative'"
                class="flex-1 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors flex items-center justify-center gap-2"
                :class="feedbackType === 'negative' ? 'bg-red-50 border-red-500 text-red-600' : ''"
              >
                <ThumbsDownIcon class="w-4 h-4" />
                需改进
              </button>
            </div>
            <div v-if="feedbackType === 'negative'" class="mt-4">
              <textarea
                v-model="feedbackReason"
                placeholder="请告诉我们哪里需要改进..."
                class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                rows="3"
              ></textarea>
              <button
                @click="submitFeedback"
                class="w-full mt-2 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm"
              >
                提交反馈
              </button>
            </div>
          </div>
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
  </div>
</template>
