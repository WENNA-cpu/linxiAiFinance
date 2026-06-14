<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import BrainIcon from '@/components/icons/BrainIcon.vue';
import TrendingUpIcon from '@/components/icons/TrendingUpIcon.vue';
import TrendingDownIcon from '@/components/icons/TrendingDownIcon.vue';
import MinusIcon from '@/components/icons/MinusIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';
import CpuIcon from '@/components/icons/CpuIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';
import UploadIcon from '@/components/icons/UploadIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const selectedAsset = ref('');
const manualCode = ref('');
const timeRange = ref('3y');
const isLoading = ref(false);
const error = ref('');
const chartContainer = ref<HTMLDivElement | null>(null);
let chartInstance: any = null;

const portfolioAssets = computed(() =>
  portfolioStore.portfolio.assets.map((asset) => ({
    code: asset.code,
    name: asset.name,
    type: asset.type,
  })),
);

const hasAssets = computed(() => portfolioAssets.value.length > 0);

interface HistoryPoint {
  date: string;
  value: number;
}

interface CycleData {
  ts_code: string;
  name: string;
  current_pe: number;
  current_pb: number;
  pe_percentile: number;
  pb_percentile: number;
  pe_30_percentile: number;
  pe_70_percentile: number;
  pb_30_percentile: number;
  pb_70_percentile: number;
  interval: string;
  suggestion: string;
  confidence: number;
  pe_history: HistoryPoint[];
  pb_history: HistoryPoint[];
  pe_forecast: HistoryPoint[];
  pe_forecast_lower: HistoryPoint[];
  pe_forecast_upper: HistoryPoint[];
  predicted_pe?: number[];
  forecast_available: boolean;
  forecast_horizon_days: number;
  time_range: string;
  lookback_days: number;
  data_source: string;
  model_version: string;
  use_price_fallback?: boolean;
}

const cycleData = ref<CycleData | null>(null);

const activeAssetCode = computed(() => selectedAsset.value || manualCode.value.trim());

const displayName = computed(() => cycleData.value?.name || activeAssetCode.value || '-');

const isUndervalued = computed(() => cycleData.value?.interval.includes('低估') ?? false);
const isFair = computed(() => cycleData.value?.interval.includes('合理') ?? false);
const isOvervalued = computed(() => cycleData.value?.interval.includes('高估') ?? false);

const intervalBadgeClass = computed(() => {
  if (isUndervalued.value) return 'bg-emerald-50 text-emerald-700 border border-emerald-300';
  if (isOvervalued.value) return 'bg-red-50 text-red-700 border border-red-300';
  return 'bg-blue-50 text-blue-700 border border-blue-300';
});

const bareCode = (code: string) => normalizeTsCode(code).replace(/\.(SH|SZ|BJ)$/i, '');

const clampPercent = (value: number) => Math.min(100, Math.max(0, Number(value) || 0));

const isInPortfolio = computed(() => {
  if (!cycleData.value || !hasAssets.value) return false;

  const analyzedTs = normalizeTsCode(cycleData.value.ts_code || activeAssetCode.value);
  const analyzedBare = bareCode(analyzedTs);
  const analyzedName = cycleData.value.name.trim();

  return portfolioAssets.value.some((asset) => {
    const assetTs = normalizeTsCode(asset.code);
    if (assetTs === analyzedTs || bareCode(asset.code) === analyzedBare) return true;
    if (analyzedName && asset.name.trim() === analyzedName) return true;
    return false;
  });
});

const peProgressWidth = computed(() => clampPercent(cycleData.value?.pe_percentile ?? 0));
const pbProgressWidth = computed(() => clampPercent(cycleData.value?.pb_percentile ?? 0));

const suggestionDetailText = computed(() => {
  const data = cycleData.value;
  if (!data) return '';
  if (isUndervalued.value) {
    return `当前估值处于低估区间，${data.suggestion}。可考虑逐步建仓或加仓。`;
  }
  if (isOvervalued.value) {
    return `当前估值处于高估区间，${data.suggestion}。可考虑逐步减仓或观望。`;
  }
  return `当前估值处于合理区间，${data.suggestion}。`;
});

const suggestionCardClass = computed(() => {
  if (isUndervalued.value) return 'bg-emerald-50 border-emerald-200';
  if (isOvervalued.value) return 'bg-red-50 border-red-200';
  return 'bg-blue-50 border-blue-200';
});

const LOOKBACK_DAYS: Record<string, number> = {
  '1m': 30,
  '3m': 90,
  '6m': 180,
  '1y': 365,
  '3y': 1095,
};

const lookbackDays = computed(() => LOOKBACK_DAYS[timeRange.value] ?? 365);

const timeRangeLabel = computed(() => {
  const map: Record<string, string> = {
    '1m': '近1个月',
    '3m': '近3个月',
    '6m': '近6个月',
    '1y': '近1年',
    '3y': '近3年',
  };
  return map[timeRange.value] ?? '近1年';
});

const normalizeTsCode = (code: string) => {
  const trimmed = code.trim().toUpperCase();
  if (trimmed.includes('.')) return trimmed;
  if (trimmed.startsWith('6') || trimmed.startsWith('5')) return `${trimmed}.SH`;
  return `${trimmed}.SZ`;
};

