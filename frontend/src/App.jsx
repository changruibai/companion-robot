import { useState, useEffect } from 'react'
import ChatInterface from './components/ChatInterface'
import Header from './components/Header'
import DebugConsole from './components/DebugConsole'

function App() {
  const [tab, setTab] = useState('chat')

  // 初始化主题（跟随系统）
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme')
    const savedIsSystem = localStorage.getItem('isSystemTheme') !== 'false'
    
    if (savedTheme && !savedIsSystem) {
      document.documentElement.setAttribute('data-theme', savedTheme)
    } else {
      // 默认跟随系统
      const systemTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      document.documentElement.setAttribute('data-theme', systemTheme)
    }
  }, [])

  return (
    <div className="min-h-screen bg-base-100">
      <Header />
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="mb-6 flex gap-2">
          <button
            onClick={() => setTab('chat')}
            className={`btn ${tab === 'chat' ? 'btn-primary' : 'btn-ghost'}`}
          >
            线上聊天
          </button>
          <button
            onClick={() => setTab('debug')}
            className={`btn ${tab === 'debug' ? 'btn-primary' : 'btn-ghost'}`}
          >
            多用户/多狗/多对话调试
          </button>
        </div>

        {tab === 'chat' ? <ChatInterface /> : <DebugConsole />}
      </div>
    </div>
  )
}

export default App
