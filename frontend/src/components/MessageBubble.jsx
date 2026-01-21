import { useState } from 'react'

const MessageBubble = ({ message }) => {
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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] ${isUser ? 'order-2' : 'order-1'}`}>
        {/* 头像 */}
        <div className={`flex items-start space-x-2 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
          <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
            isUser 
              ? 'bg-gradient-to-br from-blue-500 to-purple-600' 
              : 'bg-gradient-to-br from-purple-500 to-pink-600'
          } shadow-lg`}>
            {isUser ? (
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            )}
          </div>
          
          {/* 消息内容 */}
          <div className={`rounded-2xl px-4 py-3 shadow-lg ${
            isUser 
              ? 'bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-tr-none' 
              : 'bg-white text-gray-800 rounded-tl-none border border-gray-100'
          }`}>
            <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
            
            {/* 显示记忆库来源（如果有） */}
            {!isUser && message.memories && message.memories.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="flex items-center space-x-1 mb-2">
                  <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-xs font-semibold text-purple-600">记忆库来源 ({message.memories.length})</span>
                </div>
                <div className="space-y-1">
                  {message.memories.map((mem, idx) => {
                    const isExpanded = expandedMemories[idx]
                    const shouldTruncate = mem.content.length > 100
                    const displayContent = isExpanded || !shouldTruncate 
                      ? mem.content 
                      : mem.content.substring(0, 100)
                    
                    return (
                      <div key={idx} className="text-xs text-gray-600 bg-purple-50 rounded-lg px-2 py-1 border border-red-200">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1">
                            <span className="font-medium">记忆 {idx + 1}:</span>{' '}
                            <span className="whitespace-pre-wrap break-words">{displayContent}</span>
                            {!isExpanded && shouldTruncate && <span>...</span>}
                            <span className="ml-2 text-purple-500">(相关性: {(mem.score * 100).toFixed(0)}%)</span>
                          </div>
                          {shouldTruncate && (
                            <button
                              onClick={() => toggleMemory(idx)}
                              className="flex-shrink-0 text-purple-600 hover:text-purple-800 transition-colors ml-2"
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
            
            <p className={`text-xs mt-2 ${
              isUser ? 'text-blue-100' : 'text-gray-400'
            }`}>
              {timeStr}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default MessageBubble
