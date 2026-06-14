<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import * as XLSX from 'xlsx';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import UploadIcon from '@/components/icons/UploadIcon.vue';
import LockIcon from '@/components/icons/LockIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';
import CloseIcon from '@/components/icons/CloseIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

const showClearConfirm = ref(false);

const hasStoredPortfolio = computed(() => portfolioStore.hasPortfolio);

onMounted(() => {
  portfolioStore.loadPortfolio();
});

const showSecurityModal = ref(false);
const agreedToSecurity = ref(false);
const importMethod = ref<'manual' | 'file'>('manual');

const manualAssets = ref([
  { code: '', name: '', type: 'stock', quantity: 0, costPrice: 0 },
]);

const addAsset = () => {
  manualAssets.value.push({ code: '', name: '', type: 'stock', quantity: 0, costPrice: 0 });
};

const removeAsset = (index: number) => {
  manualAssets.value.splice(index, 1);
};

const handleImport = () => {
  if (!agreedToSecurity.value) {
    showSecurityModal.value = true;
    return;
  }
  submitPortfolio();
};

const submitPortfolio = async () => {
    const validAssets = manualAssets.value.filter(a => a.code && a.name && a.quantity > 0);
    const assets = validAssets.map(a => ({
      code: a.code,
      name: a.name,
      type: a.type as 'stock' | 'fund' | 'bond' | 'other',
      quantity: a.quantity,
      costPrice: a.costPrice,
      currentPrice: 0,
      marketValue: a.quantity * a.costPrice,
    }));
    const totalCost = assets.reduce((sum, a) => sum + a.quantity * a.costPrice, 0);
    const totalValue = assets.reduce((sum, a) => sum + a.marketValue, 0);
    const portfolio = {
      assets,
      totalValue,
      totalCost,
      totalReturn: totalValue - totalCost,
      totalReturnRate: totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0,
    };

    // 保存到本地 store（AES-256 加密写入 localStorage）
    portfolioStore.setPortfolio(portfolio);
    await portfolioStore.refreshLiveQuotes();

    router.push('/portfolio/diagnosis');
};

const confirmSecurity = () => {
  if (agreedToSecurity.value) {
    showSecurityModal.value = false;
    submitPortfolio();
  }
};

const FORMAT_UNSUPPORTED_MSG = '文件格式不支持，请使用下载的模板';

type ParsedAsset = {
  code: string;
  name: string;
  type: string;
  quantity: number;
  costPrice: number;
};

const TYPE_MAP: Record<string, string> = {
  股票: 'stock',
  基金: 'fund',
  债券: 'bond',
  ETF: 'fund',
  etf: 'fund',
  其他: 'other',
  stock: 'stock',
  fund: 'fund',
  bond: 'bond',
  other: 'other',
};

const normalizeCell = (value: unknown): string =>
  String(value ?? '').trim().replace(/^\uFEFF/, '');

const normalizeHeader = (value: unknown): string => normalizeCell(value).toLowerCase();

const findColumnIndex = (headers: string[], matchers: string[]): number =>
  headers.findIndex((header) => {
    const normalized = normalizeHeader(header);
    return matchers.some(
      (matcher) => normalized.includes(matcher.toLowerCase()) || normalized === matcher.toLowerCase(),
    );
  });

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number' && !Number.isNaN(value)) return value;
  const parsed = Number(String(value).replace(/,/g, '').trim());
  return Number.isNaN(parsed) ? null : parsed;
};

const rowsFromWorkbook = (workbook: XLSX.WorkBook): unknown[][] => {
  const sheetName = workbook.SheetNames[0];
  if (!sheetName) return [];
  const sheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(sheet, {
    header: 1,
    defval: '',
    blankrows: false,
    raw: false,
  }) as unknown[][];
};

