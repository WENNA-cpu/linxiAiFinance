<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import RiskBanner from '@/components/RiskBanner.vue';
import DataLineageChart, { type LineageStep } from '@/components/DataLineageChart.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import ClockIcon from '@/components/icons/ClockIcon.vue';
import DatabaseIcon from '@/components/icons/DatabaseIcon.vue';
import CpuIcon from '@/components/icons/CpuIcon.vue';
import ShieldIcon from '@/components/icons/ShieldIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import FileTextIcon from '@/components/icons/FileTextIcon.vue';
import LinkIcon from '@/components/icons/LinkIcon.vue';
import GlobeIcon from '@/components/icons/GlobeIcon.vue';
import LayersIcon from '@/components/icons/LayersIcon.vue';
import AlertTriangleIcon from '@/components/icons/AlertTriangleIcon.vue';

const router = useRouter();
const route = useRoute();

const requestId = ref(route.params.requestId as string || route.query.request_id as string);
const isLoading = ref(true);
const error = ref('');

interface TraceLog {
  step_order?: number;
  step_name: string;
  step_status: string;
  step_detail: string;
  started_at: string;
  completed_at: string;
}

interface TraceData {
  request_id: string;
  found: boolean;
  message?: string;
  generated_at?: string;
  logs: TraceLog[];
  steps?: LineageStep[];
  summary: {
    total_steps: number;
    success_steps: number;
    failed_steps: number;
    warning_steps?: number;
    expected_steps?: number;
    is_complete?: boolean;
  };
  data_sources?: string[];
  model_analysis?: string[];
  rule_checks?: string[];
  is_mock?: boolean;
  error_detail?: string;
}

interface FeedbackItem {
  feedback_type: string;
  reason: string | null;
  created_at: string | null;
}

const traceData = ref<TraceData | null>(null);
const isLineageLoading = ref(true);
const activeDetailTab = ref('audit');
const feedbacks = ref<FeedbackItem[]>([]);
const feedbackLoading = ref(false);
const feedbackError = ref('');

const resolveRequestIdFromRoute = (): string => {
  const fromParam = route.params.requestId as string | undefined;
  const fromQuery = route.query.request_id as string | undefined;
  let id = (fromParam || fromQuery || '').trim();

  if (!id || id === 'latest') {
    id = (localStorage.getItem('last_diagnosis_id') || '').trim();
  }

  requestId.value = id;
  return id;
};