const buildForecastFromPredictedPe = (raw: Partial<CycleData> & Record<string, unknown>): HistoryPoint[] => {
  const predicted = raw.predicted_pe;
  if (!Array.isArray(predicted) || predicted.length === 0) return [];

  const peHistory = Array.isArray(raw.pe_history) ? raw.pe_history : [];
  const lastDate = peHistory.length > 0 ? String(peHistory[peHistory.length - 1].date) : '';
  const base = lastDate ? new Date(lastDate) : null;

  return predicted.map((value, idx) => {
    let date = `T+${idx + 1}`;
    if (base && !Number.isNaN(base.getTime())) {
      const next = new Date(base);
      let added = 0;
      while (added <= idx) {
        next.setDate(next.getDate() + 1);
        if (next.getDay() !== 0 && next.getDay() !== 6) added += 1;
      }
      date = next.toISOString().slice(0, 10);
    }
    return { date, value: Number(value) };
  });
};

const normalizeCycleData = (raw: Partial<CycleData> & Record<string, unknown>): CycleData => {
  const peForecast = Array.isArray(raw.pe_forecast) && raw.pe_forecast.length > 0
    ? raw.pe_forecast
    : buildForecastFromPredictedPe(raw);

  return {
    ts_code: String(raw.ts_code ?? ''),
    name: String(raw.name ?? ''),
    current_pe: Number(raw.current_pe ?? 0),
    current_pb: Number(raw.current_pb ?? 0),
    pe_percentile: Number(raw.pe_percentile ?? 50),
    pb_percentile: Number(raw.pb_percentile ?? 50),
    pe_30_percentile: Number(raw.pe_30_percentile ?? 0),
    pe_70_percentile: Number(raw.pe_70_percentile ?? 0),
    pb_30_percentile: Number(raw.pb_30_percentile ?? 0),
    pb_70_percentile: Number(raw.pb_70_percentile ?? 0),
    interval: String(raw.interval ?? '合理区间'),
    suggestion: String(raw.suggestion ?? '持有观望'),
    confidence: Number(raw.confidence ?? 70),
    pe_history: Array.isArray(raw.pe_history) ? raw.pe_history : [],
    pb_history: Array.isArray(raw.pb_history) ? raw.pb_history : [],
    pe_forecast: peForecast,
    pe_forecast_lower: Array.isArray(raw.pe_forecast_lower) ? raw.pe_forecast_lower : [],
    pe_forecast_upper: Array.isArray(raw.pe_forecast_upper) ? raw.pe_forecast_upper : [],
    predicted_pe: Array.isArray(raw.predicted_pe) ? raw.predicted_pe.map(Number) : undefined,
    forecast_available: Boolean(raw.forecast_available) && peForecast.length > 0,
    forecast_horizon_days: Number(raw.forecast_horizon_days ?? 0),
    time_range: String(raw.time_range ?? '3y'),
    lookback_days: Number(raw.lookback_days ?? 365),
    data_source: String(raw.data_source ?? 'Tushare'),
    model_version: String(raw.model_version ?? 'percentile_only'),
    use_price_fallback: Boolean(raw.use_price_fallback),
  };
};

const formatChangePct = (value: number): string => {
  const abs = Math.abs(value);
  return abs >= 10 ? `${Math.round(abs)}%` : `${abs.toFixed(1)}%`;
};

const formatSignedPct = (value: number): string => {
  const rounded = Math.abs(value) >= 10 ? Math.round(value) : Number(value.toFixed(1));
  return `${rounded >= 0 ? '+' : ''}${rounded}%`;
};

const modelVersionLabel = (version: string): string => {
  if (version === 'legacy') return 'v1.0';
  if (version === 'new') return 'v2.0';
  return 'v2.0';
};

const toConfidenceShort = (pct: number): string => {
  const level = Math.min(9, Math.max(5, Math.round(pct / 10)));
  const labels: Record<number, string> = {
    9: '九成',
    8: '八成',
    7: '七成',
    6: '六成',
    5: '五成',
  };
  return labels[level] ?? '七成';
};

const trendPhrase = (changePct: number, absPct: number): string => {
  if (absPct < 3) return '横盘震荡';
  if (changePct > 0) return absPct < 10 ? '小涨一点' : '上涨一些';
  return absPct < 10 ? '小跌一点' : '下跌一些';
};

const valuationLevelText = (interval: string): string => {
  if (interval.includes('低估')) return '估值偏低';
  if (interval.includes('高估')) return '估值偏高';
  return '估值合理';
};

const statusIcon = (interval: string): string => {
  if (interval.includes('高估')) return '📈';
  if (interval.includes('低估')) return '📉';
  return '➡️';
};

const lstmTrendIcon = (changePct: number, absPct: number): string => {
  if (absPct < 3) return '➡️';
  return changePct >= 0 ? '📈' : '📉';
};

const predictionBlock = computed(() => {
  const data = cycleData.value;
  if (!data) return null;

  const status = {
    icon: statusIcon(data.interval),
    level: valuationLevelText(data.interval),
    suggestion: data.suggestion,
  };

  let lstm: {
    icon: string;
    days: number;
    phrase: string;
    changeLabel: string;
    confidence: string;
    details: string[];
  } | null = null;

  if (data.forecast_available && data.pe_forecast.length > 0) {
    const days = data.forecast_horizon_days || data.pe_forecast.length;
    const current = data.current_pe;
    const forecasts = data.pe_forecast.map((p) => p.value);
    const avgForecast = forecasts.reduce((a, b) => a + b, 0) / forecasts.length;
    const changePct = current > 0 ? ((avgForecast - current) / current) * 100 : 0;
    const absChange = Math.abs(changePct);

    let rangeMin = changePct;
    let rangeMax = changePct;
    if (current > 0 && data.pe_forecast_lower.length > 0 && data.pe_forecast_upper.length > 0) {
      const lowerPcts = data.pe_forecast_lower.map((p) => ((p.value - current) / current) * 100);
      const upperPcts = data.pe_forecast_upper.map((p) => ((p.value - current) / current) * 100);
      rangeMin = Math.min(...lowerPcts);
      rangeMax = Math.max(...upperPcts);
    } else {
      const spread = Math.max(absChange * 0.3, 1.5);
      rangeMin = changePct - spread;
      rangeMax = changePct + spread;
    }

    lstm = {
      icon: lstmTrendIcon(changePct, absChange),
      days,
      phrase: trendPhrase(changePct, absChange),
      changeLabel: formatChangePct(changePct),
      confidence: toConfidenceShort(data.confidence),
      details: [
        `当前 PE 处于历史 ${data.pe_percentile}% 分位（${data.interval}）`,
        'LSTM 模型基于过去 30 天估值数据预测',
        `预测区间：${formatSignedPct(rangeMin)} ~ ${formatSignedPct(rangeMax)}`,
        `置信度 ${Math.round(data.confidence)}% · 模型版本 ${modelVersionLabel(data.model_version)} · 训练数据：沪深300 近3年`,
      ],
    };
  }

  return { status, lstm };
});

