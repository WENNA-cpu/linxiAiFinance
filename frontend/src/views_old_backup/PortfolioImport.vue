<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { usePortfolioStore } from '@/stores/portfolio';
import RiskBanner from '@/components/RiskBanner.vue';
import UploadIcon from '@/components/icons/UploadIcon.vue';
import LockIcon from '@/components/icons/LockIcon.vue';
import CheckCircleIcon from '@/components/icons/CheckCircleIcon.vue';
import ArrowRightIcon from '@/components/icons/ArrowRightIcon.vue';
import HomeIcon from '@/components/icons/HomeIcon.vue';

const router = useRouter();
const portfolioStore = usePortfolioStore();

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

    portfolioStore.setPortfolio(portfolio);
  router.push('/portfolio/diagnosis');
};

const confirmSecurity = () => {
  if (agreedToSecurity.value) {
    showSecurityModal.value = false;
    submitPortfolio();
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
                    class="flex-1 px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                  <button
                    v-if="manualAssets.length > 1"
                    @click="removeAsset(index)"
                    class="px-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
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
          <button class="px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
            选择文件
          </button>
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
