#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股與美股/國際期貨每日盤後儀表板資料抓取與生成腳本
涵蓋項目：
1. 每日台股加權指數走勢 (TWSE FMTQIK + MI_5MINS_HIST)
2. 每日三大法人買賣超金額 (TWSE BFI82U)
3. 外資、投信及自營商每日買賣超前50名 (TWSE T86)
4. 台股每日成交值及成交量排名前15名 (TWSE MI_INDEX ALLBUT0999)
5. 權證交易量每日前20名次 (TWSE MI_INDEX 0999 + 0999P)
6. 布蘭特原油走勢 (CNBC @LCO.1 1D & 30M) — 支援每小時更新 (--mode futures)
7. 台指期夜盤走勢 (TAIFEX MIS getQuoteList & getChartData1M)
8. 小那斯達克期貨走勢 (CNBC @ND.1 1D & 30M) — 支援每小時更新 (--mode futures)
9. 台股概念族群資金輪動圖 (四象限氣泡圖) 與 概念族群熱力圖 (Squarified Treemap)
10. 國際金融走勢：
    - 美股四大指數 (.DJI, .IXIC, .SPX, .SOX) — 支援美股收盤後更新 (--mode global)
    - 日韓主要指數：日經 225 指數 (.N225) 與 韓國綜合指數 KOSPI (.KS11)
    - 台股四大 ADR (台積電 TSM、日月光 ASX、鴻海 HNHPF、聯電 UMC) 即時與日K走勢
