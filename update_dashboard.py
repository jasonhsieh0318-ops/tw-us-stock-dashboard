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
6. 布蘭特原油走勢 (CNBC @LCO.1 1D & 30M)
7. 台指期夜盤走勢 (TAIFEX MIS getQuoteList & getChartData1M)
8. 小那斯達克期貨走勢 (CNBC @ND.1 1D & 30M)
9. 台股概念族群資金輪動圖 (四象限氣泡圖) 與 概念族群熱力圖 (Squarified Treemap)
10. 國際金融走勢：美股四大指數 (.DJI, .IXIC, .SPX, .SOX) 及 台股四大 ADR (台積電 TSM、日月光 ASX、鴻海 HNHPF、聯電 UMC) 即時與日K走勢
"""

import datetime
import json
import math
import os
import re
import ssl
import time
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON_PATH = os.path.join(BASE_DIR, "data.json")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

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

TW_ADR_SPECS = [
    {"symbol": "TSM",   "alt_symbols": [],            "code": "TSM",   "name": "台積電 ADR", "tw_code": "2330", "tw_name": "台積電", "ratio": 5.0},
    {"symbol": "ASX",   "alt_symbols": [],            "code": "ASX",   "name": "日月光 ADR", "tw_code": "3711", "tw_name": "日月光投控", "ratio": 2.0},
    {"symbol": "HNHPF", "alt_symbols": ["HNHAY", "HHPD-GB"], "code": "HNHPF", "name": "鴻海 ADR",   "tw_code": "2317", "tw_name": "鴻海", "ratio": 2.0},
    {"symbol": "UMC",   "alt_symbols": [],            "code": "UMC",   "name": "聯電 ADR",   "tw_code": "2303", "tw_name": "聯電", "ratio": 5.0},
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
    return latest_date, series


def fetch_institutional_summary(latest_date):
    print(f"[2/8] Fetching TWSE Institutional Investors net buy/sell amount (BFI82U {latest_date})...")
    bfi = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?response=json&dayDate={latest_date}"
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
            f"{int(latest_date[:4]) - 1911}/{latest_date[4:6]}/{latest_date[6:8]}"
        ),
        "title": bfi.get("title", "三大法人買賣金額統計表"),
        "items": items,
    }


def fetch_market_stocks_and_top15(latest_date):
    print(f"[3/8] Fetching TWSE MI_INDEX (ALLBUT0999) for stock prices & Top 15 Value/Volume ({latest_date})...")
    mi = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={latest_date}&type=ALLBUT0999"
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


def fetch_institutional_top50(latest_date, stock_map):
    print(f"[4/8] Fetching TWSE T86 for Foreign/Trust/Dealer Top 50 net buy & sell ({latest_date})...")
    t86 = fetch_json(
        f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={latest_date}&selectType=ALLBUT0999"
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


def fetch_warrants_top20(latest_date):
    print(f"[5/8] Fetching TWSE Warrants Call (0999) & Put (0999P) Top 20 ({latest_date})...")
    warrants = []
    for w_type, label in [("0999", "認購"), ("0999P", "認售")]:
        time.sleep(0.35)
        mi_w = fetch_json(
            f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?response=json&date={latest_date}&type={w_type}"
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


def fetch_us_indices_and_tw_adrs(stock_map):
    print("[8/8] Fetching US 4 Major Indices (.DJI, .IXIC, .SPX, .SOX) & Taiwan ADRs (TSM, ASX, HNHPF, UMC)...")
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

    # 3. Fetch Taiwan 4 Major ADRs
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
            # 折算台股價格 = ADR價格 * USD_TWD / 換算股數
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
        "tw_adrs": tw_adrs,
    }


def main():
    latest_date, taiex_series = fetch_taiex_history()
    time.sleep(0.35)
    inst_summary = fetch_institutional_summary(latest_date)
    time.sleep(0.35)
    stock_map, top15_value, top15_volume, breadth = fetch_market_stocks_and_top15(latest_date)
    time.sleep(0.35)
    inst_top50, inst_by_code = fetch_institutional_top50(latest_date, stock_map)

    for item in top15_value + top15_volume:
        ic = inst_by_code.get(item["code"], {})
        item["foreign_net_lots"] = ic.get("foreign_net_lots", 0)
        item["trust_net_lots"] = ic.get("trust_net_lots", 0)
        item["dealer_net_lots"] = ic.get("dealer_net_lots", 0)
        item["total_net_lots"] = ic.get("total_net_lots", 0)

    print("[4.5/8] Computing Concept Sector Rotation & Treemap Heatmap metrics...")
    concept_sectors = build_concept_sectors(stock_map, inst_by_code, taiex_series)

    time.sleep(0.35)
    warrants_data = fetch_warrants_top20(latest_date)
    time.sleep(0.35)
    txf_night = fetch_taifex_night_session()

    print("[7/8] Fetching Brent Crude Oil (@LCO.1) & E-mini Nasdaq-100 Futures (@ND.1)...")
    brent_data = fetch_cnbc_symbol("@LCO.1", "布蘭特原油期貨 (Brent Crude)")
    nq_data = fetch_cnbc_symbol("@ND.1", "小那斯達克期貨 (E-mini Nasdaq-100)")

    global_markets = fetch_us_indices_and_tw_adrs(stock_map)

    payload = {
        "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "twse_date": f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}",
        "twse_date_raw": latest_date,
        "taiex": {
            "latest": taiex_series[-1] if taiex_series else {},
            "breadth": breadth,
            "series": taiex_series,
        },
        "institutional_summary": inst_summary,
        "institutional_top50": inst_top50,
        "top15_value": top15_value,
        "top15_volume": top15_volume,
        "concept_sectors": concept_sectors,
        "warrants": warrants_data,
        "txf_night": txf_night,
        "brent": brent_data,
        "nq": nq_data,
        "global_markets": global_markets,
    }

    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"[OK] Wrote {DATA_JSON_PATH} ({os.path.getsize(DATA_JSON_PATH):,} bytes)")

    render_script = os.path.join(BASE_DIR, "render_html.py")
    if os.path.exists(render_script):
        import render_html
        render_html.build_html(payload, INDEX_HTML_PATH)
        print(f"[OK] Built {INDEX_HTML_PATH} ({os.path.getsize(INDEX_HTML_PATH):,} bytes)")

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


if __name__ == "__main__":
    main()

