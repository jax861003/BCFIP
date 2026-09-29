# 优选IP · 原样（4.原样优选）

在 `1.cfyxip`（原版）/ `2.BestCF` / `3.QNAir` 基础上重做的**统一抓取版**：

- **复刻原项目的取数方式**：每个上游怎么抓，就怎么抓（订阅源 `curl -A Clash` 原样透传、CFYes/vvHan/WeTest/麒麟/NiREvil/Gslege/ZhiXuan/S5 走各自公开接口）。
- **去掉重依赖**：原 `mia`（xinyitang3）的 Playwright 抓取改为普通 HTTP 抓取公开镜像，不再需要 chromium 环境。
- **保持上游原生格式**：订阅源 `IP:端口#备注` 一行不改地落地；API 源只保留上游自身字段（地区 / 运营商）作备注，**不注入 `CFYes优选` / `QNAir-LL` 这类项目品牌**，也不重新编号。
- **24 小时时效过滤**：某源本次抓取失败，且上一次成功已超过 24h，则在合并（`all.txt` / `sources.json`）时直接剔除；24h 内的旧数据保留。
- **单一工作流**：一个 `fetch.yml` 替代原项目「每上游一个 workflow」，GitHub Actions 运行记录不再爆炸。
- **可控部署**：仅在内容真正变化时才 `commit + push`，Cloudflare Pages 不会每次调度都部署 → 从根上避免「部署记录 >100 后删项目要先清记录」的麻烦。

## 目录结构

```
4.原样优选/
├── index.html              # 展示页（基于 QNAir UI，列出各上游 + 合并订阅）
├── sources.json            # 脚本生成，驱动 UI（含每源活跃状态/更新时间/条数）
├── all.txt                 # 脚本生成，活跃源合并订阅（原样拼接）
├── _headers                # Cloudflare Pages 缓存策略（no-cache）
├── scripts/fetch_all.py    # 统一抓取脚本（19 个上游）
└── .github/workflows/fetch.yml
```

每个上游的数据单独落在 `<源名>/all.txt`，格式即上游原生格式。

## 部署到 Cloudflare Pages

