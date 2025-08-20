// 全域常數定義

export const DEFAULT_STORAGE_KEY = "pdfAnalysis";

// 應用程式配置
export const APP_CONFIG = {
  HEADER_HEIGHT: 72,
  REACT_APP_TITLE:
    process.env.REACT_APP_TITLE || "AI PDF 小幫手 - 智能PDF分析助手",
  PUBLIC_URL: process.env.PUBLIC_URL,
};

// 動態生成 API URL 的工具函數
export const getApiBaseUrl = () => {
  // 如果有設定環境變數，優先使用
  if (process.env.REACT_APP_API_BASE_URL) {
    return process.env.REACT_APP_API_BASE_URL;
  }

  // 根據當前頁面的協議決定 API 協議
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;

  // 開發環境
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return `${protocol}//${hostname}:5009`;
  }

  // 生產環境
  return `${protocol}//${hostname}/pdf-chat`;
};

// 取得當前環境的協議
export const getProtocol = () => {
  return window.location.protocol.replace(":", "");
};

// 檢查是否使用 HTTPS
export const isSecure = () => {
  return window.location.protocol === "https:";
};
