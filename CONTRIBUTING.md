# 貢獻指南

感謝您對 HeartBox 專案的關注！我們歡迎所有形式的貢獻，包括但不限於錯誤報告、功能建議、文檔改進和代碼貢獻。

## 📋 目錄

- [行為準則](#行為準則)
- [如何貢獻](#如何貢獻)
- [開發流程](#開發流程)
- [代碼規範](#代碼規範)
- [提交規範](#提交規範)
- [Pull Request 流程](#pull-request-流程)
- [測試要求](#測試要求)

## 🤝 行為準則

本專案遵循 [Contributor Covenant](https://www.contributor-covenant.org/) 行為準則。參與本專案即表示您同意遵守其條款。

### 我們的承諾
- 尊重所有貢獻者
- 歡迎不同觀點和經驗
- 接受建設性批評
- 專注於對社群最有利的事情

## 🚀 如何貢獻

### 報告錯誤

發現錯誤？請：
1. 檢查 [Issues](https://github.com/alanlin0604/HeartBox/issues) 確認未被報告
2. 使用 Bug Report 模板創建新 Issue
3. 提供詳細的重現步驟
4. 包含錯誤截圖或日誌

**好的錯誤報告包含**:
- 清晰的標題
- 重現步驟
- 預期行為 vs 實際行為
- 環境資訊（瀏覽器、作業系統等）
- 錯誤訊息或截圖

### 建議新功能

有好點子？請：
1. 檢查是否已有類似建議
2. 使用 Feature Request 模板
3. 清楚描述功能和使用場景
4. 說明為什麼這個功能有價值

### 改進文檔

文檔改進同樣重要！您可以：
- 修正錯字或語法錯誤
- 添加缺失的文檔
- 改進現有說明
- 翻譯文檔

## 💻 開發流程

### 1. Fork 並 Clone

```bash
# Fork 本專案到您的 GitHub 帳號

# Clone 到本地
git clone https://github.com/YOUR_USERNAME/HeartBox.git
cd HeartBox

# 添加上游倉庫
git remote add upstream https://github.com/alanlin0604/HeartBox.git
```

### 2. 創建分支

```bash
# 更新 main 分支
git checkout main
git pull upstream main

# 創建功能分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

**分支命名規範**:
- `feature/` - 新功能
- `fix/` - 錯誤修復
- `docs/` - 文檔更新
- `refactor/` - 代碼重構
- `test/` - 測試相關
- `chore/` - 構建/工具相關

### 3. 設置開發環境

參考 [README.md](README.md) 中的「快速開始」章節。

### 4. 進行更改

遵循 [代碼規範](#代碼規範)，並確保：
- 代碼格式正確
- 添加必要的測試
- 更新相關文檔
- 通過所有測試

### 5. 提交更改

遵循 [提交規範](#提交規範)：

```bash
git add .
git commit -m "feat: add amazing feature"
```

### 6. 推送並創建 PR

```bash
git push origin feature/your-feature-name
```

然後在 GitHub 上創建 Pull Request。

## 📝 代碼規範

### 前端 (React)

```javascript
// ✅ 好的範例
import { useState, useCallback, useMemo } from 'react'

// 使用函數組件和 Hooks
export default function MyComponent({ data }) {
  const [count, setCount] = useState(0)
  
  // 使用 useCallback 穩定化回調
  const handleClick = useCallback(() => {
    setCount(prev => prev + 1)
  }, [])
  
  // 使用 useMemo 緩存計算
  const expensiveValue = useMemo(() => {
    return data.reduce((acc, item) => acc + item.value, 0)
  }, [data])
  
  return (
    <button onClick={handleClick} className="btn-primary">
      Count: {count}
    </button>
  )
}

// ❌ 避免的範例
// - 使用 class 組件
// - 內聯函數在 JSX 中
// - 不必要的 useEffect
```

**規範**:
- 使用函數組件和 Hooks
- 遵循 React Hooks 規則
- 組件名稱使用 PascalCase
- 文件名與組件名一致
- 使用 PropTypes 或 TypeScript
- 提取可重用邏輯到自定義 Hooks

### 後端 (Django)

```python
# ✅ 好的範例
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

class NoteSerializer(serializers.ModelSerializer):
    """筆記序列化器"""
    
    class Meta:
        model = Note
        fields = ['id', 'title', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']

class NoteViewSet(viewsets.ModelViewSet):
    """筆記 ViewSet"""
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Note.objects.filter(user=self.request.user)

# ❌ 避免的範例
# - 沒有 docstring
# - 不安全的查詢（沒有用戶過濾）
# - 缺少權限檢查
```

**規範**:
- 遵循 PEP 8
- 使用 Django ORM（避免原始 SQL）
- 添加 docstring
- 實施適當的權限檢查
- 使用 DRF 序列化器驗證
- 避免 N+1 查詢問題

### CSS / Tailwind

```jsx
// ✅ 好的範例 - 使用 Tailwind 工具類
<button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
  Click me
</button>

// ❌ 避免 - 內聯樣式
<button style={{ padding: '8px 16px', backgroundColor: 'blue' }}>
  Click me
</button>
```

**規範**:
- 優先使用 Tailwind 工具類
- 避免內聯樣式
- 使用 CSS 變數定義主題顏色
- 響應式設計（mobile-first）

## 📋 提交規範

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 類型
- `feat`: 新功能
- `fix`: 錯誤修復
- `docs`: 文檔更新
- `style`: 代碼格式（不影響邏輯）
- `refactor`: 重構
- `perf`: 性能優化
- `test`: 測試相關
- `build`: 構建系統
- `ci`: CI 配置
- `chore`: 其他（構建/工具）
- `revert`: 撤銷提交

### Scope 範圍
- `frontend`: 前端相關
- `backend`: 後端相關
- `api`: API 相關
- `ui`: UI 組件
- `docs`: 文檔
- `deps`: 依賴項

### 範例

```bash
# 簡單提交
git commit -m "feat(ui): add Toast component"

# 詳細提交
git commit -m "feat(api): add health data sync endpoint

- Add /api/health/sync/ endpoint
- Support iOS HealthKit and Android Health Connect
- Include steps, heart rate, and sleep data

Closes #123"
```

## 🔄 Pull Request 流程

### PR 標題

遵循 Conventional Commits 格式：
```
feat(ui): add dark mode toggle
fix(api): resolve authentication bug
docs: update installation guide
```

### PR 描述模板

```markdown
## 📝 變更描述
<!-- 簡要描述此 PR 的變更 -->

## 🎯 相關 Issue
<!-- 關閉或相關的 Issue，如: Closes #123 -->

## 🧪 測試
<!-- 描述如何測試此變更 -->
- [ ] 添加了單元測試
- [ ] 添加了整合測試
- [ ] 手動測試通過

## 📸 截圖（如適用）
<!-- 添加截圖或 GIF -->

## ✅ 檢查清單
- [ ] 代碼遵循專案規範
- [ ] 已添加必要的測試
- [ ] 所有測試通過
- [ ] 已更新相關文檔
- [ ] Commit 訊息遵循規範
```

### PR Review 流程

1. **自動檢查**: GitHub Actions 會自動運行
   - ESLint 檢查
   - 測試套件
   - 構建驗證

2. **代碼審查**: 至少需要 1 位維護者批准

3. **修改請求**: 根據反饋進行調整

4. **合併**: 審查通過後由維護者合併

## 🧪 測試要求

### 前端測試

```javascript
// frontend/src/components/__tests__/Button.test.jsx
import { render, screen, fireEvent } from '@testing-library/react'
import Button from '../Button'

describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByText('Click me')).toBeInTheDocument()
  })
  
  it('calls onClick when clicked', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    fireEvent.click(screen.getByText('Click me'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})
```

**運行測試**:
```bash
cd frontend
npm test              # 運行所有測試
npm run test:coverage # 測試覆蓋率報告
```

### 後端測試

```python
# backend/api/tests.py
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Note

class NoteAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('test', 'test@test.com', 'pass')
        
    def test_create_note(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/notes/', {
            'title': 'Test Note',
            'content': 'Test Content'
        })
        self.assertEqual(response.status_code, 201)
```

**運行測試**:
```bash
cd backend
python manage.py test
```

### 測試覆蓋率要求
- **新功能**: 必須有測試（覆蓋率 >= 80%）
- **錯誤修復**: 添加回歸測試
- **重構**: 確保現有測試通過

## 🎨 UI/UX 貢獻

設計變更請遵循：
- [UI/UX 改善報告](docs/UI-UX-改善報告-完整版.md)
- WCAG 2.1 AA 無障礙標準
- Material Design 3 或 Apple HIG 指南
- 最小觸控目標 44x44px

## 🐛 調試技巧

### 前端

```javascript
// 開發環境調試
if (import.meta.env.DEV) {
  console.log('[DEBUG]', data)
}

// 使用 React DevTools
// Chrome Extension: React Developer Tools
```

### 後端

```python
# settings.py
DEBUG = True

# 使用 Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']

# 使用 pdb 調試
import pdb; pdb.set_trace()
```

## 📞 獲取幫助

遇到問題？
- 查看 [文檔](docs/)
- 搜尋現有 [Issues](https://github.com/alanlin0604/HeartBox/issues)
- 在 Discussions 提問
- 發送郵件到 support@heartbox.tw

## 🙏 致謝

感謝所有貢獻者讓 HeartBox 變得更好！

## 📄 許可證

貢獻到本專案，即表示您同意您的貢獻將以 [MIT 許可證](LICENSE) 授權。