const chartNotice = computed(() => {
  const data = cycleData.value;
  if (!data) return '';
  if (data.pe_history.length < 5) return '暂无足够历史数据';
  if (!data.forecast_available) return '数据不足，无法预测';
  return '';
});

const normalizeDisplayDate = (date: string): string => {
  const trimmed = String(date).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) return trimmed;
  if (/^\d{8}$/.test(trimmed)) {
    return `${trimmed.slice(0, 4)}-${trimmed.slice(4, 6)}-${trimmed.slice(6, 8)}`;
  }
  return trimmed;
};

const dataAsOfDate = computed(() => {
  const data = cycleData.value;
  if (!data) return '';

  const latestDates = [
    data.pe_history.at(-1)?.date,
    data.pb_history.at(-1)?.date,
  ].filter((d): d is string => Boolean(d));

  if (latestDates.length === 0) return '';
  return normalizeDisplayDate(latestDates.sort().at(-1)!);
});

const getChartDisplayDays = (range: string): number => {
  switch (range) {
    case '1m': return 22;
    case '3m': return 66;
    case '6m': return 132;
    case '1y': return 252;
    case '3y': return 756;
    default: return 252;
  }
};

const computeLinearTrend = (values: number[]) => {
  const n = values.length;
  if (n < 2) return values.map(() => values[0] ?? 0);
  const x = Array.from({ length: n }, (_, i) => i);
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = values.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((acc, xi, i) => acc + xi * values[i], 0);
  const sumXX = x.reduce((acc, xi) => acc + xi * xi, 0);
  const denom = n * sumXX - sumX * sumX;
  const slope = denom !== 0 ? (n * sumXY - sumX * sumY) / denom : 0;
  const intercept = (sumY - slope * sumX) / n;
  return x.map((xi) => slope * xi + intercept);
};

const padSeries = <T>(data: T[], extra: number, fill: T): T[] =>
  (extra > 0 ? [...data, ...Array(extra).fill(fill)] : data);

const MA_WINDOW = 20;
const CI_STD_MULT = 1.96;

const formatMMDD = (date: string) => (date.length >= 10 ? date.slice(5) : date);

const stdDev = (values: number[]): number => {
  if (values.length < 2) return 0;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / values.length;
  return Math.sqrt(variance);
};

const movingAverage = (values: number[], window: number): (number | null)[] =>
  values.map((_, i) => {
    if (i < window - 1) return null;
    const slice = values.slice(i - window + 1, i + 1);
    return slice.reduce((a, b) => a + b, 0) / window;
  });

const bollingerBands = (values: number[], window: number, mult: number) => {
  const ma = movingAverage(values, window);
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];

  values.forEach((_, i) => {
    if (i < window - 1) {
      upper.push(null);
      lower.push(null);
      return;
    }
    const slice = values.slice(i - window + 1, i + 1);
    const mean = ma[i]!;
    const sd = stdDev(slice);
    upper.push(mean + mult * sd);
    lower.push(Math.max(0.01, mean - mult * sd));
  });

  return { ma, upper, lower };
};

const padWithForecastNulls = (histPart: (number | null)[], forecastLen: number) =>
  [...histPart, ...Array(forecastLen).fill(null)];

interface ChartMetrics {
  xLabels: string[];
  histLen: number;
  hasForecast: boolean;
  splitIndex: number;
  histSeries: (number | null)[];
  forecastSeries: (number | null)[];
  trendSeries: (number | null)[];
  upperSeries: (number | null)[];
  lowerSeries: (number | null)[];
  ciBaseSeries: (number | null)[];
  ciFillSeries: (number | null)[];
  trendStatus: string;
  bandStatus: string;
  confidenceStatus: string;
  peHistoryStatus: string;
  pbHistoryStatus: string;
  lstmForecastStatus: string;
}