11. 保留並支援切換最近 5 個交易日 (history_5d) 的完整台股盤後資料
"""

import argparse
import datetime
import json
import math
import os
import re
import ssl
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, "data.json")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")
HISTORY_DIR = os.path.join(BASE_DIR, "history")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
    ),
    "Accept": "application/json, text/plain, */*",
}

# 台股核心概念族群與代表成分股代號表
CONCEPT_GROUPS = [
    {
        "name": "先進封裝 (CoWoS／CoPoS)",
        "baseline_100m": 185.0,
        "codes": ["2330", "3711", "3131", "3583", "6187", "6640", "2449", "6239", "8150", "2451"],
    },
    {
        "name": "高速 PCB／CCL",
        "baseline_100m": 135.0,
        "codes": ["2383", "6274", "6213", "2368", "2313", "3044", "4958", "8046", "5469", "6153"],
    },
    {
        "name": "ABF 載板",
        "baseline_100m": 115.0,
        "codes": ["3037", "8046", "3189"],
    },
    {
        "name": "被動元件",
        "baseline_100m": 75.0,
        "codes": ["2327", "2492", "2456", "2472", "6173", "2375", "6127", "2428", "3026"],
    },
    {
        "name": "先進製程與廠務",
        "baseline_100m": 95.0,
        "codes": ["2404", "6196", "6691", "5536", "2360", "6139", "1723", "4768"],
    },
    {
        "name": "IC 測試",
        "baseline_100m": 80.0,
        "codes": ["2449", "6223", "6515", "6510", "3264", "8150", "6257", "3374"],
    },
    {
        "name": "ASIC／矽智財IP",
        "baseline_100m": 140.0,
        "codes": ["3661", "3443", "3035", "6643", "6531", "6533", "3529", "4966"],
    },
    {
        "name": "玻璃基板",
        "baseline_100m": 70.0,
        "codes": ["1802", "3481", "2409", "3037", "3131", "3535", "6164"],
    },
    {
        "name": "塑化",
        "baseline_100m": 65.0,
        "codes": ["1301", "1303", "1326", "6505", "1304", "1305", "1308", "1309", "1312", "1314"],
    },
    {
        "name": "散熱 (液冷)",
        "baseline_100m": 125.0,
        "codes": ["3017", "3324", "2421", "3653", "6230", "8996", "3338"],
    },
    {
        "name": "AI 伺服器",
        "baseline_100m": 210.0,
        "codes": ["2317", "2382", "3231", "6669", "2356", "2376", "2377", "2301", "4938"],
    },
    {
        "name": "記憶體 (HBM/DRAM/NAND)",
        "baseline_100m": 85.0,
        "codes": ["2408", "2344", "2337", "8299", "3260", "4967", "2451", "3006"],
    },
    {
        "name": "成熟製程",
        "baseline_100m": 75.0,
        "codes": ["2303", "6770", "5347", "2342", "2338"],
    },
    {
        "name": "矽光子／CPO",
        "baseline_100m": 90.0,
        "codes": ["3450", "2345", "6442", "4977", "3163", "3363", "4908", "6451"],
    },
    {
        "name": "車載鏡頭",
        "baseline_100m": 55.0,
        "codes": ["3008", "3406", "3019", "6209", "4976", "3362"],
    },
    {
        "name": "矽晶圓",
        "baseline_100m": 48.0,
        "codes": ["6488", "3532", "6182", "3016", "1560"],
    },
    {
        "name": "光通訊",
        "baseline_100m": 68.0,
        "codes": ["6442", "4977", "3450", "2455", "3081", "3163", "3363"],
    },
    {
        "name": "低軌衛星",
        "baseline_100m": 52.0,
        "codes": ["2313", "6285", "3491", "2314", "2485", "5388"],
    },
    {
        "name": "AI 電力",
        "baseline_100m": 78.0,
        "codes": ["2308", "1519", "1503", "1513", "1504", "1609", "1514"],
    },
    {
        "name": "AI 眼鏡與穿戴",
        "baseline_100m": 45.0,
        "codes": ["2498", "3504", "3406", "2340", "6209", "3059", "6176"],
    },
    {
        "name": "金控金融",
        "baseline_100m": 150.0,
        "codes": ["2881", "2882", "2891", "2886", "2884", "2885", "2892", "2880", "2883", "2887", "2890", "5880"],
    },
    {
        "name": "5G／6G 網通",
        "baseline_100m": 55.0,
        "codes": ["2345", "6285", "5388", "3596", "3704", "2419", "3380"],
    },
    {
        "name": "AI PC／邊緣運算",
        "baseline_100m": 65.0,
        "codes": ["2357", "2353", "2324", "2377", "2376", "2395", "3005", "6414"],
    },
    {
        "name": "半導體設備與耗材",
        "baseline_100m": 52.0,
        "codes": ["1560", "2467", "6196", "3680", "6438", "3413", "2464", "8028"],
    },
    {
        "name": "戰後重建",
        "baseline_100m": 48.0,
        "codes": ["2002", "1101", "1102", "2606", "2027", "2014", "2637"],
    },
    {
        "name": "貨櫃航運",
        "baseline_100m": 85.0,
        "codes": ["2603", "2609", "2615", "2637", "2606"],
    },
    {
        "name": "節能儲能",
        "baseline_100m": 38.0,
        "codes": ["1519", "1513", "6806", "1503", "6443", "3576"],
    },
    {
        "name": "二極體",
        "baseline_100m": 28.0,
        "codes": ["2481", "3675", "5425", "8261"],
    },
    {
        "name": "資安",
        "baseline_100m": 25.0,
        "codes": ["6214", "2453", "3029", "5203", "2471", "6690"],
    },
    {
        "name": "機器人",
        "baseline_100m": 46.0,
        "codes": ["2049", "1590", "2359", "2395", "4576", "8374", "6669"],
    },
    {
        "name": "BBU 備援電池",
        "baseline_100m": 32.0,
        "codes": ["6781", "2308", "2301", "6282", "1513"],
    },
    {
        "name": "生技醫材／新藥",
        "baseline_100m": 35.0,
        "codes": ["1795", "6446", "4746", "1760", "4142", "6589", "1707"],
    },
]

US_INDICES_SPECS = [
    {"symbol": ".DJI",  "code": "DJI",  "name": "道瓊工業指數", "en_name": "Dow Jones Industrial"},
    {"symbol": ".IXIC", "code": "IXIC", "name": "那斯達克指數", "en_name": "Nasdaq Composite"},
    {"symbol": ".SPX",  "code": "SPX",  "name": "標普 500 指數", "en_name": "S&P 500 Index"},
    {"symbol": ".SOX",  "code": "SOX",  "name": "費城半導體指數", "en_name": "PHLX Semiconductor"},
]

ASIA_INDICES_SPECS = [
    {
        "symbol": ".N225",
        "alt_symbols": ["N225", "@NK.1"],
        "code": "N225",
        "name": "日經 225 指數",
        "en_name": "Nikkei 225 Index (Japan)",
    },
    {
        "symbol": ".KS11",
        "alt_symbols": ["KS11", ".KOSPI"],
        "code": "KOSPI",
        "name": "韓國綜合指數 (KOSPI)",
        "en_name": "KOSPI Composite Index (Korea)",
    },
]

TW_ADR_SPECS = [
    {"symbol": "TSM",   "alt_symbols": [],                   "code": "TSM",   "name": "台積電 ADR", "tw_code": "2330", "tw_name": "台積電", "ratio": 5.0},
    {"symbol": "ASX",   "alt_symbols": [],                   "code": "ASX",   "name": "日月光 ADR", "tw_code": "3711", "tw_name": "日月光投控", "ratio": 2.0},
    {"symbol": "HNHPF", "alt_symbols": ["HNHAY", "HHPD-GB"], "code": "HNHPF", "name": "鴻海 ADR",   "tw_code": "2317", "tw_name": "鴻海", "ratio": 2.0},
    {"symbol": "UMC",   "alt_symbols": [],                   "code": "UMC",   "name": "聯電 ADR",   "tw_code": "2303", "tw_name": "聯電", "ratio": 5.0},
]


def fetch_json(url, method="GET", data=None, headers=None, retries=3):
    h = dict(HEADERS)
    if headers:
        h.update(headers)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method=method)
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return json.loads(raw)
        except Exception as e:
            last_err = e
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def parse_num(val, default=0.0):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("--", "").replace("X", "")
    s = re.sub(r"<[^>]+>", "", s).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def parse_sign(html_or_str):
    if not html_or_str:
        return 0
    s = str(html_or_str)
    if "+" in s or "red" in s.lower():
        return 1
    if "-" in s or "green" in s.lower():
        return -1
    return 0


def roc_to_iso(roc_str):
    parts = str(roc_str).strip().split("/")
    if len(parts) == 3:
        try:
            y = int(parts[0]) + 1911
            return f"{y:04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        except ValueError:
            pass
    return str(roc_str)


def prev_month_date_str(yyyymmdd):
    dt = datetime.datetime.strptime(yyyymmdd, "%Y%m%d")
    first = dt.replace(day=1)
    prev = first - datetime.timedelta(days=1)
    return prev.strftime("%Y%m01")


def fetch_taiex_history():
    print("[1/8] Fetching TWSE TAIEX daily trend (FMTQIK & MI_5MINS_HIST)...")
    fmt_curr = fetch_json("https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?response=json")
    latest_date = fmt_curr.get("date", datetime.datetime.now().strftime("%Y%m%d"))
    prev_m_str = prev_month_date_str(latest_date)

    time.sleep(0.35)
    fmt_prev = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?response=json&date={prev_m_str}"
    )
    time.sleep(0.35)
    hist_curr = fetch_json("https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?response=json")
    time.sleep(0.35)
    hist_prev = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST?response=json&date={prev_m_str}"
    )

    ohlc_map = {}
    for src in (hist_prev, hist_curr):
        for row in src.get("data", []) or []:
            if len(row) >= 5:
                d_iso = roc_to_iso(row[0])
                ohlc_map[d_iso] = {
                    "open": parse_num(row[1]),
                    "high": parse_num(row[2]),
                    "low": parse_num(row[3]),
                    "close": parse_num(row[4]),
                }

    series_map = {}
    for src in (fmt_prev, fmt_curr):
        for row in src.get("data", []) or []:
            if len(row) >= 6:
                d_iso = roc_to_iso(row[0])
                close_val = parse_num(row[4])
                chg_val = parse_num(row[5])
                ohlc = ohlc_map.get(d_iso, {})
                prev_close = close_val - chg_val
                pct = (chg_val / prev_close * 100.0) if prev_close else 0.0
                series_map[d_iso] = {
                    "date": d_iso,
                    "roc_date": row[0],
                    "volume_shares": int(parse_num(row[1])),
                    "turnover_twd": int(parse_num(row[2])),
                    "turnover_100m": round(parse_num(row[2]) / 1e8, 2),
                    "transactions": int(parse_num(row[3])),
                    "open": ohlc.get("open", close_val),
                    "high": ohlc.get("high", close_val),
                    "low": ohlc.get("low", close_val),
                    "close": close_val,
                    "change": chg_val,
                    "change_pct": round(pct, 2),
                }

    series = [series_map[k] for k in sorted(series_map.keys())]
    if series:
        latest_date = series[-1]["date"].replace("-", "")
    return latest_date, series


def fetch_institutional_summary(target_date):
    print(f"  -> Fetching TWSE Institutional summary (BFI82U {target_date})...")
    bfi = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json&dayDate={target_date}"
    )
    items = []
    for row in bfi.get("data", []) or []:
        if len(row) >= 4:
            buy_twd = parse_num(row[1])
            sell_twd = parse_num(row[2])
            net_twd = parse_num(row[3])
            items.append({
                "name": str(row[0]).strip(),
                "buy_twd": int(buy_twd),
                "sell_twd": int(sell_twd),
                "net_twd": int(net_twd),
                "buy_100m": round(buy_twd / 1e8, 2),
                "sell_100m": round(sell_twd / 1e8, 2),
                "net_100m": round(net_twd / 1e8, 2),
            })
    return {
        "date": roc_to_iso(
            f"{int(target_date[:4]) - 1911}/{target_date[4:6]}/{target_date[6:8]}"
        ),
        "title": bfi.get("title", "三大法人買賣金額統計表"),
        "items": items,
    }


def fetch_market_stocks_and_top15(target_date):
    print(f"  -> Fetching TWSE MI_INDEX (ALLBUT0999) for stocks & Top 15 ({target_date})...")
    mi = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={target_date}&type=ALLBUT0999"
    )
    tables = mi.get("tables", []) or []

    breadth = {}
    for tb in tables:
        title = tb.get("title") or ""
        if "漲跌證券數" in title:
            for row in tb.get("data", []) or []:
                if len(row) >= 3:
                    breadth[str(row[0]).strip()] = {
                        "all_market": str(row[1]).strip(),
                        "stocks": str(row[2]).strip(),
                    }

    stock_rows = []
    for tb in tables:
        fields = tb.get("fields") or []
        if "證券代號" in fields and "成交金額" in fields and "收盤價" in fields:
            stock_rows = tb.get("data", []) or []
            break

    stock_map = {}
    all_stocks = []
    for row in stock_rows:
        if len(row) < 11:
            continue
        code = str(row[0]).strip()
        name = str(row[1]).strip()
        vol_shares = int(parse_num(row[2]))
        vol_lots = round(vol_shares / 1000.0, 1)
        tx_count = int(parse_num(row[3]))
        turnover_twd = int(parse_num(row[4]))
        turnover_100m = round(turnover_twd / 1e8, 2)
        open_p = parse_num(row[5])
        high_p = parse_num(row[6])
        low_p = parse_num(row[7])
        close_p = parse_num(row[8])
        sign = parse_sign(row[9])
        diff = parse_num(row[10]) * (sign if sign != 0 else 1)
        prev_c = close_p - diff
        chg_pct = round((diff / prev_c * 100.0), 2) if prev_c > 0 else 0.0

        info = {
            "code": code,
            "name": name,
            "volume_shares": vol_shares,
            "volume_lots": int(round(vol_lots)),
            "transactions": tx_count,
            "turnover_twd": turnover_twd,
            "turnover_100m": turnover_100m,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "change": round(diff, 2),
            "change_pct": chg_pct,
        }
        stock_map[code] = info
        all_stocks.append(info)

    top15_value = sorted(all_stocks, key=lambda x: x["turnover_twd"], reverse=True)[:15]
    for i, item in enumerate(top15_value, 1):
        item["rank_value"] = i

    top15_volume = sorted(all_stocks, key=lambda x: x["volume_shares"], reverse=True)[:15]
    for i, item in enumerate(top15_volume, 1):
        item["rank_volume"] = i

    return stock_map, top15_value, top15_volume, breadth


def fetch_institutional_top50(target_date, stock_map):
    print(f"  -> Fetching TWSE T86 for Foreign/Trust/Dealer Top 50 ({target_date})...")
    t86 = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={target_date}&selectType=ALLBUT0999"
    )
    rows = t86.get("data", []) or []
    records = []
    inst_by_code = {}

    for row in rows:
        if len(row) < 19:
            continue
        code = str(row[0]).strip()
        name = str(row[1]).strip()

        f_buy = int(parse_num(row[2]) + parse_num(row[5]))
        f_sell = int(parse_num(row[3]) + parse_num(row[6]))
        f_net = int(parse_num(row[4]) + parse_num(row[7]))

        t_buy = int(parse_num(row[8]))
        t_sell = int(parse_num(row[9]))
        t_net = int(parse_num(row[10]))

        d_net = int(parse_num(row[11]))
        d_self_buy = int(parse_num(row[12]))
        d_self_sell = int(parse_num(row[13]))
        d_self_net = int(parse_num(row[14]))
        d_hedge_buy = int(parse_num(row[15]))
        d_hedge_sell = int(parse_num(row[16]))
        d_hedge_net = int(parse_num(row[17]))
        d_buy = d_self_buy + d_hedge_buy
        d_sell = d_self_sell + d_hedge_sell

        total_net = int(parse_num(row[18]))

        st = stock_map.get(code, {})
        close_p = st.get("close", 0.0)
        chg_pct = st.get("change_pct", 0.0)

        rec = {
            "code": code,
            "name": name,
            "close": close_p,
            "change_pct": chg_pct,
            "foreign_buy_lots": int(round(f_buy / 1000.0)),
            "foreign_sell_lots": int(round(f_sell / 1000.0)),
            "foreign_net_lots": int(round(f_net / 1000.0)),
            "foreign_net_shares": f_net,
            "foreign_est_m": round(f_net * close_p / 1e6, 1) if close_p else 0.0,
            "trust_buy_lots": int(round(t_buy / 1000.0)),
            "trust_sell_lots": int(round(t_sell / 1000.0)),
            "trust_net_lots": int(round(t_net / 1000.0)),
            "trust_net_shares": t_net,
            "trust_est_m": round(t_net * close_p / 1e6, 1) if close_p else 0.0,
            "dealer_buy_lots": int(round(d_buy / 1000.0)),
            "dealer_sell_lots": int(round(d_sell / 1000.0)),
            "dealer_net_lots": int(round(d_net / 1000.0)),
            "dealer_self_net_lots": int(round(d_self_net / 1000.0)),
            "dealer_hedge_net_lots": int(round(d_hedge_net / 1000.0)),
            "dealer_net_shares": d_net,
            "dealer_est_m": round(d_net * close_p / 1e6, 1) if close_p else 0.0,
            "total_net_lots": int(round(total_net / 1000.0)),
            "total_net_shares": total_net,
            "total_est_m": round(total_net * close_p / 1e6, 1) if close_p else 0.0,
        }
        records.append(rec)
        inst_by_code[code] = rec

    def top50_pair(key_shares):
        buy50 = [r for r in sorted(records, key=lambda x: x[key_shares], reverse=True) if r[key_shares] > 0][:50]
        sell50 = [r for r in sorted(records, key=lambda x: x[key_shares]) if r[key_shares] < 0][:50]
        return buy50, sell50

    f_buy50, f_sell50 = top50_pair("foreign_net_shares")
    t_buy50, t_sell50 = top50_pair("trust_net_shares")
    d_buy50, d_sell50 = top50_pair("dealer_net_shares")
    tot_buy50, tot_sell50 = top50_pair("total_net_shares")

    return {
        "foreign": {"buy50": f_buy50, "sell50": f_sell50},
        "trust": {"buy50": t_buy50, "sell50": t_sell50},
        "dealer": {"buy50": d_buy50, "sell50": d_sell50},
        "total": {"buy50": tot_buy50, "sell50": tot_sell50},
    }, inst_by_code


def build_concept_sectors(stock_map, inst_by_code, taiex_series):
    recent_dates = [d["date"] for d in taiex_series[-20:]] if taiex_series else []
    recent_mkt_chg = [d.get("change_pct", 0.0) for d in taiex_series[-20:]] if taiex_series else []
    latest_mkt_chg = recent_mkt_chg[-1] if recent_mkt_chg else 0.0

    raw_sectors = []
    for idx, cg in enumerate(CONCEPT_GROUPS):
        name = cg["name"]
        matched_stocks = []

        for code in cg["codes"]:
            st = stock_map.get(code)
            if not st:
                continue
            ic = inst_by_code.get(code, {})
            matched_stocks.append({
                "code": code,
                "name": st["name"],
                "close": st["close"],
                "change": st["change"],
                "change_pct": st["change_pct"],
                "turnover_100m": st["turnover_100m"],
                "volume_lots": st["volume_lots"],
                "foreign_net_lots": ic.get("foreign_net_lots", 0),
                "trust_net_lots": ic.get("trust_net_lots", 0),
                "dealer_net_lots": ic.get("dealer_net_lots", 0),
                "total_net_lots": ic.get("total_net_lots", 0),
                "total_est_m": ic.get("total_est_m", 0.0),
            })

        matched_stocks.sort(key=lambda x: x["turnover_100m"], reverse=True)

        if matched_stocks:
            capped_turnovers = [
                min(s["turnover_100m"], 220.0) if s["code"] == "2330" else s["turnover_100m"]
                for s in matched_stocks
            ]
            total_turnover_100m = round(sum(s["turnover_100m"] for s in matched_stocks), 2)
            display_weight = round(sum(capped_turnovers), 2)
            per_stock_turnover = display_weight / len(matched_stocks)
            avg_chg = round(
                sum(s["change_pct"] for s in matched_stocks) / len(matched_stocks), 2
            )
            inst_net_m = round(sum(s["total_est_m"] for s in matched_stocks), 1)
            inst_net_100m = round(inst_net_m / 100.0, 2)
            up_count = sum(1 for s in matched_stocks if s["change_pct"] > 0)
            down_count = sum(1 for s in matched_stocks if s["change_pct"] < 0)
        else:
            total_turnover_100m = 10.0
            display_weight = 10.0
            per_stock_turnover = 2.0
            avg_chg = 0.0
            inst_net_100m = 0.0
            up_count = 0
            down_count = 0

        raw_sectors.append({
            "idx": idx,
            "name": name,
            "matched_stocks": matched_stocks,
            "total_turnover_100m": total_turnover_100m,
            "display_weight": max(display_weight, 15.0),
            "per_stock_turnover": per_stock_turnover,
            "avg_chg": avg_chg,
            "inst_net_100m": inst_net_100m,
            "up_count": up_count,
            "down_count": down_count,
        })

    sorted_pst = sorted(s["per_stock_turnover"] for s in raw_sectors)
    median_pst = sorted_pst[len(sorted_pst) // 2] if sorted_pst else 25.0
    avg_chg_all = sum(s["avg_chg"] for s in raw_sectors) / max(len(raw_sectors), 1)

    sectors = []
    for s in raw_sectors:
        idx = s["idx"]
        flow_rel_pct = round(((s["per_stock_turnover"] - median_pst) / max(median_pst, 1.0)) * 100.0, 1)
        flow_rel_pct = max(-98.0, min(428.0, flow_rel_pct))

        rel_chg = s["avg_chg"] - (avg_chg_all * 0.85)
        inst_ratio = (s["inst_net_100m"] / max(s["display_weight"], 10.0)) * 180.0
        raw_momentum = rel_chg * 28.0 + inst_ratio
        momentum_y = round(max(-260.0, min(260.0, raw_momentum)), 1)

        if flow_rel_pct >= 0 and momentum_y >= 0:
            quadrant = "inflow"
        elif flow_rel_pct < 0 and momentum_y >= 0:
            quadrant = "watch"
        elif flow_rel_pct < 0 and momentum_y < 0:
            quadrant = "outflow"
        else:
            quadrant = "rotate"

        trail = []
        n_days = len(recent_dates)
        for d_idx, d_str in enumerate(recent_dates):
            progress = (d_idx + 1) / max(n_days, 1)
            phase = (idx * 0.75) + (d_idx * 0.38)
            mkt_bias = (recent_mkt_chg[d_idx] - latest_mkt_chg) if d_idx < len(recent_mkt_chg) else 0.0
            decay = 1.0 - progress
            sim_x = flow_rel_pct + decay * (math.sin(phase) * 85.0 - flow_rel_pct * 0.35)
            sim_y = momentum_y + decay * (math.cos(phase * 1.1) * 95.0 + mkt_bias * 18.0)
            if d_idx == n_days - 1:
                sim_x = flow_rel_pct
                sim_y = momentum_y
            trail.append({
                "date": d_str,
                "x": round(max(-98.0, min(428.0, sim_x)), 1),
                "y": round(max(-280.0, min(280.0, sim_y)), 1),
            })

        sectors.append({
            "id": f"sec-{idx+1}",
            "name": s["name"],
            "avg_change_pct": s["avg_chg"],
            "turnover_100m": s["total_turnover_100m"],
            "display_weight": s["display_weight"],
            "inst_net_100m": s["inst_net_100m"],
            "flow_rel_pct": flow_rel_pct,
            "momentum_y": momentum_y,
            "quadrant": quadrant,
            "up_count": s["up_count"],
            "down_count": s["down_count"],
            "stock_count": len(s["matched_stocks"]),
            "stocks": s["matched_stocks"],
            "trail": trail,
        })

    sectors.sort(key=lambda x: x["display_weight"], reverse=True)
    return {
        "dates": recent_dates,
        "sectors": sectors,
    }


def fetch_warrants_top20(target_date):
    print(f"  -> Fetching TWSE Warrants Call (0999) & Put (0999P) Top 20 ({target_date})...")
    warrants = []
    for w_type, label in [("0999", "認購"), ("0999P", "認售")]:
        time.sleep(0.35)
        mi_w = fetch_json(
            f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={target_date}&type={w_type}"
        )
        for tb in mi_w.get("tables", []) or []:
            fields = tb.get("fields") or []
            if "證券代號" in fields and "標的代號" in fields:
                for row in tb.get("data", []) or []:
                    if len(row) < 20:
                        continue
                    vol_shares = int(parse_num(row[3]))
                    if vol_shares <= 0:
                        continue
                    turnover_twd = int(parse_num(row[5]))
                    close_p = parse_num(row[9])
                    sign = parse_sign(row[10])
                    diff = parse_num(row[11]) * (sign if sign != 0 else 1)
                    prev_c = close_p - diff
                    chg_pct = round((diff / prev_c * 100.0), 2) if prev_c > 0 else 0.0
                    warrants.append({
                        "code": str(row[1]).strip(),
                        "name": str(row[2]).strip(),
                        "type": label,
                        "volume_shares": vol_shares,
                        "volume_lots": int(round(vol_shares / 1000.0)),
                        "transactions": int(parse_num(row[4])),
                        "turnover_twd": turnover_twd,
                        "turnover_10k": round(turnover_twd / 1e4, 1),
                        "close": close_p,
                        "change": round(diff, 2),
                        "change_pct": chg_pct,
                        "target_code": str(row[17]).strip(),
                        "target_name": str(row[18]).strip(),
                        "target_close": parse_num(row[19]),
                    })

    top20_by_vol = sorted(warrants, key=lambda x: x["volume_shares"], reverse=True)[:20]
    for i, w in enumerate(top20_by_vol, 1):
        w["rank_vol"] = i

    top20_by_val = sorted(warrants, key=lambda x: x["turnover_twd"], reverse=True)[:20]
    for i, w in enumerate(top20_by_val, 1):
        w["rank_val"] = i

    total_warrant_turnover = sum(w["turnover_twd"] for w in warrants)
    total_warrant_lots = sum(w["volume_lots"] for w in warrants)

    return {
        "total_turnover_100m": round(total_warrant_turnover / 1e8, 2),
        "total_volume_lots": total_warrant_lots,
        "active_count": len(warrants),
        "top20_volume": top20_by_vol,
        "top20_value": top20_by_val,
    }


def fetch_single_twse_day_snapshot(date_raw, date_iso, taiex_series_up_to_date, use_cache=True):
    """
    抓取或從本地快取讀取指定交易日 (YYYYMMDD) 的完整台股盤後資料快照
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    cache_file = os.path.join(HISTORY_DIR, f"twse_{date_raw}.json")
    if use_cache and os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as cf:
                cached = json.load(cf)
            if cached.get("twse_date") == date_iso and cached.get("top15_value"):
                print(f"  [Cache Hit] Loaded {date_iso} snapshot from {cache_file}")
                return cached, {}
        except Exception:
            pass

    print(f"[TWSE Snapshot] Fetching full Taiwan market data for {date_iso} ({date_raw})...")
    time.sleep(0.35)
    inst_summary = fetch_institutional_summary(date_raw)
    time.sleep(0.35)
    stock_map, top15_value, top15_volume, breadth = fetch_market_stocks_and_top15(date_raw)
    time.sleep(0.35)
    inst_top50, inst_by_code = fetch_institutional_top50(date_raw, stock_map)

    for item in top15_value + top15_volume:
        ic = inst_by_code.get(item["code"], {})
        item["foreign_net_lots"] = ic.get("foreign_net_lots", 0)
        item["trust_net_lots"] = ic.get("trust_net_lots", 0)
        item["dealer_net_lots"] = ic.get("dealer_net_lots", 0)
        item["total_net_lots"] = ic.get("total_net_lots", 0)

    concept_sectors = build_concept_sectors(stock_map, inst_by_code, taiex_series_up_to_date)
    time.sleep(0.35)
    warrants_data = fetch_warrants_top20(date_raw)

    taiex_day = taiex_series_up_to_date[-1] if taiex_series_up_to_date else {}
    # 只保留關鍵母股價格給 ADR 折溢價計算
    adr_parent_stocks = {
        code: stock_map.get(code, {})
        for code in ["2330", "3711", "2317", "2303"]
        if code in stock_map
    }

    snapshot = {
        "twse_date": date_iso,
        "twse_date_raw": date_raw,
        "taiex_latest": taiex_day,
        "taiex_breadth": breadth,
        "institutional_summary": inst_summary,
        "institutional_top50": inst_top50,
        "top15_value": top15_value,
        "top15_volume": top15_volume,
        "concept_sectors": concept_sectors,
        "warrants": warrants_data,
        "adr_parent_stocks": adr_parent_stocks,
    }

    try:
        with open(cache_file, "w", encoding="utf-8") as cf:
            json.dump(snapshot, cf, ensure_ascii=False)
    except Exception as e:
        print(f"  [WARN] Failed to write history cache {cache_file}: {e}")

    return snapshot, stock_map


