#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BCFIP —— 统一抓取脚本（按上游原生方式抓取公开优选 IP，取数方式参考 wanwushequ/cfyxip）

设计目标：
1. 复刻 wanwushequ/cfyxip「每个上游单独的取数方式」，但合并进【单个脚本 + 单个工作流】，
   避免上游项目每上游一个 workflow 导致 GitHub Actions 运行记录膨胀、
   Cloudflare Pages 每次 push 都部署（部署记录 >100 后删项目很麻烦）。
2. 取到的 IP 保持【上游原生格式】：
   - 订阅类源（cmliu/cmliu2/luoli/lzj）：`curl -A Clash <订阅URL>` 后【原样透传】，
     不做任何改名 / 重新编号（即上游 `cat raw_nodes.txt > <src>/all.txt` 的行为）。
   - Mia（xinyitang3）：直接镜像 wanwushequ/cfyxip 公开数据文件，【原样透传】到 <src>/all.txt（无需 Playwright）。
   - API 类源（cfyes/vvhan/wetest/uouin/nirevil/gslege/zhixuanwang/s5gy）：
     调用上游公开接口，抽取 IP:端口，仅保留【上游自身字段】作为备注
     （如运营商/机房），【不注入 CFYes优选 / QNAir-LL 这类项目品牌】。
3. 24 小时时效过滤：
   - 每个源抓取成功 → 写文件 + 记 last_updated=现在 + active=True。
   - 抓取失败 → 若上一次成功在 24h 内且旧文件存在，保留旧数据（active=True，不覆盖）；
     否则标记 inactive，合并时剔除该源。
   - 合并的 all.txt / sources.json 仅包含 active 源。

订阅类源的抓取地址：
  - cmliu / cmliu2 / Mia(xinyitang3) 已内置【公开上游地址 public_url】，无需任何配置即可运行；
    若你有自己的个人订阅链接，可配置同名 Secret（CMLIU_URL / CMLIU2_URL / XINYITANG3_URL）覆盖之。
  - 洛璃(luoli) / 辣子鸡(lzj) 已内置【公开探测】：用占位 host/uuid 触发 workerVless2sub 返回其
    公开优选IP列表，无需任何个人订阅即可获取（详见 README「原理」章节）。
    若你有自己的个人订阅链接，可配置同名 Secret（LUOLI_URL / LZJ_URL）覆盖探测结果。
