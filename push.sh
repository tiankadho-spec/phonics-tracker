#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "🔄 推送代码到 GitHub..."
echo "提示：如果不知道 token，请访问 https://github.com/settings/tokens/new 重新生成"
echo "      权限只需要勾选 'repo' 即可"
read -s -p "🔐 请输入 GitHub Personal Access Token: " TOKEN
echo ""

REMOTE="https://tiankadho-spec:${TOKEN}@github.com/tiankadho-spec/phonics-tracker.git"
git push "$REMOTE" master

echo "✅ 推送成功！"
echo "⚠️  安全提示：推送完成后请到 GitHub 删除这个 token（Settings -> Developer settings -> Personal access tokens）"