def fetch_taifex_night_session():
    print("[6/8] Fetching TAIFEX Night Session TXF quotes & 1-minute chart...")
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Referer": "https://mis.taifex.com.tw/futures/AfterHoursSession/",
    }
    qd = fetch_json(
        "https://mis.taifex.com.tw/futures/api/getQuoteList",
        method="POST",
        data=json.dumps({
            "MarketType": "1",
            "SymbolType": "F",
            "KindID": "1",
            "CID": "TXF",
            "ExpireMonth": "",
            "RowSize": "全部",
            "PageNo": "",
            "SortColumn": "",
            "AscDesc": "A",
        }).encode("utf-8"),
        headers=headers,
    )
    quotes = qd.get("RtData", {}).get("QuoteList", [])
    txf_near = next(
        (q for q in quotes if q.get("SymbolID", "").endswith("-M") and q.get("CLastPrice")),
        quotes[1] if len(quotes) > 1 else {},
    )
    sym_id = txf_near.get("SymbolID", "TXFK6-M")
    cd = fetch_json(
        "https://mis.taifex.com.tw/futures/api/getChartData1M",
        method="POST",
        data=json.dumps({"SymbolID": sym_id}).encode("utf-8"),
        headers=headers,
    )
    rt = cd.get("RtData", {})
    quote_info = rt.get("Quote", {}) or txf_near
    raw_ticks = rt.get("Ticks", []) or []
    field_list = rt.get("Field", []) or []

    ticks = []
    for t in raw_ticks:
        if isinstance(t, dict):
            tm = str(t.get("T", t.get("Time", ""))).strip()
            close_p = parse_num(t.get("C", t.get("Close", t.get("P", 0))))
            open_p = parse_num(t.get("O", close_p))
            high_p = parse_num(t.get("H", close_p))
            low_p = parse_num(t.get("L", close_p))
            vol = int(parse_num(t.get("V", t.get("Vol", 0))))
        elif isinstance(t, list) and field_list:
            d = dict(zip(field_list, t))
            tm = str(d.get("T", d.get("Time", t[0] if t else ""))).strip()
            close_p = parse_num(d.get("C", d.get("Close", 0)))
            open_p = parse_num(d.get("O", close_p))
            high_p = parse_num(d.get("H", close_p))
            low_p = parse_num(d.get("L", close_p))
            vol = int(parse_num(d.get("V", 0)))
        elif isinstance(t, list) and len(t) >= 5:
            tm = str(t[0])
            open_p = parse_num(t[1])
            high_p = parse_num(t[2])
            low_p = parse_num(t[3])
            close_p = parse_num(t[4])
            vol = int(parse_num(t[5])) if len(t) > 5 else 0
        else:
            continue

        if close_p > 0:
            if len(tm) >= 4 and tm.isdigit():
                tm_fmt = f"{tm[:2]}:{tm[2:4]}"
            else:
                tm_fmt = tm
            ticks.append({
                "time": tm_fmt,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "close": close_p,
                "volume": vol,
            })

    last_p = parse_num(txf_near.get("CLastPrice") or quote_info.get("CLastPrice"))
    ref_p = parse_num(txf_near.get("CRefPrice") or quote_info.get("CRefPrice"))
    diff = parse_num(txf_near.get("CDiff"), last_p - ref_p if (last_p and ref_p) else 0.0)
    diff_rate = parse_num(
        txf_near.get("CDiffRate"),
        round(diff / ref_p * 100.0, 2) if ref_p else 0.0,
    )

    return {
        "symbol_id": sym_id,
        "name": txf_near.get("DispCName", "臺指期近月(夜盤)"),
        "last": last_p,
        "open": parse_num(txf_near.get("COpenPrice") or quote_info.get("COpenPrice")),
        "high": parse_num(txf_near.get("CHighPrice") or quote_info.get("CHighPrice")),
        "low": parse_num(txf_near.get("CLowPrice") or quote_info.get("CLowPrice")),
        "ref_price": ref_p,
        "change": diff,
        "change_pct": round(diff_rate, 2),
        "volume": int(parse_num(txf_near.get("CTotalVolume") or quote_info.get("CTotalVolume"))),
        "update_time": txf_near.get("CTime", ""),
        "ticks": ticks,
    }


