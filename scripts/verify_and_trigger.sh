#!/usr/bin/env bash
# ============================================================
# verify_and_trigger.sh —— 限免有效性轻量校验 + 按需触发下架（ECS 本地跑）
#
# 目的
# ----
# 主跑批（daily.yml）每 6 小时一轮，GitHub Actions 排队再拖 1~3 小时，
# 而 Apple 的限免促销随时可能结束 —— 全站每天约 24 条限免到期
# （cn ≈8 + us ≈16）。这导致一条已恢复收费的 App 最长可能在网站上
# 多挂 ~9 小时，用户点进去发现要钱，直接伤信任与 SEO。
#
# 本脚本每 2 小时在 ECS 本地跑一次校验：
#   1. 用「站点部署目录里正在对外提供的那份数据」做校验；
#   2. 跑只读校验 scripts/verify_live_freebies.py（实测两区仅 6.6 秒）；
#   3. **只有确有失效条目时**才 dispatch daily.yml 去下架；
#      没有失效 → 什么都不做（不推 main、不消耗 Actions 额度）。
#
# 🔴 数据源的选择（重要，勿改成从 GitHub 拉）
# --------------------------------------------
# 校验的对象必须是「**用户此刻在网站上看到的条目**」，即站点部署目录
# (/opt/1panel/.../appstore.limzero.com/index/data/) 里的 JSON —— 它由
# sync.sh 从仓库同步而来，与线上完全一致。
# 若改为从 GitHub clone 最新 main：
#   ① 大陆 → github.com 链路不稳（实测频繁超时，clone 要等数分钟甚至失败），
#      而校验的目的是「快速发现失效」，链路一慢就失去意义；
#   ② 仓库 main 可能比部署目录更新（还没同步到站点），校验的是
#      「尚未上架给用户」的条目，验错了对象。
# 因此：校验只读本地部署目录 + 本地脚本副本，零 GitHub 依赖；
# 只有真需要下架时，才发一次 GitHub API 请求（失败有重试，且不丢结果，
# 下一轮会再发现一次失效）。
#
# 🔴 只读铁律
# ----------
# 校验脚本（verify_live_freebies.py）**只读**，绝不写 data/ 与 app/。
# 下架动作一律由 daily.yml 里的 generate.py 执行（全站唯一写页人）。
# 本脚本自身也只做「读 + dispatch」，不碰任何站点数据文件。
#
# 依赖
# ----
# · /root/.freebie-github-token（chmod 600，fine-grained PAT，
#   含 repo contents:read + Actions:write）—— 仅 dispatch 时才用
# · python3（ECS 自带 3.10，无需额外依赖，脚本只用标准库）
# · 校验脚本副本：/root/freebie-deploy/verify_live_freebies.py
#   （由部署时从仓库 scripts/ 复制而来；更新脚本需重新复制）
#
# 日志：/var/log/freebie-verify.log
# 手动运行：bash /root/freebie-deploy/verify_and_trigger.sh
# ============================================================
set -u

REPO="nickyam/appstore-freebie"
BRANCH="main"
TOKEN_FILE="/root/.freebie-github-token"
LOG="/var/log/freebie-verify.log"

# 站点部署目录 —— 校验的数据源（用户此刻正在看的那份数据）
DEPLOY_DIR="/opt/1panel/apps/openresty/openresty/www/sites/appstore.limzero.com/index"
DATA_DIR="$DEPLOY_DIR/data"
# 校验脚本副本（与站点分离存放，不放进部署目录，避免被 sync.sh rsync 出去）
VERIFY_SCRIPT="/root/freebie-deploy/verify_live_freebies.py"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"; }

# ---- 1. 前置检查 ----
if [ ! -s "$TOKEN_FILE" ]; then
  log "ERROR: token 文件不存在或为空: $TOKEN_FILE（仅 dispatch 下架时需要）"
  exit 1
fi
if [ ! -f "$VERIFY_SCRIPT" ]; then
  log "SKIP: 校验脚本不存在: $VERIFY_SCRIPT（尚未部署），本轮跳过"
  exit 0
fi
if [ ! -f "$DATA_DIR/free-today-cn.json" ] || [ ! -f "$DATA_DIR/free-today-us.json" ]; then
  log "SKIP: 站点数据不完整（$DATA_DIR 缺 free-today-*.json），本轮跳过"
  exit 0
fi

# ---- 2. 跑只读校验（数据源 = 站点部署目录）----
REPORT="/tmp/freebie-verify-report.json"
rm -f "$REPORT"

# 校验脚本用 --data-dir 指定数据目录；把脚本自身所在目录塞进 PYTHONPATH
# 是为了让脚本能 import 同目录的模块（当前无跨文件依赖，属预留）。
VERIFY_OUT=$(python3 "$VERIFY_SCRIPT" --data-dir "$DATA_DIR" --report "$REPORT" 2>&1)
VERIFY_RC=$?
echo "$VERIFY_OUT" >> "$LOG"

if [ ! -f "$REPORT" ]; then
  log "ERROR: 校验未产出报告（退出码 $VERIFY_RC），本轮放弃"
  exit 1
fi

STALE=$(python3 -c "import json;print(json.load(open('$REPORT'))['total_stale'])" 2>/dev/null)
MISSING=$(python3 -c "import json;print(json.load(open('$REPORT'))['total_missing'])" 2>/dev/null)
STALE="${STALE:-0}"
MISSING="${MISSING:-0}"

log "校验完成：失效 $STALE 条 / 疑似下架 $MISSING 条"

if [ "$STALE" -eq 0 ]; then
  log "无失效条目，无需下架，本轮结束（未推 main、未触发任何 workflow）"
  exit 0
fi

# ---- 3. 确有失效 → dispatch daily.yml 去下架 ----
# 复用 generate.py 既有的「促销粘性」下架逻辑，本脚本不自己改数据。
log "发现 $STALE 条失效条目，触发 daily 跑批下架…"

TOKEN="$(tr -d '[:space:]' < "$TOKEN_FILE")"
WF="daily.yml"
URL="https://api.github.com/repos/${REPO}/actions/workflows/${WF}/dispatches"
for i in 1 2 3; do
  CODE=$(curl -sS -m 20 -o /tmp/dispatch_resp_verify.json -w '%{http_code}' \
    -X POST \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    -d "{\"ref\":\"${BRANCH}\"}" \
    "$URL")
  if [ "$CODE" = "204" ]; then
    log "OK: dispatched ${WF} (尝试 $i, HTTP $CODE)，失效 $STALE 条将下架"
    exit 0
  fi
  log "WARN: dispatch 失败 (尝试 $i, HTTP $CODE): $(head -c 200 /tmp/dispatch_resp_verify.json 2>/dev/null)"
  sleep 15
done
log "ERROR: dispatch 连续 3 次失败，放弃本次（失效 $STALE 条仍在站上，等下一轮或主跑批处理）"
exit 1
