📌 项目初衷与最根本的引用来源

本项目所有上游清单与取数思路，最根本的引用来源是：

> **[wanwushequ/cfyxip](https://github.com/wanwushequ/cfyxip)** —— 感谢原作者整理并公开了这份优选 IP 上游聚合。

---

## 🔧 原理

### 1. 统一抓取，复刻各上游原取数方式

所有上游由单个脚本 `scripts/fetch_all.py` 抓取，按各上游原本的方式取数，分为三类：

| 类型         | 取数方式                                                                   | 涉及上游                                              |
| ---------- | ---------------------------------------------------------------------- | ------------------------------------------------- |
| `raw`      | 原样抓取公开地址                                                               | CM、CM 2、Mia                                       |
| `probesub` | [`cmliu/edgetunnel`](https://github.com/cmliu/edgetunnel) 的「优选订阅生成器」机制 | 洛璃、辣子鸡、Moist_R、辣椒炒肉少放辣、Kristi、周润发、DanFeng、天诚      |
| `api`      | 各源各自的公开优选 IP 接口                                                        | CFYes、vvHan、WeTest、麒麟、NiREvil、Gslege、ZhiXuan、S5公益 |

### 2. 统一格式输出（QNAir）

所有上游抓到的节点，统一重写为固定格式，便于直接订阅与区分来源：

```
IP:PORT#QNAir丨归属地（未知归属地则显示运营商）丨上游标识丨序号（001 起）
```

- `归属地`：优先从上游备注/接口解析地区；解析不到则回退显示**运营商**；两者皆无则显示「未知」；
- `上游标识`：各源的代码（如 `LL` / `LZ` / `CM` / `CFY`）；
- `序号`：每个上游内从 `001` 开始递增，便于按源定位。

### 3. 24 小时时效过滤

某源本次抓取失败、且上一次成功已超过 24 小时，则在合并（`all.txt` / `sources.json`）时剔除；24 小时内的旧数据予以保留，避免单源抖动导致整份订阅缺块。

### 4. 单一工作流 + diff 门控

- 一个 `fetch.yml` 替代「每上游一个 workflow」，GitHub Actions 运行记录不再爆炸；
- 仅在内容真正变化时才 `commit + push`，Cloudflare 不会每次调度都部署。

---

## 📡 上游来源与致谢

当前共 **19 个上游**，全部零 Secret 开箱即用。实时活跃状态与条数见站点 `sources.json`。

| #  | 名称      | 标识    | 类型       |
| -- | ------- | ----- | -------- |
| 1  | CM      | `CM`  | raw      |
| 2  | CM 2    | `CM`  | raw      |
| 3  | 洛璃      | `LL`  | probesub |
| 4  | 辣子鸡     | `LZ`  | probesub |
| 5  | Mia     | `MIA` | raw      |
| 6  | CFYes   | `CFY` | api      |
| 7  | vvHan   | `VH`  | api      |
| 8  | WeTest  | `WT`  | api      |
| 9  | 麒麟      | `QL`  | api      |
| 10 | NiREvil | `NR`  | api      |
| 11 | Gslege  | `GS`  | api      |
| 12 | ZhiXuan | `ZX`  | api      |
| 13 | S5公益    | `S5`  | api      |
| 14 | Moist_R | `MR`  | probesub |
| 15 | 辣椒炒肉少放辣 | `CL`  | probesub |
| 16 | Kristi  | `KR`  | probesub |
| 17 | 周润发     | `ZRF` | probesub |
| 18 | DanFeng | `DF`  | probesub |
| 19 | 天诚      | `TC`  | probesub |

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
├── all.txt                 # 脚本生成，活跃源合并订阅（统一格式拼接）
├── _headers                # Cloudflare Pages 缓存策略（no-cache）
├── scripts/fetch_all.py    # 统一抓取脚本（19 个上游）
└── .github/workflows/fetch.yml
```

每个上游的数据单独落在 `<源名>/all.txt`，格式即上游原生格式。

---

## 🚀 部署步骤

### 步骤 1：Fork 本仓库

1. 点击仓库右上角 **Fork**，将本项目复制到你的 GitHub 账号。
2. 进入你 Fork 仓库的 **Actions** 标签页，启用 `fetch` 工作流（Fork 后默认禁用），并点击 **Run workflow** 手动跑一次，生成首批 `sources.json` / `all.txt`。

### 步骤 2：Cloudflare Pages 连接 Git 部署

1. Cloudflare 控制台 → **Workers & Pages → Create → Pages → Connect to Git**。
2. 授权 GitHub，选择你 **Fork 后的仓库**。
3. 构建配置：
   - **Framework preset**：`None`
   - **Build command**：留空
   - **Output directory（输出目录）**：`.`（点号，因为 `index.html` / `sources.json` / `all.txt` 都在仓库根）
4. 点击 **Save and Deploy**。首次基于当前 `main` 分支直接上线，页面立即可见。

> **必须用「连接 Git 仓库」（Git 集成），不要用 Direct Upload。** 只有 Git 集成时，GitHub 工作流 push 数据才会触发 Cloudflare 自动部署；Direct Upload 每次重传会丢失 diff 门控。

### 步骤 3：定时自动更新

仓库内 `.github/workflows/fetch.yml` 已配置：

- **定时**：每 6 小时一次（`cron '21 */6 * * *'`）；
- **手动**：GitHub → Actions → fetch → **Run workflow** 可随时触发；
- **门控**：仅在抓取结果相对上次有变化时才 `commit + push`，Cloudflare 随之自动重新部署；无变化则跳过，不产生部署记录。

推送权限由 workflow 内的 `permissions: contents: write` 保证，使用内置 `GITHUB_TOKEN`，无需额外配置。

---

## ⚠️ 注意事项

- **国内 API 源偶发超时**：CI 直连国内接口可能因网络抖动超时，靠 24h 时效过滤保留旧数据；个别源某次显示「剔除」属正常，下次成功即恢复。
- **数据可用性取决于上游**：任一上游停服或改接口，对应源会自动失效并被时效过滤剔除，不影响其余源。
- **`_headers` 已设 `no-cache`**：保证访客拿到的是最新合并订阅。