"""

import base64
import concurrent.futures
import ipaddress
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRESH_HOURS = 24
BJ = timezone(timedelta(hours=8))
UA_BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
UA_CLASH = "Clash"

# ---------------------------------------------------------------- 上游定义
# type:
#   raw   -> 订阅/镜像类，curl -A Clash 原样透传（优先 env 个人订阅，缺省回退 public_url 公开上游）
#   cfyes/vvhan/wetest/uouin/nirevil/gslege/zhixuanwang/s5gy -> 公开接口抽取
SOURCES = [
    {"name": "cmliu",       "label": "CM",     "code": "CM",  "type": "raw",
     "env": "CMLIU_URL",
     "public_url": "https://090227.pages.dev/bestcf?isp=all&ips=20",
     "folder": "cmliu"},
    {"name": "cmliu2",      "label": "CM 2",   "code": "CM",  "type": "raw",
     "env": "CMLIU2_URL",
     "public_url": "https://raw.githubusercontent.com/wanwushequ/cfyxip/main/cmliu2/all.txt",
     "folder": "cmliu2"},
    {"name": "luoli",       "label": "洛璃",    "code": "LL",  "type": "probesub",
     "env": "LUOLI_URL",  "probe_host": "loli.sub.us.ci",   "folder": "luoli"},
    {"name": "lzj",         "label": "辣子鸡",  "code": "LZ",  "type": "probesub",
     "env": "LZJ_URL",     "probe_host": "sub.lzjbaby.com",  "folder": "lzj"},
    {"name": "mia",         "label": "Mia",     "code": "MIA", "type": "raw",
     "env": "XINYITANG3_URL",
     "public_url": "https://raw.githubusercontent.com/wanwushequ/cfyxip/main/xinyitang3/ipv4.txt",
     "folder": "mia"},
    {"name": "cfyes",       "label": "CFYes",   "code": "CFY", "type": "cfyes",       "folder": "cfyes"},
    {"name": "vvhan",       "label": "vvHan",   "code": "VH",  "type": "vvhan",       "folder": "vvhan"},
    {"name": "wetest",      "label": "WeTest",  "code": "WT",  "type": "wetest",      "folder": "wetest"},
    {"name": "uouin",       "label": "麒麟",    "code": "QL",  "type": "uouin",       "folder": "uouin"},
    {"name": "nirevil",     "label": "NiREvil", "code": "NR",  "type": "nirevil",     "folder": "nirevil"},
    {"name": "gslege",      "label": "Gslege",  "code": "GS",  "type": "gslege",      "folder": "gslege"},
    {"name": "zhixuanwang", "label": "ZhiXuan", "code": "ZX",  "type": "zhixuanwang", "folder": "zhixuanwang"},
    {"name": "s5gy",        "label": "S5公益",  "code": "S5",  "type": "s5gy",        "folder": "s5gy"},
    # ---- 以下为新增的 workerVless2sub 部署（同款占位参数公开探测，无需 Secret）----
    {"name": "moistr",      "label": "Moist_R",        "code": "MR",  "type": "probesub",
     "env": "MOISTR_URL",   "probe_host": "owo.o00o.ooo",        "folder": "moistr"},
    {"name": "chili",       "label": "辣椒炒肉少放辣",  "code": "CL",  "type": "probesub",
     "env": "CHILI_URL",    "probe_host": "sub.xdu.qzz.io",      "folder": "chili"},
    {"name": "kristi",      "label": "Kristi",         "code": "KR",  "type": "probesub",
     "env": "KRISTI_URL",   "probe_host": "sub.mot.cloudns.biz", "folder": "kristi"},
    {"name": "zrf",         "label": "周润发",          "code": "ZRF", "type": "probesub",
     "env": "ZRF_URL",      "probe_host": "zrf.zrf.me",          "folder": "zrf"},
    {"name": "danfeng",     "label": "DanFeng",        "code": "DF",  "type": "probesub",
     "env": "DANFENG_URL",  "probe_host": "sub.danfeng.eu.org",  "folder": "danfeng"},
    {"name": "tiancheng",   "label": "天诚",           "code": "TC",  "type": "probesub",
     "env": "TIANCHENG_URL","probe_host": "cm.soso.edu.kg",    "folder": "tiancheng"},
]

# 公开接口地址（与原项目一致）
S5GY_URL = ("https://sub.995677.xyz/sub?uuid=00000000-0000-4000-8000-"
            "000000000000&host=example.com")
NIREVIL_URLS = [
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/Cf-ipv4.json",
    "https://raw.githubusercontent.com/NiREvil/vless/refs/heads/main/sub/Cf-ipv6.json",
]
GSLEGE_URLS = {
    "https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/Cfxyz.txt": None,
    "https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/JP.txt": "日本",
    "https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/NL.txt": "荷兰",
    "https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/US.txt": "美国",
    "https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/DE.txt": "德国",
    "https://raw.githubusercontent.com/gslege/CloudflareIP/refs/heads/main/SG.txt": "新加坡",
}
ZHIXUANWANG_URL = ("https://raw.githubusercontent.com/ZhiXuanWang/cf-speed-dns/"
                   "refs/heads/main/ipTop10.html")
WETEST_URL = "https://www.wetest.vip/page/cloudflare/address_v4.html"
CFYES_URL = "https://api.hostmonit.com/get_optimization_ip"
VVHAN_URL = "https://api.4ce.cn/api/bestCFIP"
UOUIN_URL = "https://api.uouin.com/cloudflare.html"

# ---------------------------------------------------------------- 时间工具
def now_bj():
    return datetime.now(BJ)

def bj_compact():
    return now_bj().strftime("%m-%d %H:%M")

def bj_iso(dt=None):
    return (dt or now_bj()).isoformat()

def parse_embedded_time(text):
    m = re.search(r"\b(\d{2})-(\d{2})\s+(\d{2}):(\d{2})\b", text or "")
    if not m:
        return None
    try:
        return datetime(now_bj().year, int(m.group(1)), int(m.group(2)),
                        int(m.group(3)), int(m.group(4)), tzinfo=BJ)
    except ValueError:
        return None

def is_fresh(t):
    if not t:
        return False
    if isinstance(t, str):
        t = parse_embedded_time(t)
    if not t:
        return False
    if t.tzinfo is None:
        t = t.replace(tzinfo=BJ)
    return now_bj() - t <= timedelta(hours=FRESH_HOURS)

# ---------------------------------------------------------------- 地区/运营商归一化（仅 API 源用）
ISP_EXACT = {"CM": "移动", "CU": "联通", "CT": "电信",
             "CMCC": "移动", "CTCC": "电信", "CUCC": "联通"}
REGION_NAMES = [
    "印度尼西亚", "哈萨克斯坦", "斯里兰卡", "孟加拉国", "尼日利亚",
    "澳大利亚", "马来西亚", "阿根廷", "阿联酋", "比利时", "葡萄牙",
    "香港", "澳门", "台湾", "日本", "韩国", "新加坡", "美国", "英国",
    "德国", "法国", "荷兰", "俄罗斯", "加拿大", "土耳其", "越南",
    "菲律宾", "泰国", "印度", "奥地利", "拉脱维亚", "多哥", "中国",
    "巴西", "墨西哥", "瑞典", "瑞士", "意大利", "西班牙", "波兰",
    "芬兰", "挪威", "爱尔兰", "捷克", "乌克兰", "以色列", "蒙古",
    "柬埔寨", "缅甸", "尼泊尔", "巴基斯坦", "沙特", "卡塔尔", "埃及",
    "南非", "智利", "哥伦比亚", "秘鲁", "印尼", "新西兰", "伊拉克",
]
FUN_NAMES = {
    "小日本儿": "日本", "港岛茶记": "香港", "港岛古惑": "香港",
    "印加坡县": "新加坡", "宝岛正妹": "台湾", "战争贩子": "美国",
    "大嘤帝国": "英国", "战斗毛子": "俄罗斯", "元首复活": "德国",
    "大马榴莲": "马来西亚", "西贡咖啡": "越南", "菲氏叶猴": "菲律宾",
    "萨瓦迪卡": "泰国", "干净卫生": "印度", "每日乳法": "法国",
    "枫叶之国": "加拿大", "烤肉火鸡": "土耳其", "土澳袋鼠": "澳大利亚",
    "风车郁金": "荷兰", "泡菜欧巴": "韩国",
}
REGION_CODE = {
    "HK": "香港", "MO": "澳门", "TW": "台湾", "JP": "日本", "KR": "韩国",
    "SG": "新加坡", "US": "美国", "GB": "英国", "UK": "英国", "DE": "德国",
    "FR": "法国", "NL": "荷兰", "RU": "俄罗斯", "CA": "加拿大",
    "AU": "澳大利亚", "TR": "土耳其", "MY": "马来西亚", "VN": "越南",
    "PH": "菲律宾", "TH": "泰国", "IN": "印度", "AT": "奥地利",
    "LV": "拉脱维亚", "TG": "多哥", "ID": "印尼", "BR": "巴西",
    "MX": "墨西哥", "SE": "瑞典", "CH": "瑞士", "IT": "意大利",
    "ES": "西班牙", "PL": "波兰", "FI": "芬兰", "NO": "挪威",
    "IE": "爱尔兰", "BE": "比利时", "CZ": "捷克", "UA": "乌克兰",
    "AE": "阿联酋", "IL": "以色列", "KZ": "哈萨克斯坦", "MN": "蒙古",
    "KH": "柬埔寨", "MM": "缅甸", "PK": "巴基斯坦", "SA": "沙特",
    "QA": "卡塔尔", "EG": "埃及", "ZA": "南非", "CL": "智利",
    "CO": "哥伦比亚", "PE": "秘鲁", "AR": "阿根廷", "CN": "中国",
    "NZ": "新西兰",
}
COLO_MAP = {
    "HKG": "香港", "SIN": "新加坡", "NRT": "日本", "KIX": "日本",
    "HND": "日本", "ICN": "韩国", "LAX": "美国", "SJC": "美国",
    "SFO": "美国", "SEA": "美国", "ORD": "美国", "DFW": "美国",
    "IAD": "美国", "MIA": "美国", "EWR": "美国", "MSP": "美国",
    "ATL": "美国", "DEN": "美国", "PHX": "美国", "SLC": "美国",
    "YYZ": "加拿大", "YVR": "加拿大", "LHR": "英国", "FRA": "德国",
    "AMS": "荷兰", "CDG": "法国", "SVO": "俄罗斯", "DME": "俄罗斯",
    "SYD": "澳大利亚", "MEL": "澳大利亚", "AKL": "新西兰",
    "BOM": "印度", "MAA": "印度", "DEL": "印度", "BKK": "泰国",
    "KUL": "马来西亚", "MNL": "菲律宾", "CGK": "印尼", "HAN": "越南",
    "SGN": "越南", "GRU": "巴西", "MEX": "墨西哥", "EZE": "阿根廷",
    "SCL": "智利", "BOG": "哥伦比亚", "JNB": "南非", "DXB": "阿联酋",
    "TLV": "以色列", "IST": "土耳其", "WAW": "波兰", "ARN": "瑞典",
    "ZRH": "瑞士", "MXP": "意大利", "MAD": "西班牙", "VIE": "奥地利",
    "RIX": "拉脱维亚", "LGG": "比利时",
}
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\uFE0F]+")
REGION_BLACKLIST = {"CF", "VPN", "CDN", "IP", "OK", "MAX", "PRO", "TEST", "NODES"}

def match_isp(text):
    if not text:
        return None
    s = str(text).strip()
    if re.search(r"移动|CMCC|China\s*Mobile", s, re.I):
        return "移动"
    if re.search(r"电信|CTCC|China\s*Telecom", s, re.I):
        return "电信"
    if re.search(r"联通|CUCC|China\s*Unicom", s, re.I):
        return "联通"
    t = re.sub(r"[^A-Za-z]", "", s).upper()
    return ISP_EXACT.get(t)

def normalize_region(text):
    if not text:
        return None
    s = _EMOJI_RE.sub(" ", str(text))
    s = re.sub(r"[^\w\u4e00-\u9fff]+", " ", s, flags=re.UNICODE).strip()
    if not s:
        return None
    if match_isp(s):
        return None
    for name in sorted(REGION_NAMES, key=len, reverse=True):
        if name in s:
            return name
    for k, v in FUN_NAMES.items():
        if k in str(text):
            return v
    for tok in re.findall(r"[A-Za-z]{2,4}", s):
        t = tok.upper()
        if t in REGION_BLACKLIST:
            continue
        if t in COLO_MAP:
            return COLO_MAP[t]
        if t in REGION_CODE:
            return REGION_CODE[t]
    return None

# ---------------------------------------------------------------- IP 工具
def valid_ip(ip):
    try:
        addr = ipaddress.ip_address(ip.strip("[]"))
    except ValueError:
        return False
    if addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_multicast:
        return False
    return True

def fmt_ip(ip):
    ip = ip.strip()
    if ":" in ip and not ip.startswith("["):
        return f"[{ip}]"
    return ip

# ---------------------------------------------------------------- 节点（API 源用，输出不带项目品牌）
class Node:
    __slots__ = ("ip", "port", "region", "isp")
    def __init__(self, ip, port, region=None, isp=None):
        self.ip = ip
        self.port = port
        self.region = region or None
        self.isp = isp or None
    @property
    def key(self):
        return f"{self.ip}:{self.port}"
    def line(self):
        # 仅保留上游自身字段：地区 | 运营商；不注入任何项目品牌
        remark = " | ".join(p for p in [self.region, self.isp] if p and p != "未知")
        return f"{fmt_ip(self.ip)}:{self.port}" + (f"#{remark}" if remark else "")

# ---------------------------------------------------------------- HTTP
def _get(url, timeout=15, retries=2, headers=None):
    try:
        import requests
    except ImportError:
        raise RuntimeError("缺少 requests 依赖")
    last = None
    for _ in range(retries + 1):
        try:
            r = requests.get(url, timeout=timeout, headers=headers or {"User-Agent": UA_BROWSER})
            if r.status_code == 200 and r.text.strip():
                return r.text
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"GET 失败: {url} ({last})")

def _post_json(url, payload, timeout=12, retries=2):
    import requests
    last = None
    for _ in range(retries + 1):
        try:
            r = requests.post(url, json=payload, timeout=timeout,
                              headers={"Content-Type": "application/json"})
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"POST 失败: {url} ({last})")

def _get_curl(url, timeout=25, retries=3):
    """用 curl 子进程抓取（继承环境代理，如 HTTPS_PROXY），比 requests 走 SOCKS 更稳。
    对上游偶发的 TLS 握手失败做重试。
    注意：--ssl-no-revoke 仅 Windows/Schannel 后端需要（本机因吊销服务器离线必须加）；
    Linux/macOS（GitHub Actions 等 OpenSSL 后端）不支持该参数，带之会 unknown option 直接失败，故按平台判断。"""
    import subprocess
    # 仅 Windows/Schannel 需要；OpenSSL 后端（CI / ubuntu）带此参数会直接报错退出。
    ssl_flag = ["--ssl-no-revoke"] if sys.platform == "win32" else []
    last = None
    for attempt in range(retries + 1):
        try:
            out = subprocess.run(
                ["curl", "-sS", "-L", *ssl_flag, "--max-time", str(timeout),
                 "-A", UA_BROWSER, url],
                capture_output=True, text=True, timeout=timeout + 10, env=dict(os.environ))
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout
            last = f"curl rc={out.returncode}: {out.stderr[:120]}"
        except Exception as e:
            last = str(e)
    raise RuntimeError(f"curl GET 失败（{retries}次重试后仍失败）: {last}")

def _scraper_get(url, timeout=20, retries=2):
    try:
        import cloudscraper
        last = None
        for _ in range(retries + 1):
            try:
                scraper = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "windows", "desktop": True})
                r = scraper.get(url, timeout=timeout)
                if r.status_code == 200 and r.text.strip():
                    return r.text
                last = f"HTTP {r.status_code}"
            except Exception as e:
                last = str(e)
        raise RuntimeError(f"scraper GET 失败: {url} ({last})")
    except ImportError:
        return _get(url, timeout, retries, {"User-Agent": UA_BROWSER})

# ---------------------------------------------------------------- 订阅类源：原样透传
def fetch_raw_text(src):
    """curl -A Clash <订阅URL>，返回原始文本（原样，不做任何改名/解析）。
    优先用环境变量（个人订阅）；未配置则回退到 public_url 公开上游。"""
    url = (os.environ.get(src["env"]) or "").strip() or (src.get("public_url") or "").strip()
    if not url:
        raise RuntimeError(f"未配置 Secret: {src['env']} 且无可用公开上游")
    text = _get(url, 15, 2, {"User-Agent": UA_CLASH})
    # 原项目校验：至少 3 个 IP:PORT 才算有效，避免污染
    cnt = len(re.findall(r"[0-9a-zA-Z\.-]+:[0-9]+", text))
    if cnt < 3:
        raise RuntimeError(f"有效节点仅 {cnt} 个（<3），拒绝写入")
    return text

# ---------------------------------------------------------------- API 类源：抽取 IP，保留上游备注（不注入项目品牌）
def fetch_cfyes(_src):
    nodes = []
    line_map = {"CM": "移动", "CU": "联通", "CT": "电信"}
    for ip_type in ("v4", "v6"):
        data = _post_json(CFYES_URL, {"key": "iDetkOys", "type": ip_type}, 12, 2)
        for item in data.get("info", []):
            ip = (item.get("ip") or "").strip()
            if not ip or not valid_ip(ip):
                continue
            nodes.append(Node(ip, 443, None, line_map.get(item.get("line"))))
    if not nodes:
        raise RuntimeError("CFYes 数据为空")
    return nodes

def fetch_vvhan(_src):
    import json
    res = json.loads(_get(VVHAN_URL, 15, 2, {"User-Agent": UA_BROWSER}))
    if not res.get("success"):
        raise RuntimeError("vvHan API 返回失败")
    nodes = []
    data = res.get("data", {})
    for ver in ("v4", "v6"):
        for key, label in (("CM", "移动"), ("CU", "联通"), ("CT", "电信")):
            for item in data.get(ver, {}).get(key, []):
                ip = (item.get("ip") or "").strip()
                if not ip or not valid_ip(ip):
                    continue
                nodes.append(Node(ip, 443, normalize_region(item.get("colo")), label))
    if not nodes:
        raise RuntimeError("vvHan 数据为空")
    return nodes

def fetch_wetest(_src):
    html = _get(WETEST_URL, 15, 2, {"User-Agent": UA_BROWSER})
    cells = re.findall(
        r'data-label="(?:线路名称|优选地址|数据中心)"[^>]*>\s*([^<\r\n]+?)\s*<', html)
    if len(cells) < 3:
        raise RuntimeError("WeTest 页面未解析到数据")
    nodes = []
    for i in range(0, len(cells) - 2, 3):
        line_name, addr, colo = cells[i], cells[i + 1], cells[i + 2]
        ip = addr.strip()
        if not valid_ip(ip):
            continue
        nodes.append(Node(ip, 443, normalize_region(colo), match_isp(line_name)))
    if not nodes:
        raise RuntimeError("WeTest 数据为空")
    return nodes

def fetch_uouin(_src):
    html = _scraper_get(UOUIN_URL, 20, 2)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr") if table else []
        cells_of = [[td.get_text(strip=True) for td in row.find_all("td")] for row in rows]
    except ImportError:
        cells_of = []
        for row_html in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
            cells_of.append([re.sub(r"<[^>]+>", "", c).strip()
                             for c in re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)])
    nodes = []
    ipv4_re = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
    for cells in cells_of:
        if len(cells) < 5:
            continue
        if "IPv6" in cells[0].upper():
            continue
        m = ipv4_re.search(" ".join(cells))
        if not m or not valid_ip(m.group(0)):
            continue
        nodes.append(Node(m.group(0), 443, None, match_isp(cells[0])))
    if not nodes:
        raise RuntimeError("麒麟数据为空")
    return nodes

def fetch_nirevil(_src):
    import json
    nodes = []
    for url in NIREVIL_URLS:
        try:
            data = json.loads(_get(url, 15, 2, {"User-Agent": UA_BROWSER}))
        except RuntimeError:
            continue
        line_map = {"CM": "移动", "CU": "联通", "CT": "电信"}
        for item in data:
            ip = (item.get("ip") or "").strip()
            if not ip or not valid_ip(ip):
                continue
            nodes.append(Node(ip, 443, normalize_region(item.get("colo")),
                              line_map.get(item.get("line"), match_isp(item.get("line")))))
    if not nodes:
        raise RuntimeError("NiREvil 数据为空")
    return nodes

def fetch_gslege(_src):
    nodes = []
    for url, default_region in GSLEGE_URLS.items():
        try:
            text = _get(url, 15, 2, {"User-Agent": UA_BROWSER, "Cache-Control": "no-cache"})
        except RuntimeError:
            continue
        for line in text.splitlines():
            line = line.strip().replace("\r", "")
            if not line or "#" not in line:
                continue
            head, remark = line.split("#", 1)
            m = re.match(r"^(\[[0-9A-Fa-f:]+\]|[0-9A-Fa-f.]+):(\d{1,5})$", head.strip())
            if not m:
                m2 = re.match(r"^(\[[0-9A-Fa-f:]+\]|[0-9A-Fa-f.]+)$", head.strip())
                if not m2:
                    continue
                ip, port = m2.group(1), "443"
            else:
                ip, port = m.group(1), m.group(2)
            if not valid_ip(ip):
                continue
            region = normalize_region(remark.split("|")[0]) or default_region
            nodes.append(Node(ip.strip("[]"), port, region, None))
    if not nodes:
        raise RuntimeError("Gslege 数据为空")
    return nodes

def fetch_zhixuanwang(_src):
    text = _get(ZHIXUANWANG_URL, 15, 2, {"User-Agent": UA_BROWSER})
    nodes = []
    for tok in text.replace(",", "\n").split():
        tok = tok.strip()
        if not tok:
            continue
        m = re.match(r"^(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?$", tok)
        if m and valid_ip(m.group(1)):
            nodes.append(Node(m.group(1), m.group(2) or "443", None, None))
    if not nodes:
        raise RuntimeError("ZhiXuan 数据为空")
    return nodes

def fetch_s5gy(_src):
    text = _scraper_get(S5GY_URL, 15, 3)
    if "<pre" in text:
        m = re.search(r"<pre[^>]*>(.*?)</pre>", text, re.S)
        if m:
            text = m.group(1)
    text = text.strip()
    try:
        decoded = base64.b64decode(text).decode("utf-8", "ignore")
    except Exception:
        decoded = text
    nodes = []
    for line in decoded.splitlines():
        line = line.strip()
        if not line.startswith("vless://"):
            continue
        m = re.search(r"@(\[[0-9A-Fa-f:.]+\]|[^@?/]+):(\d{1,5})\?", line)
        if not m:
            continue
        ip, port = m.group(1), m.group(2)
        raw_tag = line.split("#", 1)[1] if "#" in line else ""
        tag = urllib.parse.unquote(urllib.parse.unquote(raw_tag)).strip()
        if not tag or "s5gydl" in tag:
            continue
        if not valid_ip(ip):
            continue
        nodes.append(Node(ip.strip("[]"), port, normalize_region(tag), match_isp(tag)))
    if not nodes:
        raise RuntimeError("S5公益数据为空")
    return nodes

# ---------------------------------------------------------------- workerVless2sub 类（洛璃/辣子鸡）：公开探测
def _decode_vless_sub(raw, host):
    """base64 vless 订阅 -> 提取 IP:PORT#备注（上游原生，不改名）。
    复刻 cmliu/edgetunnel 的「优选订阅生成器」探测法：用占位 host/uuid 触发上游
    返回其公开优选IP列表（uuid 为占位，@ 后的 IP:PORT 与 # 后的备注均为上游真实数据）。"""
    text = (raw or "").strip()
    # 先尝试 base64 解码（workerVless2sub 默认输出）
    try:
        decoded = base64.b64decode(text).decode("utf-8", "replace")
        if "vless://" in decoded or "vmess://" in decoded:
            text = decoded
    except Exception:
        pass
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("vless://") or line.startswith("vmess://")):
            continue
        # 提取 @ 之后的 host:port（支持 IPv6 [..]:port）
        m = re.search(r"://[^@]+@([^?/#\s]+)", line)
        if not m:
            continue
        addr = m.group(1)
        if not re.match(r"^\[?[0-9a-zA-Z\.\-]+\]?:\d+$", addr):
            continue
        remark = ""
        rm = re.search(r"#(.+)$", line)
        if rm:
            try:
                remark = "#" + urllib.parse.unquote(rm.group(1))
            except Exception:
                remark = "#" + rm.group(1)
        out.append(addr + remark)
    if len(out) < 3:
        raise RuntimeError(f"{host} 解析出有效节点仅 {len(out)} 个（<3），拒绝写入")
    return "\n".join(out) + "\n"