def fetch_cnbc_symbol(symbol, display_name, extra_meta=None):
    now = datetime.datetime.now()
    start_1d = (now - datetime.timedelta(days=110)).strftime("%Y%m%d000000")
    start_intraday = (now - datetime.timedelta(days=6)).strftime("%Y%m%d000000")
    end_str = (now + datetime.timedelta(days=2)).strftime("%Y%m%d000000")

    enc_sym = urllib.parse.quote(symbol, safe=".")
    url_1d = f"https://ts-api.cnbc.com/harmony/app/bars/{enc_sym}/1D/{start_1d}/{end_str}/adjusted/EST5EDT.json"
    url_30m = f"https://ts-api.cnbc.com/harmony/app/bars/{enc_sym}/30M/{start_intraday}/{end_str}/adjusted/EST5EDT.json"

    d1 = fetch_json(url_1d)
    bars_1d = []
    for b in d1.get("barData", {}).get("priceBars", []) or []:
        c = parse_num(b.get("close"))
        if c <= 0:
            continue
        t_raw = str(b.get("tradeTime", ""))
        d_str = f"{t_raw[:4]}-{t_raw[4:6]}-{t_raw[6:8]}" if len(t_raw) >= 8 else t_raw
        bars_1d.append({
            "date": d_str,
            "open": parse_num(b.get("open"), c),
            "high": parse_num(b.get("high"), c),
            "low": parse_num(b.get("low"), c),
            "close": c,
            "volume": int(parse_num(b.get("volume"), 0)),
        })

    bars_intra = []
    try:
        d_intra = fetch_json(url_30m)
        for b in d_intra.get("barData", {}).get("priceBars", []) or []:
            c = parse_num(b.get("close"))
            if c <= 0:
                continue
            t_raw = str(b.get("tradeTime", ""))
            lbl = (
                f"{t_raw[4:6]}/{t_raw[6:8]} {t_raw[8:10]}:{t_raw[10:12]}"
                if len(t_raw) >= 12
                else t_raw
            )
            bars_intra.append({
                "time": lbl,
                "open": parse_num(b.get("open"), c),
                "high": parse_num(b.get("high"), c),
                "low": parse_num(b.get("low"), c),
                "close": c,
                "volume": int(parse_num(b.get("volume"), 0)),
            })
    except Exception:
        pass

    latest = bars_1d[-1] if bars_1d else {}
    prev = bars_1d[-2] if len(bars_1d) >= 2 else latest
    last_c = latest.get("close", 0.0)
    prev_c = prev.get("close", last_c)
    chg = round(last_c - prev_c, 2)
    chg_pct = round((chg / prev_c * 100.0), 2) if prev_c else 0.0

    res = {
        "symbol": symbol,
        "name": display_name,
        "last": last_c,
        "open": latest.get("open", 0.0),
        "high": latest.get("high", 0.0),
        "low": latest.get("low", 0.0),
        "volume": latest.get("volume", 0),
        "date": latest.get("date", ""),
        "change": chg,
        "change_pct": chg_pct,
        "daily_bars": bars_1d[-60:],
        "intraday_bars": bars_intra[-96:],
    }
    if extra_meta:
        res.update(extra_meta)
    return res


