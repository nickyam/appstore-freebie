# 国内加速部署：freebie.limzero.com（阿里云 ECS 镜像）

背景：freebie.nickyam.com 走 Cloudflare 免费版，大陆无合规节点，国内访问慢。
本方案把同一套**纯静态**站点到已备案的 limzero.com 子域，国内访客直连阿里云 ECS。

> 合规说明：limzero.com 已在阿里云完成 ICP 备案，子域 freebie.limzero.com 继承备案，
> 且仍跑在同一台阿里云 ECS（同一接入商），无需单独备案或接入备案变更。

## 步骤

### 1. DNS
在 limzero.com 的 DNS（阿里云云解析）加一条记录：
- 主机记录：`freebie`
- 记录类型：`A`
- 记录值：你的 ECS 公网 IP
- 线路：默认（国内默认即可；海外仍可走 Cloudflare 的 freebie.nickyam.com）

### 2. 1Panel 建站
- 网站 → 创建「静态网站」，域名填 `freebie.limzero.com`
- 根目录：`/www/wwwroot/freebie.limzero.com`
- SSL：网站设置 → 证书 → 一键申请 Let's Encrypt（免费）
- 配置文件（额外配置）：把 `nginx-freebie.limzero.com.conf` 末尾【额外配置片段】
  里的规则粘贴进去（deny .git + 静态/json 缓存策略）

### 3. 首次部署
SSH 登录 ECS，执行：
```bash
bash /path/to/sync.sh
```
脚本会 clone 仓库到根目录。

### 4. 每日同步（关键）
GitHub Actions 每天 09:00（北京时间）重新生成 `data/*.json` 并提交。
在 1Panel → 计划任务 → 添加「Shell 脚本」任务，每天 **09:30** 跑一次：
```bash
bash /path/to/sync.sh
```
这样国内镜像每天自动拿到最新限免数据，比 Cloudflare 边缘晚约 30 分钟，可接受。

### 5. 验证
- 国内网络访问 `https://freebie.limzero.com`，确认列表/分类/搜索正常；
- 观察一天，确认 09:30 后数据已更新。

## 可选增强
- 在 `freebie.nickyam.com` 首页加一行提示：「国内访问慢？改用 freebie.limzero.com」。
  （若不想要双域名，可后续再加 Cloudflare Worker 按访客国家 302 跳转，见对话记录。）
- 若仓库设为私有，`sync.sh` 里的 `REPO_URL` 需改为带 PAT 的地址
  （如 `https://<token>@github.com/nickyam/appstore-freebie.git`）。

## 文件说明
- `nginx-freebie.limzero.com.conf`：OpenResty/Nginx 配置（含 1Panel 额外配置片段）
- `sync.sh`：ECS 上拉取最新静态站 + 数据，供 1Panel 计划任务调用