1. 把本目录推到 GitHub 新仓库（例如 `jax861003/BCFIP`）。
2. Cloudflare Pages → 连接该仓库 → 框架预设选 `None` / 直接上传 → 生产分支 `main` → 构建命令留空、输出目录留空（纯静态）。
3. **无需配置任何 Secret，19 个上游开箱即用。**

   **洛璃 / 辣子鸡已破解「个人订阅」依赖**（关键改进）：这两个上游（`loli.sub.us.ci` / `sub.lzjbaby.com`）都是 `cmliu/workerVless2sub`（Cloudflare Worker 版 VLESS→订阅转换器）的部署实例。复刻 `cmliu/edgetunnel` 的「优选订阅生成器」机制——用固定占位参数 `?host=example.com&uuid=00000000-0000-4000-8000-000000000000` 去探测，上游会返回其**公开优选IP列表**（base64 订阅，解密后 `@` 后即为真实 IP:端口 + 地区/测速备注，uuid 只是占位的）。脚本抓取后 base64 解码、提取 `IP:端口#备注`（上游原生、不改名）即落地。

   > 已实测：`sub.lzjbaby.com` 探测返回 **219 条**真实优选IP（如 `103.195.191.118:443#优选反代 - 辣子鸡 TG@lzjjjjjjjjjjj`）；`loli.sub.us.ci` 同理。无需任何个人 uuid。

   **所有 Secret 均为可选覆盖**（都配了也没关系，不配则走公开路径）：

   | Secret 名 | 对应上游 | 作用 |
   |---|---|---|
   | `LUOLI_URL` | 洛璃 luoli | 可选。若你有自己的真实订阅链接 `https://loli.sub.us.ci/sub?host=<host>&uuid=<uuid>`，配了就**原样透传**覆盖公开探测结果 |
   | `LZJ_URL` | 辣子鸡 lzj | 可选。同上，覆盖 `sub.lzjbaby.com` 的探测结果 |
   | `CMLIU_URL` / `CMLIU2_URL` / `XINYITANG3_URL` | CM / CM2 / Mia | 可选。覆盖下列内嵌公开上游 |

   **内嵌公开上游（缺 Secret 时自动回退，已实测可用）**：

   | 上游 | 回退公开地址 |
   |---|---|
   | `cmliu`（CM） | `https://090227.pages.dev/bestcf?isp=all&ips=20` |
   | `cmliu2`（CM2） | `https://raw.githubusercontent.com/wanwushequ/cfyxip/main/cmliu2/all.txt` |
   | `mia`（Mia / xinyitang3） | `https://raw.githubusercontent.com/wanwushequ/cfyxip/main/xinyitang3/ipv4.txt` |
   | `luoli`（洛璃） | 公开探测 `loli.sub.us.ci`（见上） |
   | `lzj`（辣子鸡） | 公开探测 `sub.lzjbaby.com`（见上） |

   > 8 个 API 源（CFYes / vvHan / WeTest / 麒麟 / NiREvil / Gslege / ZhiXuan / S5）走各自公开接口，**无需 Secret**。

   **新增 6 个 workerVless2sub 订阅生成器**（同款公开探测，无需 Secret，已实测）：

   | 上游 | 探测域名 | 实测条数 |
   |---|---|---|
   | Moist_R | `owo.o00o.ooo` | 32 |
   | 辣椒炒肉少放辣 | `sub.xdu.qzz.io` | 41 |
   | Kristi | `sub.mot.cloudns.biz` | 30 |
   | 周润发 | `zrf.zrf.me` | 38 |
   | DanFeng | `sub.danfeng.eu.org` | 30 |
   | 天诚 | `cm.soso.edu.kg` | 70 |

   ### 你提供的 13 个订阅域名验证结论

   你给出的 `sub://` 选择器清单，用同样的占位参数探测法（`?host=example.com&uuid=0000...`）逐一实测，结论如下：

   | 域名 | 名称 | 结果 | 处理 |
   |---|---|---|---|
   | `loli.sub.us.ci` | 洛璃 | ✅ 公开优选IP | 已用（探测） |
   | `sub.lzjbaby.com` | 辣子鸡 | ✅ 公开优选IP | 已用（探测） |
   | `owo.o00o.ooo` | Moist_R | ✅ 公开优选IP | 已用（探测） |
   | `sub.xdu.qzz.io` | 辣椒炒肉少放辣 | ✅ 公开优选IP | 已用（探测） |
   | `sub.995677.xyz` | S5公益 | ✅ 公开优选IP | 已用（API 接口，同域名） |
   | `sub.mot.cloudns.biz` | Kristi | ✅ 公开优选IP | 已用（探测） |
   | `zrf.zrf.me` | 周润发 | ✅ 公开优选IP | 已用（探测） |
   | `sub.danfeng.eu.org` | DanFeng | ✅ 公开优选IP | 已用（探测） |
   | `cm.soso.edu.kg` | 天诚 | ✅ 公开优选IP | 已用（探测） |
   | `sub.cmliussss.net` | CM | ⚠️ 把占位 host 当真实 host，返回 `@example.com` 废节点 | 未用（已有 CM 公开 API `090227.pages.dev`） |
   | `sub.mia.xx.kg` | Mia | ❌ 返回 TG 频道主页，不是订阅生成器 | 未用（已有 Mia GitHub 公开地址） |
   | `sub.keaeye.icu` | 文烨 | ❌ DNS 无法解析（域名失效） | 未用 |
   | `sub.pjq.cc.cd` | IDK | ❌ Cloudflare 522（上游 Worker 挂了） | 未用 |

   > 小结：**不是全部"同理"**——13 个里 9 个能用占位参数拿到真实优选IP，4 个不行（CM 机制不同、Mia 是 TG 页、文烨/IDK 域名或 Worker 故障）。可用的已全量接入；失效的两个（文烨/IDK）若日后恢复，按相同 `probesub` 写法加一行即可。

4. 手动触发一次 `fetch` 工作流（Actions → fetch → Run workflow），生成首批 `sources.json` / `all.txt` 并部署。之后每 6 小时自动更新。

## 与原项目的差异速查

| 项 | 1.cfyxip | 2.BestCF | 3.QNAir | 4.原样优选 |
|---|---|---|---|---|
| 取数方式 | 每上游独立 workflow | 每上游独立 workflow + parse_sub | 多数源镜像 bestcf | 单脚本复刻原方式 |
| 上游格式 | 原样透传 | 重解析改名 | 二手镜像+重编号 | **原样透传/上游备注** |
| 品牌改写 | API 源有（CFYes优选） | 有（洛璃/洛璃优选） | 有（QNAir-LL） | **无** |
| 时效过滤 | 无 | 无 | 有(24h) | **有(24h)** |
| 工作流数 | ~30 | ~25 | 1 | **1** |
| 部署膨胀 | 严重 | 严重 | 中 | **受控(仅变更部署)** |