def fetch_us_asia_indices_and_tw_adrs(stock_map):
    print("[8/8] Fetching US 4 Major Indices, Japan/Korea Indices (.N225, .KS11) & Taiwan ADRs...")
    # 1. Fetch USD/TWD exchange rate for ADR premium/discount conversion
    usd_twd = 32.15
    try:
        fx_data = fetch_cnbc_symbol("TWD=", "USD/TWD")
        if fx_data.get("last", 0) > 25:
            usd_twd = fx_data["last"]
    except Exception:
        pass

    # 2. Fetch US 4 Major Indices
    us_indices = []
    for spec in US_INDICES_SPECS:
        try:
            item = fetch_cnbc_symbol(
                spec["symbol"],
                spec["name"],
                {"code": spec["code"], "en_name": spec["en_name"]},
            )
            us_indices.append(item)
        except Exception as e:
            print(f"  [WARN] Failed US index {spec['symbol']}: {e}")

    # 3. Fetch Japan Nikkei 225 & Korea KOSPI Indices
    asia_indices = []
    for spec in ASIA_INDICES_SPECS:
        candidates = [spec["symbol"]] + spec.get("alt_symbols", [])
        for cand in candidates:
            try:
                item = fetch_cnbc_symbol(
                    cand,
                    spec["name"],
                    {"code": spec["code"], "en_name": spec["en_name"]},
                )
                if item.get("daily_bars"):
                    asia_indices.append(item)
                    break
            except Exception as e:
                print(f"  [WARN] Failed Asia index {cand}: {e}")

    # 4. Fetch Taiwan 4 Major ADRs
    tw_adrs = []
    for spec in TW_ADR_SPECS:
        candidates = [spec["symbol"]] + spec.get("alt_symbols", [])
        fetched = None
        for cand in candidates:
            try:
                cand_data = fetch_cnbc_symbol(cand, spec["name"])
                if cand_data.get("daily_bars"):
                    fetched = cand_data
                    break
            except Exception:
                continue

        tw_st = stock_map.get(spec["tw_code"], {})
        tw_close = tw_st.get("close", 0.0)
        tw_chg_pct = tw_st.get("change_pct", 0.0)

        if fetched:
            adr_last = fetched.get("last", 0.0)
            ratio = spec["ratio"]
            implied_twd = round((adr_last * usd_twd) / ratio, 2) if ratio else 0.0
            premium_pct = (
                round(((implied_twd - tw_close) / tw_close) * 100.0, 2)
                if tw_close > 0
                else 0.0
            )
            fetched.update({
                "code": spec["code"],
                "tw_code": spec["tw_code"],
                "tw_name": spec["tw_name"],
                "tw_close": tw_close,
                "tw_change_pct": tw_chg_pct,
                "ratio": ratio,
                "usd_twd": round(usd_twd, 3),
                "implied_tw_price": implied_twd,
                "premium_pct": premium_pct,
            })
            tw_adrs.append(fetched)

    return {
        "usd_twd": round(usd_twd, 3),
        "us_indices": us_indices,
        "asia_indices": asia_indices,
        "tw_adrs": tw_adrs,
    }


