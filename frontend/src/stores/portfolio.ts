import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

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

export const usePortfolioStore = defineStore('portfolio', () => {
  const portfolio = ref<Portfolio>({
    assets: [],
    totalValue: 0,
    totalCost: 0,
    totalReturn: 0,
    totalReturnRate: 0,
  });

  const hasPortfolio = computed(() => portfolio.value.assets.length > 0);

  const setPortfolio = (data: Portfolio) => {
    portfolio.value = data;
    localStorage.setItem('portfolio', JSON.stringify(data));
  };

  const loadPortfolio = () => {
    const saved = localStorage.getItem('portfolio');
    if (saved) {
      portfolio.value = JSON.parse(saved);
    }
  };

  const clearPortfolio = () => {
    portfolio.value = {
      assets: [],
      totalValue: 0,
      totalCost: 0,
      totalReturn: 0,
      totalReturnRate: 0,
    };
    localStorage.removeItem('portfolio');
  };

  return {
    portfolio,
    hasPortfolio,
    setPortfolio,
    loadPortfolio,
    clearPortfolio,
  };
});
