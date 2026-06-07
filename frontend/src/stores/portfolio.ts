import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { decryptPortfolio, encryptPortfolio } from '@/utils/portfolioCrypto';

export interface Asset {
  code: string;
  name: string;
  type: 'stock' | 'fund' | 'bond' | 'other';
  quantity: number;
  costPrice: number;
  currentPrice: number;
  marketValue: number;
}

export interface Portfolio {
  assets: Asset[];
  totalValue: number;
  totalCost: number;
  totalReturn: number;
  totalReturnRate: number;
}

const STORAGE_KEY = 'portfolio';

const emptyPortfolio = (): Portfolio => ({
  assets: [],
  totalValue: 0,
  totalCost: 0,
  totalReturn: 0,
  totalReturnRate: 0,
});

const clearDiagnosisCache = () => {
  const lastId = localStorage.getItem('last_diagnosis_id');
  if (lastId) {
    localStorage.removeItem(`diagnosis_${lastId}`);
  }
  localStorage.removeItem('last_diagnosis_id');

  const keysToRemove: string[] = [];
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (key?.startsWith('diagnosis_')) {
      keysToRemove.push(key);
    }
  }
  keysToRemove.forEach((key) => localStorage.removeItem(key));
};

export const usePortfolioStore = defineStore('portfolio', () => {
  const portfolio = ref<Portfolio>(emptyPortfolio());

  const hasPortfolio = computed(() => portfolio.value.assets.length > 0);

  const setPortfolio = (data: Portfolio) => {
    portfolio.value = data;
    localStorage.setItem(STORAGE_KEY, encryptPortfolio(data));
  };

  const loadPortfolio = () => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) {
      portfolio.value = emptyPortfolio();
      return;
    }

    const parsed = decryptPortfolio(saved);
    if (!parsed || !Array.isArray(parsed.assets)) {
      portfolio.value = emptyPortfolio();
      return;
    }

    portfolio.value = parsed;

    // 旧版明文数据迁移为加密存储
    if (!saved.startsWith('enc:v1:')) {
      localStorage.setItem(STORAGE_KEY, encryptPortfolio(parsed));
    }
  };

  const clearPortfolio = () => {
    portfolio.value = emptyPortfolio();
    localStorage.removeItem(STORAGE_KEY);
    clearDiagnosisCache();
  };

  return {
    portfolio,
    hasPortfolio,
    setPortfolio,
    loadPortfolio,
    clearPortfolio,
  };
});