const chartMetrics = computed((): ChartMetrics | null => {
  const data = cycleData.value;
  if (!data || data.pe_history.length === 0) return null;

  const peHistory = data.pe_history;
  const peForecast = data.pe_forecast ?? [];
  const hasForecast = data.forecast_available && peForecast.length > 0;
  const histDates = peHistory.map((item) => item.date);
  const forecastDates = hasForecast ? peForecast.map((item) => item.date) : [];
  const xLabels = hasForecast ? [...histDates, ...forecastDates] : histDates;

  const histLen = peHistory.length;
  const histValues = peHistory.map((item) => item.value);
  const forecastValues = hasForecast ? peForecast.map((item) => item.value) : [];
  const forecastLen = forecastValues.length;

  const { ma, upper, lower } = bollingerBands(histValues, MA_WINDOW, 2);

  const histSeries = hasForecast
    ? [...histValues, ...Array(forecastLen).fill(null)]
    : histValues;
  const forecastSeries = hasForecast
    ? [...Array(Math.max(histLen - 1, 0)).fill(null), histValues[histLen - 1], ...forecastValues]
    : [];

  const trendSeries = padWithForecastNulls(ma, forecastLen);
  const upperSeries = padWithForecastNulls(upper, forecastLen);
  const lowerSeries = padWithForecastNulls(lower, forecastLen);

  let ciBaseSeries: (number | null)[] = Array(xLabels.length).fill(null);
  let ciFillSeries: (number | null)[] = Array(xLabels.length).fill(null);

  if (hasForecast) {
    const recentStd = stdDev(histValues.slice(-Math.min(30, histValues.length)));
    const confLower = forecastValues.map((v) => Math.max(0.01, v - CI_STD_MULT * recentStd));
    const confUpper = forecastValues.map((v) => v + CI_STD_MULT * recentStd);
    ciBaseSeries = [...Array(histLen).fill(null), ...confLower];
    ciFillSeries = [...Array(histLen).fill(null), ...confUpper.map((u, i) => Number((u - confLower[i]).toFixed(2)))];
  }

  const validMa = ma.filter((v): v is number => v != null);
  let trendStatus = '数据不足';
  if (validMa.length >= 6) {
    const recent = validMa[validMa.length - 1];
    const prior = validMa[validMa.length - 6];
    const pct = prior > 0 ? ((recent - prior) / prior) * 100 : 0;
    if (Math.abs(pct) < 1) trendStatus = '横盘震荡';
    else if (pct > 0) trendStatus = '震荡上行';
    else trendStatus = '震荡下行';
  }

  const lastUpper = upper.filter((v): v is number => v != null).at(-1);
  const lastLower = lower.filter((v): v is number => v != null).at(-1);
  const currentPe = histValues.at(-1) ?? 0;
  let bandStatus = '数据不足';
  if (lastUpper != null && lastLower != null && lastUpper > lastLower) {
    const bandWidth = lastUpper - lastLower;
    const distUpper = (lastUpper - currentPe) / bandWidth;
    const distLower = (currentPe - lastLower) / bandWidth;
    if (distUpper <= 0.2) bandStatus = '当前 PE 接近上轨';
    else if (distLower <= 0.2) bandStatus = '当前 PE 接近下轨';
    else bandStatus = '当前 PE 处于通道中部';
  }

  let confidenceStatus = '暂无预测';
  if (hasForecast && ciBaseSeries.some((v) => v != null)) {
    const lowers = ciBaseSeries.filter((v): v is number => v != null);
    const uppers = ciBaseSeries
      .map((base, idx) => {
        const fill = ciFillSeries[idx];
        if (base == null || fill == null) return null;
        return base + fill;
      })
      .filter((v): v is number => v != null);
    const days = data.forecast_horizon_days || forecastLen;
    confidenceStatus = `未来 ${days} 天 ${Math.min(...lowers).toFixed(1)}~${Math.max(...uppers).toFixed(1)}`;
  }

  const peHistoryStatus = `当前 ${data.current_pe}，历史分位 ${data.pe_percentile}%`;

  const pbHistoryStatus = `当前 ${data.current_pb}，历史分位 ${data.pb_percentile}%`;

  let lstmForecastStatus = '暂无预测';
  if (hasForecast && forecastValues.length > 0) {
    const days = data.forecast_horizon_days || forecastValues.length;
    const avgForecast = forecastValues.reduce((a, b) => a + b, 0) / forecastValues.length;
    const lastForecast = forecastValues[forecastValues.length - 1];
    if (currentPe > 0) {
      const changePct = ((avgForecast - currentPe) / currentPe) * 100;
      const direction = Math.abs(changePct) < 1
        ? '基本持平'
        : changePct > 0
          ? `较当前 ${formatSignedPct(changePct)}`
          : `较当前 ${formatSignedPct(changePct)}`;
      lstmForecastStatus = `未来 ${days} 天均值 ${avgForecast.toFixed(2)}（${direction}）`;
    } else {
      lstmForecastStatus = `未来 ${days} 天 ${forecastValues[0].toFixed(2)}→${lastForecast.toFixed(2)}`;
    }
  }

  return {
    xLabels,
    histLen,
    hasForecast,
    splitIndex: histLen - 1,
    histSeries,
    forecastSeries,
    trendSeries,
    upperSeries,
    lowerSeries,
    ciBaseSeries,
    ciFillSeries,
    trendStatus,
    bandStatus,
    confidenceStatus,
    peHistoryStatus,
    pbHistoryStatus,
    lstmForecastStatus,
  };
});

