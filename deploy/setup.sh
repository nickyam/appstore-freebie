#!/usr/bin/env bash
# ============================================================
# setup.sh —— 在阿里云 ECS 上「一次性」完成服务器端部署
# 前置：以 root 或具 sudo 权限的用户运行；ECS 已装 git。
# 作用：
#   1) 调用 sync.sh 克隆/更新静态站到 DEPLOY_DIR
#   2) 注册系统级 cron（每 6 小时自动同步最新 data/*.json，与 GitHub Actions 节奏对齐）
# 仍需你在浏览器里做的（本脚本无法代替）：
#   - 阿里云 DNS 给 appstore.limzero.com 加 A 记录 → ECS 公网 IP
#   - 1Panel 建静态站 appstore.limzero.com + 一键 Let's Encrypt 证书
#   - 把 nginx 配置里的【额外配置片段】粘贴进网站配置
# ============================================================
set -e

# 宿主机真实路径（OpenResty 容器把该目录挂载为容器内 /www/sites/...）
# 注意目录名 index（1Panel 静态网站约定），不是 html
DEPLOY_DIR="/opt/1panel/apps/openresty/openresty/www/sites/appstore.limzero.com/index"
CRON_FILE="/etc/cron.d/freebie-sync"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SYNC_SCRIPT="$SCRIPT_DIR/sync.sh"

# 1) 首次部署 / 立即更新一次
bash "$SYNC_SCRIPT"

# 2) 注册系统级 cron（每 6 小时；确保 ECS 时区为 Asia/Shanghai，否则时间会偏）
echo "30 */6 * * * root bash $SYNC_SCRIPT >> /var/log/freebie-sync.log 2>&1" > "$CRON_FILE"
chmod 644 "$CRON_FILE"
echo "[setup] 已写入系统定时任务：$CRON_FILE"

# 3) 自检时区（仅提示，不阻断）
TZ_NOW=$(date +%Z)
echo "[setup] 当前 ECS 时区：$TZ_NOW（应为 CST/Asia；若为 UTC 请用 timedatectl set-timezone Asia/Shanghai 修正）"
echo "[setup] 完成。后续每 6 小时会自动 git pull 最新站点与限免数据。"