// 格式化时间
const formatTime = (isoString: string) => {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

// 格式化日期时间
const formatDateTime = (isoString: string) => {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleString('zh-CN');
};

// 计算处理时长
const getDuration = (started: string, completed: string) => {
  if (!started || !completed) return '-';
  const start = new Date(started).getTime();
  const end = new Date(completed).getTime();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

// 数据来源（来自「数据获取」步骤的真实日志）
const dataSources = computed(() => {
  if (!traceData.value?.logs) return [];
  return traceData.value.logs
    .filter(log => log.step_name === '数据获取')
    .map(log => ({
      name: log.step_name,
      detail: log.step_detail,
      type: 'api' as const,
      status: log.step_status,
      time: formatTime(log.completed_at || log.started_at),
    }));
});

// 全流程 7 步时间线（直接映射 API logs）
const processingTimeline = computed(() => auditLogs.value);

const isCompleteTrace = computed(() => traceData.value?.summary?.is_complete === true);

const statusLabel = (status: string) => {
  if (status === '成功') return '成功';
  if (status === '失败') return '失败';
  if (status === '警告') return '警告';
  return status;
};

const statusBadgeClass = (status: string) => {
  if (status === '成功') return 'bg-emerald-100 text-emerald-700';
  if (status === '失败') return 'bg-red-100 text-red-700';
  if (status === '警告') return 'bg-amber-100 text-amber-700';
  return 'bg-slate-100 text-slate-700';
};

// 分析维度列表 - 从审计日志中提取
const analysisDimensions = computed(() => {
  if (!traceData.value?.logs?.length) return [];

  const stepMap: Record<string, { model: string; color: string }> = {
    'LSTM模型预测': { model: 'LSTM时序模型', color: 'purple' },
    '随机森林风险评估': { model: '随机森林分类器', color: 'red' },
    '数据清洗': { model: '数据预处理管道', color: 'blue' },
    '数据获取': { model: 'Tushare行情API', color: 'emerald' },
  };

  return traceData.value.logs
    .filter(log => stepMap[log.step_name])
    .map(log => ({
      name: log.step_name,
      model: stepMap[log.step_name].model,
      confidence: log.step_status === '成功' ? 90 : log.step_status === '警告' ? 75 : 60,
      color: stepMap[log.step_name].color,
      detail: log.step_detail,
    }));
});

// 规则校验列表
const ruleChecks = computed(() => {
  if (!traceData.value?.logs) return [];
  return traceData.value.logs
    .filter(log => log.step_name.includes('规则') || log.step_name.includes('校验'))
    .map(log => ({
      name: log.step_name,
      status: log.step_status === '成功' ? 'passed' : log.step_status === '警告' ? 'warning' : 'failed',
      detail: log.step_detail,
      rawStatus: log.step_status,
    }));
});

// 将审计日志映射为血缘图 steps 格式
const mapLogToLineageStep = (log: TraceLog): LineageStep => {
  let step_status: LineageStep['step_status'];
  if (log.step_status === '失败') {
    step_status = 'failed';
  } else if (log.step_status === '成功' || log.step_status === '警告') {
    step_status = 'success';
  } else if (!log.completed_at) {
    step_status = 'running';
  } else {
    step_status = 'success';
  }

  let duration_ms: number | undefined;
  if (log.started_at && log.completed_at) {
    duration_ms = Math.max(
      0,
      new Date(log.completed_at).getTime() - new Date(log.started_at).getTime(),
    );
  }

  return {
    step_name: log.step_name,
    step_status,
    step_detail: log.step_detail,
    duration_ms,
  };
};

const lineageSteps = computed((): LineageStep[] | null => {
  if (traceData.value?.steps?.length) {
    return traceData.value.steps;
  }
  if (traceData.value?.logs?.length) {
    return traceData.value.logs.map(mapLogToLineageStep);
  }
  return null;
});

const isDemoLineage = computed(() => !lineageSteps.value?.length);

// 审计日志列表（按步骤顺序排列）
const auditLogs = computed(() => {
  if (!traceData.value?.logs) return [];
  const sorted = [...traceData.value.logs].sort((a, b) => {
    if (a.step_order != null && b.step_order != null) return a.step_order - b.step_order;
    return new Date(a.started_at).getTime() - new Date(b.started_at).getTime();
  });
  return sorted.map((log, index) => ({
    step: log.step_order ?? index + 1,
    time: formatTime(log.completed_at || log.started_at),
    duration: getDuration(log.started_at, log.completed_at),
    action: log.step_name,
    detail: log.step_detail,
    status: log.step_status,
  }));
});

const feedbackTypeLabel = (feedbackType: string) => {
  const normalized = feedbackType.trim().toLowerCase();
  if (normalized === 'helpful' || normalized === 'positive') return '有帮助';
  if (normalized === 'unhelpful' || normalized === 'negative') return '需改进';
  return feedbackType;
};

const feedbackTypeClass = (feedbackType: string) => {
  const normalized = feedbackType.trim().toLowerCase();
  if (normalized === 'helpful' || normalized === 'positive') {
    return 'bg-emerald-100 text-emerald-700';
  }
  if (normalized === 'unhelpful' || normalized === 'negative') {
    return 'bg-red-100 text-red-700';
  }
  return 'bg-slate-100 text-slate-700';
};

const isHelpfulFeedback = (feedbackType: string) => {
  const normalized = feedbackType.trim().toLowerCase();
  return normalized === 'helpful' || normalized === 'positive';
};

const feedbackCardClass = (feedbackType: string) =>
  isHelpfulFeedback(feedbackType)
    ? 'border-l-4 border-l-emerald-500 bg-emerald-50/40'
    : 'border-l-4 border-l-red-500 bg-red-50/40';

const fetchFeedbacks = async (targetId?: string) => {
  const rid = (targetId ?? requestId.value)?.trim();
  if (!rid || rid === 'latest') return;

  feedbackLoading.value = true;
  feedbackError.value = '';

  try {
    const response = await fetch(`/api/feedback/by-request/${encodeURIComponent(rid)}`);
    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `获取用户反馈失败 (${response.status})`);
    }
    const data = await response.json();
    feedbacks.value = Array.isArray(data.feedbacks) ? data.feedbacks : [];
  } catch (err) {
    feedbackError.value = err instanceof Error ? err.message : '获取用户反馈失败';
  } finally {
    feedbackLoading.value = false;
  }
};

