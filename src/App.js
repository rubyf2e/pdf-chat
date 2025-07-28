import React, { useEffect } from "react";
import ChatRoom from "./components/ChatRoom";
import "./scss/style.scss";

function App() {
  useEffect(() => {
    document.title =
      process.env.REACT_APP_TITLE || "AI PDF 小幫手 - 智能PDF分析助手";
  }, []);

  return (
    <div>
      {/* 聊天室組件 */}
      <ChatRoom />
    </div>
  );
}

export default App;