def slice_cnbc_item_for_date(item, target_date_iso, day_offset_idx=0):
    """
    根據指定交易日 (target_date_iso) 或倒數第 day_offset_idx 個交易日，
    切出該標的截至當日的報價、漲跌幅、日K與分時走勢，並附上近5個交易日明細 (recent_5d)
    """
    if not item:
        return {}
    res = dict(item)
    daily_bars = list(item.get("daily_bars") or [])
    intra_bars = list(item.get("intraday_bars") or [])

    if not daily_bars:
        res["recent_5d"] = []
        return res

    # 計算每一根日K的漲跌與漲跌幅
    enriched_bars = []
    for i, b in enumerate(daily_bars):
        prev_b = daily_bars[i - 1] if i > 0 else b
        c = float(b.get("close", 0.0))
        pc = float(prev_b.get("close", c))
        chg = round(c - pc, 2)
        chg_pct = round((chg / pc * 100.0), 2) if pc else 0.0
        eb = dict(b)
        eb["change"] = chg
        eb["change_pct"] = chg_pct
        enriched_bars.append(eb)

    # 決定截至 target_date_iso 的日K序列
    if day_offset_idx == 0:
        bars_up_to = enriched_bars[:]
    else:
        matched = [b for b in enriched_bars if b.get("date", "") <= target_date_iso]
        if matched:
            bars_up_to = matched
        else:
            cut = max(1, len(enriched_bars) - day_offset_idx)
            bars_up_to = enriched_bars[:cut]

    latest = bars_up_to[-1]
    res["last"] = latest.get("close", 0.0)
    res["open"] = latest.get("open", 0.0)
    res["high"] = latest.get("high", 0.0)
    res["low"] = latest.get("low", 0.0)
    res["volume"] = latest.get("volume", 0)
    res["date"] = latest.get("date", target_date_iso)
    res["change"] = latest.get("change", 0.0)
    res["change_pct"] = latest.get("change_pct", 0.0)
    res["daily_bars"] = bars_up_to[-60:]
    res["recent_5d"] = list(reversed(bars_up_to[-5:]))

    # 若為最新交易日 (day_offset_idx == 0) 且有更新的盤中分時K線 (例如亞洲股市當日或期貨即時報價)，
    # 但 CNBC 1D bar 尚未寫入當日收盤棒時，自動以最新分時價格更新即時報價與當日K棒
    if day_offset_idx == 0 and intra_bars:
        last_intra = intra_bars[-1]
        intra_mmdd = str(last_intra.get("time", ""))[:5]  # e.g. "10/26"
        latest_mmdd = res["date"][5:7] + "/" + res["date"][8:10] if len(res["date"]) >= 10 else ""
        if intra_mmdd and intra_mmdd != latest_mmdd:
            yyyy = res["date"][:4] if len(res["date"]) >= 4 else str(datetime.datetime.now().year)
            intra_date_iso = f"{yyyy}-{intra_mmdd[:2]}-{intra_mmdd[3:5]}"
            if intra_date_iso > res["date"]:
                same_day_intra = [b for b in intra_bars if str(b.get("time", ""))[:5] == intra_mmdd]
                prev_close = float(latest.get("close", 0.0))
                cur_c = float(last_intra.get("close", prev_close))
                cur_o = float(same_day_intra[0].get("open", cur_c)) if same_day_intra else cur_c
                cur_h = max(float(b.get("high", cur_c)) for b in same_day_intra) if same_day_intra else cur_c
                cur_l = min(float(b.get("low", cur_c)) for b in same_day_intra) if same_day_intra else cur_c
                cur_v = sum(int(b.get("volume", 0)) for b in same_day_intra)
                chg = round(cur_c - prev_close, 2)
                chg_pct = round((chg / prev_close * 100.0), 2) if prev_close else 0.0

                live_bar = {
                    "date": intra_date_iso,
                    "open": cur_o,
                    "high": cur_h,
                    "low": cur_l,
                    "close": cur_c,
                    "volume": cur_v,
                    "change": chg,
                    "change_pct": chg_pct,
                }
                res["last"] = cur_c
                res["open"] = cur_o
                res["high"] = cur_h
                res["low"] = cur_l
                res["volume"] = cur_v
                res["date"] = intra_date_iso
                res["change"] = chg
                res["change_pct"] = chg_pct
                bars_up_to = bars_up_to + [live_bar]
                res["daily_bars"] = bars_up_to[-60:]
                res["recent_5d"] = list(reversed(bars_up_to[-5:]))

    # 切出對應日期的分時走勢
    target_mmdd = res["date"][5:7] + "/" + res["date"][8:10] if len(res["date"]) >= 10 else ""
    if day_offset_idx > 0 and target_mmdd and intra_bars:
        filtered_intra = [b for b in intra_bars if str(b.get("time", ""))[:5] <= target_mmdd]
        res["intraday_bars"] = filtered_intra if len(filtered_intra) >= 8 else intra_bars
    else:
        res["intraday_bars"] = intra_bars

    return res


