# 国内加速部署：freebie.limzero.com（阿里云 ECS 镜像）

背景：freebie.nickyam.com 走 Cloudflare 免费版，大陆无合规节点，国内访问慢。
本方案把同一套**纯静态**站点到已备案的 limzero.com 子域，国内访客直连阿里云 ECS。

> 合规说明：limzero.com 已在阿里云完成 ICP 备案，子域 freebie.limzero.com 继承备案，
> 且仍跑在同一台阿里云 ECS（同一接入商），无需单独备案或接入备案变更。

## 步骤

### 0. 私有仓库授权（必须，否则 ECS 拉取会 401）
仓库是私有的，ECS 上 `git clone` 需要授权。**推荐方案 1（只读 Deploy Key，无明文 token）**：

方案 1 · 只读 Deploy Key（SSH）：
```bash
# 在 ECS 上执行，生成一对密钥（无密码）
ssh-keygen -t ed25519 -C "freebie-deploy" -N "" -f /root/.ssh/freebie_deploy
# 打印公钥，复制它
cat /root/.ssh/freebie_deploy.pub
```
把上面输出的公钥内容，加到 GitHub 仓库 **Settings → Deploy keys → Add deploy key**：
- Title 随便填（如 `freebie-ecs`）
- Key 粘贴公钥
- **不要**勾选 Allow write access（只读即可）

方案 2 · Personal Access Token（HTTPS，备选）：
生成一个仅 `repo` 读权限的 PAT，在 ECS 上保存：
```bash
echo -n 'ghp_你的PAT' > /root/.freebie-github-token
chmod 600 /root/.freebie-github-token
```
`sync.sh` 检测到该文件会自动改用 HTTPS+PAT 拉取。

> `sync.sh` 默认走 SSH（方案 1），并自动接受 github 主机密钥，cron 里不会卡住。

### 1. DNS
在 limzero.com 的 DNS（阿里云云解析）加一条记录：
- 主机记录：`freebie`
- 记录类型：`A`
- 记录值：你的 ECS 公网 IP
- 线路：默认（国内默认即可；海外仍可走 Cloudflare 的 freebie.nickyam.com）

### 2. 1Panel 建站
- 网站 → 创建「静态网站」，域名填 `freebie.limzero.com`
- 根目录：`/www/sites/freebie.limzero.com/html`（1Panel OpenResty 的站点根在 `/www/sites/<域名>/html`，已挂载进容器）
- SSL：网站设置 → 证书 → 一键申请 Let's Encrypt（免费）
- 配置文件（额外配置）：把 `nginx-freebie.limzero.com.conf` 末尾【额外配置片段】
  里的规则粘贴进去（deny .git + 静态/json 缓存策略）

### 3. 首次部署 + 每日同步（一步到位）
SSH 登录 ECS（root 或 sudo 用户），执行**一次** `setup.sh`：
```bash
bash /path/to/setup.sh
```
它会：克隆仓库到根目录 + 修正 www 权限 + 注册**系统级 cron**（每 6 小时自动 `git pull` 最新站点与数据）。
> 不需要在 1Panel 里单独建计划任务——setup.sh 已用 `/etc/cron.d` 直接挂好。
> 若不想用系统 cron，也可在 1Panel → 计划任务 加 Shell 脚本每天 09:30 跑 `sync.sh`。

GitHub Actions 每 6 小时（北京时间 02/08/14/20 点）重新生成 `data/*.json` 并提交，ECS 每班 :30 拉取，
国内镜像比 Cloudflare 边缘晚约 30 分钟，可接受。

### 5. 验证
- 国内网络访问 `https://freebie.limzero.com`，确认列表/分类/搜索正常；
- 观察一天，确认 09:30 后数据已更新。

## 可选增强
- 在 `freebie.nickyam.com` 首页加一行提示：「国内访问慢？改用 freebie.limzero.com」。
  （若不想要双域名，可后续再加 Cloudflare Worker 按访客国家 302 跳转，见对话记录。）
- 仓库为私有，**必须**先完成「步骤 0」的授权（Deploy Key 或 PAT），否则 ECS 无法克隆。

## 文件说明
- `nginx-freebie.limzero.com.conf`：OpenResty/Nginx 配置（含 1Panel 额外配置片段）
- `sync.sh`：ECS 上拉取最新静态站 + 数据，供 1Panel 计划任务调用