// 获取溯源与血缘数据
const fetchTraceData = async (targetId?: string) => {
  isLoading.value = true;
  error.value = '';
  isLineageLoading.value = true;

  const rid = (targetId ?? requestId.value)?.trim();
  if (!rid) {
    error.value = '未找到历史诊断记录，请先完成一次持仓诊断';
    isLoading.value = false;
    isLineageLoading.value = false;
    return;
  }

  requestId.value = rid;

  try {
    const response = await fetch(`/api/trace/${encodeURIComponent(rid)}`);
    if (!response.ok) {
      const errBody = await response.json().catch(() => ({}));
      throw new Error(errBody.detail || `获取溯源信息失败 (${response.status})`);
    }
    const data = await response.json();
    traceData.value = data;
  } catch (err) {
    error.value = err instanceof Error ? err.message : '获取溯源信息失败';
    traceData.value = null;
  } finally {
    isLoading.value = false;
    isLineageLoading.value = false;
  }
};

const loadPageData = async () => {
  const rid = resolveRequestIdFromRoute();
  if (!rid) {
    error.value = '未找到历史诊断记录，请先完成一次持仓诊断';
    isLoading.value = false;
    isLineageLoading.value = false;
    return;
  }

  await Promise.all([fetchTraceData(rid), fetchFeedbacks(rid)]);
};

onMounted(() => {
  loadPageData();
});

watch(
  () => `${String(route.params.requestId ?? '')}|${String(route.query.request_id ?? '')}`,
  (signature, prevSignature) => {
    if (signature === prevSignature) return;
    loadPageData();
  },
);

