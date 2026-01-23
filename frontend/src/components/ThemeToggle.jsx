import { useEffect, useState } from 'react'

const ThemeToggle = () => {
  const [theme, setTheme] = useState('light')
  const [isSystem, setIsSystem] = useState(true)

  // 获取系统主题偏好
  const getSystemTheme = () => {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark'
    }
    return 'light'
  }

  // 初始化主题
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme')
    const savedIsSystem = localStorage.getItem('isSystemTheme') !== 'false'
    
    let currentIsSystem = savedIsSystem
    
    if (savedTheme && !savedIsSystem) {
      setTheme(savedTheme)
      setIsSystem(false)
      document.documentElement.setAttribute('data-theme', savedTheme)
      currentIsSystem = false
    } else {
      // 默认跟随系统
      const systemTheme = getSystemTheme()
      setTheme(systemTheme)
      setIsSystem(true)
      document.documentElement.setAttribute('data-theme', systemTheme)
      currentIsSystem = true
    }

    // 监听系统主题变化
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e) => {
      // 使用闭包中的 currentIsSystem 而不是 state
      if (currentIsSystem) {
        const newTheme = e.matches ? 'dark' : 'light'
        setTheme(newTheme)
        document.documentElement.setAttribute('data-theme', newTheme)
      }
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  // 监听 isSystem 变化，更新系统主题监听器
  useEffect(() => {
    if (!isSystem) return
    
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e) => {
      if (isSystem) {
        const newTheme = e.matches ? 'dark' : 'light'
        setTheme(newTheme)
        document.documentElement.setAttribute('data-theme', newTheme)
      }
    }
    
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [isSystem])

  // 切换主题
  const handleThemeChange = (newTheme) => {
    if (newTheme === 'system') {
      setIsSystem(true)
      const systemTheme = getSystemTheme()
      setTheme(systemTheme)
      document.documentElement.setAttribute('data-theme', systemTheme)
      localStorage.setItem('isSystemTheme', 'true')
      localStorage.removeItem('theme')
    } else {
      setIsSystem(false)
      setTheme(newTheme)
      document.documentElement.setAttribute('data-theme', newTheme)
      localStorage.setItem('theme', newTheme)
      localStorage.setItem('isSystemTheme', 'false')
    }
  }

  const themes = [
    { name: '跟随系统', value: 'system', icon: '🌓' },
    { name: '浅色', value: 'light', icon: '☀️' },
    { name: '深色', value: 'dark', icon: '🌙' },
    { name: '杯糕', value: 'cupcake', icon: '🧁' },
    { name: '蜜蜂', value: 'bumblebee', icon: '🐝' },
    { name: '翡翠', value: 'emerald', icon: '💎' },
    { name: '企业', value: 'corporate', icon: '💼' },
    { name: '合成波', value: 'synthwave', icon: '🌆' },
    { name: '复古', value: 'retro', icon: '📻' },
    { name: '赛博朋克', value: 'cyberpunk', icon: '🤖' },
    { name: '情人节', value: 'valentine', icon: '💕' },
    { name: '万圣节', value: 'halloween', icon: '🎃' },
    { name: '花园', value: 'garden', icon: '🌺' },
    { name: '森林', value: 'forest', icon: '🌲' },
    { name: '水色', value: 'aqua', icon: '💧' },
    { name: '低保真', value: 'lofi', icon: '📻' },
    { name: '粉彩', value: 'pastel', icon: '🎨' },
    { name: '幻想', value: 'fantasy', icon: '✨' },
    { name: '线框', value: 'wireframe', icon: '📐' },
    { name: '黑色', value: 'black', icon: '⚫' },
    { name: '奢华', value: 'luxury', icon: '👑' },
    { name: '德古拉', value: 'dracula', icon: '🧛' },
    { name: 'CMYK', value: 'cmyk', icon: '🖨️' },
    { name: '秋天', value: 'autumn', icon: '🍂' },
    { name: '商务', value: 'business', icon: '📊' },
    { name: '酸性', value: 'acid', icon: '⚡' },
    { name: '柠檬', value: 'lemonade', icon: '🍋' },
    { name: '夜晚', value: 'night', icon: '🌃' },
    { name: '咖啡', value: 'coffee', icon: '☕' },
    { name: '冬天', value: 'winter', icon: '❄️' },
  ]

  return (
    <div className="dropdown dropdown-end">
      <label tabIndex={0} className="btn btn-ghost btn-circle">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
        </svg>
      </label>
      <ul tabIndex={0} className="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow-lg border border-base-300 max-h-96 overflow-y-auto">
        {themes.map((t) => (
          <li key={t.value}>
            <button
              onClick={() => handleThemeChange(t.value)}
              className={`flex items-center gap-2 ${
                (t.value === 'system' && isSystem) || (t.value === theme && !isSystem)
                  ? 'active bg-primary text-primary-content'
                  : ''
              }`}
            >
              <span className="text-lg">{t.icon}</span>
              <span>{t.name}</span>
              {((t.value === 'system' && isSystem) || (t.value === theme && !isSystem)) && (
                <svg className="w-4 h-4 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default ThemeToggle
