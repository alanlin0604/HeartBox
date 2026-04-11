#!/bin/bash
# HeartBox 空白頁問題診斷腳本
# 使用方法: bash debug-blank-page.sh

echo "🔍 HeartBox 空白頁問題診斷"
echo "================================"
echo ""

# 顏色定義
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試結果數組
declare -a results

# 測試函數
test_component() {
    local name=$1
    local file=$2

    echo -e "${YELLOW}測試: $name${NC}"

    # 恢復文件
    git show 3ffc86f:frontend/$file > $file 2>/dev/null

    if [ $? -eq 0 ]; then
        # 嘗試建置
        npm run build > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ $name - 建置成功${NC}"
            results+=("✓ $name")
            return 0
        else
            echo -e "${RED}✗ $name - 建置失敗${NC}"
            results+=("✗ $name - BUILD FAILED")
            return 1
        fi
    else
        echo -e "${YELLOW}⚠ $name - 文件不存在於優化提交中${NC}"
        results+=("⚠ $name - NOT IN COMMIT")
        return 2
    fi
}

# 恢復到安全狀態
echo "📦 恢復到安全狀態..."
git checkout main > /dev/null 2>&1
git checkout test/performance-debug > /dev/null 2>&1 || git checkout -b test/performance-debug
git reset --hard 23f5dd4 > /dev/null 2>&1
echo ""

# 測試 1: index.css
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 1: 核心樣式文件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_component "index.css" "src/index.css"
echo ""

# 測試 2: 主要配置文件
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 2: 配置文件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_component "vite.config.js" "vite.config.js"
test_component "index.html" "index.html"
test_component "Service Worker" "public/sw.js"
echo ""

# 測試 3: 新增元件
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 3: 新增元件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_component "VirtualList" "src/components/VirtualList.jsx"
test_component "ResponsiveChart" "src/components/ResponsiveChart.jsx"
test_component "OptimizedImage" "src/components/OptimizedImage.jsx"
test_component "PageTransition" "src/components/PageTransition.jsx"
echo ""

# 測試 4: 工具函數
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 4: 工具函數"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_component "haptics" "src/utils/haptics.js"
test_component "deepLinking" "src/utils/deepLinking.js"
test_component "useFormValidation" "src/hooks/useFormValidation.js"
echo ""

# 測試 5: 修改的元件
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Phase 5: 修改的核心元件"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
test_component "Layout.jsx" "src/components/Layout.jsx"
test_component "DashboardPage.jsx" "src/pages/DashboardPage.jsx"
test_component "ConfirmModal.jsx" "src/components/ConfirmModal.jsx"
test_component "SkeletonCard.jsx" "src/components/SkeletonCard.jsx"
echo ""

# 總結
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 測試總結"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

success_count=0
fail_count=0
skip_count=0

for result in "${results[@]}"; do
    if [[ $result == ✓* ]]; then
        echo -e "${GREEN}$result${NC}"
        ((success_count++))
    elif [[ $result == ✗* ]]; then
        echo -e "${RED}$result${NC}"
        ((fail_count++))
    else
        echo -e "${YELLOW}$result${NC}"
        ((skip_count++))
    fi
done

echo ""
echo "總計: $success_count 成功, $fail_count 失敗, $skip_count 跳過"
echo ""

if [ $fail_count -gt 0 ]; then
    echo -e "${RED}⚠ 發現 $fail_count 個問題文件！${NC}"
    echo "建議檢查上述標記為 ✗ 的文件"
else
    echo -e "${GREEN}✓ 所有測試文件建置成功${NC}"
    echo "問題可能出在多個文件的組合或執行時錯誤"
    echo "建議: 啟動開發伺服器手動測試"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "下一步建議:"
echo "1. 檢查失敗的文件"
echo "2. npm run dev 啟動開發伺服器測試"
echo "3. 查看瀏覽器 Console 錯誤訊息"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
