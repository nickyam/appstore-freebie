#!/usr/bin/env bash
# ============================================================
# sync.sh —— 阿里云 ECS 上同步 appstore-freebie 静态站
# 用法：
#   首次： bash /path/to/sync.sh
#   日常： setup.sh 已注册系统 cron，每日 09:30 自动跑
#
# 【重要】同步方式说明：
#   早期版本用 git clone 直接到站点根目录，导致 .git / scripts / deploy /
#   .github / README.md 这些开发文件也暴露在公网上（README.md 可直接访问，
#   会泄露部署路径等信息）。现改为 rsync 方式：仓库只作为「内容源」放在
#   /root/.freebie-repo-cache，站点根目录只保留网站真正需要的文件：
#     index.html / about.html / assets/ / data/ / robots.txt / sitemap.xml
#   源码与部署脚本不再上线。
#
# 仓库为【私有】时的授权（二选一，推荐方案 1）：
#   方案 1 · 只读 Deploy Key（SSH，无明文token）：
#     在 ECS 执行： ssh-keygen -t ed25519 -C "freebie-deploy" -N "" -f /root/.ssh/freebie_deploy
#     把 /root/.ssh/freebie_deploy.pub 的内容，加到 GitHub 仓库
#     Settings → Deploy keys（只读即可，不要勾 Allow write）。
#     本脚本默认用 SSH 地址拉取，并自动接受 github 主机密钥。
#   方案 2 · Personal Access Token（HTTPS）：
#     生成一个仅 repo 读权限的 PAT，写入 /root/.freebie-github-token（chmod 600），
#     脚本检测到该文件会自动拼成 https 地址。
# ============================================================
set -e

REPO_SSH="git@github.com:nickyam/appstore-freebie.git"
# 注意：本脚本运行在 ECS 宿主机上，必须写【宿主机真实路径】。
# OpenResty 容器把宿主机 .../www 挂载为容器内 /www，
# 因此容器内 /www/sites/freebie.limzero.com/index 对应的宿主机路径就是下面这个。
# 注意目录名是 index（1Panel 静态网站约定），不是默认的 html。
DEPLOY_DIR="/opt/1panel/apps/openresty/openresty/www/sites/freebie.limzero.com/index"
BRANCH="main"
# 仓库在本地的临时克隆目录（只作内容源，不对外提供）
REPO_TMP="/root/.freebie-repo-cache"

TOKEN_FILE="/root/.freebie-github-token"
DEPLOY_KEY="${DEPLOY_KEY:-}"   # 可选：指定部署私钥路径（如 /root/.ssh/freebie_deploy）
# 若未显式传入 DEPLOY_KEY，但本机存在部署私钥则自动启用（保证 cron 也能用）
if [ -z "$DEPLOY_KEY" ] && [ -f /root/.ssh/freebie_deploy ]; then
  DEPLOY_KEY="/root/.ssh/freebie_deploy"
fi

# ---- 1. 首次 SSH 连接自动信任 github 主机密钥（避免 cron 非交互时卡住）----
if [ -n "$DEPLOY_KEY" ]; then
  export GIT_SSH_COMMAND="ssh -i $DEPLOY_KEY -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
else
  export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new -o BatchMode=yes"
fi

if [ -f "$TOKEN_FILE" ]; then
  TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"
  REPO_URL="https://${TOKEN}@github.com/nickyam/appstore-freebie.git"
  AUTH="HTTPS+PAT"
else
  REPO_URL="$REPO_SSH"
  AUTH="SSH(deploy-key)"
fi

mkdir -p "$DEPLOY_DIR" "$REPO_TMP"

# ---- 2. 拉取 / 更新内容源 ----
if [ ! -d "$REPO_TMP/.git" ]; then
  echo "[sync] 首次克隆内容源（${AUTH}）…"
  rm -rf "$REPO_TMP"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$REPO_TMP"
else
  echo "[sync] 拉取最新内容源（${AUTH}）…"
  cd "$REPO_TMP"
  git remote set-url origin "$REPO_URL" 2>/dev/null || true
  git fetch --depth 1 origin "$BRANCH"
  git reset --hard "origin/$BRANCH" > /dev/null
  git clean -fd data/ > /dev/null 2>&1 || true
fi

# ---- 3. rsync 只同步「网站真正需要的文件」到站点根目录 ----
# 加 --delete 会顺手清掉站点根目录下多余的文件，正好清掉历史遗留的
# .git / scripts / deploy / .github / README.md。
if ! command -v rsync > /dev/null 2>&1; then
  echo "[sync] 未检测到 rsync，尝试安装…"
  yum install -y rsync > /dev/null 2>&1 || apt-get install -y rsync > /dev/null 2>&1 || true
fi

echo "[sync] 同步网站文件到站点根目录…"
# --delete-excluded：把目标端那些「被 exclude 排除」的文件也一并删掉。
#   仅用 --delete 不会删除被排除的文件，所以必须加 --delete-excluded，
#   才能真正清掉站点根目录里历史遗留的 .git / scripts / deploy /
#   .github / README.md（早期 git clone 到站点根目录留下的）。
rsync -a --delete --delete-excluded \
  --exclude '.git' \
  --exclude '.gitignore' \
  --exclude '.github' \
  --exclude 'scripts' \
  --exclude 'deploy' \
  --exclude 'README.md' \
  "$REPO_TMP/" "$DEPLOY_DIR/"

# ---- 4. 修正权限（1Panel / 容器内以 www 读取）----
chown -R www:www "$DEPLOY_DIR" 2>/dev/null || true

echo "[sync] 完成，时间：$(date '+%Y-%m-%d %H:%M:%S')"