</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <RiskBanner />

    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center gap-4">
        <button @click="router.push('/')" class="p-2 hover:bg-slate-100 rounded-lg transition-colors">
          <HomeIcon class="w-5 h-5 text-slate-600" />
        </button>
        <h1 class="text-xl font-bold text-slate-900">AI分析依据溯源</h1>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 py-8">
      <!-- 加载中 -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span class="ml-3 text-slate-600">加载溯源信息...</span>
      </div>

      <!-- 错误提示 -->
      <div v-else-if="error" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-center gap-3">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600" />
          <div class="flex-1">
            <p class="font-medium text-amber-900">{{ error }}</p>
            <p class="text-sm text-amber-600 mt-1">
              请先前往「持仓诊断」页面进行一次诊断，或检查 Request ID 是否正确
            </p>
          </div>
        </div>
        <div class="mt-4 flex gap-3">
          <button
            @click="router.push('/portfolio/diagnosis')"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            前往持仓诊断
          </button>
          <button
            @click="router.push('/')"
            class="px-4 py-2 bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors"
          >
            返回首页
          </button>
        </div>
      </div>

      <!-- 未找到数据 -->
      <div v-else-if="traceData && !traceData.found" class="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
        <div class="flex items-center gap-3">
          <AlertTriangleIcon class="w-6 h-6 text-amber-600" />
          <div>
            <p class="font-medium text-amber-900">未找到该次诊断的溯源信息</p>
            <p class="text-sm text-amber-600 mt-1">Request ID: {{ requestId }}</p>
          </div>
        </div>
      </div>

      <!-- 正常展示 -->
      <template v-else-if="traceData">

        <div class="bg-indigo-50 border border-indigo-200 rounded-xl p-4 mb-8">
          <div class="flex items-center justify-between flex-wrap gap-3">
            <div class="flex items-center gap-3">
              <FileTextIcon class="w-6 h-6 text-indigo-600" />
              <div>
                <p class="text-sm text-indigo-800 font-medium">Request ID: {{ requestId }}</p>
                <p class="text-xs text-indigo-600">生成时间: {{ formatDateTime(traceData.generated_at || '') }}</p>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span
                v-if="isCompleteTrace"
                class="px-3 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700"
              >
                7 步审计日志完整
              </span>
              <span
                v-else
                class="px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700"
              >
                已记录 {{ traceData.summary.total_steps }}/{{ traceData.summary.expected_steps || 7 }} 步
              </span>
              <button
                @click="router.back()"
                class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
              >
                <ArrowRightIcon class="w-4 h-4 rotate-180" />
                返回
              </button>
            </div>
          </div>
        </div>

        <!-- 审计日志 / 用户反馈 -->
        <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
          <div class="flex items-center gap-2 mb-4">
            <LayersIcon class="w-5 h-5 text-indigo-600" />
            <h2 class="text-lg font-semibold text-slate-900">诊断记录详情</h2>
          </div>

          <div class="border-b border-slate-200 mb-5">
            <nav class="flex gap-1">
              <button
                type="button"
                class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px"
                :class="activeDetailTab === 'audit'
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'"
                @click="activeDetailTab = 'audit'"
              >
                审计日志
              </button>
              <button
                type="button"
                class="px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px flex items-center gap-1.5"
                :class="activeDetailTab === 'feedback'
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'"
                @click="activeDetailTab = 'feedback'"
              >
                用户反馈
                <span
                  v-if="feedbacks.length > 0"
                  class="text-xs px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700"
                >
                  {{ feedbacks.length }}
                </span>
              </button>
            </nav>
          </div>

          <div v-show="activeDetailTab === 'audit'">
              <div class="flex items-center gap-2 mb-4">
                <span class="text-sm font-medium text-slate-700">诊断全流程审计日志</span>
                <span class="text-xs text-slate-400">数据来源：SQLite audit_logs 表</span>
              </div>
              <div v-if="processingTimeline.length === 0" class="text-sm text-slate-500 py-4">
                暂无审计日志
              </div>
              <div v-else class="relative">
                <div
                  v-if="processingTimeline.length > 1"
                  class="absolute left-4 w-0.5 bg-slate-200 -translate-x-1/2 pointer-events-none"
                  style="top: 16px; bottom: 16px"
                />
                <div
                  v-for="log in processingTimeline"
                  :key="log.step"
                  class="flex gap-4 pb-5 last:pb-0"
                >
                  <div
                    class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0 relative z-10"
                    :class="log.status === '成功' ? 'bg-emerald-500' : log.status === '失败' ? 'bg-red-500' : 'bg-amber-500'"
                  >
                    {{ log.step }}
                  </div>
                  <div class="flex-1 min-w-0 pt-0.5">
                    <div class="flex flex-wrap items-center gap-2 mb-1">
                      <span class="font-medium text-slate-900">{{ log.action }}</span>
                      <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadgeClass(log.status)">
                        {{ statusLabel(log.status) }}
                      </span>
                      <span class="text-xs text-slate-400">{{ log.time }}</span>
                      <span v-if="log.duration !== '-'" class="text-xs text-slate-400">耗时 {{ log.duration }}</span>
                    </div>
                    <p class="text-sm text-slate-600">{{ log.detail }}</p>
                  </div>
                </div>
              </div>
          </div>

          <div v-show="activeDetailTab === 'feedback'">
              <div
                v-if="feedbackError"
                class="mb-3 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700 flex items-start gap-2"
              >
                <AlertTriangleIcon class="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{{ feedbackError }}</span>
              </div>
              <div
                v-if="feedbackLoading && feedbacks.length === 0"
                class="flex items-center justify-center py-10 text-sm text-slate-500"
              >
                <div class="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600 mr-2"></div>
                加载用户反馈...
              </div>
              <div
                v-else-if="feedbacks.length === 0"
                class="text-sm text-slate-500 py-10 text-center"
              >
                暂无用户反馈
              </div>
              <div v-else class="space-y-3 mt-2">
                <div
                  v-if="feedbackLoading"
                  class="text-xs text-slate-400 flex items-center gap-2"
                >
                  <div class="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-indigo-600"></div>
                  正在刷新反馈数据...
                </div>
                <div
                  v-for="(item, index) in feedbacks"
                  :key="`${item.created_at}-${index}`"
                  class="p-4 rounded-lg border border-slate-200"
                  :class="feedbackCardClass(item.feedback_type)"
                >
                  <div class="flex flex-wrap items-center gap-2 mb-2">
                    <span
                      class="text-xs px-2.5 py-1 rounded-full font-semibold"
                      :class="feedbackTypeClass(item.feedback_type)"
                    >
                      {{ feedbackTypeLabel(item.feedback_type) }}
                    </span>
                    <span class="text-xs text-slate-400">
                      {{ item.created_at ? formatDateTime(item.created_at) : '-' }}
                    </span>
                  </div>
                  <p v-if="!isHelpfulFeedback(item.feedback_type) && item.reason" class="text-sm text-slate-700">
                    <span class="text-slate-500">反馈原因：</span>{{ item.reason }}
                  </p>
                  <p
                    v-else-if="!isHelpfulFeedback(item.feedback_type)"
                    class="text-sm text-slate-400"
                  >
                    未填写反馈原因
                  </p>
                </div>
              </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <!-- 数据来源 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <DatabaseIcon class="w-5 h-5 text-blue-600" />
              <h2 class="text-lg font-semibold text-slate-900">数据来源</h2>
            </div>
            <div v-if="dataSources.length === 0" class="text-sm text-slate-500 py-4">
              暂无数据源记录
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="source in dataSources"
                :key="source.name + source.time"
                class="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
              >
                <div class="flex items-center gap-3 min-w-0">
                  <GlobeIcon class="w-4 h-4 text-slate-400 flex-shrink-0" />
                  <div class="min-w-0">
                    <span class="text-sm font-medium text-slate-900 block">{{ source.name }}</span>
                    <span class="text-xs text-slate-500 truncate block">{{ source.detail }}</span>
                  </div>
                </div>
                <div class="flex items-center gap-2 flex-shrink-0">
                  <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadgeClass(source.status)">
                    {{ source.status }}
                  </span>
                  <span class="text-xs text-slate-500">{{ source.time }}</span>
                </div>
              </div>
            </div>
            <div class="mt-4 p-3 bg-blue-50 rounded-lg">
              <div class="flex items-center gap-2 text-sm text-blue-800">
                <ClockIcon class="w-4 h-4" />
                <span>记录时间: {{ formatDateTime(traceData.generated_at || '') }}</span>
              </div>
            </div>
          </div>

          <!-- 分析维度 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <CpuIcon class="w-5 h-5 text-purple-600" />
              <h2 class="text-lg font-semibold text-slate-900">分析维度</h2>
            </div>
            <div v-if="analysisDimensions.length === 0" class="text-sm text-slate-500 py-4">
              暂无分析维度记录
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="dim in analysisDimensions"
                :key="dim.name"
                class="p-3 bg-slate-50 rounded-lg"
              >
                <div class="flex items-center justify-between mb-2">
                  <span class="text-sm font-medium text-slate-900">{{ dim.name }}</span>
                  <span class="text-xs text-slate-500">{{ dim.model }}</span>
                </div>
                <p class="text-xs text-slate-600">{{ dim.detail }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <!-- 规则校验记录 -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <ShieldIcon class="w-5 h-5 text-emerald-600" />
              <h2 class="text-lg font-semibold text-slate-900">规则校验记录</h2>
            </div>
            <div v-if="ruleChecks.length === 0" class="text-sm text-slate-500 py-4">
              暂无规则校验记录
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="check in ruleChecks"
                :key="check.name"
                class="flex items-start gap-3 p-3 bg-slate-50 rounded-lg"
              >
                <CheckCircleIcon
                  v-if="check.status === 'passed'"
                  class="w-5 h-5 text-emerald-500 flex-shrink-0"
                />
                <AlertTriangleIcon
                  v-else-if="check.status === 'warning'"
                  class="w-5 h-5 text-amber-500 flex-shrink-0"
                />
                <AlertTriangleIcon v-else class="w-5 h-5 text-red-500 flex-shrink-0" />
                <div>
                  <p class="text-sm font-medium text-slate-900">{{ check.name }}</p>
                  <p class="text-xs text-slate-500">{{ check.detail }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 步骤摘要（与上方时间线同源） -->
          <div class="bg-white rounded-xl border border-slate-200 p-6">
            <div class="flex items-center gap-2 mb-4">
              <LayersIcon class="w-5 h-5 text-amber-600" />
              <h2 class="text-lg font-semibold text-slate-900">步骤摘要</h2>
            </div>
            <div class="space-y-2">
              <div
                v-for="log in auditLogs"
                :key="'s-' + log.step"
                class="flex items-center gap-3 text-sm"
              >
                <span class="w-6 text-center text-indigo-600 font-medium">{{ log.step }}</span>
                <span class="text-slate-900 flex-1">{{ log.action }}</span>
                <span class="text-xs px-2 py-0.5 rounded-full" :class="statusBadgeClass(log.status)">
                  {{ log.status }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 统计摘要 -->
        <div class="bg-white rounded-xl border border-slate-200 p-6 mb-8">
          <h2 class="text-lg font-semibold text-slate-900 mb-4">处理统计</h2>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="text-center p-4 bg-slate-50 rounded-lg">
              <p class="text-2xl font-bold text-slate-900">{{ traceData.summary.total_steps }}</p>
              <p class="text-sm text-slate-500">总步骤</p>
            </div>
            <div class="text-center p-4 bg-emerald-50 rounded-lg">
              <p class="text-2xl font-bold text-emerald-600">{{ traceData.summary.success_steps }}</p>
              <p class="text-sm text-slate-500">成功</p>
            </div>
            <div class="text-center p-4 bg-amber-50 rounded-lg">
              <p class="text-2xl font-bold text-amber-600">{{ traceData.summary.warning_steps || 0 }}</p>
              <p class="text-sm text-slate-500">警告</p>
            </div>
            <div class="text-center p-4 bg-red-50 rounded-lg">
              <p class="text-2xl font-bold text-red-600">{{ traceData.summary.failed_steps }}</p>
              <p class="text-sm text-slate-500">失败</p>
            </div>
          </div>
        </div>
      </template>

      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <div class="flex items-center gap-2 mb-4">
          <LinkIcon class="w-5 h-5 text-indigo-600" />
          <h2 class="text-lg font-semibold text-slate-900">数据血缘图</h2>
        </div>
        <p class="text-sm text-slate-500 mb-4">
          展示从原始数据到最终AI输出的完整处理流程
        </p>
        <div v-if="isLineageLoading" class="flex items-center justify-center py-12">
          <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600"></div>
          <span class="ml-2 text-sm text-slate-500">加载血缘数据...</span>
        </div>
        <DataLineageChart
          v-else
          :steps="lineageSteps"
          :is-demo="isDemoLineage"
        />
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
