import { useState } from 'react'

const MessageBubble = ({ message, isTyping = false }) => {
  const isUser = message.role === 'user'
  const timeStr = message.timestamp.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
  
  // 跟踪每条记忆的展开状态
  const [expandedMemories, setExpandedMemories] = useState({})

  const toggleMemory = (idx) => {
    setExpandedMemories(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }))
  }

  return (
    <div className={`chat ${isUser ? 'chat-end' : 'chat-start'} my-2`}>
      <div className="flex items-center gap-3">
        <div className="chat-image avatar">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center relative ${isUser ? 'bg-primary' : 'bg-secondary'}`}>
            {isUser ? (
              <svg className="w-6 h-6 text-primary-content flex-shrink-0 m-0" fill="currentColor" viewBox="0 0 20 20" style={{ display: 'block' }}>
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-secondary-content flex-shrink-0 m-0" fill="currentColor" viewBox="0 0 20 20" style={{ display: 'block' }}>
                <path d="M11 3a1 1 0 10-2 0v1a1 1 0 102 0V3zM15.657 5.757a1 1 0 00-1.414-1.414l-.707.707a1 1 0 001.414 1.414l.707-.707zM18 10a1 1 0 01-1 1h-1a1 1 0 110-2h1a1 1 0 011 1zM5.05 6.464A1 1 0 106.464 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zM5 10a1 1 0 01-1 1H3a1 1 0 110-2h1a1 1 0 011 1zM8 16v-1h4v1a2 2 0 11-4 0zM12 14c.015-.34.208-.646.477-.859a4 4 0 10-4.954 0c.27.213.462.519.477.859h4z" />
              </svg>
            )}
          </div>
        </div>
        <div>
          <div className="chat-header mb-1">
            <time className="text-xs opacity-50">{timeStr}</time>
          </div>
          <div
            className={`chat-bubble max-w-[80vw] md:max-w-[70%] ${
              isUser
                ? 'chat-bubble-primary'
                : 'bg-[#ffd6e8] text-[#4b1033] shadow-sm'
            }`}
          >
        {message.content ? (
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        ) : null}
        
        {/* 打字指示器 - 只在助手消息且正在输入时显示 */}
        {!isUser && isTyping && (
          <div className="flex items-center space-x-1 mt-2">
            <div className="w-1.5 h-1.5 bg-secondary-content rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-1.5 h-1.5 bg-secondary-content rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-1.5 h-1.5 bg-secondary-content rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
        )}
        
        {/* 显示记忆库来源（如果有） */}
        {!isUser && message.memories && message.memories.length > 0 && (
          <div className="mt-3 pt-3 border-t border-secondary/30">
            <div className="flex items-center space-x-1 mb-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-xs font-semibold">记忆库来源 ({message.memories.length})</span>
            </div>
            <div className="space-y-1">
              {message.memories.map((mem, idx) => {
                const isExpanded = expandedMemories[idx]
                const shouldTruncate = mem.content.length > 100
                const displayContent = isExpanded || !shouldTruncate 
                  ? mem.content 
                  : mem.content.substring(0, 100)
                
                return (
                  <div key={idx} className="text-xs bg-base-200 rounded-lg px-2 py-1 border border-base-300">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <span className="font-medium">记忆 {idx + 1}:</span>{' '}
                        <span className="whitespace-pre-wrap break-words">{displayContent}</span>
                        {!isExpanded && shouldTruncate && <span>...</span>}
                        <span className="ml-2 opacity-70">(相关性: {(mem.score * 100).toFixed(0)}%)</span>
                      </div>
                      {shouldTruncate && (
                        <button
                          onClick={() => toggleMemory(idx)}
                          className="flex-shrink-0 btn btn-ghost btn-xs"
                          title={isExpanded ? '收起' : '展开'}
                        >
                          {isExpanded ? (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default MessageBubble
