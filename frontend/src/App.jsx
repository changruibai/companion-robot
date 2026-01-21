import { useState } from 'react'
import ChatInterface from './components/ChatInterface'
import Header from './components/Header'
import DebugConsole from './components/DebugConsole'

function App() {
  const [tab, setTab] = useState('chat')
  return (
    <div className="min-h-screen">
      <Header />
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <div className="mb-6 flex gap-2">
          <button
            onClick={() => setTab('chat')}
            className={[
              'px-4 py-2 rounded-2xl text-sm border transition-all',
              tab === 'chat' ? 'bg-gray-900 text-white border-gray-900' : 'bg-white/70 text-gray-800 border-gray-200',
            ].join(' ')}
          >
            线上聊天
          </button>
          <button
            onClick={() => setTab('debug')}
            className={[
              'px-4 py-2 rounded-2xl text-sm border transition-all',
              tab === 'debug' ? 'bg-gray-900 text-white border-gray-900' : 'bg-white/70 text-gray-800 border-gray-200',
            ].join(' ')}
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
