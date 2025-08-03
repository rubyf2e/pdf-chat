import React, { useState, useRef, useEffect } from "react";
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
                </div></div>請選擇您想使用的 AI 模型，然後開始討論您的PDF吧！`,
      sender: "assistant",
      timestamp: new Date(),
    },
  ]);

  const [newMessage, setNewMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gemini");
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
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

  const handleSendMessage = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!newMessage.trim()) return;

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

    try {
      // 調用後端 API
      const apiBaseUrl =
        process.env.REACT_APP_API_BASE_URL || "http://localhost:5001";
      const response = await fetch(`${apiBaseUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: currentMessage,
          model: selectedModel,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      const aiMessage = {
        id: Date.now() + 1,
        text: data.response || "抱歉，我無法處理您的請求。",
        sender: "assistant",
        timestamp: new Date(),
        model: selectedModel,
        sources: data.sources || [], // 添加來源資訊
      };

      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    } catch (error) {
      console.error("發送訊息錯誤:", error);

      // 顯示錯誤訊息
      const errorMessage = {
        id: Date.now() + 1,
        text: `抱歉，發生了錯誤：${error.message}。請檢查網路連線或稍後再試。`,
        sender: "assistant",
        timestamp: new Date(),
        model: selectedModel,
        isError: true,
      };

      setMessages((prev) => [...prev, errorMessage]);
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

    // 添加清空資料的提示消息
    const clearingMessage = {
      id: Date.now(),
      text: `🗑️ 正在清空舊資料並上傳新文件 "${file.name}"...\n\n⏳ 這個過程可能需要幾秒鐘，請稍候...`,
      sender: "assistant",
      timestamp: new Date(),
      model: "system",
    };
    setMessages((prev) => [...prev, clearingMessage]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const apiBaseUrl =
        process.env.REACT_APP_API_BASE_URL || "http://localhost:5001";
      const response = await fetch(`${apiBaseUrl}/api/upload`, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const successMessage = {
          id: Date.now() + 1,
          text: `✅ 已清空舊資料並成功上傳 "${file.name}"！現在您可以開始與AI討論這個新PDF的內容了。`,
          sender: "assistant",
          timestamp: new Date(),
          model: "system",
        };
        setMessages((prev) => [...prev, successMessage]);
      } else {
        const errorData = await response.json();
        const errorMessage = {
          id: Date.now() + 1,
          text: `❌ 文件上傳失敗：${errorData.error}`,
          sender: "assistant",
          timestamp: new Date(),
          model: "system",
          isError: true,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error("上傳錯誤:", error);
      const errorMessage = {
        id: Date.now() + 1,
        text: `❌ 上傳失敗，請重試`,
        sender: "assistant",
        timestamp: new Date(),
        model: "system",
        isError: true,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsUploading(false);
    }
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
      const apiBaseUrl =
        process.env.REACT_APP_API_BASE_URL || "http://localhost:5001";
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

          {/* 清理資料按鈕 */}
          <button
            className="clear-data-button"
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
        </div>

        {/* 聊天區域 */}
        <div className="chat-room-content">
          {/* 消息列表 */}
          <div className="chat-room-messages">
            {messages.map((message) => (
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
                placeholder={`使用 ${
                  getCurrentModel().name
                } 與 AI 討論您的PDF...`}
                rows="1"
                className="message-input"
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
              <button
                type="submit"
                disabled={!newMessage.trim()}
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
