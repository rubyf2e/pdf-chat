import React, { useState, useRef, useEffect } from 'react';
import { getApiBaseUrl } from '../utils/constants';
import { SiteIcon } from "./Icons";

const ChatRoom = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: `嗨！我是您的AI PDF 小幫手，我可以幫您：<div class="chat-content"><div class="chat-options">
                <button class="chat-option">📄 分析PDF內容</button>
                <button class="chat-option">🔍 搜尋PDF資訊</button> 
                <button class="chat-option">📝 總結PDF重點</button>
                <button class="chat-option">💡 解答PDF問題</button>
                </div></div>

🚀 <strong>開始使用步驟：</strong>
1️⃣ 選擇您想使用的 AI 模型
2️⃣ 點擊右下角 📎 按鈕上傳您的 PDF 檔案
3️⃣ 等待檔案處理完成
4️⃣ 開始與 AI 討論您的 PDF 內容！

💡 提示：請先上傳 PDF 檔案才能開始聊天對話。`,
      sender: "assistant",
      timestamp: new Date(),
    },
  ]);

  const [newMessage, setNewMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gemini");
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [hasUploadedFile, setHasUploadedFile] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);

  const aiModels = [
    {
      id: "gemini",
      name: "Gemini",
      description: "",
      icon: "✨",
    },
    {
      id: "azure",
      name: "Azure",
      description: "",
      icon: "🧠",
    },
    {
      id: "ollama",
      name: "Ollama",
      description: "",
      icon: "⚡",
    },
  ];

  // 自動滾動到最新消息
  const scrollToBottom = () => {
    const messagesContainer = document.querySelector(".chat-room-messages");
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 組件載入後聚焦輸入框
  useEffect(() => {
    if (inputRef.current) {
      setTimeout(() => {
        inputRef.current.focus();
      }, 500);
    }
  }, []);

  // 組件載入時檢查是否已有上傳的檔案
  useEffect(() => {
    const checkUploadedFiles = async () => {
      try {
        const apiBaseUrl = getApiBaseUrl();
        const response = await fetch(`${apiBaseUrl}/api/status`);
        
        if (response.ok) {
          const statusData = await response.json();
          // 如果有完成處理的檔案且查詢引擎就緒，則設置為已上傳
          if (statusData.completed_files > 0 && statusData.query_engine_ready) {
            setHasUploadedFile(true);
          }
        }
      } catch (error) {
        console.log("檢查上傳檔案狀態失敗:", error);
      }
    };

    checkUploadedFiles();
  }, []);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!newMessage.trim()) return;

    // 檢查是否已上傳檔案
    if (!hasUploadedFile) {
      const errorMessage = {
        id: Date.now(),
        text: `❌ 請先上傳 PDF 檔案再開始聊天\n\n💡 點擊右下角的 📎 按鈕來上傳您的 PDF 檔案`,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    const userMessage = {
      id: Date.now(),
      text: newMessage.trim(),
      sender: "user",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentMessage = newMessage.trim();
    setNewMessage("");
    setIsTyping(true);

    // 延遲滾動，確保消息已更新
    setTimeout(() => {
      scrollToBottom();
    }, 100);

    // 創建一個空的 AI 回應訊息
    const aiMessageId = Date.now() + 1;
    const aiMessage = {
      id: aiMessageId,
      text: "",
      sender: "assistant",
      timestamp: new Date(),
      model: selectedModel,
      sources: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, aiMessage]);

    try {
      // 調用後端 API - 使用流式端點
      const apiBaseUrl = getApiBaseUrl();

      // 設置10分鐘超時控制器
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000); // 10分鐘超時

      // 使用 fetch 處理流式回應
      const response = await fetch(`${apiBaseUrl}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: currentMessage,
          model: selectedModel,
        }),
        signal: controller.signal,
      });

      // 清除超時計時器
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      // 用簡單變數儲存累積的文字和來源
      let currentText = "";
      let currentSources = [];

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const jsonData = JSON.parse(line.slice(6));

              if (jsonData.error) {
                throw new Error(jsonData.error);
              }

              if (jsonData.chunk) {
                currentText += jsonData.chunk;

                // 創建新的文字變數來避免閉包問題
                const newText = currentText;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId ? { ...msg, text: newText } : msg
                  )
                );
              }

              if (jsonData.sources) {
                currentSources = jsonData.sources;
              }

              if (jsonData.status === "complete") {
                // 流式完成，更新最終狀態
                const finalText = currentText;
                const finalSources = currentSources;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === aiMessageId
                      ? {
                          ...msg,
                          text: finalText,
                          sources: finalSources,
                          isStreaming: false,
                        }
                      : msg
                  )
                );
                setIsTyping(false);
                return; // 結束處理
              }

              if (jsonData.status === "error") {
                throw new Error(jsonData.error || "未知錯誤");
              }
            } catch (parseError) {
              console.warn("解析 SSE 數據失敗:", parseError);
            }
          }
        }

        // 即時滾動到底部
        scrollToBottom();
      }

      // 如果流式處理完成但沒有收到 complete 狀態，手動結束
      setIsTyping(false);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? {
                ...msg,
                sources: currentSources,
                isStreaming: false,
              }
            : msg
        )
      );
    } catch (error) {
      console.error("發送訊息錯誤:", error);

      let errorMessage = "抱歉，發生了錯誤。請檢查網路連線或稍後再試。";
      
      if (error.name === 'AbortError') {
        errorMessage = "⏰ 回應時間過長（超過10分鐘），請嘗試使用更簡短的問題或稍後再試。";
      } else if (error.message) {
        errorMessage = `抱歉，發生了錯誤：${error.message}。請檢查網路連線或稍後再試。`;
      }

      // 錯誤處理：將現有的 AI 訊息更新為錯誤狀態，而不是添加新訊息
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === aiMessageId
            ? {
                ...msg,
                text: errorMessage,
                isError: true,
                isStreaming: false,
              }
            : msg
        )
      );

      setIsTyping(false);
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString("zh-TW", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
      // 防止頁面滾動
      e.stopPropagation();
    }
  };

  const getCurrentModel = () => {
    return aiModels.find((model) => model.id === selectedModel);
  };

  const handleFileUpload = async (file) => {
    // 檢查文件類型
    if (!file.type.includes("pdf")) {
      const errorMessage = {
        id: Date.now(),
        text: `❌ 只支援 PDF 文件格式`,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    // 檢查文件大小 (16MB限制)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
      const errorMessage = {
        id: Date.now(),
        text: `❌ 文件大小不能超過 16MB`,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
      return;
    }

    setIsUploading(true);

    // 添加上傳開始的消息
    const uploadingMessageId = Date.now();
    const uploadingMessage = {
      id: uploadingMessageId,
      text: `� 正在上傳文件 "${file.name}"...\n\n⏳ 請稍候，這個過程可能需要一些時間...`,
      sender: "assistant",
      timestamp: new Date(),
      model: "system",
    };
    setMessages((prev) => [...prev, uploadingMessage]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiBaseUrl = getApiBaseUrl();
      
      // 設置10分鐘超時時間
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000); // 10分鐘超時

      const response = await fetch(`${apiBaseUrl}/api/upload`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const responseData = await response.json();
        
        // 更新上傳狀態消息
        const uploadSuccessMessage = {
          id: uploadingMessageId,
          text: `✅ 文件 "${file.name}" 上傳成功！\n\n🔄 正在處理和索引文件內容，請稍候...`,
          sender: "assistant",
          timestamp: new Date(),
          model: "system",
        };
        setMessages((prev) => 
          prev.map(msg => msg.id === uploadingMessageId ? uploadSuccessMessage : msg)
        );

        // 如果是異步處理，開始輪詢狀態
        if (responseData.processing) {
          await pollProcessingStatus(uploadingMessageId, file.name);
        } else {
          // 立即完成
          const finalMessage = {
            id: uploadingMessageId,
            text: `✅ 文件 "${file.name}" 已完成處理！現在您可以開始與AI討論這個PDF的內容了。`,
            sender: "assistant",
            timestamp: new Date(),
            model: "system",
          };
          setMessages((prev) => 
            prev.map(msg => msg.id === uploadingMessageId ? finalMessage : msg)
          );
          // 設置檔案已上傳標記
          setHasUploadedFile(true);
        }
      } else {
        const errorData = await response.json();
        const errorMessage = {
          id: uploadingMessageId,
          text: `❌ 文件上傳失敗：${errorData.error}`,
          sender: "assistant",
          timestamp: new Date(),
          model: "system",
          isError: true,
        };
        setMessages((prev) => 
          prev.map(msg => msg.id === uploadingMessageId ? errorMessage : msg)
        );
      }
    } catch (error) {
      console.error("上傳錯誤:", error);
      let errorText = "❌ 上傳失敗，請重試";
      
      if (error.name === 'AbortError') {
        errorText = "❌ 上傳超時，請檢查文件大小並重試";
      } else if (error.message) {
        errorText = `❌ 上傳失敗：${error.message}`;
      }

      const errorMessage = {
        id: uploadingMessageId,
        text: errorText,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => 
        prev.map(msg => msg.id === uploadingMessageId ? errorMessage : msg)
      );
    } finally {
      setIsUploading(false);
    }
  };

  // 輪詢處理狀態的函數
  const pollProcessingStatus = async (messageId, fileName) => {
    const apiBaseUrl = getApiBaseUrl();
    const maxAttempts = 120; // 增加到 120 次（10分鐘）
    let attempts = 0;

    const poll = async () => {
      try {
        attempts++;
        const response = await fetch(`${apiBaseUrl}/api/status`);
        
        if (response.ok) {
          const statusData = await response.json();
          const currentFile = statusData.files_detail.find(f => f.filename === fileName);
          
          if (currentFile) {
            if (currentFile.status === 'error') {
              // 文件處理錯誤
              const errorMessage = {
                id: messageId,
                text: `❌ 文件 "${fileName}" 處理失敗：${currentFile.error || '未知錯誤'}`,
                sender: "assistant",
                timestamp: new Date(),
                model: "system",
                isError: true,
              };
              setMessages((prev) => 
                prev.map(msg => msg.id === messageId ? errorMessage : msg)
              );
              return;
            }
            
            if (currentFile.status === 'completed' && statusData.query_engine_ready) {
              // 處理完成
              const successMessage = {
                id: messageId,
                text: `✅ 文件 "${fileName}" 已完成處理！現在您可以開始與AI討論這個PDF的內容了。`,
                sender: "assistant",
                timestamp: new Date(),
                model: "system",
              };
              setMessages((prev) => 
                prev.map(msg => msg.id === messageId ? successMessage : msg)
              );
              // 設置檔案已上傳標記
              setHasUploadedFile(true);
              return;
            }
            
            if (currentFile.status === 'processing') {
              // 更新處理進度消息
              const processingTime = Math.floor((Date.now() / 1000 - currentFile.upload_time) / 60);
              const progressMessage = {
                id: messageId,
                text: `🔄 文件 "${fileName}" 正在處理中...\n\n⏱️ 已處理時間：${processingTime} 分鐘\n📊 處理狀態：${statusData.status}\n📝 總文件數：${statusData.total_files}\n✅ 已完成：${statusData.completed_files}\n⚠️ 錯誤：${statusData.error_files}`,
                sender: "assistant",
                timestamp: new Date(),
                model: "system",
              };
              setMessages((prev) => 
                prev.map(msg => msg.id === messageId ? progressMessage : msg)
              );
            }
          }
          
          if (attempts < maxAttempts) {
            // 繼續輪詢，處理時間較長時增加間隔
            const pollInterval = attempts > 60 ? 10000 : 5000; // 5分鐘後改為每10秒檢查一次
            setTimeout(poll, pollInterval);
          } else {
            // 超時，但提供更詳細的狀態資訊
            const timeoutMessage = {
              id: messageId,
              text: `⚠️ 文件 "${fileName}" 處理時間較長（超過 10 分鐘）\n\n📊 當前狀態：${statusData.status}\n📝 處理進度：${statusData.completed_files}/${statusData.total_files}\n\n您可以：\n• 繼續等待處理完成\n• 重新上傳文件\n• 聯繫技術支援`,
              sender: "assistant",
              timestamp: new Date(),
              model: "system",
              isError: true,
            };
            setMessages((prev) => 
              prev.map(msg => msg.id === messageId ? timeoutMessage : msg)
            );
          }
        } else {
          console.error("狀態檢查失敗:", response.status);
          if (attempts < maxAttempts) {
            setTimeout(poll, 5000);
          }
        }
      } catch (error) {
        console.error("輪詢狀態錯誤:", error);
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          // 網路錯誤的處理
          const networkErrorMessage = {
            id: messageId,
            text: `❌ 無法檢查文件 "${fileName}" 的處理狀態\n\n網路連線錯誤，請檢查網路連線後重試。`,
            sender: "assistant",
            timestamp: new Date(),
            model: "system",
            isError: true,
          };
          setMessages((prev) => 
            prev.map(msg => msg.id === messageId ? networkErrorMessage : msg)
          );
        }
      }
    };

    // 開始輪詢
    setTimeout(poll, 3000); // 3秒後開始第一次檢查
  };

  const handleUploadButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
      // 清空文件輸入
      e.target.value = "";
    }
  };

  const handleClearData = async () => {
    if (
      !window.confirm("確定要清空所有上傳的文件和資料集嗎？此操作無法復原。")
    ) {
      return;
    }

    try {
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/clear`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      const data = await response.json();

      if (response.ok) {
        const successMessage = {
          id: Date.now(),
          text: `🗑️ ${data.message}`,
          sender: "assistant",
          timestamp: new Date(),
          model: "system",
        };
        setMessages((prev) => [...prev, successMessage]);
        // 重置檔案上傳狀態
        setHasUploadedFile(false);
      } else {
        throw new Error(data.error || "清空資料失敗");
      }
    } catch (error) {
      console.error("清空資料錯誤:", error);
      const errorMessage = {
        id: Date.now(),
        text: `❌ 清空資料失敗：${error.message}`,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleCheckStatus = async () => {
    try {
      const apiBaseUrl = getApiBaseUrl();
      const response = await fetch(`${apiBaseUrl}/api/status`);

      if (response.ok) {
        const statusData = await response.json();
        
        let statusText = `📊 系統狀態檢查結果\n\n`;
        statusText += `🔧 服務狀態：${statusData.status}\n`;
        statusText += `🤖 查詢引擎：${statusData.query_engine_ready ? '已就緒' : '未就緒'}\n`;
        statusText += `📝 總文件數：${statusData.total_files}\n`;
        statusText += `✅ 已完成：${statusData.completed_files}\n`;
        statusText += `🔄 處理中：${statusData.processing_files}\n`;
        statusText += `❌ 錯誤：${statusData.error_files}\n\n`;
        
        if (statusData.files_detail && statusData.files_detail.length > 0) {
          statusText += `📄 文件詳情：\n`;
          statusData.files_detail.forEach((file, index) => {
            const processingTime = Math.floor((Date.now() / 1000 - file.upload_time) / 60);
            statusText += `${index + 1}. ${file.filename}\n`;
            statusText += `   狀態：${file.status}\n`;
            statusText += `   處理時間：${processingTime} 分鐘\n`;
            if (file.error) {
              statusText += `   錯誤：${file.error}\n`;
            }
            statusText += `\n`;
          });
        } else {
          statusText += `📄 目前沒有上傳的文件\n`;
        }

        const statusMessage = {
          id: Date.now(),
          text: statusText,
          sender: "assistant",
          timestamp: new Date(),
          model: "system",
        };
        setMessages((prev) => [...prev, statusMessage]);
      } else {
        throw new Error(`狀態檢查失敗: ${response.status}`);
      }
    } catch (error) {
      console.error("狀態檢查錯誤:", error);
      const errorMessage = {
        id: Date.now(),
        text: `❌ 狀態檢查失敗：${error.message}`,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <section id="chat" className="chat-room-section">
      <div className="chat-room-container">
        {/* 聊天室標題 */}
        <div className="chat-room-header">
          <div className="header-content">
            <div className="header-title">
              <h2>
                <span className="chat-logo-icon">
                  <SiteIcon />
                </span>
                AI PDF 小幫手
              </h2>
              <p className="chat-room-subtitle">
                與 AI 討論PDF，獲得專業見解與分析
              </p>
            </div>
          </div>

          {/* 模型選擇器 */}
          <div className="model-selector">
            <button
              className="model-toggle"
              onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
            >
              <span className="model-icon">{getCurrentModel().icon}</span>
              <span className="model-name">{getCurrentModel().name}</span>
              <svg
                className={`dropdown-arrow ${isModelMenuOpen ? "open" : ""}`}
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polyline points="6,9 12,15 18,9"></polyline>
              </svg>
            </button>

            {isModelMenuOpen && (
              <div className="model-menu">
                {aiModels.map((model) => (
                  <button
                    key={model.id}
                    className={`model-option ${
                      selectedModel === model.id ? "active" : ""
                    }`}
                    onClick={() => {
                      setSelectedModel(model.id);
                      setIsModelMenuOpen(false);
                    }}
                  >
                    <span className="model-icon">{model.icon}</span>
                    <div className="model-info">
                      <span className="model-name">{model.name}</span>
                      <span className="model-description">
                        {model.description}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 聊天區域 */}
        <div className="chat-room-content">
          {/* 消息列表 */}
          <div className="chat-room-messages">
            {messages
              .filter((message) => {
                // 顯示所有用戶訊息
                if (message.sender === "user") return true;
                
                // 對於 AI 訊息，只顯示有文字內容的或錯誤訊息
                if (message.sender === "assistant") {
                  return message.text.trim() !== "" || message.isError;
                }
                
                return true;
              })
              .map((message) => (
              <div
                key={message.id}
                className={`chat-message ${message.sender}-message ${
                  message.isError ? "error-message" : ""
                }`}
              >
                <div className="message-content">
                  <div className="message-header">
                    {message.sender === "assistant" && (
                      <div className="ai-info">
                        <span className="ai-icon">
                          <SiteIcon />
                        </span>
                        <span className="ai-name">AI PDF 小幫手</span>
                        {message.model && (
                          <span className="model-badge">
                            {message.model.toUpperCase()}
                          </span>
                        )}
                      </div>
                    )}
                    {message.sender === "user" && (
                      <div className="user-info">
                        <span className="user-icon">👤</span>
                        <span className="user-name">您</span>
                      </div>
                    )}
                  </div>
                  <div
                    className="message-text"
                    dangerouslySetInnerHTML={{ __html: message.text }}
                  />

                  {/* 顯示來源資訊 */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="message-sources">
                      <div className="sources-header">📖 參考來源：</div>
                      <div className="sources-list">
                        {message.sources.slice(0, 3).map((source, index) => (
                          <div key={index} className="source-item">
                            <span className="source-number">{index + 1}.</span>
                            <span className="source-info">
                              {source.file_name} - 第 {source.page} 頁
                            </span>
                            <span className="source-score">
                              (相關度: {(source.score || 0).toFixed(2)})
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="message-time">
                    {formatTime(message.timestamp)}
                  </div>
                </div>
              </div>
            ))}

            {/* 輸入中指示器 */}
            {isTyping && (
              <div className="chat-message assistant-message">
                <div className="message-content">
                  <div className="typing-indicator">
                    <div className="ai-info">
                      <span className="ai-icon">
                        <SiteIcon />
                      </span>
                      <span className="ai-name">AI PDF 小幫手</span>
                      <span className="model-badge">
                        {selectedModel.toUpperCase()}
                      </span>
                    </div>
                    <div className="typing-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* 輸入區域 */}
          <form className="chat-room-input" onSubmit={handleSendMessage}>
            <div className="input-container">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
              <textarea
                ref={inputRef}
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={hasUploadedFile 
                  ? `使用 ${getCurrentModel().name} 與 AI 討論您的PDF...`
                  : "請先上傳 PDF 檔案，然後開始聊天..."
                }
                rows="1"
                className="message-input"
                disabled={!hasUploadedFile}
              />
              <button
                type="button"
                onClick={handleUploadButtonClick}
                className="upload-button"
                disabled={isUploading}
                title="上傳PDF文件"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.64 16.2a2 2 0 0 1-2.83-2.83l8.49-8.49" />
                </svg>
              </button>

              {/* 狀態檢查按鈕 */}
              <button
                className="status-check-button input-control-button"
                onClick={handleCheckStatus}
                title="檢查處理狀態"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"></path>
                </svg>
              </button>

              {/* 清理資料按鈕 */}
              <button
                className="clear-data-button input-control-button"
                onClick={handleClearData}
                title="清空所有資料"
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="3,6 5,6 21,6"></polyline>
                  <path d="M19,6l-2,14H7L5,6"></path>
                  <path d="M10,11v6"></path>
                  <path d="M14,11v6"></path>
                  <path d="M9,6V4a1,1 0 0,1 1,-1h4a1,1 0 0,1 1,1V6"></path>
                </svg>
              </button>

              <button
                type="submit"
                disabled={!newMessage.trim() || !hasUploadedFile}
                className="send-button"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22,2 15,22 11,13 2,9 22,2"></polygon>
                </svg>
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
};

export default ChatRoom;