const initChart = async () => {
  if (!chartContainer.value || !cycleData.value) return;

  const echarts = await import('echarts');
  if (chartInstance) chartInstance.dispose();
  chartInstance = echarts.init(chartContainer.value);

  const days = getChartDisplayDays(timeRange.value);
  const peHistory = cycleData.value.pe_history.slice(-days);
  const pbHistory = cycleData.value.pb_history.slice(-days);

  if (peHistory.length === 0) {
    chartInstance.setOption({
      title: {
        text: '暂无足够历史数据',
        left: 'center',
        top: 'middle',
        textStyle: { color: '#94a3b8', fontSize: 14, fontWeight: 'normal' },
      },
    });
    return;
  }

  const peValues = peHistory.map((item) => item.value);
  const pbValues = pbHistory.map((item) => item.value);
  const trendLine = computeLinearTrend(peValues);
  const upperBand = trendLine.map((v) => v * 1.1);
  const lowerBand = trendLine.map((v) => v * 0.9);

  const peForecast = cycleData.value.forecast_available ? (cycleData.value.pe_forecast ?? []) : [];
  const hasForecast = peForecast.length > 0;
  const forecastLen = peForecast.length;
  const histLen = peHistory.length;

  const histDates = peHistory.map((item) => item.date);
  const forecastDates = peForecast.map((item) => item.date);
  const xLabels = hasForecast ? [...histDates, ...forecastDates] : histDates;
  const xAxisData = xLabels.map(formatMMDD);

  const peData = padSeries(peValues, forecastLen, null);
  const pbData = padSeries(pbValues, forecastLen, null);
  const trendData = padSeries(trendLine, forecastLen, null);
  const upperData = padSeries(upperBand, forecastLen, null);
  const lowerData = padSeries(lowerBand, forecastLen, null);
  const lstmData = hasForecast
    ? [...Array(Math.max(histLen - 1, 0)).fill(null), peValues[histLen - 1], ...peForecast.map((p) => p.value)]
    : [];

  const legendItems = hasForecast
    ? ['PE历史', 'PB历史', 'LSTM 预测 PE', '趋势线', '上轨', '下轨']
    : ['PE历史', 'PB历史', '趋势线', '上轨', '下轨'];

  const series: Record<string, unknown>[] = [
    {
      name: 'PE历史',
      type: 'line',
      data: peData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: true,
      lineStyle: { color: '#6366f1', width: 2 },
      itemStyle: { color: '#ffffff', borderColor: '#6366f1', borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(99, 102, 241, 0.3)' },
            { offset: 1, color: 'rgba(99, 102, 241, 0.05)' },
          ],
        },
      },
      z: 4,
    },
    {
      name: 'PB历史',
      type: 'line',
      data: pbData,
      smooth: true,
      symbol: 'circle',
      symbolSize: 5,
      showSymbol: true,
      lineStyle: { color: '#22c55e', width: 2 },
      itemStyle: { color: '#ffffff', borderColor: '#22c55e', borderWidth: 2 },
      z: 3,
    },
    {
      name: '趋势线',
      type: 'line',
      data: trendData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#a855f7', width: 2, type: 'dashed' },
      z: 2,
    },
    {
      name: '上轨',
      type: 'line',
      data: upperData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#a855f7', width: 1, type: 'dotted' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(168, 85, 247, 0.1)' },
            { offset: 1, color: 'rgba(168, 85, 247, 0.02)' },
          ],
        },
      },
      z: 1,
    },
    {
      name: '下轨',
      type: 'line',
      data: lowerData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#a855f7', width: 1, type: 'dotted' },
      z: 1,
    },
  ];

  if (hasForecast) {
    series.splice(2, 0, {
      name: 'LSTM 预测 PE',
      type: 'line',
      data: lstmData,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#f39c12', width: 3, type: 'dashed' },
      itemStyle: { color: '#f39c12' },
      z: 5,
    });
  }

  chartInstance.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: unknown) => {
        const items = Array.isArray(params) ? params : [params];
        if (items.length === 0) return '';
        const idx = (items[0] as { dataIndex?: number }).dataIndex ?? 0;
        const lines = [`<span style="font-weight:600">${formatMMDD(xLabels[idx] ?? '')}</span>`];
        legendItems.forEach((name) => {
          const hit = items.find((it) => (it as { seriesName?: string }).seriesName === name) as
            | { value?: number | null }
            | undefined;
          if (!hit || hit.value == null || Number.isNaN(hit.value)) return;
          lines.push(`${name}：${Number(hit.value).toFixed(2)}`);
        });
        return lines.join('<br/>');
      },
    },
    legend: {
      data: legendItems,
      bottom: 36,
      left: 'center',
      itemGap: 24,
      itemWidth: 14,
      itemHeight: 8,
      textStyle: { fontSize: 12, color: '#64748b' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '22%',
      top: '10%',
      containLabel: true,
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        bottom: 4,
        height: 20,
        showDetail: false,
        showDataShadow: false,
        brushSelect: false,
        borderColor: '#e2e8f0',
        backgroundColor: '#f8fafc',
        fillerColor: 'rgba(99, 102, 241, 0.12)',
        handleStyle: { color: '#94a3b8', borderColor: '#cbd5e1' },
      },
    ],
    xAxis: {
      type: 'category',
      data: xAxisData,
      boundaryGap: false,
      axisLabel: { rotate: 45, fontSize: 10, color: '#64748b' },
      axisLine: { lineStyle: { color: '#e2e8f0' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '估值',
      scale: true,
      axisLabel: { fontSize: 10, color: '#64748b' },
      splitLine: { lineStyle: { type: 'dashed', color: '#e2e8f0' } },
      axisLine: { show: false },
      axisTick: { show: false },
    },
    graphic: !hasForecast
      ? [{
          type: 'text',
          right: 14,
          top: 12,
          style: { text: '数据不足，无法预测', fill: '#f39c12', fontSize: 11 },
        }]
      : [],
    series,
  }, true);
};

const fetchCycleAnalysis = async () => {
  if (!activeAssetCode.value) return;

  isLoading.value = true;
  error.value = '';

  try {
    const tsCode = normalizeTsCode(activeAssetCode.value);
    const response = await fetch('/api/cycle/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        asset_code: tsCode,
        time_range: timeRange.value,
        lookback_days: lookbackDays.value,
      }),
    });

    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `获取周期分析失败 (${response.status})`);
    }

    cycleData.value = normalizeCycleData(await response.json());
    setTimeout(() => initChart(), 100);
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取周期分析数据失败';
    cycleData.value = null;
  } finally {
    isLoading.value = false;
  }
};

const applyManualCode = () => {
  const code = manualCode.value.trim();
  if (!code) return;
  selectedAsset.value = '';
  fetchCycleAnalysis();
};

const onSelectAsset = () => {
  manualCode.value = '';
};

