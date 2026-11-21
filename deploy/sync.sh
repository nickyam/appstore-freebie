#!/usr/bin/env bash
# ============================================================
# sync.sh —— 阿里云 ECS 上同步 appstore-freebie 静态站
# 用法：
#   首次： bash /path/to/sync.sh
#   日常： setup.sh 已注册系统 cron（/etc/cron.d/freebie-sync，30 */2 → 每 2 小时 :30）自动跑
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
# 因此容器内 /www/sites/appstore.limzero.com/index 对应的宿主机路径就是下面这个。
# 注意目录名是 index（1Panel 静态网站约定），不是默认的 html。
DEPLOY_DIR="/opt/1panel/apps/openresty/openresty/www/sites/appstore.limzero.com/index"
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
# 大陆 ECS → github.com:443 偶发不可达（2026-10-26 22:30 之后连续两班握手超时、
# HTTP2 framing error），单次失败会让镜像站掉队整整一个班（2 小时），用户在
# appstore.limzero.com 上看到的还是旧页面/旧资源戳。
# 故改成「重试 + 协议降级」：前两次走默认 HTTP/2（快），之后降级 HTTP/1.1
# （跨境链路上 curl 16 / GnuTLS framing 错误的常见解法），并加低速超时保护；
# 全部失败则保留上一版内容退出 —— 宁可旧，也不能半新半旧（资源戳与 assets 不一致）。
pull_repo() {
  local attempt httpopt backoff
  for attempt in 1 2 3 4; do
    if [ "$attempt" -le 2 ]; then httpopt=""; else httpopt="-c http.version=HTTP/1.1"; fi
    if [ ! -d "$REPO_TMP/.git" ]; then
      echo "[sync] 首次克隆内容源（${AUTH}）… 第 ${attempt} 次"
      rm -rf "$REPO_TMP"
      if git $httpopt -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=60 \
           clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$REPO_TMP"; then
        return 0
      fi
    else
      echo "[sync] 拉取最新内容源（${AUTH}）… 第 ${attempt} 次"
      if (
        cd "$REPO_TMP" || exit 1
        git remote set-url origin "$REPO_URL" 2>/dev/null || true
        git $httpopt -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=60 \
          fetch --depth 1 origin "$BRANCH" &&
        git reset --hard "origin/$BRANCH" > /dev/null &&
        git clean -fd data/ > /dev/null 2>&1
      ); then
        return 0
      fi
    fi
    case "$attempt" in 1) backoff=15;; 2) backoff=30;; *) backoff=60;; esac
    echo "[sync] GitHub 不可达，${backoff}s 后重试…"
    sleep "$backoff"
  done
  return 1
}

if ! pull_repo; then
  echo "[sync] ⚠️ GitHub 连续 4 次不可达，本班放弃；站点保留上一版完整内容: $(date '+%Y-%m-%d %H:%M:%S')"
  exit 1
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
#
# 🔴 内部状态文件不上线（2026-11-21）：
#   data/iap-history-*.json（cn 10MB + us 8.6MB）纯属内部台账（含播种心跳、
#   错误串、逐 IAP 变价史），前端从不 fetch（app.js 只取 free-today /
#   iap-free / iap-current-free），verify_live_freebies.py 也不读它。
#   排除后：ECS 磁盘少 18MB、rsync 少搬 18MB、也避免
#   /data/iap-history-us.json 被公网直接下载。
#   CF Pages 侧对应的是「构建命令 rm -f data/history-* data/iap-history-*」，
#   CF 上两份都可删；但 ECS **只能删 iap-history**，原因见下。
#
# 🔴 data/history-*.json 必须留在部署目录 —— 不要"顺手"排除！
#   scripts/verify_live_freebies.py 读它取「历史最高价 mx」判定特价失效
#   （max_price_of）；文件缺失时它返回 None 并 continue，**不报错**，
#   结果是特价失效检测被静默关闭（每轮 verify 都变瞎子，还看不出来）。
#   将来若要一并排除，必须先把 verify 的 history 源改指向内容源缓存
#   /root/.freebie-repo-cache/data（那里有完整 history），再动 rsync。
#
#   data/.* —— data 下的点文件（如 .seed_iap_apprcn_manifest.json）全是 Actions
#   内部台账，前端不读；一条通配覆盖，免得以后每加一个点文件就要补一条 exclude。
#
# ⚠️ 本文件的权威版在仓库，ECS 上跑的是 /root/freebie-deploy/sync.sh（手工副本）。
#   改完必须手动同步过去，否则只在仓库里"看起来改了"（2026-11-21 踩过：
#   仓库版曾丢失 pull_repo 重试逻辑，与 ECS 版分叉；ECS 版又多出 preview.html 排除）。
#   合并时以两边并集为准，勿单方向覆盖。
rsync -a --delete --delete-excluded \
  --exclude '.git' \
  --exclude '.gitignore' \
  --exclude '.github' \
  --exclude 'scripts' \
  --exclude 'deploy' \
  --exclude 'README.md' \
  --exclude 'preview.html' \
  --exclude 'AGENTS.md' \
  --exclude 'data/iap-history-cn.json' \
  --exclude 'data/iap-history-us.json' \
  --exclude 'data/.*' \
  "$REPO_TMP/" "$DEPLOY_DIR/"

# ---- 4. 修正权限（1Panel / 容器内以 www 读取）----
chown -R www:www "$DEPLOY_DIR" 2>/dev/null || true

echo "[sync] 完成，时间：$(date '+%Y-%m-%d %H:%M:%S')"