#!/usr/bin/env bash
# ============================================================
# sync.sh —— 阿里云 ECS 上拉取最新静态站（含每日生成的 data/*.json）
# 用法：
#   首次： bash /path/to/sync.sh
#   日常： setup.sh 已注册系统 cron，每日 09:30 自动跑
#
# 仓库为【私有】时的授权（二选一，推荐方案 1）：
#   方案 1 · 只读 Deploy Key（SSH，无明文 token）：
#     在 ECS 执行： ssh-keygen -t ed25519 -C "freebie-deploy" -N "" -f /root/.ssh/freebie_deploy
#     把 /root/.ssh/freebie_deploy.pub 的内容，加到 GitHub 仓库
#     Settings → Deploy keys（勾选 Allow write? 不勾，只读即可）。
#     本脚本默认用 SSH 地址拉取，并自动接受 github 主机密钥。
#   方案 2 · Personal Access Token（HTTPS）：
#     生成一个仅 repo 读权限的 PAT，写入 /root/.freebie-github-token（chmod 600），
#     脚本检测到该文件会自动拼成 https 地址。
# ============================================================
set -e

REPO_SSH="git@github.com:nickyam/appstore-freebie.git"
DEPLOY_DIR="/www/sites/freebie.limzero.com/html"
BRANCH="main"
TOKEN_FILE="/root/.freebie-github-token"
DEPLOY_KEY="${DEPLOY_KEY:-}"   # 可选：指定部署私钥路径（如 /root/.ssh/freebie_deploy）

# 首次 SSH 连接自动信任 github 主机密钥（避免 cron 非交互时卡住）
if [ -n "$DEPLOY_KEY" ]; then
  export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
else
  export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
fi

if [ -f "$TOKEN_FILE" ]; then
  TOKEN="$(cat "$TOKEN_FILE" | tr -d '[:space:]')"
  REPO_URL="https://${TOKEN}@github.com/nickyam/appstore-freebie.git"
  AUTH="HTTPS+PAT"
else
  REPO_URL="$REPO_SSH"
  AUTH="SSH(deploy-key)"
fi

mkdir -p "$DEPLOY_DIR"

if [ ! -d "$DEPLOY_DIR/.git" ]; then
  echo "[sync] 首次克隆（${AUTH}）…"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
else
  echo "[sync] 拉取最新（${AUTH}）…"
  cd "$DEPLOY_DIR"
  git remote set-url origin "$REPO_URL" 2>/dev/null || true
  git fetch --depth 1 origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
  git clean -fd data/   # 清掉本地可能残留的未跟踪数据文件
fi

# 1Panel 默认以 www 用户运行站点，修正权限避免 403
chown -R www:www "$DEPLOY_DIR" 2>/dev/null || true

echo "[sync] 完成，时间：$(date '+%Y-%m-%d %H:%M:%S')"