def build_txf_snapshot_for_date(base_txf, taiex_day, is_latest=False):
    """
    為近 5 個交易日建立對應的台指期夜盤快照與近 5 日摘要
    """
    if not base_txf:
        return {}
    if is_latest or not taiex_day:
        return dict(base_txf)

    res = dict(base_txf)
    t_close = float(taiex_day.get("close", base_txf.get("last", 0)))
    t_chg = float(taiex_day.get("change", 0))
    t_pct = float(taiex_day.get("change_pct", 0))
    t_high = float(taiex_day.get("high", t_close))
    t_low = float(taiex_day.get("low", t_close))
    t_open = float(taiex_day.get("open", t_close))

    base_last = float(base_txf.get("last") or t_close)
    offset = round(t_close - base_last)

    res["last"] = round(t_close)
    res["open"] = round(t_open)
    res["high"] = round(t_high)
    res["low"] = round(t_low)
    res["ref_price"] = round(t_close - t_chg)
    res["change"] = round(t_chg)
    res["change_pct"] = round(t_pct, 2)
    res["update_time"] = f"{taiex_day.get('date', '')} 夜盤收盤"

    base_ticks = base_txf.get("ticks") or []
    if base_ticks:
        adj_ticks = []
        for tk in base_ticks:
            ntk = dict(tk)
            ntk["open"] = round(float(tk.get("open", 0)) + offset)
            ntk["high"] = round(float(tk.get("high", 0)) + offset)
            ntk["low"] = round(float(tk.get("low", 0)) + offset)
            ntk["close"] = round(float(tk.get("close", 0)) + offset)
            adj_ticks.append(ntk)
        res["ticks"] = adj_ticks
    return res


def enrich_5d_full_snapshots(payload):
    """
    確保 payload 內的所有區塊（台股、三大法人、台指期夜盤、美股四大指數、日經225、韓國KOSPI、
    小那斯達克期貨、布蘭特原油、台股四大ADR）皆完整保留最近 5 個交易日的資料快照與 5 日明細
    """
    avail_dates = payload.get("available_dates") or []
    hist_5d = payload.get("history_5d") or {}
    taiex_series = (payload.get("taiex") or {}).get("series") or []
    base_brent = payload.get("brent") or {}
    base_nq = payload.get("nq") or {}
    base_txf = payload.get("txf_night") or {}
    base_gm = payload.get("global_markets") or {}
    usd_twd = float(base_gm.get("usd_twd") or 32.15)

    # 先為頂層標的補上 recent_5d
    if base_brent:
        payload["brent"] = slice_cnbc_item_for_date(base_brent, avail_dates[0] if avail_dates else "", 0)
    if base_nq:
        payload["nq"] = slice_cnbc_item_for_date(base_nq, avail_dates[0] if avail_dates else "", 0)

    if base_gm:
        base_gm["us_indices"] = [
            slice_cnbc_item_for_date(it, avail_dates[0] if avail_dates else "", 0)
            for it in (base_gm.get("us_indices") or [])
        ]
        base_gm["asia_indices"] = [
            slice_cnbc_item_for_date(it, avail_dates[0] if avail_dates else "", 0)
            for it in (base_gm.get("asia_indices") or [])
        ]
        enriched_adrs = []
        for it in (base_gm.get("tw_adrs") or []):
            sliced = slice_cnbc_item_for_date(it, avail_dates[0] if avail_dates else "", 0)
            ratio = float(sliced.get("ratio") or 1.0)
            # 為 ADR 的 recent_5d 補上每日折算台股價與對應母股溢價率
            r5 = []
            for b in sliced.get("recent_5d") or []:
                nb = dict(b)
                d_str = nb.get("date", "")
                parent_snap = (hist_5d.get(d_str) or {}).get("adr_parent_stocks") or {}
                p_st = parent_snap.get(sliced.get("tw_code"), {})
                tw_c = float(p_st.get("close") or sliced.get("tw_close") or 0.0)
                imp = round((float(nb.get("close", 0.0)) * usd_twd) / ratio, 2) if ratio else 0.0
                prem = round(((imp - tw_c) / tw_c) * 100.0, 2) if tw_c > 0 else 0.0
                nb["implied_tw_price"] = imp
                nb["tw_close"] = tw_c
                nb["premium_pct"] = prem
                r5.append(nb)
            sliced["recent_5d"] = r5
            enriched_adrs.append(sliced)
        base_gm["tw_adrs"] = enriched_adrs

    # 建立近 5 日三大法人買賣超匯總對照表 (institutional_5d_overview)
    inst_5d_overview = []
    for d_iso in avail_dates:
        snap = hist_5d.get(d_iso) or {}
        t_lat = snap.get("taiex_latest") or {}
        inst_items = (snap.get("institutional_summary") or {}).get("items") or []
        f_net = next((x["net_100m"] for x in inst_items if "外資及陸資" in x.get("name", "")), 0.0)
        t_net = next((x["net_100m"] for x in inst_items if "投信" in x.get("name", "")), 0.0)
        d_net = sum(x["net_100m"] for x in inst_items if "自營商" in x.get("name", ""))
        tot_net = next((x["net_100m"] for x in inst_items if "合計" in x.get("name", "")), round(f_net + t_net + d_net, 2))
        inst_5d_overview.append({
            "date": d_iso,
            "taiex_close": t_lat.get("close", 0.0),
            "taiex_change": t_lat.get("change", 0.0),
            "taiex_change_pct": t_lat.get("change_pct", 0.0),
            "turnover_100m": t_lat.get("turnover_100m", 0.0),
            "foreign_net_100m": round(f_net, 2),
            "trust_net_100m": round(t_net, 2),
            "dealer_net_100m": round(d_net, 2),
            "total_net_100m": round(tot_net, 2),
            "foreign_100m": round(f_net, 2),
            "trust_100m": round(t_net, 2),
            "dealer_100m": round(d_net, 2),
            "total_100m": round(tot_net, 2),
        })
    payload["twse_5d_overview"] = inst_5d_overview

    # 為每一個交易日 (avail_dates) 補齊完整的台股 + 國際金融 + 期貨快照
    for idx, d_iso in enumerate(avail_dates):
        snap = hist_5d.get(d_iso)
        if not snap:
            continue
        cut_idx = next((i for i, x in enumerate(taiex_series) if x.get("date") == d_iso), len(taiex_series) - 1)
        snap["taiex_series"] = taiex_series[: cut_idx + 1]
        snap["txf_night"] = build_txf_snapshot_for_date(base_txf, snap.get("taiex_latest"), is_latest=(idx == 0))
        snap["brent"] = slice_cnbc_item_for_date(base_brent, d_iso, idx)
        snap["nq"] = slice_cnbc_item_for_date(base_nq, d_iso, idx)

        parent_stocks = snap.get("adr_parent_stocks") or {}
        day_us = [slice_cnbc_item_for_date(it, d_iso, idx) for it in (base_gm.get("us_indices") or [])]
        day_asia = [slice_cnbc_item_for_date(it, d_iso, idx) for it in (base_gm.get("asia_indices") or [])]
        day_adrs = []
        for it in (base_gm.get("tw_adrs") or []):
            s_adr = slice_cnbc_item_for_date(it, d_iso, idx)
            tw_code = s_adr.get("tw_code", "")
            p_info = parent_stocks.get(tw_code, {})
            tw_close = float(p_info.get("close") or s_adr.get("tw_close") or 0.0)
            tw_chg_pct = float(p_info.get("change_pct") or s_adr.get("tw_change_pct") or 0.0)
            ratio = float(s_adr.get("ratio") or 1.0)
            adr_last = float(s_adr.get("last") or 0.0)
            imp_twd = round((adr_last * usd_twd) / ratio, 2) if ratio else 0.0
            prem_pct = round(((imp_twd - tw_close) / tw_close) * 100.0, 2) if tw_close > 0 else 0.0
            s_adr["tw_close"] = tw_close
            s_adr["tw_change_pct"] = tw_chg_pct
            s_adr["implied_tw_price"] = imp_twd
            s_adr["premium_pct"] = prem_pct
            day_adrs.append(s_adr)

        snap["global_markets"] = {
            "usd_twd": round(usd_twd, 3),
            "us_indices": day_us,
            "asia_indices": day_asia,
            "tw_adrs": day_adrs,
        }

    return payload


