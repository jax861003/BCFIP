# 优选IP · 原样透传（BCFIP）

统一抓取多个 Cloudflare 优选 IP 上游，**保持上游原生格式**，**零 Secret 开箱即用**，并通过 GitHub Actions 定时更新、自动部署到 Cloudflare Pages。

---

## 📌 项目初衷与最根本的引用来源

本项目所有上游清单与取数思路，最根本的引用来源是：

> **[wanwushequ/cfyxip](https://github.com/wanwushequ/cfyxip)** —— 感谢原作者整理并公开了这份优选 IP 上游聚合。

其中 `cmliu2`（CM 2）与 `Mia`（xinyitang3）两个上游，直接复用该仓库公开的 `cmliu2/all.txt` 与 `xinyitang3/ipv4.txt` 文件；其余上游的探测/接口方式也均受其启发。本仓库是对这份上游清单的「原样透传」复刻，不做改名、不注入品牌、不重编号。

---

## 🔧 原理

### 1. 统一抓取，复刻各上游原取数方式

所有上游由单个脚本 `scripts/fetch_all.py` 抓取，按各上游原本的方式取数，分为三类：

| 类型 | 取数方式 | 涉及上游 |
|---|---|---|
| `raw` | `curl -A Clash` 原样抓取公开地址 | CM、CM 2、Mia |
| `probesub` | workerVless2sub 公开探测（见下） | 洛璃、辣子鸡、Moist_R、辣椒炒肉少放辣、Kristi、周润发、DanFeng、天诚 |
| `api` | 各源各自的公开优选 IP 接口 | CFYes、vvHan、WeTest、麒麟、NiREvil、Gslege、ZhiXuan、S5公益 |

**`probesub` 探测机制**：洛璃（`loli.sub.us.ci`）、辣子鸡（`sub.lzjbaby.com`）等均为 [`cmliu/workerVless2sub`](https://github.com/cmliu/workerVless2sub)（Cloudflare Worker 版 VLESS→订阅转换器）的部署实例。参考 [`cmliu/edgetunnel`](https://github.com/cmliu/edgetunnel) 的「优选订阅生成器」机制，用固定占位参数：

```
https://<host>/sub?host=example.com&uuid=00000000-0000-4000-8000-000000000000
```

触发上游返回其**公开优选 IP 列表**（base64 订阅）。脚本解码后提取 `@` 后的 `IP:端口#备注`—— uuid 仅为占位，真实 IP 与地区/测速备注均为上游原生数据，**无需任何个人订阅 Secret**。

### 2. 保持上游原生格式

- 订阅/探测源：`IP:端口#备注` 一行不改地落地；
- API 源：仅保留上游自身字段（地区 / 运营商）作备注；
- **不注入 `CFYes优选` / `QNAir-LL` 这类项目品牌，也不重新编号。**

### 3. 24 小时时效过滤

某源本次抓取失败、且上一次成功已超过 24 小时，则在合并（`all.txt` / `sources.json`）时剔除；24 小时内的旧数据予以保留，避免单源抖动导致整份订阅缺块。

### 4. 单一工作流 + diff 门控

- 一个 `fetch.yml` 替代「每上游一个 workflow」，GitHub Actions 运行记录不再爆炸；
- 仅在内容真正变化时才 `commit + push`，Cloudflare Pages 不会每次调度都部署 → 从根上避免「部署记录 >100 后删项目要先清记录」的麻烦。

---

## 📡 上游来源与致谢

当前共 **19 个上游**，全部零 Secret 开箱即用。实时活跃状态与条数见站点 `sources.json`。

| # | 名称 | 标识 | 类型 | 数据来源 | 备注 |
|---|---|---|---|---|---|
| 1 | CM | `CM` | raw | `090227.pages.dev/bestcf` | cmliu 的 bestcf 部署 |
| 2 | CM 2 | `CM` | raw | `wanwushequ/cfyxip` 仓库 `cmliu2/all.txt` | 直接复用原项目公开文件 |
| 3 | 洛璃 | `LL` | probesub | `loli.sub.us.ci` | workerVless2sub 部署实例 |
| 4 | 辣子鸡 | `LZ` | probesub | `sub.lzjbaby.com` | workerVless2sub 部署实例 |
| 5 | Mia | `MIA` | raw | `wanwushequ/cfyxip` 仓库 `xinyitang3/ipv4.txt` | 直接复用原项目公开文件 |
| 6 | CFYes | `CFY` | api | CFYes 公开接口 | — |
| 7 | vvHan | `VH` | api | vvHan 公开接口 | — |
| 8 | WeTest | `WT` | api | WeTest 公开接口 | — |
| 9 | 麒麟 | `QL` | api | 麒麟公开接口 | — |
| 10 | NiREvil | `NR` | api | NiREvil 公开接口 | — |
| 11 | Gslege | `GS` | api | Gslege 公开接口 | — |
| 12 | ZhiXuan | `ZX` | api | 智选公开接口 | — |
| 13 | S5公益 | `S5` | api | S5 公开接口 | — |
| 14 | Moist_R | `MR` | probesub | `owo.o00o.ooo` | 订阅生成器 |
| 15 | 辣椒炒肉少放辣 | `CL` | probesub | `sub.xdu.qzz.io` | 订阅生成器 |
| 16 | Kristi | `KR` | probesub | `sub.mot.cloudns.biz` | 订阅生成器 |
| 17 | 周润发 | `ZRF` | probesub | `zrf.zrf.me` | 订阅生成器 |
| 18 | DanFeng | `DF` | probesub | `sub.danfeng.eu.org` | 订阅生成器 |
| 19 | 天诚 | `TC` | probesub | `cm.soso.edu.kg` | 订阅生成器 |

**致谢：**
- 感谢 **[wanwushequ/cfyxip](https://github.com/wanwushequ/cfyxip)** —— 最根本的引用来源，整理并公开了这份优选 IP 上游清单（CM 2、Mia 直接复用其公开文件）。
- 感谢 **[cmliu/workerVless2sub](https://github.com/cmliu/workerVless2sub)** 与 **[cmliu/edgetunnel](https://github.com/cmliu/edgetunnel)** 提供的开源机制，使洛璃、辣子鸡等订阅生成器的公开优选 IP 可被无 Secret 探测。
- 感谢各 API 接口提供方：**CFYes、vvHan、WeTest、麒麟、NiREvil、Gslege、智选（ZhiXuan）、S5公益**。
- 感谢各订阅生成器提供方：**洛璃、辣子鸡、Moist_R、辣椒炒肉少放辣、Kristi、周润发、DanFeng、天诚**。

> 优选 IP 数据版权与可用性归各上游所有；本仓库仅做聚合与格式化展示，不对数据准确性负责。

---

## 📁 目录结构

```
BCFIP/
├── index.html              # 展示页（列出各上游 + 合并订阅，动态读 sources.json）
├── sources.json            # 脚本生成，驱动 UI（含每源活跃状态/更新时间/条数）
├── all.txt                 # 脚本生成，活跃源合并订阅（原样拼接）
├── _headers                # Cloudflare Pages 缓存策略（no-cache）
├── scripts/fetch_all.py    # 统一抓取脚本（19 个上游）
└── .github/workflows/fetch.yml
```

每个上游的数据单独落在 `<源名>/all.txt`，格式即上游原生格式。

---

## 🚀 部署步骤

### 步骤 1：准备 GitHub 仓库

代码需托管在 GitHub 仓库（本项目已发布于 `jax861003/BCFIP`）。若为从零自建：

```bash
git init -b main
git add -A
git commit -m "init: 优选IP原样透传"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

> 无需配置任何 Secret，19 个上游开箱即用。

### 步骤 2：（可选）本地生成首批数据并预览

Cloudflare 首次部署会直接用仓库内的 `sources.json` / `all.txt`。如需本地先跑一遍：

```bash
cd BCFIP
python -m venv .venv
.venv/Scripts/activate          # Windows；macOS/Linux 用 source .venv/bin/activate
pip install requests cloudscraper
python scripts/fetch_all.py
```

本地预览（**必须走 http server，不能 file:// 双击**，`fetch` 跨域会被拦）：

```bash
python -m http.server 8137
# 浏览器打开 http://127.0.0.1:8137/
```

### 步骤 3：Cloudflare Pages 连接 Git 部署

1. Cloudflare 控制台 → **Workers & Pages → Create → Pages → Connect to Git**。
2. 授权 GitHub，选择本仓库（`jax861003/BCFIP`）。
3. 构建配置：
   - **Framework preset**：`None`
   - **Build command**：留空
   - **Output directory（输出目录）**：`.`（点号，因为 `index.html` / `sources.json` / `all.txt` 都在仓库根）
4. 点击 **Save and Deploy**。首次基于当前 `main` 分支直接上线，页面立即可见。

> **必须用「连接 Git 仓库」（Git 集成），不要用 Direct Upload。** 只有 Git 集成时，GitHub 工作流 push 数据才会触发 Cloudflare 自动部署；Direct Upload 每次重传会丢失 diff 门控。

### 步骤 4：定时自动更新

仓库内 `.github/workflows/fetch.yml` 已配置：

- **定时**：每 6 小时一次（`cron '21 */6 * * *'`）；
- **手动**：GitHub → Actions → fetch → **Run workflow** 可随时触发；
- **门控**：仅在抓取结果相对上次有变化时才 `commit + push`，Cloudflare 随之自动重新部署；无变化则跳过，不产生部署记录。

推送权限由 workflow 内的 `permissions: contents: write` 保证，使用内置 `GITHUB_TOKEN`，无需额外配置。

### 步骤 5：（可选）用个人订阅覆盖

若你拥有洛璃 / 辣子鸡等上游的**个人订阅链接**，可在仓库 **Settings → Secrets and variables → Actions** 配置同名 Secret，脚本会原样透传覆盖公开探测结果；不配置则走公开路径。

| Secret 名 | 对应上游 | 作用 |
|---|---|---|
| `LUOLI_URL` | 洛璃 | 可选，覆盖公开探测 |
| `LZJ_URL` | 辣子鸡 | 可选，覆盖公开探测 |
| `CMLIU_URL` / `CMLIU2_URL` / `XINYITANG3_URL` | CM / CM 2 / Mia | 可选，覆盖内嵌公开地址 |

---

## ⚠️ 注意事项

- **国内 API 源偶发超时**：CI 直连国内接口可能因网络抖动超时，靠 24h 时效过滤保留旧数据；个别源某次显示「剔除」属正常，下次成功即恢复。
- **数据可用性取决于上游**：任一上游停服或改接口，对应源会自动失效并被时效过滤剔除，不影响其余源。
- **`_headers` 已设 `no-cache`**：保证访客拿到的是最新合并订阅。
