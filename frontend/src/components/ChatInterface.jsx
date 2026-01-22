import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import MessageBubble from './MessageBubble'
import LoadingSpinner from './LoadingSpinner'

const ChatInterface = () => {
  // 用户和狗的选择
  const [users, setUsers] = useState([])
  const [dogs, setDogs] = useState([])
  const [selectedUserId, setSelectedUserId] = useState('')
  const [selectedDogId, setSelectedDogId] = useState('')
  
  // 模型选择
  const [selectedModel, setSelectedModel] = useState('deepseek')
  const modelOptions = [
    { id: 'chatgpt', name: 'ChatGPT', description: 'OpenAI GPT-4o-mini' },
    { id: 'deepseek', name: 'DeepSeek', description: 'DeepSeek Chat' },
  ]
  
  // 会话管理
  const [conversations, setConversations] = useState([])
  const [selectedConversationId, setSelectedConversationId] = useState('')
  const [isLoadingConversations, setIsLoadingConversations] = useState(false)
  
  // 消息和输入
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  
  // 是否已初始化（已选择用户和狗）
  const [isInitialized, setIsInitialized] = useState(false)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 初始化：加载用户列表和狗列表
  useEffect(() => {
    const loadUsersAndDogs = async () => {
      try {
        const [usersRes, dogsRes] = await Promise.all([
          axios.get('/api/users'),
          axios.get('/api/dogs')
        ])
        
        const usersList = usersRes.data.users || []
        const dogsList = dogsRes.data.dogs || []
        const defaultUser = usersRes.data.default || usersList[0] || ''
        const defaultDog = dogsRes.data.default || dogsList[0] || ''
        
        setUsers(usersList)
        setDogs(dogsList)
        
        // 设置默认值
        if (defaultUser && defaultDog) {
          setSelectedUserId(defaultUser)
          setSelectedDogId(defaultDog)
          setIsInitialized(true)
          // 加载该用户和狗的历史会话
          loadConversations(defaultUser, defaultDog)
        }
      } catch (error) {
        console.error('加载用户和狗列表失败:', error)
        // 设置默认值作为后备
        setUsers(['user_001'])
        setDogs(['dog_001'])
        setSelectedUserId('user_001')
        setSelectedDogId('dog_001')
        setIsInitialized(true)
      }
    }
    
    loadUsersAndDogs()
  }, [])

  // 当用户或狗改变时，重新加载会话列表
  useEffect(() => {
    if (selectedUserId && selectedDogId) {
      loadConversations(selectedUserId, selectedDogId)
      // 重置消息
      setMessages([{
        role: 'assistant',
        content: '👋 你好！我是 VikingDB 智能记忆助手。我可以帮你查询记忆库中的信息，并基于 AI 能力为你提供智能回答。试试问我一些问题吧！',
        timestamp: new Date(),
      }])
      setSelectedConversationId('')
    }
  }, [selectedUserId, selectedDogId])

  // 加载历史会话列表
  const loadConversations = async (userId, dogId) => {
    if (!userId || !dogId) return
    
    setIsLoadingConversations(true)
    try {
      const res = await axios.get('/api/conversations', {
        params: { user_id: userId, dog_id: dogId }
      })
      const convs = res.data.conversations || []
      setConversations(convs)
      
      // 如果有会话，默认选择最新的
      if (convs.length > 0 && !selectedConversationId) {
        setSelectedConversationId(convs[0].id)
      }
    } catch (error) {
      console.error('加载会话列表失败:', error)
      // 创建一个默认会话
      const defaultConvId = `conv_${userId}_${dogId}_${new Date().toISOString().split('T')[0].replace(/-/g, '')}`
      setConversations([{
        id: defaultConvId,
        title: '新对话',
        last_message_time: Date.now(),
      }])
      setSelectedConversationId(defaultConvId)
    } finally {
      setIsLoadingConversations(false)
    }
  }

  // 开启新对话
  const startNewConversation = () => {
    if (!selectedUserId || !selectedDogId) return
    
    const newConvId = `conv_${selectedUserId}_${selectedDogId}_${Date.now()}`
    const newConversation = {
      id: newConvId,
      title: '新对话',
      last_message_time: Date.now(),
    }
    
    setConversations(prev => [newConversation, ...prev])
    setSelectedConversationId(newConvId)
    setMessages([{
      role: 'assistant',
      content: '👋 你好！我是 VikingDB 智能记忆助手。我可以帮你查询记忆库中的信息，并基于 AI 能力为你提供智能回答。试试问我一些问题吧！',
      timestamp: new Date(),
    }])
  }

  // 选择历史会话
  const selectConversation = (convId) => {
    setSelectedConversationId(convId)
    // 这里可以加载该会话的历史消息（如果需要的话）
    // 目前先重置消息
    setMessages([{
      role: 'assistant',
      content: '👋 你好！我是 VikingDB 智能记忆助手。我可以帮你查询记忆库中的信息，并基于 AI 能力为你提供智能回答。试试问我一些问题吧！',
      timestamp: new Date(),
    }])
  }

  // 处理用户选择
  const handleUserChange = (userId) => {
    setSelectedUserId(userId)
    setIsInitialized(userId && selectedDogId)
  }

  // 处理狗选择
  const handleDogChange = (dogId) => {
    setSelectedDogId(dogId)
    setIsInitialized(selectedUserId && dogId)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading || !isInitialized || !selectedUserId || !selectedDogId || !selectedConversationId) return

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    const currentInput = input
    setInput('')
    setLoading(true)

    // 创建助手消息占位符，用于流式更新
    const assistantMessageId = Date.now()
    const assistantMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, assistantMessage])

    // 打字效果相关状态
    let fullAnswerBuffer = '' // 存储完整答案（待显示的内容）
    let displayedLength = 0 // 已显示的字符数
    let typingTimer = null // 打字定时器
    let isTypingActive = false // 打字效果是否激活

    // 打字效果函数：逐字符显示
    const typeWriter = () => {
      if (!isTypingActive) return
      
      if (displayedLength < fullAnswerBuffer.length) {
        // 每次显示更多字符，实现平滑的打字效果
        // 根据剩余内容动态调整显示速度：内容多时快一点，少时慢一点
        const remaining = fullAnswerBuffer.length - displayedLength
        const charsToShow = remaining > 50 ? 5 : (remaining > 10 ? 3 : 1) // 每次显示1-5个字符
        displayedLength = Math.min(displayedLength + charsToShow, fullAnswerBuffer.length)
        const displayContent = fullAnswerBuffer.substring(0, displayedLength)
        
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: displayContent }
            : msg
        ))
        
        // 继续打字效果
        typingTimer = setTimeout(typeWriter, 200) // 每20ms显示一次，约150字符/秒
      } else {
        // 打字完成
        isTypingActive = false
      }
    }

    // 启动打字效果
    const startTyping = () => {
      if (!isTypingActive) {
        isTypingActive = true
        typeWriter()
      }
    }

    // 停止打字效果并显示完整内容
    const finishTyping = () => {
      isTypingActive = false
      if (typingTimer) {
        clearTimeout(typingTimer)
        typingTimer = null
      }
      // 立即显示完整内容
      if (fullAnswerBuffer) {
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { ...msg, content: fullAnswerBuffer }
            : msg
        ))
      }
    }

    try {
      // 使用 fetch 接收流式响应
      const response = await fetch('/api/debug/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: currentInput,
          user_id: selectedUserId,
          dog_id: selectedDogId,
          conversation_id: selectedConversationId,
          assistant_id: 'assistant_001',
          limit: 5,
          model: selectedModel
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // 检查响应类型
      const contentType = response.headers.get('content-type')
      console.log('响应 Content-Type:', contentType)
      
      if (!contentType || !contentType.includes('text/event-stream')) {
        console.warn('响应不是 SSE 格式，尝试按普通 JSON 处理')
        // 如果不是流式响应，尝试按普通 JSON 处理（向后兼容）
        const data = await response.json()
        if (data.answer) {
          fullAnswerBuffer = data.answer
          startTyping()
          // 等待打字完成
          setTimeout(() => {
            finishTyping()
            setLoading(false)
          }, (data.answer.length / 3) * 30 + 100)
        } else {
          setLoading(false)
        }
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let chunkCount = 0

      console.log('开始读取流式响应...')

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.log('流读取完成，总chunk数:', chunkCount, '总长度:', fullAnswerBuffer.length)
          // 流结束时，如果还有内容但没有收到 done 信号，也要更新
          if (buffer.trim()) {
            // 处理最后可能剩余的数据
            const lines = buffer.split('\n')
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6))
                  if (data.content) {
                    fullAnswerBuffer += data.content
                    chunkCount++
                  }
                } catch (e) {
                  console.error('解析最后的数据失败:', e)
                }
              }
            }
          }
          // 确保打字效果完成
          finishTyping()
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // 保留最后一个不完整的行

        for (const line of lines) {
          if (line.trim() === '') continue // 跳过空行
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.error) {
                throw new Error(data.error)
              }
              if (data.content) {
                chunkCount++
                fullAnswerBuffer += data.content
                console.log(`收到第 ${chunkCount} 个chunk，当前总长度: ${fullAnswerBuffer.length}`)
                // 启动或继续打字效果
                if (!isTypingActive) {
                  startTyping()
                }
              }
              if (data.done) {
                console.log('收到完成信号')
                finishTyping()
                setLoading(false)
                // 更新会话列表（将当前会话移到最前面）
                setConversations(prev => {
                  const updated = prev.map(conv => 
                    conv.id === selectedConversationId 
                      ? { ...conv, last_message_time: Date.now(), title: currentInput.slice(0, 50) + (currentInput.length > 50 ? '...' : '') }
                      : conv
                  )
                  // 按时间排序
                  updated.sort((a, b) => b.last_message_time - a.last_message_time)
                  return updated
                })
              }
            } catch (parseError) {
              console.error('解析 SSE 数据失败:', parseError, '原始行:', line)
            }
          } else if (line.trim() !== '') {
            console.log('收到非 data 行:', line)
          }
        }
      }
      
      // 确保 loading 状态被清除
      setLoading(false)
      console.log('流式处理完成，最终答案长度:', fullAnswerBuffer.length)
    } catch (error) {
      // 清理定时器
      if (typingTimer) {
        clearTimeout(typingTimer)
        typingTimer = null
      }
      isTypingActive = false
      setLoading(false)
      const errorMessage = {
        role: 'assistant',
        content: `抱歉，查询失败：${error.message}`,
        timestamp: new Date(),
      }
      // 移除占位符消息，添加错误消息
      setMessages(prev => prev.filter(msg => msg.id !== assistantMessageId).concat(errorMessage))
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] glass-effect rounded-3xl shadow-2xl overflow-hidden">
      {/* 顶部选择区域 */}
      <div className="border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50 p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-3">
          {/* 用户选择 */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">选择用户</label>
            <select
              value={selectedUserId}
              onChange={(e) => handleUserChange(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border-2 border-gray-200 bg-white focus:border-blue-400 focus:outline-none transition-all text-sm"
            >
              <option value="">请选择用户</option>
              {users.map(user => (
                <option key={user} value={user}>{user}</option>
              ))}
            </select>
          </div>

          {/* 狗选择 */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">选择狗</label>
            <select
              value={selectedDogId}
              onChange={(e) => handleDogChange(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border-2 border-gray-200 bg-white focus:border-blue-400 focus:outline-none transition-all text-sm"
            >
              <option value="">请选择狗</option>
              {dogs.map(dog => (
                <option key={dog} value={dog}>{dog}</option>
              ))}
            </select>
          </div>

          {/* 模型选择 */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1">选择模型</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border-2 border-gray-200 bg-white focus:border-blue-400 focus:outline-none transition-all text-sm"
            >
              {modelOptions.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
          </div>

          {/* 会话管理 */}
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-gray-600 mb-1">选择会话</label>
              <select
                value={selectedConversationId}
                onChange={(e) => selectConversation(e.target.value)}
                disabled={!isInitialized || isLoadingConversations}
                className="w-full px-3 py-2 rounded-xl border-2 border-gray-200 bg-white focus:border-blue-400 focus:outline-none transition-all text-sm disabled:opacity-50"
              >
                <option value="">请选择会话</option>
                {conversations.map(conv => (
                  <option key={conv.id} value={conv.id}>
                    {conv.title || conv.id}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-end">
              <button
                onClick={startNewConversation}
                disabled={!isInitialized}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-blue-500 to-purple-600 text-white text-sm font-medium hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
              >
                新对话
              </button>
            </div>
          </div>
        </div>
        
        {!isInitialized && (
          <div className="text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg">
            ⚠️ 请先选择用户和狗，然后才能开始对话
          </div>
        )}
      </div>

      {/* 消息区域 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-400">
            {!isInitialized ? '请先选择用户和狗' : '开始你的对话吧！'}
          </div>
        ) : (
          messages.map((message, index) => {
            // 判断是否是最后一条助手消息且正在加载
            const isLastAssistantMessage = message.role === 'assistant' && index === messages.length - 1
            const isTyping = loading && isLastAssistantMessage
            return (
              <MessageBubble 
                key={message.id || index} 
                message={message} 
                isTyping={isTyping}
              />
            )
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="border-t border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50 p-4">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={isInitialized ? "输入你的问题..." : "请先选择用户和狗"}
              className="w-full px-4 py-3 pr-12 rounded-2xl border-2 border-gray-200 focus:border-blue-400 focus:outline-none transition-all bg-white shadow-sm disabled:opacity-50"
              disabled={loading || !isInitialized}
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || !isInitialized || !selectedConversationId}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </form>
        <p className="text-xs text-gray-500 mt-2 text-center">
          基于 VikingDB 记忆库 + {modelOptions.find(m => m.id === selectedModel)?.description || 'AI'} 智能回答
        </p>
      </div>
    </div>
  )
}

export default ChatInterface