watch(selectedAsset, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal) fetchCycleAnalysis();
});

watch(timeRange, () => {
  if (activeAssetCode.value) fetchCycleAnalysis();
});

const handleResize = () => chartInstance?.resize();

onMounted(async () => {
  portfolioStore.loadPortfolio();
  if (hasAssets.value && portfolioAssets.value.length > 0) {
    await portfolioStore.refreshLiveQuotes();
    selectedAsset.value = portfolioAssets.value[0].code;
    fetchCycleAnalysis();
  }
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  chartInstance?.dispose();
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
        <h1 class="text-xl font-bold text-slate-900">资产周期分析</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-8">
        <div class="flex items-center gap-3">
          <BrainIcon class="w-6 h-6 text-indigo-600 shrink-0" />
          <p class="text-sm text-indigo-800">
            结合历史 PE/PB 分位与 LSTM 时序预测，分析资产估值所处周期。仅提供状态参考，不构成买卖建议。
          </p>
        </div>
      </div>

      <!-- 头部：股票选择 + 时间周期 -->
      <div class="bg-white rounded-xl border border-slate-200 p-4 mb-6">
        <div class="flex flex-wrap gap-4 items-end">
          <div v-if="hasAssets" class="flex-1 min-w-[200px]">
            <label class="block text-xs text-slate-500 mb-1">从持仓选择</label>
            <select
              v-model="selectedAsset"
              class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              @change="onSelectAsset"
            >
              <option value="">手动输入代码</option>
              <option v-for="asset in portfolioAssets" :key="asset.code" :value="asset.code">
                {{ asset.name }} ({{ asset.code }})
              </option>
            </select>
          </div>
          <div v-else class="flex-1 min-w-[200px]">
            <p class="text-sm text-slate-500 mb-2">暂无持仓，请手动输入股票代码</p>
            <button
              @click="router.push('/portfolio/import')"
              class="text-sm text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              <UploadIcon class="w-4 h-4" /> 前往导入持仓
            </button>
          </div>
          <div class="flex-1 min-w-[200px]">
            <label class="block text-xs text-slate-500 mb-1">手动输入代码</label>
            <div class="flex gap-2">
              <input
                v-model="manualCode"
                type="text"
                placeholder="如 600519 或 600519.SH"
                class="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                @keyup.enter="applyManualCode"
              />
              <button
                @click="applyManualCode"
                class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm"
              >
                分析
              </button>
            </div>
          </div>
          <div class="flex gap-2 flex-wrap">
            <button
              v-for="range in ['1m', '3m', '6m', '1y', '3y']"
              :key="range"
              @click="timeRange = range"
              class="px-4 py-2 rounded-lg font-medium transition-colors text-sm"
              :class="timeRange === range ? 'bg-indigo-600 text-white' : 'bg-slate-50 border border-slate-300 text-slate-600 hover:bg-slate-100'"
            >
              {{ range === '1m' ? '1个月' : range === '3m' ? '3个月' : range === '6m' ? '6个月' : range === '1y' ? '1年' : '3年' }}
            </button>
          </div>
        </div>
        <p v-if="cycleData" class="text-xs text-slate-400 mt-3">
          当前分析：{{ displayName }}（{{ cycleData.ts_code }}）· {{ timeRangeLabel }}
        </p>
      </div>

      <div v-if="!activeAssetCode && !hasAssets" class="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <UploadIcon class="w-10 h-10 text-slate-400 mx-auto mb-3" />
        <p class="text-slate-600">请输入股票代码或导入持仓后开始分析</p>
      </div>

      <div v-else-if="isLoading" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span class="ml-3 text-slate-600">加载估值与 LSTM 预测数据...</span>
      </div>

      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <p class="text-red-800 font-medium mb-2">加载失败</p>
        <p class="text-sm text-red-600">{{ error }}</p>
        <button
          @click="fetchCycleAnalysis"
          class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm"
        >
          重试
        </button>
      </div>

      <template v-else-if="cycleData">
        <div class="space-y-5">
          <div
            v-if="!isInPortfolio"
            class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"
          >
            该股票不在您的持仓中，以下分析仅供参考，不构成操作建议。
          </div>

          <!-- 左右两栏：左图表+PE/PB，右周期判定+建议 -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
            <!-- 左栏：估值周期分析 + 图表 + PE/PB -->
            <div class="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6">
              <div class="flex items-center justify-between mb-4">
                <h2 class="text-lg font-semibold text-slate-900">估值周期分析</h2>
                <span class="text-xs px-3 py-1.5 rounded-full font-medium shrink-0" :class="intervalBadgeClass">
                  当前阶段：{{ cycleData.interval }}
                </span>
              </div>
              <div ref="chartContainer" class="h-96 w-full" />
              <p v-if="chartNotice" class="mt-2 text-sm text-amber-600 text-center">{{ chartNotice }}</p>
              <p v-if="dataAsOfDate" class="mt-2 text-sm text-slate-500 text-center">
                📅 数据基于截至 {{ dataAsOfDate }} 的行情
              </p>

              <details v-if="chartMetrics" class="mt-4 rounded-lg border border-slate-200 bg-slate-50 overflow-hidden group">
                <summary class="px-4 py-3 text-sm font-medium text-slate-700 cursor-pointer select-none hover:bg-slate-100 transition-colors list-none [&::-webkit-details-marker]:hidden">
                  📖 指标说明（点开学习）
                </summary>
                <div class="px-4 pb-4 overflow-x-auto">
                  <table class="w-full text-sm text-left border-collapse">
                    <thead>
                      <tr class="text-xs text-slate-500 border-b border-slate-200">
                        <th class="py-2 pr-4 font-medium">指标</th>
                        <th class="py-2 pr-4 font-medium">它代表什么</th>
                        <th class="py-2 font-medium">当前状态</th>
                      </tr>
                    </thead>
                    <tbody class="text-slate-700">
                      <tr class="border-b border-slate-100">
                        <td class="py-2.5 pr-4 font-medium whitespace-nowrap">PE历史</td>
                        <td class="py-2.5 pr-4 text-slate-600">市盈率历史走势，反映市场对公司盈利的估值水平（蓝线）</td>
                        <td class="py-2.5 text-indigo-700 font-medium">{{ chartMetrics.peHistoryStatus }}</td>
                      </tr>
                      <tr class="border-b border-slate-100">
                        <td class="py-2.5 pr-4 font-medium whitespace-nowrap">PB历史</td>
                        <td class="py-2.5 pr-4 text-slate-600">市净率历史走势，反映市场对公司净资产的估值水平（绿线）</td>
                        <td class="py-2.5 text-indigo-700 font-medium">{{ chartMetrics.pbHistoryStatus }}</td>
                      </tr>
                      <tr class="border-b border-slate-100">
                        <td class="py-2.5 pr-4 font-medium whitespace-nowrap">LSTM 预测 PE</td>
                        <td class="py-2.5 pr-4 text-slate-600">LSTM 时序模型基于历史 PE 预测未来走向，橙色虚线为预测值</td>
                        <td class="py-2.5 text-indigo-700 font-medium">{{ chartMetrics.lstmForecastStatus }}</td>
                      </tr>
                      <tr class="border-b border-slate-100">
                        <td class="py-2.5 pr-4 font-medium whitespace-nowrap">趋势线</td>
                        <td class="py-2.5 pr-4 text-slate-600">估值的长期方向，向上=涨，向下=跌（线性回归）</td>
                        <td class="py-2.5 text-indigo-700 font-medium">{{ chartMetrics.trendStatus }}</td>
                      </tr>
                      <tr class="border-b border-slate-100">
                        <td class="py-2.5 pr-4 font-medium whitespace-nowrap">上轨/下轨</td>
                        <td class="py-2.5 pr-4 text-slate-600">正常波动范围，趋势线 ±10%，触上轨可能回调</td>
                        <td class="py-2.5 text-indigo-700 font-medium">{{ chartMetrics.bandStatus }}</td>
                      </tr>
                      <tr>
                        <td class="py-2.5 pr-4 font-medium whitespace-nowrap">置信区间</td>
                        <td class="py-2.5 pr-4 text-slate-600">预测的可能范围，越窄越确定（±1.96×标准差）</td>
                        <td class="py-2.5 text-indigo-700 font-medium">{{ chartMetrics.confidenceStatus }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </details>

              <div
                v-if="predictionBlock"
                class="lstm-prediction mt-5 rounded-xl border border-slate-200 bg-slate-50 px-5 py-4"
              >
                <div class="space-y-2.5 text-sm sm:text-base text-slate-700 leading-relaxed">
                  <p v-if="predictionBlock.lstm">
                    {{ predictionBlock.lstm.icon }}
                    <strong class="text-slate-900">LSTM 预测</strong>：未来 {{ predictionBlock.lstm.days }} 天估值可能会<strong class="text-slate-900">{{ predictionBlock.lstm.phrase }}</strong>（约 {{ predictionBlock.lstm.changeLabel }}），有<strong class="text-slate-900">{{ predictionBlock.lstm.confidence }}把握</strong>。
                  </p>
                  <p v-if="isInPortfolio">
                    {{ predictionBlock.status.icon }}
                    <strong class="text-slate-900">当前状态</strong>：{{ predictionBlock.status.level }}，建议<strong class="text-slate-900">{{ predictionBlock.status.suggestion }}</strong>（置信度 {{ cycleData.confidence }}%）。
                  </p>
                  <p v-else>
                    {{ predictionBlock.status.icon }}
                    <strong class="text-slate-900">当前状态</strong>：{{ predictionBlock.status.level }}。
                  </p>
                </div>
                <div v-if="predictionBlock.lstm" class="prediction-details mt-3 pt-3 border-t border-slate-200">
                  <p class="text-xs font-medium text-slate-600 mb-2">详细依据</p>
                  <ul class="space-y-1 text-xs text-slate-500">
                    <li v-for="(line, idx) in predictionBlock.lstm.details" :key="idx">{{ line }}</li>
                  </ul>
                </div>
              </div>

              <!-- PE / PB 数值卡片 -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5 pt-5 border-t border-slate-100">
                <div class="rounded-lg border border-slate-200 p-4 flex flex-col">
                  <p class="text-sm text-slate-500 mb-1">市盈率 (PE)</p>
                  <p class="text-3xl font-bold text-slate-900">{{ cycleData.current_pe }}</p>
                  <p class="text-xs text-slate-500 mt-2">历史分位: {{ cycleData.pe_percentile }}%</p>
                  <div class="mt-auto pt-3">
                    <div class="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                      <div
                        class="h-2 rounded-full transition-all duration-300"
                        :style="{ width: `${peProgressWidth}%`, backgroundColor: '#6366f1' }"
                      />
                    </div>
                  </div>
                </div>
                <div class="rounded-lg border border-slate-200 p-4 flex flex-col">
                  <p class="text-sm text-slate-500 mb-1">市净率 (PB)</p>
                  <p class="text-3xl font-bold text-slate-900">{{ cycleData.current_pb }}</p>
                  <p class="text-xs text-slate-500 mt-2">历史分位: {{ cycleData.pb_percentile }}%</p>
                  <div class="mt-auto pt-3">
                    <div class="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                      <div
                        class="h-2 rounded-full transition-all duration-300"
                        :style="{ width: `${pbProgressWidth}%`, backgroundColor: '#22c55e' }"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 右栏：周期判定 + 建议区间 -->
            <div class="space-y-5">
              <div class="bg-white rounded-xl border border-slate-200 p-6">
                <h2 class="text-lg font-semibold text-slate-900 mb-4">周期判定</h2>
                <div class="space-y-3">
                  <div
                    class="flex items-center gap-3 p-3 rounded-lg border transition-all"
                    :class="isUndervalued ? 'bg-emerald-50 border-2 border-emerald-500 shadow-sm' : 'bg-emerald-50/40 border-emerald-200'"
                  >
                    <div class="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center shrink-0">
                      <TrendingDownIcon class="w-4 h-4 text-emerald-600" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="font-medium text-emerald-900">低估区间</p>
                      <p class="text-xs text-emerald-700">PE/PB 处于历史低位 30% 以下</p>
                    </div>
                    <span v-if="isUndervalued" class="px-2 py-0.5 bg-emerald-600 text-white text-xs rounded font-medium shrink-0">当前</span>
                  </div>
                  <div
                    class="flex items-center gap-3 p-3 rounded-lg border transition-all"
                    :class="isFair ? 'bg-blue-50 border-2 border-blue-500 shadow-sm' : 'bg-blue-50/40 border-blue-200'"
                  >
                    <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center shrink-0">
                      <MinusIcon class="w-4 h-4 text-blue-600" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="font-medium text-blue-900">合理区间</p>
                      <p class="text-xs text-blue-700">PE/PB 处于历史 30%-70% 分位</p>
                    </div>
                    <span v-if="isFair" class="px-2 py-0.5 bg-blue-600 text-white text-xs rounded font-medium shrink-0">当前</span>
                  </div>
                  <div
                    class="flex items-center gap-3 p-3 rounded-lg border transition-all"
                    :class="isOvervalued ? 'bg-red-50 border-2 border-red-500 shadow-sm' : 'bg-red-50/40 border-red-200'"
                  >
                    <div class="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center shrink-0">
                      <TrendingUpIcon class="w-4 h-4 text-red-600" />
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="font-medium text-red-900">高估区间</p>
                      <p class="text-xs text-red-700">PE/PB 处于历史高位 70% 以上</p>
                    </div>
                    <span v-if="isOvervalued" class="px-2 py-0.5 bg-red-600 text-white text-xs rounded font-medium shrink-0">当前</span>
                  </div>
                </div>
              </div>

              <div v-if="isInPortfolio" class="bg-white rounded-xl border border-slate-200 p-6">
                <p class="text-lg font-semibold text-slate-900 mb-4">建议区间</p>
                <div class="rounded-lg border p-4" :class="suggestionCardClass">
                  <div class="flex items-start gap-2 mb-2">
                    <AlertTriangleIcon class="w-5 h-5 shrink-0 mt-0.5" :class="isUndervalued ? 'text-emerald-600' : isOvervalued ? 'text-red-600' : 'text-blue-600'" />
                    <p class="text-lg font-bold" :class="isUndervalued ? 'text-emerald-700' : isOvervalued ? 'text-red-700' : 'text-blue-700'">
                      {{ cycleData.suggestion }}
                    </p>
                  </div>
                  <p class="text-sm leading-relaxed" :class="isUndervalued ? 'text-emerald-700' : isOvervalued ? 'text-red-700' : 'text-blue-700'">
                    {{ suggestionDetailText }}
                  </p>
                </div>
                <p class="text-xs text-slate-400 mt-3">基于估值分位与 LSTM 趋势的综合区间判断，不构成具体买卖指令。</p>
                <p class="text-xs text-slate-500 mt-1">置信度 {{ cycleData.confidence }}%</p>
              </div>
            </div>
          </div>

          <!-- 分析依据（全宽底部） -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <DatabaseIcon class="w-5 h-5 text-slate-500" />
              <span class="font-semibold text-slate-900">分析依据</span>
            </div>
            <div class="space-y-2 text-sm text-slate-600">
              <div class="flex items-center gap-2">
                <ClockIcon class="w-4 h-4 text-slate-400" />
                <span>数据区间：{{ timeRangeLabel }}（{{ cycleData.lookback_days }} 天）</span>
              </div>
              <div class="flex items-center gap-2">
                <DatabaseIcon class="w-4 h-4 text-slate-400" />
                <span>数据来源：Tushare {{ cycleData.use_price_fallback ? '（估值限流时使用日线替代）' : '历史估值' }}</span>
              </div>
              <div class="flex items-center gap-2">
                <CpuIcon class="w-4 h-4 text-slate-400" />
                <span>模型：LSTM 时序预测 + 历史分位规则</span>
              </div>
              <div class="flex items-center gap-2">
                <AlertTriangleIcon class="w-4 h-4 text-slate-400" />
                <span>模型版本：{{ cycleData.model_version }} · 置信度 {{ cycleData.confidence }}%（样本量与预测可用性综合估算）</span>
              </div>
              <div class="mt-3 pt-3 border-t border-slate-100 grid grid-cols-2 gap-2 text-xs text-slate-500">
                <p>PE 30% 分位：{{ cycleData.pe_30_percentile }}</p>
                <p>PE 70% 分位：{{ cycleData.pe_70_percentile }}</p>
                <p>PB 30% 分位：{{ cycleData.pb_30_percentile }}</p>
                <p>PB 70% 分位：{{ cycleData.pb_70_percentile }}</p>
              </div>
              <p class="text-xs text-slate-400 pt-2">基于估值分位与 LSTM 趋势的综合区间判断，不构成具体买卖指令。</p>
            </div>
          </div>
        </div>
      </template>
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
