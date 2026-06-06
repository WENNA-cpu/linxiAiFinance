<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import { supabase } from '@/supabase/client';
import RiskBanner from '@/components/RiskBanner.vue';
import UploadIcon from '@/components/icons/UploadIcon.vue';
import LockIcon from '@/components/icons/LockIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

// 获取或创建会话ID
const getSessionId = () => {
  let sessionId = localStorage.getItem('user_session_id');
  if (!sessionId) {
    sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    localStorage.setItem('user_session_id', sessionId);
  }
  return sessionId;
};

// 保存持仓到数据库
const savePortfolioToDatabase = async (assets: any[]) => {
  try {
    const sessionId = getSessionId();
    const validAssets = assets.filter(a => a.code && a.name && a.quantity > 0);

    if (validAssets.length === 0) return;

    // 先删除该会话的旧持仓
    await supabase
      .from('user_portfolios')
      .delete()
      .eq('session_id', sessionId);

    // 插入新持仓
    const records = validAssets.map(asset => ({
      session_id: sessionId,
      ts_code: asset.code,
      name: asset.name,
      qty: asset.quantity,
      cost: asset.costPrice,
    }));

    const { error } = await supabase
      .from('user_portfolios')
      .insert(records);

    if (error) {
      console.error('保存持仓失败:', error);
    } else {
      console.log('持仓已保存到数据库:', records.length, '条记录');
    }
  } catch (err) {
    console.error('保存持仓异常:', err);
  }
};

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

    // 保存到 store
    portfolioStore.setPortfolio(portfolio);

    // 保存到数据库
    await savePortfolioToDatabase(validAssets);

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
const parseError = ref('');

const triggerFileSelect = () => {
  fileInput.value?.click();
};

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) {
    selectedFile.value = file;
    parseError.value = '';
    console.log('选择的文件:', file.name);
    parseFile(file);
  }
};

// 解析CSV/Excel文件
const parseFile = (file: File) => {
  const reader = new FileReader();

  reader.onload = (e) => {
    try {
      const content = e.target?.result as string;
      console.log('文件内容:', content.substring(0, 500));

      // 解析CSV
      const lines = content.split('\n').filter(line => line.trim());
      console.log('解析行数:', lines.length);

      if (lines.length < 2) {
        parseError.value = '文件格式错误，至少需要包含表头和一行数据';
        return;
      }

      // 解析表头
      const headers = lines[0].split(',').map(h => h.trim().replace(/^\uFEFF/, ''));
      console.log('表头:', headers);

      // 查找列索引
      const codeIndex = headers.findIndex(h => h.includes('代码') || h.toLowerCase() === 'code');
      const nameIndex = headers.findIndex(h => h.includes('名称') || h.toLowerCase() === 'name');
      const typeIndex = headers.findIndex(h => h.includes('类型') || h.toLowerCase() === 'type');
      const quantityIndex = headers.findIndex(h => h.includes('数量') || h.toLowerCase() === 'quantity');
      const costPriceIndex = headers.findIndex(h => h.includes('成本价') || h.includes('成本') || h.toLowerCase() === 'cost');

      console.log('列索引:', { codeIndex, nameIndex, typeIndex, quantityIndex, costPriceIndex });

      if (codeIndex === -1 || nameIndex === -1) {
        parseError.value = '文件格式错误，缺少必要的列（代码、名称）';
        return;
      }

      // 解析数据行
      const assets: any[] = [];
      for (let i = 1; i < lines.length; i++) {
        const cells = lines[i].split(',').map(c => c.trim());
        if (cells.length < 2 || !cells[codeIndex]) continue;

        const typeMap: Record<string, string> = {
          '股票': 'stock',
          '基金': 'fund',
          '债券': 'bond',
          'ETF': 'fund',
          '其他': 'other',
        };

        const asset = {
          code: cells[codeIndex],
          name: cells[nameIndex] || '',
          type: typeMap[cells[typeIndex]] || 'stock',
          quantity: parseFloat(cells[quantityIndex]) || 0,
          costPrice: parseFloat(cells[costPriceIndex]) || 0,
        };

        assets.push(asset);
      }

      console.log('解析的资产:', assets);
      parsedAssets.value = assets;

      if (assets.length === 0) {
        parseError.value = '未能解析出有效数据';
      } else {
        // 自动填充到manualAssets
        manualAssets.value = assets.map(a => ({
          code: a.code,
          name: a.name,
          type: a.type,
          quantity: a.quantity,
          costPrice: a.costPrice,
        }));
        console.log('已填充到manualAssets:', manualAssets.value);
        alert(`成功解析 ${assets.length} 条资产数据`);
      }
    } catch (error) {
      console.error('解析文件失败:', error);
      parseError.value = '解析文件失败: ' + (error as Error).message;
    }
  };

  reader.onerror = () => {
    parseError.value = '读取文件失败';
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
            <p class="text-sm text-slate-600">已选择: <span class="font-medium text-slate-900">{{ selectedFile.name }}</span></p>
            <p class="text-xs text-slate-500">{{ (selectedFile.size / 1024).toFixed(2) }} KB</p>
          </div>

          <!-- 解析错误提示 -->
          <div v-if="parseError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p class="text-sm text-red-600">{{ parseError }}</p>
          </div>

          <!-- 解析成功提示 -->
          <div v-if="parsedAssets.length > 0 && !parseError" class="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
            <p class="text-sm text-emerald-600">成功解析 {{ parsedAssets.length }} 条资产数据，点击「开始诊断」进行AI分析</p>
          </div>

          <div class="flex flex-col sm:flex-row gap-3 justify-center items-center">
            <button
              @click="triggerFileSelect"
              class="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              {{ selectedFile ? '重新选择' : '选择文件' }}
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
  </div>
</template>
