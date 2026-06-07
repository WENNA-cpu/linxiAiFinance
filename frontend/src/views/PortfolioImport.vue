<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
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

const submitPortfolio = () => {
    const validAssets = manualAssets.value.filter(a => a.code && a.name && a.quantity > 0);
    const assets = validAssets.map(a => ({
      code: a.code,
      name: a.name,
      type: a.type as 'stock' | 'fund' | 'bond' | 'other',
      quantity: a.quantity,
      costPrice: a.costPrice,
      currentPrice: a.costPrice * (1 + (Math.random() - 0.3) * 0.2),
      marketValue: a.quantity * a.costPrice * (1 + (Math.random() - 0.3) * 0.2),
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

    router.push('/portfolio/diagnosis');
};

const confirmSecurity = () => {
  if (agreedToSecurity.value) {
    showSecurityModal.value = false;
    submitPortfolio();
  }
};

// 下载Excel模板
const downloadTemplate = () => {
  // 模板数据
  const templateData = [
    ['代码', '名称', '类型', '数量', '成本价'],
    ['000001', '平安银行', '股票', '100', '15.50'],
    ['600519', '贵州茅台', '股票', '10', '1500.00'],
    ['510050', '上证50ETF', 'ETF', '500', '2.80'],
  ];

  // 创建CSV内容
  const csvContent = templateData.map(row => row.join(',')).join('\n');

  // 添加BOM以支持中文
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' });

  // 创建下载链接
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = '持仓导入模板.csv';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
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

// 解析 CSV/Excel 文件
const parseFile = (file: File) => {
  const reader = new FileReader();

  reader.onload = (e) => {
    try {
      const content = e.target?.result as string;

      const lines = content.split('\n').filter(line => line.trim());

      if (lines.length < 2) {
        showParseFailure('文件格式错误，至少需要包含表头和一行数据');
        return;
      }

      const headers = lines[0].split(',').map(h => h.trim().replace(/^\uFEFF/, ''));

      const codeIndex = headers.findIndex(h => h.includes('代码') || h.toLowerCase() === 'code');
      const nameIndex = headers.findIndex(h => h.includes('名称') || h.toLowerCase() === 'name');
      const typeIndex = headers.findIndex(h => h.includes('类型') || h.toLowerCase() === 'type');
      const quantityIndex = headers.findIndex(h => h.includes('数量') || h.toLowerCase() === 'quantity');
      const costPriceIndex = headers.findIndex(h => h.includes('成本价') || h.includes('成本') || h.toLowerCase() === 'cost');

      if (codeIndex === -1 || nameIndex === -1) {
        showParseFailure('文件格式错误，缺少必要的列（代码、名称）');
        return;
      }

      const assets: any[] = [];
      for (let i = 1; i < lines.length; i++) {
        const rowNum = i + 1;
        const cells = lines[i].split(',').map(c => c.trim());
        if (cells.length < 2 || !cells[codeIndex]) continue;

        const quantityStr = quantityIndex >= 0 ? cells[quantityIndex] : '';
        const costStr = costPriceIndex >= 0 ? cells[costPriceIndex] : '';

        if (quantityStr && Number.isNaN(Number(quantityStr))) {
          showParseFailure(`第 ${rowNum} 行数据格式错误`);
          return;
        }
        if (costStr && Number.isNaN(Number(costStr))) {
          showParseFailure(`第 ${rowNum} 行数据格式错误`);
          return;
        }

        const typeMap: Record<string, string> = {
          '股票': 'stock',
          '基金': 'fund',
          '债券': 'bond',
          'ETF': 'fund',
          '其他': 'other',
        };

        assets.push({
          code: cells[codeIndex],
          name: cells[nameIndex] || '',
          type: typeMap[cells[typeIndex]] || 'stock',
          quantity: quantityStr ? parseFloat(quantityStr) : 0,
          costPrice: costStr ? parseFloat(costStr) : 0,
        });
      }

      parsedAssets.value = assets;

      if (assets.length === 0) {
        showParseFailure('未能解析出有效数据');
      } else {
        manualAssets.value = assets.map(a => ({
          code: a.code,
          name: a.name,
          type: a.type,
          quantity: a.quantity,
          costPrice: a.costPrice,
        }));
        showParseSuccess(assets.length);
      }
    } catch (error) {
      showParseFailure('解析文件失败: ' + (error as Error).message);
    }
  };

  reader.onerror = () => {
    showParseFailure('读取文件失败');
  };

  reader.readAsText(file);
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
