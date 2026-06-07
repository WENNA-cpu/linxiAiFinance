import CryptoJS from 'crypto-js';
import type { Portfolio } from '@/stores/portfolio';

const ENCRYPTED_PREFIX = 'enc:v1:';

/** 设备本地派生密钥（AES-256），仅用于本地存储加密 */
const ENCRYPTION_KEY = CryptoJS.SHA256('lingxi-ai-finance-portfolio-v1').toString();

export function encryptPortfolio(data: Portfolio): string {
  const json = JSON.stringify(data);
  const ciphertext = CryptoJS.AES.encrypt(json, ENCRYPTION_KEY).toString();
  return `${ENCRYPTED_PREFIX}${ciphertext}`;
}

export function decryptPortfolio(raw: string): Portfolio | null {
  try {
    if (raw.startsWith(ENCRYPTED_PREFIX)) {
      const ciphertext = raw.slice(ENCRYPTED_PREFIX.length);
      const bytes = CryptoJS.AES.decrypt(ciphertext, ENCRYPTION_KEY);
      const json = bytes.toString(CryptoJS.enc.Utf8);
      if (!json) return null;
      return JSON.parse(json) as Portfolio;
    }
    // 兼容旧版明文 JSON，读取后由 store 重新加密写入
    return JSON.parse(raw) as Portfolio;
  } catch {
    return null;
  }
}

export function isEncryptedPortfolio(raw: string): boolean {
  return raw.startsWith(ENCRYPTED_PREFIX);
}
