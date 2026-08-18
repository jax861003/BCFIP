# Cloudflare 优选IP

一个专注于 **Cloudflare 优选IP / BestIP** 的独立页面，内容与线上 bestcf.pages.dev 的「优选IP BestIP」区块一致（42 张卡片），数据由 GitHub Actions **每 6 小时定时自动更新**，部署于 Cloudflare Pages。

## 功能

- 完整复刻「优选IP BestIP」板块：WeTest / UOUIN / Mia / LuoLi / CFYes / 天诚1-3 / S5公益 / Gslege / MJZ / ZhiXuan / vvHan / NiREvil / MingYu / Yuanxiawan / CM1-3 / Laziji / Lajiao / MoistR / Kristi / Joname / Senflare / 碧海 / SUB订阅合集 / 随机优选 等
- 交互组件：按地区随机优选（下拉选择地区/数量）、按运营商随机优选、按网段随机优选、SUB优选订阅合集
- 每个来源提供 txt 订阅链接（通用格式 `IP:端口#备注`），复制按钮自动补全当前域名
- 数据文件通过 `.github/workflows/*.yml` 定时抓取上游数据源，内容有变化才提交，避免无谓的 commit

## 目录结构

```
BestCF-IP/
├── index.html              # 独立优选IP页面（42卡片）
├── _headers                # 禁止 txt/html 缓存
├── favicon.svg
├── .github/workflows/      # 23个定时抓取工作流（每6小时，错峰执行）
├── cfyes/                  # CFYes 优选
├── cmliu/  cmliu2/         # CMLiu 优选
├── entryip/                # Anycast Entry IP（静态维护）
├── gslege/                 # Gslege 优选（github.com/gslege/CloudflareIP）
├── ircf/  kristi/  lajiao/  luoli/  lzj/  moistr/  uouin/  yutian/
├── nirevil/                # NiREvil 优选
├── random-region/          # 按地区随机优选数据（list/mix/各国家各数量）
├── s5gy/                   # S5公益 优选
├── tiancheng/  tiancheng2/  tiancheng3/   # 天诚 1/2/3
├── vvhan/                  # vvHan 优选
├── WARP/                   # WARP 通用线路（静态维护）
├── wetest/  xinyitang3/  zhixuanwang/
├── CIDR/                   # CF 网段库（静态维护）
└── tools/                  # CIDR 工具 / CIDR转IP / Colo查询
```

## 部署到 Cloudflare Pages

1. **上传到 GitHub**：新建仓库，推送本项目，确认 `.github/workflows/` 下 23 个工作流已生效（Actions 页面可见）
2. **连接 Pages**：Cloudflare 控制台 → Workers 和 Pages → Create → Pages → Connect to Git → 选择该仓库
3. **构建设置**（本项目无构建步骤）：
   - Framework preset: 选择 **None**（纯静态）
   - Build command: 留空
   - Build output directory: 留空（或 `/`）
4. 保存后首次自动部署，页面和订阅链接立即可用

## 定时更新说明

- 每个来源一个 workflow，触发方式：`schedule` cron（每 6 小时，错峰分钟避免冲突）+ `workflow_dispatch`（可手动触发）
- 工作流抓取 → 与仓库旧文件比对 → **有变化才 commit+push** → Pages 自动重新部署
- 也可在 Actions 页手动点 **Run workflow** 立即刷新
- `entryip/` 与 `WARP/` 为手工维护数据，无对应工作流
- 注意：GitHub 对 60 天无活动的仓库会暂停定时任务，保持仓库活跃即可

## 需要的 Secrets

以下来源的上游订阅地址是私有的（不公开在代码里），工作流通过 GitHub Secrets 读取。**未配置时对应工作流会自动跳过（不会污染数据），仓库内的初始数据仍然可用；配置后即恢复自动更新。**

| Secret | 对应来源 |
| --- | --- |
| `CMLIU_URL` | cmliu |
| `CMLIU2_URL` | cmliu2 |
| `KRISTI_URL` | kristi |
| `LAJIAO_URL` | lajiao |
| `LUOLI_URL` | luoli |
| `LZJ_URL` | lzj |
| `MOISTR_URL` | moistr |
| `PROXY_URL` | random-region（按地区随机优选） |
| `S5GY_URL` | s5gy-cf |
| `XINYITANG3_URL` | xinyitang3（Mia） |
| `YUTIAN_URL` | yutian |

配置方法：仓库 Settings → Secrets and variables → Actions → New repository secret，名称与上表一致，值为对应订阅链接。

无需 Secrets 即可自动更新的来源：cfyes、gslege、ircf、nirevil、s5gy、tiancheng1/2/3、uouin、vvhan、wetest、zhixuanwang。

## 数据源说明

上游数据均来自公开渠道，页面与数据文件仅供学习研究，请遵守相关服务条款与当地法律。