def fetch_probe_sub(src):
    """洛璃/辣子鸡等 workerVless2sub 部署：公开探测，无需 Secret。
    若配置了个人订阅 Secret(env) 则优先原样透传（保持上游格式）。"""
    secret = (os.environ.get(src.get("env", "")) or "").strip()
    if secret:
        text = _get(secret, 15, 2, {"User-Agent": UA_BROWSER})
        cnt = len(re.findall(r"[0-9a-zA-Z\.\-]+:\d+", text))
        if cnt < 3:
            raise RuntimeError(f"有效节点仅 {cnt} 个（<3），拒绝写入")
        return text
    host = src.get("probe_host")
    if not host:
        raise RuntimeError(f"未配置 {src['name']} 的 probe_host 且未配置 Secret")
    url = f"https://{host}/sub?host=example.com&uuid=00000000-0000-4000-8000-000000000000"
    # 用 curl 子进程抓取（比 requests 走 SOCKS 代理更稳，且 GitHub Actions 直连也好使）
    raw = _get_curl(url, 25)
    return _decode_vless_sub(raw, host)

FETCHERS = {
    "raw": fetch_raw_text,
    "probesub": fetch_probe_sub,
    "cfyes": fetch_cfyes,
    "vvhan": fetch_vvhan,
    "wetest": fetch_wetest,
    "uouin": fetch_uouin,
    "nirevil": fetch_nirevil,
    "gslege": fetch_gslege,
    "zhixuanwang": fetch_zhixuanwang,
    "s5gy": fetch_s5gy,
}

