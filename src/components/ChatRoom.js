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
                <button class="chat-option">📚 推薦相關PDF</button> 
                </div></div>請選擇您想使用的 AI 模型，然後開始討論您的PDF吧！`,
      sender: "assistant",
      timestamp: new Date(),
    },
  ]);

  const [newMessage, setNewMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [selectedModel, setSelectedModel] = useState("gpt-4");
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const aiModels = [
    {
      id: "gpt-4",
      name: "GPT-4",
      description: "最強大的模型，適合深度PDF分析",
      icon: "🧠",
    },
    {
      id: "gpt-3.5-turbo",
      name: "GPT-3.5 Turbo",
      description: "快速回應，適合一般PDF討論",
      icon: "⚡",
    },
    {
      id: "claude-3",
      name: "Claude 3",
      description: "創意豐富，適合PDF內容創作",
      icon: "🎨",
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
    setNewMessage("");
    setIsTyping(true);

    // 延遲滾動，確保消息已更新
    setTimeout(() => {
      scrollToBottom();
    }, 100);

    // 模擬 AI 回覆（實際應用中這裡會調用 ChatGPT API）
    setTimeout(() => {
      const aiReplies = [
        `我使用 ${selectedModel.toUpperCase()} 模型來分析您的PDF。這個PDF的內容確實很豐富！您想了解更多關於哪個部分的信息嗎？`,
        `根據 ${selectedModel.toUpperCase()} 的分析，這個PDF在結構和內容方面都很出色。您對哪個章節特別感興趣？`,
        `作為您的AI PDF 小幫手，我推薦您也可以看看相關主題的其他PDF。需要我為您推薦一些嗎？`,
        `這個問題很有趣！讓我用 ${selectedModel.toUpperCase()} 的視角來分析一下這個PDF的內容。`,
        `我理解您對這個PDF的疑問。從 ${selectedModel.toUpperCase()} 的角度來看，這個觀點很有見地。`,
        `這個PDF的內容組織確實很棒！您想了解更多關於PDF結構的信息嗎？`,
        `根據 ${selectedModel.toUpperCase()} 的資料庫，這個主題的其他PDF也很值得參考。`,
        `這個PDF的寫作風格很獨特。您想了解如何更好地理解這類PDF嗎？`,
        `從 ${selectedModel.toUpperCase()} 的角度分析，這個PDF的結論確實很有啟發性。`,
        `我推薦您也可以看看這個領域的其他經典PDF。需要我列出一些嗎？`,
      ];

      const randomReply =
        aiReplies[Math.floor(Math.random() * aiReplies.length)];

      const aiMessage = {
        id: Date.now() + 1,
        text: randomReply,
        sender: "assistant",
        timestamp: new Date(),
        model: selectedModel,
      };
      setMessages((prev) => [...prev, aiMessage]);
      setIsTyping(false);
    }, 1000 + Math.random() * 2000);
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
              <p className="chat-room-subtitle">與 AI 討論PDF，獲得專業見解與分析</p>
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
            {messages.map((message) => (
              <div
                key={message.id}
                className={`chat-message ${message.sender}-message`}
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
              <textarea
                ref={inputRef}
                value={newMessage}
                onChange={(e) => setNewMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={`使用 ${getCurrentModel().name} 與 AI 討論您的PDF...`}
                rows="1"
                className="message-input"
              />
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