def save_and_deploy(payload, skip_api_deploy=False):
    enrich_5d_full_snapshots(payload)
    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Wrote {DATA_JSON_PATH} ({os.path.getsize(DATA_JSON_PATH):,} bytes)")

    render_script = os.path.join(BASE_DIR, "render_html.py")
    if os.path.exists(render_script):
        import render_html
        render_html.build_html(payload, INDEX_HTML_PATH)
        print(f"[OK] Built {INDEX_HTML_PATH} ({os.path.getsize(INDEX_HTML_PATH):,} bytes)")

    if skip_api_deploy:
        return

    gh_cfg_path = os.path.join(BASE_DIR, "github_config.json")
    if os.path.exists(gh_cfg_path):
        try:
            with open(gh_cfg_path, "r", encoding="utf-8") as gf:
                gh_cfg = json.load(gf)
            if gh_cfg.get("token"):
                import deploy_github
                print("[GitHub Pages] Syncing updated dashboard to GitHub Pages...")
                deploy_github.deploy(
                    token=gh_cfg["token"],
                    repo=gh_cfg.get("repo", "tw-us-stock-dashboard"),
                    branch=gh_cfg.get("branch", "main"),
                )
        except Exception as e:
            print(f"[WARN] GitHub Pages auto-sync failed: {e}")


def load_existing_payload():
    if os.path.exists(DATA_JSON_PATH):
        try:
            with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def main():
    parser = argparse.ArgumentParser(description="更新台股與國際金融儀表板資料")
    parser.add_argument(
        "--mode",
        choices=["all", "global", "futures"],
        default="all",
        help="all: 每日18:00完整更新(含台股近5日歷史); global: 美股收盤後更新美股/ADR/日韓/期貨; futures: 每小時更新布蘭特原油與小那斯達克期貨",
    )
    parser.add_argument(
        "--skip-api-deploy",
        action="store_true",
        help="略過內建 GitHub API 部署 (供 GitHub Actions 使用 git commit & push 時呼叫)",
    )
    args = parser.parse_args()

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing = load_existing_payload()

    # 模式 1：每小時快速更新 布蘭特原油 (@LCO.1)、小那斯達克期貨 (@ND.1) 與 台指期夜盤
    if args.mode == "futures" and existing.get("taiex"):
        print(f"[Mode: futures] Hourly update for Brent Crude (@LCO.1) & E-mini Nasdaq-100 (@ND.1) at {now_str}...")
        brent_data = fetch_cnbc_symbol("@LCO.1", "布蘭特原油期貨 (Brent Crude)")
        nq_data = fetch_cnbc_symbol("@ND.1", "小那斯達克期貨 (E-mini Nasdaq-100)")
        try:
            txf_night = fetch_taifex_night_session()
            existing["txf_night"] = txf_night
        except Exception as e:
            print(f"  [WARN] TAIFEX Night update skipped: {e}")

        existing["brent"] = brent_data
        existing["nq"] = nq_data
        existing["updated_at"] = now_str
        existing["futures_updated_at"] = now_str
        save_and_deploy(existing, skip_api_deploy=args.skip_api_deploy)
        return

    # 模式 2：美股收盤後更新 美股四大指數、台股 ADR、日韓指數 與 國際期貨
    if args.mode == "global" and existing.get("taiex"):
        print(f"[Mode: global] Post-US-Close update for US Indices, ADRs, Nikkei/KOSPI & Futures at {now_str}...")
        parent_stock_map = {}
        latest_date_iso = existing.get("twse_date")
        hist_5d = existing.get("history_5d", {})
        if latest_date_iso and latest_date_iso in hist_5d:
            parent_stock_map = hist_5d[latest_date_iso].get("adr_parent_stocks", {})
        if not parent_stock_map:
            for item in existing.get("top15_value", []) + existing.get("top15_volume", []):
                parent_stock_map[item["code"]] = item

        brent_data = fetch_cnbc_symbol("@LCO.1", "布蘭特原油期貨 (Brent Crude)")
        nq_data = fetch_cnbc_symbol("@ND.1", "小那斯達克期貨 (E-mini Nasdaq-100)")
        global_markets = fetch_us_asia_indices_and_tw_adrs(parent_stock_map)

        existing["brent"] = brent_data
        existing["nq"] = nq_data
        existing["global_markets"] = global_markets
        existing["updated_at"] = now_str
        existing["global_updated_at"] = now_str
        save_and_deploy(existing, skip_api_deploy=args.skip_api_deploy)
        return

    # 模式 3 (預設 all)：每日 18:00 完整更新台股（保留最近 5 個交易日完整資料）+ 國際金融 + 期貨
    print(f"[Mode: all] Full update (including last 5 TWSE trading days) at {now_str}...")
    latest_date, taiex_series = fetch_taiex_history()

    # 取得最近 5 個交易日清單 (由新到舊排序供前端切換)
    last_5_entries = taiex_series[-5:] if len(taiex_series) >= 5 else taiex_series[:]
    available_dates = [d["date"] for d in reversed(last_5_entries)]

    history_5d = {}
    latest_stock_map = {}
    latest_snapshot = None

    for idx_d, entry in enumerate(last_5_entries):
        d_iso = entry["date"]
        d_raw = d_iso.replace("-", "")
        # 擷取截至該交易日為止的 taiex_series
        cut_idx = next((i for i, x in enumerate(taiex_series) if x["date"] == d_iso), len(taiex_series) - 1)
        series_up_to = taiex_series[: cut_idx + 1]
        is_latest_day = (d_iso == last_5_entries[-1]["date"])

        snap, s_map = fetch_single_twse_day_snapshot(
            date_raw=d_raw,
            date_iso=d_iso,
            taiex_series_up_to_date=series_up_to,
            use_cache=(not is_latest_day),
        )
        history_5d[d_iso] = snap
        if is_latest_day:
            latest_snapshot = snap
            latest_stock_map = s_map or snap.get("adr_parent_stocks", {})

    # 清理超過最近 5 個交易日的舊快取檔
    keep_raw_dates = {d["date"].replace("-", "") for d in last_5_entries}
    if os.path.exists(HISTORY_DIR):
        for fname in os.listdir(HISTORY_DIR):
            if fname.startswith("twse_") and fname.endswith(".json"):
                f_raw = fname[5:-5]
                if f_raw not in keep_raw_dates:
                    try:
                        os.remove(os.path.join(HISTORY_DIR, fname))
                    except Exception:
                        pass

    time.sleep(0.35)
    txf_night = fetch_taifex_night_session()

    print("[7/8] Fetching Brent Crude Oil (@LCO.1) & E-mini Nasdaq-100 Futures (@ND.1)...")
    brent_data = fetch_cnbc_symbol("@LCO.1", "布蘭特原油期貨 (Brent Crude)")
    nq_data = fetch_cnbc_symbol("@ND.1", "小那斯達克期貨 (E-mini Nasdaq-100)")

    global_markets = fetch_us_asia_indices_and_tw_adrs(latest_stock_map)

    if not latest_snapshot:
        latest_snapshot = {}

    payload = {
        "updated_at": now_str,
        "twse_updated_at": now_str,
        "global_updated_at": now_str,
        "futures_updated_at": now_str,
        "twse_date": latest_snapshot.get("twse_date", f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"),
        "twse_date_raw": latest_date,
        "available_dates": available_dates,
        "history_5d": history_5d,
        "taiex": {
            "latest": latest_snapshot.get("taiex_latest", taiex_series[-1] if taiex_series else {}),
            "breadth": latest_snapshot.get("taiex_breadth", {}),
            "series": taiex_series,
        },
        "institutional_summary": latest_snapshot.get("institutional_summary", {}),
        "institutional_top50": latest_snapshot.get("institutional_top50", {}),
        "top15_value": latest_snapshot.get("top15_value", []),
        "top15_volume": latest_snapshot.get("top15_volume", []),
        "concept_sectors": latest_snapshot.get("concept_sectors", {}),
        "warrants": latest_snapshot.get("warrants", {}),
        "txf_night": txf_night,
        "brent": brent_data,
        "nq": nq_data,
        "global_markets": global_markets,
    }

    save_and_deploy(payload, skip_api_deploy=args.skip_api_deploy)


if __name__ == "__main__":
    main()
