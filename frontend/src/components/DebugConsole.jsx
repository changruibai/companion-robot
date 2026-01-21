import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

const LS_KEY = 'viking_debug_entities_v1'

function loadEntities() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function saveEntities(state) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(state))
  } catch {
    // ignore
  }
}

const defaultState = {
  users: ['user_001'],
  dogs: ['dog_001'],
  conversations: ['conv_001'],
  selected: { userId: 'user_001', dogId: 'dog_001', conversationId: 'conv_001' },
}

function Select({ label, value, options, onChange }) {
  return (
    <label className="block">
      <div className="text-xs font-semibold text-gray-600 mb-1">{label}</div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    </label>
  )
}

function AddId({ placeholder, onAdd }) {
  const [val, setVal] = useState('')
  return (
    <div className="flex gap-2">
      <input
        value={val}
        onChange={(e) => setVal(e.target.value)}
        placeholder={placeholder}
        className="flex-1 px-3 py-2 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
      />
      <button
        onClick={() => {
          const v = val.trim()
          if (!v) return
          onAdd(v)
          setVal('')
        }}
        className="px-3 py-2 rounded-xl bg-gray-900 text-white text-sm hover:bg-black"
      >
        添加
      </button>
    </div>
  )
}

export default function DebugConsole() {
  const [entities, setEntities] = useState(() => loadEntities() || defaultState)
  const [collections, setCollections] = useState(null)

  const [profileText, setProfileText] = useState('')
  const [dogProfileText, setDogProfileText] = useState('')
  const [relationshipText, setRelationshipText] = useState('')

  const [chatInput, setChatInput] = useState('')
  const [chatLog, setChatLog] = useState([])
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState(null)
  const [toasts, setToasts] = useState([])

  useEffect(() => {
    saveEntities(entities)
  }, [entities])

  useEffect(() => {
    ;(async () => {
      try {
        const res = await axios.get('/api/collections')
        setCollections(res.data)
      } catch (e) {
        setCollections({ error: e.response?.data?.detail || e.message })
      }
    })()
  }, [])

  const selected = entities.selected
  const canChat = selected.userId && selected.dogId && selected.conversationId

  const selectedSummary = useMemo(() => {
    return `user=${selected.userId} | dog=${selected.dogId} | conversation=${selected.conversationId}`
  }, [selected.userId, selected.dogId, selected.conversationId])

  const updateSelected = (patch) => {
    setEntities((prev) => ({ ...prev, selected: { ...prev.selected, ...patch } }))
  }

  const addEntity = (key, id) => {
    setEntities((prev) => {
      const list = prev[key]
      if (list.includes(id)) return prev
      const next = { ...prev, [key]: [...list, id] }
      // 如果是空选中，顺便选上
      if (key === 'users' && !prev.selected.userId) next.selected.userId = id
      if (key === 'dogs' && !prev.selected.dogId) next.selected.dogId = id
      if (key === 'conversations' && !prev.selected.conversationId) next.selected.conversationId = id
      return next
    })
  }

  const pushToast = (text, type = 'ok') => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, text, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 2000)
  }

  const writeProfile = async ({ collection_key, user_id, assistant_id, memory_info }) => {
    return await axios.post('/api/memory/profile/add', {
      collection_key,
      profile_type: 'profile_v1',
      memory_info,
      user_id,
      assistant_id,
      is_upsert: true,
    })
  }

  const handleWriteUser = async () => {
    if (!selected.userId) return
    setStatus(null)
    try {
      const res = await writeProfile({
        collection_key: 'user',
        user_id: selected.userId,
        assistant_id: 'assistant_001',
        memory_info: { user_profile: profileText },
      })
      setStatus({ type: 'ok', text: `user 写入成功：${res.data?.data?.id || 'OK'}` })
      pushToast('user 写入成功')
    } catch (e) {
      setStatus({ type: 'err', text: e.response?.data?.detail || e.message })
    }
  }

  const handleWriteDog = async () => {
    if (!selected.dogId) return
    setStatus(null)
    try {
      const res = await writeProfile({
        collection_key: 'dog',
        user_id: selected.dogId,
        assistant_id: 'assistant_001',
        memory_info: { user_profile: dogProfileText },
      })
      setStatus({ type: 'ok', text: `dog 写入成功：${res.data?.data?.id || 'OK'}` })
      pushToast('dog 写入成功')
    } catch (e) {
      setStatus({ type: 'err', text: e.response?.data?.detail || e.message })
    }
  }

  const handleWriteRelationship = async () => {
    if (!selected.userId || !selected.dogId) return
    setStatus(null)
    try {
      const res = await writeProfile({
        collection_key: 'relationship',
        user_id: selected.userId,
        assistant_id: selected.dogId,
        memory_info: { user_profile: relationshipText },
      })
      setStatus({ type: 'ok', text: `relationship 写入成功：${res.data?.data?.id || 'OK'}` })
      pushToast('relationship 写入成功')
    } catch (e) {
      setStatus({ type: 'err', text: e.response?.data?.detail || e.message })
    }
  }

  const handleChat = async () => {
    if (!chatInput.trim() || loading || !canChat) return
    const q = chatInput.trim()
    setChatInput('')
    setLoading(true)
    setStatus(null)
    setChatLog((prev) => [...prev, { role: 'user', content: q, ts: Date.now() }])
    try {
      const res = await axios.post('/api/debug/chat', {
        query: q,
        user_id: selected.userId,
        dog_id: selected.dogId,
        conversation_id: selected.conversationId,
        assistant_id: 'assistant_001',
        limit: 5,
      })
      setChatLog((prev) => [
        ...prev,
        { role: 'assistant', content: res.data.answer, context: res.data.context, ts: Date.now() },
      ])
      setStatus({ type: 'ok', text: `conversation 已写入（${selected.conversationId}）` })
      pushToast('conversation 写入成功')
    } catch (e) {
      setChatLog((prev) => [
        ...prev,
        { role: 'assistant', content: `请求失败：${e.response?.data?.detail || e.message}`, ts: Date.now() },
      ])
      setStatus({ type: 'err', text: e.response?.data?.detail || e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* 左侧：实体选择 */}
      <div className="glass-effect rounded-3xl shadow-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-lg font-bold text-gray-900">调试控制台</div>
          <span className="text-xs text-gray-500">多用户 / 多狗 / 多对话</span>
        </div>

        <div className="text-xs text-gray-600 bg-white/60 rounded-2xl p-3 border border-gray-100">
          当前选择：<span className="font-mono">{selectedSummary}</span>
        </div>

        <div className="grid grid-cols-1 gap-3">
          <Select
            label="User"
            value={selected.userId}
            options={entities.users}
            onChange={(v) => updateSelected({ userId: v })}
          />
          <AddId placeholder="新增 user_id，例如 user_002" onAdd={(v) => addEntity('users', v)} />

          <Select
            label="Dog"
            value={selected.dogId}
            options={entities.dogs}
            onChange={(v) => updateSelected({ dogId: v })}
          />
          <AddId placeholder="新增 dog_id，例如 dog_A" onAdd={(v) => addEntity('dogs', v)} />

          <Select
            label="Conversation"
            value={selected.conversationId}
            options={entities.conversations}
            onChange={(v) => updateSelected({ conversationId: v })}
          />
          <AddId placeholder="新增 conversation_id，例如 conv_20260121_1" onAdd={(v) => addEntity('conversations', v)} />
        </div>

        <div className="rounded-2xl border border-gray-100 bg-white/60 p-3">
          <div className="text-xs font-semibold text-gray-700 mb-2">后端 collection 绑定</div>
          <pre className="text-[11px] leading-4 text-gray-700 whitespace-pre-wrap">
            {collections ? JSON.stringify(collections, null, 2) : '加载中...'}
          </pre>
        </div>
      </div>

      {/* 中间：写入画像/关系 */}
      <div className="glass-effect rounded-3xl shadow-xl p-5 space-y-4">
        <div className="text-lg font-bold text-gray-900">写入记忆（真实落库）</div>

        <div className="space-y-2">
          <div className="text-sm font-semibold text-gray-800">User 画像（写入 user 库）</div>
          <textarea
            value={profileText}
            onChange={(e) => setProfileText(e.target.value)}
            placeholder="例如：张三，喜欢咖啡，住在北京..."
            className="w-full min-h-[90px] px-3 py-2 rounded-2xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <button onClick={handleWriteUser} className="px-3 py-2 rounded-xl bg-blue-600 text-white text-sm hover:bg-blue-700">
            写入 user
          </button>
        </div>

        <div className="space-y-2">
          <div className="text-sm font-semibold text-gray-800">Dog 画像（写入 dog 库）</div>
          <textarea
            value={dogProfileText}
            onChange={(e) => setDogProfileText(e.target.value)}
            placeholder="例如：dog_001 是柴犬外形，名字旺财，喜欢追球..."
            className="w-full min-h-[90px] px-3 py-2 rounded-2xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <button onClick={handleWriteDog} className="px-3 py-2 rounded-xl bg-indigo-600 text-white text-sm hover:bg-indigo-700">
            写入 dog
          </button>
        </div>

        <div className="space-y-2">
          <div className="text-sm font-semibold text-gray-800">关系记忆（写入 relationship 库）</div>
          <textarea
            value={relationshipText}
            onChange={(e) => setRelationshipText(e.target.value)}
            placeholder="例如：用户张三与旺财是主人与宠物关系，旺财怕洗澡..."
            className="w-full min-h-[90px] px-3 py-2 rounded-2xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300"
          />
          <button
            onClick={handleWriteRelationship}
            className="px-3 py-2 rounded-xl bg-purple-600 text-white text-sm hover:bg-purple-700"
          >
            写入 relationship（user + dog）
          </button>
        </div>

        {status && (
          <div
            className={[
              'rounded-2xl p-3 text-sm border',
              status.type === 'ok' ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800',
            ].join(' ')}
          >
            {status.text}
          </div>
        )}
      </div>

      {/* 右侧：聊天 + 展示召回 */}
      <div className="glass-effect rounded-3xl shadow-xl p-5 flex flex-col">
        <div className="text-lg font-bold text-gray-900 mb-3">对话调试（写入 conversation 库）</div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {chatLog.length === 0 && (
            <div className="text-sm text-gray-600 bg-white/60 rounded-2xl p-3 border border-gray-100">
              在右下输入一句话，后端会跨四个库召回上下文并回答，同时把本轮写入 conversation。
            </div>
          )}
          {chatLog.map((m, idx) => (
            <div key={idx} className={m.role === 'user' ? 'text-right' : 'text-left'}>
              <div
                className={[
                  'inline-block max-w-[92%] rounded-2xl px-4 py-3 border',
                  m.role === 'user'
                    ? 'bg-blue-600 text-white border-blue-700'
                    : 'bg-white/80 text-gray-900 border-gray-100',
                ].join(' ')}
              >
                <div className="text-sm whitespace-pre-wrap">{m.content}</div>
              </div>
              {m.role === 'assistant' && m.context && (
                <details className="mt-2 text-left">
                  <summary className="cursor-pointer text-xs text-gray-600">查看召回上下文（user/dog/relationship/conversation）</summary>
                  <pre className="mt-2 text-[11px] leading-4 text-gray-700 bg-white/70 border border-gray-100 rounded-2xl p-3 whitespace-pre-wrap">
                    {JSON.stringify(m.context, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          ))}
        </div>

        <div className="mt-4 border-t border-gray-200 pt-4">
          <div className="flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={canChat ? '输入一句话，回车发送...' : '请先选择 user/dog/conversation'}
              disabled={!canChat || loading}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleChat()
              }}
              className="flex-1 px-4 py-3 rounded-2xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-300 disabled:opacity-60"
            />
            <button
              onClick={handleChat}
              disabled={!canChat || loading || !chatInput.trim()}
              className="px-4 py-3 rounded-2xl bg-gray-900 text-white text-sm hover:bg-black disabled:opacity-50"
            >
              {loading ? '发送中...' : '发送'}
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-500">
            注意：conversation 库写入采用 <span className="font-mono">conversation_id + 时间戳</span>，保证每轮都落库。
          </div>
        </div>
      </div>

      {/* 全局 Toast */}
      <div className="fixed bottom-6 right-6 space-y-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={[
              'px-4 py-3 rounded-2xl shadow-lg text-sm border bg-white',
              t.type === 'ok'
                ? 'border-green-200 text-green-800 bg-green-50'
                : 'border-red-200 text-red-800 bg-red-50',
            ].join(' ')}
          >
            {t.text}
          </div>
        ))}
      </div>
    </div>
  )
}