# ---------------------------------------------------------------- 单源超时护栏
# 防止某个上游（如 CF 挑战页面）无限挂起，拖垮整个工作流。
SOURCE_TIMEOUT = 45
def run_with_timeout(fn, src):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, src)
        try:
            return fut.result(timeout=SOURCE_TIMEOUT)
        except concurrent.futures.TimeoutError:
            raise RuntimeError(f"抓取超时（>{SOURCE_TIMEOUT}s）")

# ---------------------------------------------------------------- 路径与写入
def source_file(src):
    return ROOT / src["folder"] / "all.txt"

def write_raw(src, text):
    path = source_file(src)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = text.rstrip("\n") + "\n"
    path.write_text(content, encoding="utf-8")
    return path

def write_api(src, nodes):
    path = source_file(src)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(n.line() for n in nodes) + "\n", encoding="utf-8")
    return path

def count_lines(path):
    try:
        return sum(1 for _ in Path(path).read_text(encoding="utf-8").splitlines() if _.strip())
    except Exception:
        return 0

# ---------------------------------------------------------------- 编排
def load_prev_state():
    try:
        meta = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        return {s["name"]: s for s in meta.get("sources", [])}
    except Exception:
        return {}

def main():
    prev = load_prev_state()
    sources_out = []
    active_count = 0
    total_entries = 0

    for src in SOURCES:
        name = src["name"]
        label = src["label"]
        path = source_file(src)
        prev_entry = prev.get(name, {})
        prev_time = prev_entry.get("last_updated")
        prev_active = prev_entry.get("active", False)
        prev_fresh = is_fresh(prev_time) if prev_time else False

        try:
            result = run_with_timeout(FETCHERS[src["type"]], src)
            # 订阅/mia/probesub：返回原始文本；API：返回 Node 列表
            if src["type"] in ("raw", "mia", "probesub"):
                write_raw(src, result)
                entries = count_lines(path)
            else:
                if not result:
                    raise RuntimeError("抓取结果为空")
                write_api(src, result)
                entries = len(result)
            last_updated = bj_iso()
            active = True
            print(f"[OK] {label}: {entries} 条 -> {src['folder']}/all.txt")
        except Exception as e:
            # 抓取失败：保留 24h 内旧数据，否则剔除
            if prev_active and prev_fresh and path.exists():
                entries = count_lines(path)
                last_updated = prev_time
                active = True
                print(f"[回退] {label}: 抓取失败({e})，保留 {entries} 条 24h 内旧数据")
            else:
                entries = count_lines(path) if path.exists() else 0
                last_updated = prev_time
                active = False
                print(f"[剔除] {label}: 抓取失败({e})，"
                      f"{'旧数据超24h' if prev_time else '无历史数据'}，本次不纳入合并")
                if "Secret" in str(e):
                    print(f"       提示: 请在仓库 Secrets 配置 {src['env']}")

        if active:
            active_count += 1
            total_entries += entries
        sources_out.append({
            "name": name, "label": label, "code": src["code"],
            "path": f"{src['folder']}/all.txt",
            "entries": entries, "active": active,
            "last_updated": last_updated,
        })

    # 生成 sources.json（驱动 UI）
    meta = {
        "generated_at": bj_iso(),
        "generated_compact": bj_compact(),
        "fresh_hours": FRESH_HOURS,
        "total_entries": total_entries,
        "active_sources": active_count,
        "total_sources": len(SOURCES),
        "format": "上游原生格式（订阅源原样透传 / API 源仅保留上游自身备注）",
        "sources": sources_out,
    }
    (ROOT / "sources.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    # 合并 active 源到根 all.txt（原样拼接，方便一次性订阅）
    merged = []
    for s in sources_out:
        if not s["active"]:
            continue
        p = ROOT / s["path"]
        if p.exists():
            merged.append(f"# ===== {s['label']} ({s['code']}) =====")
            merged.append(p.read_text(encoding="utf-8").rstrip("\n"))
    (ROOT / "all.txt").write_text("\n".join(merged) + "\n", encoding="utf-8")

    print(f"\n完成：活跃 {active_count}/{len(SOURCES)} 源，"
          f"去重前合计 {total_entries} 条 -> sources.json / all.txt")

if __name__ == "__main__":
    main()