const parseRowsFromMatrix = (rows: unknown[][]): ParsedAsset[] | { error: string } => {
  const nonEmptyRows = rows.filter(
    (row) => Array.isArray(row) && row.some((cell) => normalizeCell(cell) !== ''),
  );

  if (nonEmptyRows.length < 2) {
    return { error: FORMAT_UNSUPPORTED_MSG };
  }

  const headers = nonEmptyRows[0].map((cell) => normalizeCell(cell));
  const codeIndex = findColumnIndex(headers, ['代码', 'code', '证券代码']);
  const nameIndex = findColumnIndex(headers, ['名称', 'name', '证券名称']);
  const typeIndex = findColumnIndex(headers, ['类型', 'type']);
  const quantityIndex = findColumnIndex(headers, ['数量', 'quantity', '持仓数量']);
  const costPriceIndex = findColumnIndex(headers, ['成本价', '成本', 'cost', '买入价']);

  if (codeIndex === -1 || nameIndex === -1) {
    return { error: FORMAT_UNSUPPORTED_MSG };
  }

  const assets: ParsedAsset[] = [];
  for (let i = 1; i < nonEmptyRows.length; i += 1) {
    const rowNum = i + 1;
    const cells = nonEmptyRows[i].map((cell) => normalizeCell(cell));
    const code = cells[codeIndex] ?? '';
    if (!code) continue;

    const quantityValue = quantityIndex >= 0 ? toNumber(nonEmptyRows[i][quantityIndex]) : null;
    const costValue = costPriceIndex >= 0 ? toNumber(nonEmptyRows[i][costPriceIndex]) : null;

    if (quantityIndex >= 0 && normalizeCell(nonEmptyRows[i][quantityIndex]) && quantityValue === null) {
      return { error: `第 ${rowNum} 行数据格式错误` };
    }
    if (costPriceIndex >= 0 && normalizeCell(nonEmptyRows[i][costPriceIndex]) && costValue === null) {
      return { error: `第 ${rowNum} 行数据格式错误` };
    }

    const typeLabel = typeIndex >= 0 ? normalizeCell(nonEmptyRows[i][typeIndex]) : '';
    assets.push({
      code,
      name: cells[nameIndex] ?? '',
      type: TYPE_MAP[typeLabel] || TYPE_MAP[typeLabel.toLowerCase()] || 'stock',
      quantity: quantityValue ?? 0,
      costPrice: costValue ?? 0,
    });
  }

  if (assets.length === 0) {
    return { error: FORMAT_UNSUPPORTED_MSG };
  }

  return assets;
};

const readWorkbookFromFile = (file: File): Promise<XLSX.WorkBook> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    const lowerName = file.name.toLowerCase();
    const isCsv = lowerName.endsWith('.csv');

    reader.onload = (event) => {
      try {
        const result = event.target?.result;
        if (!result) {
          reject(new Error('empty file'));
          return;
        }

        const workbook = isCsv
          ? XLSX.read(result as string, {
              type: 'string',
              raw: false,
              codepage: 65001,
            })
          : XLSX.read(new Uint8Array(result as ArrayBuffer), {
              type: 'array',
              cellDates: true,
              cellNF: false,
              cellText: false,
              raw: false,
            });

        resolve(workbook);
      } catch (error) {
        reject(error);
      }
    };

    reader.onerror = () => reject(new Error('read failed'));

    if (isCsv) {
      reader.readAsText(file, 'UTF-8');
    } else {
      reader.readAsArrayBuffer(file);
    }
  });

const applyParsedAssets = (assets: ParsedAsset[]) => {
  parsedAssets.value = assets;
  manualAssets.value = assets.map((asset) => ({
    code: asset.code,
    name: asset.name,
    type: asset.type,
    quantity: asset.quantity,
    costPrice: asset.costPrice,
  }));
  showParseSuccess(assets.length);
};

// 下载 Excel 模板（标准 .xlsx）
const downloadTemplate = () => {
  const templateData = [
    ['代码', '名称', '类型', '数量', '成本价'],
    ['000001', '平安银行', '股票', 100, 15.5],
    ['600519', '贵州茅台', '股票', 10, 1500],
    ['510050', '上证50ETF', 'ETF', 500, 2.8],
  ];

  const worksheet = XLSX.utils.aoa_to_sheet(templateData);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, '持仓导入');
  XLSX.writeFile(workbook, '持仓导入模板.xlsx');
};

// 文件上传相关
const fileInput = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const parsedAssets = ref<any[]>([]);

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

  toast.value = {
    visible: true,
    fading: false,
    message,
    type,
  };

  toastTimer = setTimeout(() => hideToast(), 2000);
};

const showParseSuccess = (count: number) => {
  showToast(`成功解析 ${count} 条资产数据`, 'success');
};

const showParseFailure = (message: string) => {
  showToast(message, 'error');
};

onUnmounted(() => {
  if (toastTimer) clearTimeout(toastTimer);
  if (toastFadeTimer) clearTimeout(toastFadeTimer);
});

const clearSelectedFile = () => {
  selectedFile.value = null;
  parsedAssets.value = [];
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  manualAssets.value = [{ code: '', name: '', type: 'stock', quantity: 0, costPrice: 0 }];
};

