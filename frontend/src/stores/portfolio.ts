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

export interface RefreshQuotesResult {
  ok: boolean;
  assets?: BackendQuoteRow[];
  updateTime?: string;
}

export interface BackendQuoteRow {
  code: string;
  current_price?: number | null;
  market_value?: number | null;
  trade_date?: string;
  data_source?: string;
}

const STORAGE_KEY = 'portfolio';

const emptyPortfolio = (): Portfolio => ({
  assets: [],
  totalValue: 0,
  totalCost: 0,
  totalReturn: 0,
  totalReturnRate: 0,
});

const normalizeAssetCode = (code: string) => code.replace(/\.(SH|SZ|BJ)$/i, '').toUpperCase();

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

    if (!saved.startsWith('enc:v1:')) {
      localStorage.setItem(STORAGE_KEY, encryptPortfolio(parsed));
    }
  };

  const syncQuotesFromBackend = (rows: BackendQuoteRow[]) => {
    if (!rows.length || !portfolio.value.assets.length) return;

    const quoteMap = new Map<string, BackendQuoteRow>();
    rows.forEach((row) => {
      quoteMap.set(row.code, row);
      quoteMap.set(normalizeAssetCode(row.code), row);
    });

    let updated = false;
    const assets = portfolio.value.assets.map((asset) => {
      const quote = quoteMap.get(asset.code) ?? quoteMap.get(normalizeAssetCode(asset.code));
      const currentPrice = quote?.current_price;
      if (!quote || currentPrice == null || currentPrice <= 0) return asset;
      updated = true;
      const marketValue = quote.market_value ?? asset.quantity * currentPrice;
      return {
        ...asset,
        currentPrice,
        marketValue,
      };
    });

    if (!updated) return;

    const totalValue = assets.reduce((sum, asset) => sum + (asset.marketValue || 0), 0);
    const totalCost = assets.reduce(
      (sum, asset) => sum + (asset.costPrice || 0) * (asset.quantity || 0),
      0,
    );

    setPortfolio({
      ...portfolio.value,
      assets,
      totalValue,
      totalCost,
      totalReturn: totalValue - totalCost,
      totalReturnRate: totalCost > 0 ? ((totalValue - totalCost) / totalCost) * 100 : 0,
    });
  };

  const refreshLiveQuotes = async (): Promise<RefreshQuotesResult> => {
    const assets = portfolio.value.assets;
    if (!assets.length) return { ok: false };

    try {
      const response = await fetch('/api/portfolio/refresh-quotes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          assets: assets.map((asset) => ({
            code: asset.code,
            name: asset.name,
            quantity: asset.quantity,
            cost_price: asset.costPrice,
            asset_type: asset.type,
          })),
        }),
      });

      if (!response.ok) {
        console.warn('[PortfolioStore] 刷新现价失败', response.status);
        return { ok: false };
      }

      const data = await response.json() as { assets?: BackendQuoteRow[]; update_time?: string };
      if (Array.isArray(data.assets)) {
        syncQuotesFromBackend(data.assets);
        console.table(
          data.assets.map((row) => ({
            代码: row.code,
            current_price: row.current_price,
            trade_date: row.trade_date,
            source: row.data_source,
          })),
        );
        return { ok: true, assets: data.assets, updateTime: data.update_time };
      }
      return { ok: false };
    } catch (error) {
      console.warn('[PortfolioStore] 刷新现价异常', error);
      return { ok: false };
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
    syncQuotesFromBackend,
    refreshLiveQuotes,
    clearPortfolio,
  };
});
