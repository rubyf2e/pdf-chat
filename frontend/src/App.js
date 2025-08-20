import React, { useEffect } from "react";
import ChatRoom from "./components/ChatRoom";
import { getApiBaseUrl } from "./utils/constants";
import "./scss/style.scss";

function App() {
  useEffect(() => {
    document.title =
      process.env.REACT_APP_TITLE || "AI PDF 小幫手 - 智能PDF分析助手";
    
    // 頁面載入時自動清除所有文件
    clearAllFiles();
  }, []);

  const clearAllFiles = async () => {
    try {
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/clear`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ 頁面載入時清除文件成功:', result.message);
      } else {
        console.warn('⚠️ 清除文件請求失敗:', response.status);
      }
    } catch (error) {
      console.error('❌ 清除文件時發生錯誤:', error);
    }
  };

  return (
    <div>
      {/* 聊天室組件 */}
      <ChatRoom />
    </div>
  );
}

export default App;
