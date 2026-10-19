#!/usr/bin/env bash
# ============================================================
# sync.sh —— 阿里云 ECS 上拉取最新静态站（含每日生成的 data/*.json）
# 用法：
#   首次： bash /path/to/sync.sh
#   日常： 在 1Panel → 计划任务 → Shell 脚本，每天 09:30 跑一次（等 GitHub Actions 09:00 跑完）
# 前置： ECS 已装 git；若仓库为私有，REPO_URL 需换成带 token 的地址。
# ============================================================
set -e

REPO_URL="https://github.com/nickyam/appstore-freebie.git"
DEPLOY_DIR="/www/wwwroot/freebie.limzero.com"
BRANCH="main"

mkdir -p "$DEPLOY_DIR"

if [ ! -d "$DEPLOY_DIR/.git" ]; then
  echo "[sync] 首次克隆仓库…"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
else
  echo "[sync] 拉取最新提交（浅克隆，避免历史堆积）…"
  cd "$DEPLOY_DIR"
  git fetch --depth 1 origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
  git clean -fd data/   # 清掉本地可能残留的未跟踪数据文件
fi

# 1Panel 默认以 www 用户运行站点，修正权限避免 403
chown -R www:www "$DEPLOY_DIR" 2>/dev/null || true

echo "[sync] 完成，时间：$(date '+%Y-%m-%d %H:%M:%S')"