const handleClearData = () => {
  portfolioStore.clearPortfolio();
  agreedToSecurity.value = false;
  manualAssets.value = [{ code: '', name: '', type: 'stock', quantity: 0, costPrice: 0 }];
  clearSelectedFile();
  showClearConfirm.value = false;
  showToast('本地持仓数据已清空', 'success');
};

const triggerFileSelect = () => {
  fileInput.value?.click();
};

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  // 直接选择新文件时自动替换当前文件
  selectedFile.value = file;
  parsedAssets.value = [];
  parseFile(file);
};

// 解析 CSV / Excel 文件
const parseFile = async (file: File) => {
  const lowerName = file.name.toLowerCase();
  const supported = lowerName.endsWith('.xlsx') || lowerName.endsWith('.xls') || lowerName.endsWith('.csv');

  if (!supported) {
    showParseFailure(FORMAT_UNSUPPORTED_MSG);
    return;
  }

  try {
    const workbook = await readWorkbookFromFile(file);
    const rows = rowsFromWorkbook(workbook);
    const parsed = parseRowsFromMatrix(rows);

    if ('error' in parsed) {
      showParseFailure(parsed.error);
      return;
    }

    applyParsedAssets(parsed);
  } catch {
    showParseFailure(FORMAT_UNSUPPORTED_MSG);
  }
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
        <h1 class="text-xl font-bold text-slate-900">导入持仓</h1>
        <div v-if="hasStoredPortfolio" class="ml-auto flex items-center gap-3">
          <span class="text-sm text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
            已保存 {{ portfolioStore.portfolio.assets.length }} 只资产（本地加密）
          </span>
          <button
            type="button"
            class="text-sm text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors"
            @click="showClearConfirm = true"
          >
            清空数据
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-4 py-8">
      <div class="bg-white rounded-xl border border-slate-200 p-6">
        <div class="flex gap-4 mb-6">
          <button
            @click="importMethod = 'manual'"
            class="flex-1 py-3 px-4 rounded-lg border-2 font-medium transition-all"
            :class="importMethod === 'manual' ? 'border-indigo-600 text-indigo-600 bg-indigo-50' : 'border-slate-200 text-slate-600'"
          >
            手动录入
          </button>
          <button
            @click="importMethod = 'file'"
            class="flex-1 py-3 px-4 rounded-lg border-2 font-medium transition-all"
            :class="importMethod === 'file' ? 'border-indigo-600 text-indigo-600 bg-indigo-50' : 'border-slate-200 text-slate-600'"
          >
            文件导入
          </button>
        </div>

        <div v-if="importMethod === 'manual'" class="space-y-4">
          <div v-for="(asset, index) in manualAssets" :key="index" class="p-4 bg-slate-50 rounded-lg">
            <div class="grid grid-cols-5 gap-3">
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">代码</label>
                <input
                  v-model="asset.code"
                  type="text"
                  placeholder="如: 000001"
                  class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">名称</label>
                <input
                  v-model="asset.name"
                  type="text"
                  placeholder="如: 平安银行"
                  class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">类型</label>
                <select
                  v-model="asset.type"
                  class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="stock">股票</option>
                  <option value="fund">基金</option>
                  <option value="bond">债券</option>
                  <option value="other">其他</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">数量</label>
                <input
                  v-model.number="asset.quantity"
                  type="number"
                  placeholder="0"
                  class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 mb-1">成本价</label>
                <div class="flex gap-2">
                  <input
                    v-model.number="asset.costPrice"
                    type="number"
                    placeholder="0.00"
                    class="w-full min-w-[120px] px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  <button
                    v-if="manualAssets.length > 1"
                    @click="removeAsset(index)"
                    class="px-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0"
                  >
                    删除
                  </button>
                </div>
              </div>
            </div>
          </div>
          <button
            @click="addAsset"
            class="w-full py-3 border-2 border-dashed border-slate-300 rounded-lg text-slate-600 hover:border-indigo-500 hover:text-indigo-600 transition-colors"
          >
            + 添加资产
          </button>
        </div>

        <div v-else class="text-center py-12">
          <div class="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <UploadIcon class="w-8 h-8 text-slate-400" />
          </div>
          <p class="text-slate-500 mb-4">支持 Excel、CSV 格式文件</p>

          <!-- 隐藏的文件输入 -->
          <input
            ref="fileInput"
            type="file"
            accept=".csv,.xlsx,.xls"
            class="hidden"
            @change="handleFileChange"
          />

          <!-- 已选择文件显示 -->
          <div v-if="selectedFile" class="mb-4 p-3 bg-slate-100 rounded-lg">
            <div class="flex items-center justify-center gap-2 flex-wrap">
              <p class="text-sm text-slate-600">
                已选择: <span class="font-medium text-slate-900">{{ selectedFile.name }}</span>
              </p>
              <button
                type="button"
                class="inline-flex items-center justify-center p-1 rounded-md text-slate-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                title="清除已选文件"
                aria-label="清除已选文件"
                @click="clearSelectedFile"
              >
                <CloseIcon class="w-4 h-4" />
              </button>
              <button
                type="button"
                class="text-sm text-indigo-600 hover:text-indigo-800 hover:underline"
                @click="clearSelectedFile"
              >
                重新选择
              </button>
            </div>
            <p class="text-xs text-slate-500 mt-1">{{ (selectedFile.size / 1024).toFixed(2) }} KB</p>
          </div>

          <div class="flex flex-col sm:flex-row gap-3 justify-center items-center">
            <button
              @click="triggerFileSelect"
              class="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              选择文件
            </button>
            <button
              @click="downloadTemplate"
              class="px-6 py-3 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 hover:border-slate-400 transition-colors flex items-center gap-2"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              下载 Excel 模板
            </button>
          </div>
        </div>

        <div class="mt-6 p-4 bg-amber-50 rounded-lg flex items-start gap-3">
          <LockIcon class="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div class="text-sm text-amber-800">
            <p class="font-medium mb-1">数据安全承诺</p>
            <p>您的持仓数据将使用 AES-256 加密存储在本地，不会上传至云端。首次导入需确认数据安全承诺书。</p>
          </div>
        </div>

        <button
          @click="handleImport"
          class="w-full mt-6 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2"
        >
          开始诊断
          <ArrowRightIcon class="w-4 h-4" />
        </button>
      </div>
    </main>

    <div
      v-if="showSecurityModal"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showSecurityModal = false"
    >
      <div class="bg-white rounded-xl p-6 w-full max-w-lg mx-4">
        <h3 class="text-lg font-semibold text-slate-900 mb-4">数据安全承诺书</h3>
        <div class="space-y-3 text-sm text-slate-600 mb-6">
          <p>1. 您的持仓数据将使用 AES-256 加密算法进行本地加密存储</p>
          <p>2. 所有敏感数据不会上传至任何云端服务器</p>
          <p>3. 数据仅在您的设备本地处理，不会对外共享</p>
          <p>4. 您可以随时删除本地存储的所有数据</p>
          <p>5. 我们承诺保护您的数据隐私安全</p>
        </div>
        <div class="flex items-center gap-2 mb-6">
          <input
            v-model="agreedToSecurity"
            type="checkbox"
            id="security-agree"
            class="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
          />
          <label for="security-agree" class="text-sm text-slate-700">我已阅读并同意数据安全承诺书</label>
        </div>
        <div class="flex gap-3">
          <button
            @click="showSecurityModal = false"
            class="flex-1 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
          >
            取消
          </button>
          <button
            @click="confirmSecurity"
            :disabled="!agreedToSecurity"
            class="flex-1 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            确认
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="showClearConfirm"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="showClearConfirm = false"
    >
      <div class="bg-white rounded-xl p-6 w-full max-w-md mx-4">
        <h3 class="text-lg font-semibold text-slate-900 mb-2">确认清空本地数据？</h3>
        <p class="text-sm text-slate-600 mb-6">
          将删除本设备上 AES-256 加密存储的全部持仓与诊断缓存，此操作不可恢复。
        </p>
        <div class="flex gap-3">
          <button
            type="button"
            class="flex-1 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors"
            @click="showClearConfirm = false"
          >
            取消
          </button>
          <button
            type="button"
            class="flex-1 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            @click="handleClearData"
          >
            确认清空
          </button>
        </div>
      </div>
    </div>

    <!-- 浮动消息提示（Teleport 至 body，不影响页面布局） -->
    <Teleport to="body">
      <div
        v-show="toast.visible"
        class="fixed top-4 right-4 z-[9999] max-w-sm pointer-events-none"
      >
        <div
          class="flex items-start gap-3 px-4 py-3 rounded-lg shadow-lg text-white pointer-events-auto transition-opacity duration-300 ease-in-out"
          :class="[
            toast.type === 'success' ? 'bg-emerald-600' : 'bg-red-600',
            toast.fading ? 'opacity-0' : 'opacity-100',
          ]"
          role="alert"
        >
          <p class="text-sm flex-1 leading-relaxed">{{ toast.message }}</p>
          <button
            type="button"
            class="flex-shrink-0 p-0.5 rounded hover:bg-white/20 transition-colors"
            aria-label="关闭提示"
            @click="hideToast"
          >
            <CloseIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>
