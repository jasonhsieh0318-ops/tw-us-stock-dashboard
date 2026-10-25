#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成互動式台股與國際期貨盤後儀表板 (index.html)
採用左側固定導覽選單 (Left Sidebar Menu) 架構，整合三大核心分頁：
- 分頁 1：📊 台股每日盤後總覽（加權指數、三大法人買賣超金額、台指期夜盤走勢、成交值/量前15名、三大法人買賣超前50名、權證交易量前20名）
- 分頁 2：🔥 概念族群資金輪動與熱力圖（概念族群 Treemap 熱力圖、20日四象限資金輪動重播圖、成分股與法人籌碼明細）
- 分頁 3：🌎 國際金融頁面（美股四大指數、小那斯達克期貨 NQ & 布蘭特原油期貨 Brent、台積電/日月光/鴻海/聯電 ADR 即時走勢與折溢價對照表）
"""

import json
import os

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>台股與國際金融每日盤後儀表板 | TWSE, US Indices, ADRs & Futures</title>
  <style>
    :root {
      --bg-primary: #0b0f17;
      --bg-sidebar: #0e1420;
      --bg-card: #131a26;
      --bg-card-hover: #192231;
      --bg-elevated: #1c2638;
      --border: #253247;
      --text-primary: #f1f5f9;
      --text-secondary: #94a3b8;
      --text-muted: #64748b;
      --accent: #38bdf8;
      --accent-indigo: #6366f1;
      /* 台股習慣：紅漲綠跌 */
      --up: #f43f5e;
      --up-bg: rgba(244, 63, 94, 0.14);
      --down: #10b981;
      --down-bg: rgba(16, 185, 129, 0.14);
      --flat: #94a3b8;
      --sidebar-width: 268px;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html {
      scroll-behavior: smooth;
    }

    html, body {
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang TC", "Microsoft JhengHei", sans-serif;
      line-height: 1.5;
      overflow-x: hidden;
      max-width: 100vw;
      -webkit-tap-highlight-color: transparent;
    }

    /* Top Header */
    .topbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      min-height: 68px;
      z-index: 120;
      background: rgba(11, 15, 23, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      padding: 8px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 0;
    }

    .sidebar-toggle-btn {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      color: var(--text-primary);
      width: 36px;
      height: 36px;
      border-radius: 9px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 17px;
      transition: all 0.15s;
      flex-shrink: 0;
    }

    .sidebar-toggle-btn:hover {
      border-color: var(--accent);
      color: var(--accent);
    }

    .brand-badge {
      width: 34px;
      height: 34px;
      border-radius: 9px;
      background: linear-gradient(135deg, #38bdf8, #6366f1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 15px;
      color: #fff;
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.3);
      flex-shrink: 0;
    }

    .brand h1 {
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.3px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Main Page Switcher in Topbar */
    .page-switcher {
      display: inline-flex;
      background: #080b11;
      border: 1px solid var(--border);
      padding: 4px;
      border-radius: 11px;
      gap: 5px;
    }

    .page-tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      padding: 7px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      transition: all 0.18s;
      white-space: nowrap;
    }

    .page-tab-btn:hover {
      color: var(--text-primary);
    }

    .page-tab-btn.active {
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.22), rgba(99, 102, 241, 0.28));
      color: #fff;
      border: 1px solid rgba(56, 189, 248, 0.45);
      box-shadow: 0 2px 12px rgba(56, 189, 248, 0.2);
    }

    .meta-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      flex-shrink: 0;
    }

    .pill {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      padding: 5px 11px;
      border-radius: 999px;
      font-size: 12px;
      color: var(--text-secondary);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
    }

    .pill strong {
      color: var(--text-primary);
    }

    .dot-live {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 8px #10b981;
    }

    /* App Shell with Left Sidebar + Main Content */
    .app-shell {
      display: flex;
      padding-top: 68px;
      min-height: 100vh;
      max-width: 100vw;
    }

    /* Mobile Sidebar Backdrop */
    .sidebar-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(2, 6, 23, 0.65);
      backdrop-filter: blur(3px);
      z-index: 140;
    }

    body.sidebar-open-mobile .sidebar-backdrop {
      display: block;
    }

    /* Left Sidebar Menu */
    .left-sidebar {
      position: fixed;
      top: 68px;
      left: 0;
      bottom: 0;
      width: var(--sidebar-width);
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border);
      padding: 16px 12px 28px;
      overflow-y: auto;
      z-index: 150;
      display: flex;
      flex-direction: column;
      gap: 18px;
      transition: transform 0.22s ease;
    }

    body.sidebar-collapsed .left-sidebar {
      transform: translateX(-100%);
    }

    .sidebar-group {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .sidebar-group-header {
      font-size: 11.5px;
      font-weight: 800;
      color: var(--accent);
      letter-spacing: 0.5px;
      padding: 6px 10px 4px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      text-transform: uppercase;
      cursor: pointer;
      border-radius: 7px;
      transition: background 0.15s;
    }

    .sidebar-group-header:hover {
      background: rgba(56, 189, 248, 0.08);
    }

    .sidebar-link {
      display: flex;
      align-items: center;
      gap: 9px;
      padding: 9px 12px;
      border-radius: 9px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-secondary);
      background: transparent;
      border: 1px solid transparent;
      text-decoration: none;
      cursor: pointer;
      transition: all 0.15s;
      text-align: left;
      width: 100%;
    }

    .sidebar-link:hover {
      background: var(--bg-card-hover);
      color: var(--text-primary);
      border-color: rgba(56, 189, 248, 0.28);
    }

    .sidebar-link.active {
      background: linear-gradient(90deg, rgba(56, 189, 248, 0.18), rgba(99, 102, 241, 0.10));
      color: #ffffff;
      border-color: rgba(56, 189, 248, 0.48);
      box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25);
    }

    .sidebar-link .num-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 21px;
      height: 21px;
      padding: 0 5px;
      border-radius: 5px;
      font-size: 11px;
      font-weight: 700;
      background: var(--bg-elevated);
      color: var(--text-secondary);
      flex-shrink: 0;
    }

    .sidebar-link.active .num-pill {
      background: var(--accent);
      color: #0b0f17;
    }

    .sidebar-divider {
      height: 1px;
      background: var(--border);
      margin: 2px 6px;
    }

    /* Main Content Container */
    .main-area {
      flex: 1;
      min-width: 0;
      margin-left: var(--sidebar-width);
      padding: 22px 26px 64px;
      max-width: calc(100vw - var(--sidebar-width));
      transition: margin-left 0.22s ease, max-width 0.22s ease;
    }

    body.sidebar-collapsed .main-area {
      margin-left: 0;
      max-width: 100vw;
    }

    .page-view {
      display: none;
      flex-direction: column;
      gap: 24px;
      min-width: 0;
      max-width: 100%;
    }

    .page-view.active {
      display: flex;
    }

    section[id] {
      scroll-margin-top: 90px;
    }

    /* KPI Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(225px, 1fr));
      gap: 16px;
      min-width: 0;
    }

    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 10px;
      position: relative;
      overflow: hidden;
      min-width: 0;
    }

    .kpi-card::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--accent);
      opacity: 0.7;
    }

    .kpi-card.up-card::before { background: var(--up); }
    .kpi-card.down-card::before { background: var(--down); }

    .kpi-title {
      font-size: 12.5px;
      color: var(--text-secondary);
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 6px;
      min-width: 0;
    }

    .kpi-value {
      font-size: 25px;
      font-weight: 800;
      font-variant-numeric: tabular-nums;
      letter-spacing: -0.5px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .kpi-change {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 700;
      padding: 3px 9px;
      border-radius: 6px;
      width: fit-content;
      max-width: 100%;
      font-variant-numeric: tabular-nums;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .kpi-foot {
      font-size: 12px;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
      border-top: 1px solid rgba(255, 255, 255, 0.05);
      padding-top: 8px;
    }

    .up { color: var(--up); }
    .down { color: var(--down); }
    .flat { color: var(--flat); }
    .up-badge { color: var(--up); background: var(--up-bg); }
    .down-badge { color: var(--down); background: var(--down-bg); }
    .flat-badge { color: var(--flat); background: rgba(148, 163, 184, 0.12); }

    /* Section Card */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 22px 24px;
      min-width: 0;
      max-width: 100%;
      overflow: hidden;
    }

    .card-header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 18px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border);
    }

    .card-title {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      font-size: 17px;
      font-weight: 700;
      min-width: 0;
    }

    .section-tag {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      text-transform: uppercase;
      flex-shrink: 0;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
      gap: 20px;
      min-width: 0;
    }

    .grid-2 > *, .grid-3 > * {
      min-width: 0;
      max-width: 100%;
    }

    .grid-3 {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: 20px;
      min-width: 0;
    }

    .inst-bar-row {
      display: grid;
      grid-template-columns: 185px 1fr 95px;
      align-items: center;
      gap: 12px;
      font-size: 12.5px;
    }

    /* Tabs & Controls */
    .tab-group {
      display: inline-flex;
      background: var(--bg-primary);
      border: 1px solid var(--border);
      border-radius: 9px;
      padding: 3px;
      gap: 3px;
      flex-wrap: wrap;
      max-width: 100%;
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }

    .tab-btn.active {
      background: var(--bg-elevated);
      color: var(--text-primary);
      box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    }

    .search-input {
      background: var(--bg-primary);
      border: 1px solid var(--border);
      color: var(--text-primary);
      padding: 7px 13px;
      border-radius: 8px;
      font-size: 13px;
      min-width: 180px;
      max-width: 100%;
      outline: none;
    }

    .search-input:focus {
      border-color: var(--accent);
    }

    .replay-btn {
      background: #10b981;
      color: #fff;
      border: none;
      padding: 6px 14px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 2px 10px rgba(16, 185, 129, 0.35);
      transition: all 0.15s;
    }

    .replay-btn:hover {
      background: #059669;
      transform: translateY(-1px);
    }

    .timeline-slider {
      accent-color: #10b981;
      width: 150px;
      max-width: 100%;
      cursor: pointer;
    }

    /* Tablet & Mobile Responsive Rules */
    @media (max-width: 1024px) {
      .topbar {
        flex-wrap: wrap;
        padding: 8px 14px;
        gap: 8px;
      }
      .left-sidebar {
        top: 0;
        padding-top: 20px;
        transform: translateX(-100%);
        box-shadow: 8px 0 32px rgba(0, 0, 0, 0.65);
      }
      body.sidebar-open-mobile .left-sidebar {
        transform: translateX(0);
      }
      .main-area {
        margin-left: 0;
        max-width: 100vw;
        padding: 16px 14px 56px;
      }
      .app-shell {
        padding-top: 108px;
      }
      section[id] {
        scroll-margin-top: 116px;
      }
      .page-switcher {
        order: 3;
        width: 100%;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 4px;
      }
      .page-tab-btn {
        padding: 7px 6px;
        font-size: 12px;
      }
    }

    @media (max-width: 768px) {
      .brand h1 {
        font-size: 15px;
      }
      .brand-badge {
        width: 30px;
        height: 30px;
        font-size: 13px;
      }
      .meta-updated-pill {
        display: none;
      }
      .pill {
        font-size: 11px;
        padding: 4px 9px;
      }
      .grid-2, .grid-3 {
        grid-template-columns: 1fr;
        gap: 14px;
      }
      .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
      }
      .kpi-card {
        padding: 13px 12px;
        gap: 6px;
        border-radius: 12px;
      }
      .kpi-title {
        font-size: 11.5px;
      }
      .kpi-value {
        font-size: 19px;
      }
      .kpi-change {
        font-size: 11.5px;
        padding: 2px 7px;
      }
      .kpi-foot {
        font-size: 10.5px;
        padding-top: 6px;
      }
      .card {
        padding: 14px 12px;
        border-radius: 13px;
      }
      .card-header {
        margin-bottom: 12px;
        padding-bottom: 10px;
        gap: 8px;
      }
      .card-title {
        font-size: 15px;
      }
      .treemap-wrapper {
        height: 440px !important;
      }
      .rotation-box {
        height: 460px !important;
      }
      .inst-bar-row {
        grid-template-columns: 108px 1fr 74px;
        gap: 8px;
        font-size: 11.5px;
      }
      .search-input {
        width: 100%;
      }
      thead th, tbody td {
        padding: 8px 9px;
        font-size: 12px;
      }
    }

    @media (max-width: 400px) {
      .kpi-grid {
        grid-template-columns: 1fr;
      }
      .page-tab-btn {
        font-size: 11px;
        padding: 6px 4px;
      }
    }

    /* Treemap Styles */
    .treemap-wrapper {
      position: relative;
      width: 100%;
      height: 620px;
      background: #0d1117;
      border: 2px solid #1e293b;
      border-radius: 10px;
      overflow: hidden;
      user-select: none;
    }

    .treemap-node {
      position: absolute;
      border: 2px solid #0d1117;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 4px;
      cursor: pointer;
      overflow: hidden;
      transition: filter 0.15s, transform 0.12s;
    }

    .treemap-node:hover {
      filter: brightness(1.18);
      z-index: 10;
      border-color: #fff;
    }

    .treemap-node.selected-node {
      border: 2.5px solid #38bdf8;
      box-shadow: inset 0 0 0 2px rgba(56, 189, 248, 0.5);
    }

    .tm-name {
      font-weight: 800;
      color: #ffffff;
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.65);
      line-height: 1.2;
      word-break: keep-all;
    }

    .tm-pct {
      font-weight: 700;
      color: rgba(255, 255, 255, 0.95);
      text-shadow: 0 1px 3px rgba(0, 0, 0, 0.65);
      margin-top: 2px;
      font-variant-numeric: tabular-nums;
    }

    /* Rotation Chart Wrapper */
    .rotation-box {
      position: relative;
      width: 100%;
      height: 600px;
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      border-radius: 14px;
      overflow: hidden;
      color: #1e293b;
    }

    /* Tables */
    .table-wrap {
      overflow-x: auto;
      max-height: 540px;
      overflow-y: auto;
      border: 1px solid var(--border);
      border-radius: 10px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      font-variant-numeric: tabular-nums;
    }

    thead th {
      position: sticky;
      top: 0;
      z-index: 5;
      background: #172030;
      color: var(--text-secondary);
      font-weight: 600;
      text-align: right;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      white-space: nowrap;
    }

    thead th:first-child,
    thead th:nth-child(2),
    thead th:nth-child(3) {
      text-align: left;
    }

    tbody tr {
      border-bottom: 1px solid rgba(37, 50, 71, 0.55);
      transition: background 0.12s;
    }

    tbody tr:hover {
      background: var(--bg-card-hover);
    }

    tbody td {
      padding: 9px 12px;
      text-align: right;
      white-space: nowrap;
    }

    tbody td:first-child,
    tbody td:nth-child(2),
    tbody td:nth-child(3) {
      text-align: left;
    }

    .rank-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 700;
      background: var(--bg-elevated);
      color: var(--text-secondary);
    }

    .rank-1 { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .rank-2 { background: rgba(148, 163, 184, 0.2); color: #e2e8f0; border: 1px solid rgba(148, 163, 184, 0.4); }
    .rank-3 { background: rgba(217, 119, 6, 0.2); color: #fb923c; border: 1px solid rgba(217, 119, 6, 0.4); }

    .code-tag {
      font-family: "SF Mono", "JetBrains Mono", Menlo, monospace;
      font-weight: 700;
      color: var(--accent);
    }

    .bar-cell {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: 8px;
    }

    .mini-bar-track {
      width: 72px;
      height: 6px;
      background: rgba(255, 255, 255, 0.06);
      border-radius: 99px;
      overflow: hidden;
      flex-shrink: 0;
    }

    .mini-bar-fill {
      height: 100%;
      border-radius: 99px;
    }

    .chart-box {
      width: 100%;
      height: 320px;
      position: relative;
      background: rgba(11, 15, 23, 0.45);
      border: 1px solid rgba(37, 50, 71, 0.7);
      border-radius: 12px;
      padding: 12px;
    }

    .chart-tooltip {
      position: absolute;
      pointer-events: none;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 12px;
      color: var(--text-primary);
      box-shadow: 0 8px 24px rgba(0,0,0,0.45);
      display: none;
      z-index: 30;
      white-space: nowrap;
    }

    .breadth-strip {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 14px;
    }

    .breadth-item {
      background: var(--bg-primary);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .breadth-label {
      font-size: 11.5px;
      color: var(--text-secondary);
    }

    .breadth-val {
      font-size: 15px;
      font-weight: 700;
    }

    .w-call {
      background: rgba(244, 63, 94, 0.16);
      color: #fb7185;
      padding: 2px 7px;
      border-radius: 5px;
      font-size: 11.5px;
      font-weight: 700;
    }

    .w-put {
      background: rgba(16, 185, 129, 0.16);
      color: #34d399;
      padding: 2px 7px;
      border-radius: 5px;
      font-size: 11.5px;
      font-weight: 700;
    }

    /* 5-Trading-Day Selector & Chip Bar */
    .date-select {
      background: transparent;
      border: none;
      color: var(--text-primary);
      font-weight: 700;
      font-size: 12px;
      cursor: pointer;
      outline: none;
      padding-right: 4px;
    }

    .date-select option {
      background: #0f172a;
      color: #f8fafc;
    }

    .history-5d-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
      background: rgba(19, 27, 43, 0.85);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 10px 14px;
      margin-bottom: 16px;
    }

    .history-5d-chips {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .day-chip {
      background: var(--bg-primary);
      border: 1px solid var(--border);
      color: var(--text-secondary);
      padding: 5px 11px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
      white-space: nowrap;
    }

    .day-chip:hover {
      border-color: var(--accent);
      color: var(--text-primary);
    }

    .day-chip.active {
      background: linear-gradient(135deg, rgba(56, 189, 248, 0.22), rgba(99, 102, 241, 0.25));
      color: #fff;
      border-color: rgba(56, 189, 248, 0.55);
      box-shadow: 0 2px 8px rgba(56, 189, 248, 0.18);
    }

    /* Recent 5-Day Mini History Strip inside KPI Cards */
    .recent-5d-strip {
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed rgba(148, 163, 184, 0.18);
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .recent-5d-title {
      font-size: 10.5px;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.03em;
      margin-bottom: 2px;
    }

    .recent-5d-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      font-variant-numeric: tabular-nums;
      padding: 2px 6px;
      border-radius: 5px;
      background: rgba(11, 15, 23, 0.35);
    }

    .recent-5d-row.active-day {
      background: rgba(56, 189, 248, 0.14);
      border: 1px solid rgba(56, 189, 248, 0.35);
    }
  </style>
</head>
<body>

  <!-- Top Header -->
  <header class="topbar">
    <div class="brand">
      <button class="sidebar-toggle-btn" onclick="toggleSidebar()" title="收合/展開左側選單">☰</button>
      <div class="brand-badge">TW</div>
      <div style="min-width:0;">
        <h1>台股與國際金融每日盤後儀表板</h1>
      </div>
    </div>

    <!-- Top-Level Page Switcher -->
    <div class="page-switcher">
      <button class="page-tab-btn active" id="btn-page-overview" onclick="switchMainPage('overview')">
        📊 每日盤後總覽
      </button>
      <button class="page-tab-btn" id="btn-page-sectors" onclick="switchMainPage('sectors')">
        🔥 族群輪動與熱力圖
      </button>
      <button class="page-tab-btn" id="btn-page-global" onclick="switchMainPage('global')">
        🌎 國際金融頁面
      </button>
    </div>

    <div class="meta-bar">
      <span class="pill">
        <span class="dot-live"></span> 交易日：
        <select id="twse-date-select" class="date-select" onchange="switchTradingDay(this.value)">
          <option id="meta-twse-date" value="">--</option>
        </select>
      </span>
      <span class="pill meta-updated-pill">最後更新：<strong id="meta-updated-at">--</strong></span>
    </div>
  </header>

  <!-- App Shell: Left Sidebar + Main Content -->
  <div class="app-shell">

    <div class="sidebar-backdrop" onclick="document.body.classList.remove('sidebar-open-mobile')"></div>

    <!-- Left Sidebar Navigation Menu -->
    <aside class="left-sidebar" id="left-sidebar">

      <!-- Group 1: 台股每日盤後總覽 -->
      <div class="sidebar-group">
        <div class="sidebar-group-header" onclick="switchMainPage('overview')">
          <span>📊 每日盤後總覽 (台股)</span>
        </div>
        <button class="sidebar-link active" data-target="sec-kpi" onclick="navigateToSection('overview', 'sec-kpi', this)">
          <span class="num-pill">★</span>
          <span>市場總覽 KPI</span>
        </button>
        <button class="sidebar-link" data-target="sec-taiex" onclick="navigateToSection('overview', 'sec-taiex', this)">
          <span class="num-pill">1</span>
          <span>台股加權指數走勢</span>
        </button>
        <button class="sidebar-link" data-target="sec-inst-sum" onclick="navigateToSection('overview', 'sec-inst-sum', this)">
          <span class="num-pill">2</span>
          <span>三大法人買賣超金額</span>
        </button>
        <button class="sidebar-link" data-target="sec-txf-night" onclick="navigateToSection('overview', 'sec-txf-night', this)">
          <span class="num-pill">3</span>
          <span>台指期夜盤走勢</span>
        </button>
        <button class="sidebar-link" data-target="sec-top15" onclick="navigateToSection('overview', 'sec-top15', this)">
          <span class="num-pill">4</span>
          <span>台股成交值 & 成交量前 15 名</span>
        </button>
        <button class="sidebar-link" data-target="sec-top50" onclick="navigateToSection('overview', 'sec-top50', this)">
          <span class="num-pill">5</span>
          <span>三大法人買賣超前 50 名</span>
        </button>
        <button class="sidebar-link" data-target="sec-warrants" onclick="navigateToSection('overview', 'sec-warrants', this)">
          <span class="num-pill">6</span>
          <span>權證交易量前 20 名</span>
        </button>
      </div>

      <div class="sidebar-divider"></div>

      <!-- Group 2: 概念族群資金輪動與熱力圖 -->
      <div class="sidebar-group">
        <div class="sidebar-group-header" onclick="switchMainPage('sectors')">
          <span>🔥 概念族群輪動與熱力圖</span>
        </div>
        <button class="sidebar-link" data-target="sec-heatmap" onclick="navigateToSection('sectors', 'sec-heatmap', this)">
          <span class="num-pill">1</span>
          <span>概念族群熱力圖 (Treemap)</span>
        </button>
        <button class="sidebar-link" data-target="sec-rotation" onclick="navigateToSection('sectors', 'sec-rotation', this)">
          <span class="num-pill">2</span>
          <span>台股概念股資金輪動圖</span>
        </button>
        <button class="sidebar-link" data-target="sec-sector-detail" onclick="navigateToSection('sectors', 'sec-sector-detail', this)">
          <span class="num-pill">3</span>
          <span>概念族群成分股與籌碼明細</span>
        </button>
      </div>

      <div class="sidebar-divider"></div>

      <!-- Group 3: 國際金融頁面 -->
      <div class="sidebar-group">
        <div class="sidebar-group-header" onclick="switchMainPage('global')">
          <span>🌎 國際金融頁面</span>
        </div>
        <button class="sidebar-link" data-target="sec-us-indices" onclick="navigateToSection('global', 'sec-us-indices', this)">
          <span class="num-pill">1</span>
          <span>美股四大指數即時走勢</span>
        </button>
        <button class="sidebar-link" data-target="sec-asia-indices" onclick="navigateToSection('global', 'sec-asia-indices', this)">
          <span class="num-pill">2</span>
          <span>日經 225 & 韓國 KOSPI 指數</span>
        </button>
        <button class="sidebar-link" data-target="sec-global-futures" onclick="navigateToSection('global', 'sec-global-futures', this)">
          <span class="num-pill">3</span>
          <span>小那斯達克 (NQ) & 布蘭特原油</span>
        </button>
        <button class="sidebar-link" data-target="sec-tw-adrs" onclick="navigateToSection('global', 'sec-tw-adrs', this)">
          <span class="num-pill">4</span>
          <span>台積電 / 日月光 / 鴻海 / 聯電 ADR</span>
        </button>
        <button class="sidebar-link" data-target="sec-adr-table" onclick="navigateToSection('global', 'sec-adr-table', this)">
          <span class="num-pill">5</span>
          <span>台股 ADR 折溢價對照表</span>
        </button>
      </div>

    </aside>

    <!-- Main Content Area -->
    <main class="main-area">

      <!-- 最近 5 個交易日快速切換列 -->
      <div class="history-5d-bar" id="history-5d-bar">
        <div style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:var(--text-secondary);font-weight:600;">
          <span>📅 儀表板近 5 個交易日歷史資料切換（全頁面同步）：</span>
        </div>
        <div class="history-5d-chips" id="history-5d-chips"></div>
      </div>

      <!-- ==========================================================
           PAGE 1: 台股每日盤後總覽儀表板
           ========================================================== -->
      <div id="page-overview" class="page-view active">

        <!-- KPI Summary Row (台股核心指標) -->
        <section id="sec-kpi" class="kpi-grid"></section>

        <!-- Section 1 & 2: TAIEX Trend + Institutional Summary -->
        <div class="grid-2">
          <section id="sec-taiex" class="card">
            <div class="card-header">
              <div class="card-title">
                <span class="section-tag">TWSE</span>
                每日台股加權指數走勢與成交量值
              </div>
              <div class="tab-group">
                <button class="tab-btn active" onclick="switchTaiexChart('candle', this)">K線走勢 (OHLC)</button>
                <button class="tab-btn" onclick="switchTaiexChart('line', this)">收盤走勢線</button>
              </div>
            </div>
            <div id="taiex-chart-container" class="chart-box"></div>
            <div id="taiex-breadth" class="breadth-strip"></div>
          </section>

          <section id="sec-inst-sum" class="card">
            <div class="card-header">
              <div class="card-title">
                <span class="section-tag">INSTITUTIONAL</span>
                每日三大法人買賣超金額統計 (單位：億元)
              </div>
              <span class="pill" id="inst-date-pill">--</span>
            </div>
            <div id="inst-bar-chart" class="chart-box" style="height: 210px; margin-bottom: 14px;"></div>
            <div class="table-wrap">
              <table id="inst-summary-table">
                <thead>
                  <tr>
                    <th>法人別</th>
                    <th>買進金額 (億)</th>
                    <th>賣出金額 (億)</th>
                    <th>買賣超差額 (億)</th>
                    <th>多空動向</th>
                  </tr>
                </thead>
                <tbody></tbody>
              </table>
            </div>
            <div style="margin-top:14px;">
              <div style="font-size:12.5px;font-weight:700;color:var(--accent);margin-bottom:8px;">📅 近 5 個交易日台股加權指數與三大法人買賣超總覽（點擊列可切換當日全儀表板明細）</div>
              <div class="table-wrap">
                <table id="twse-5d-summary-table">
                  <thead>
                    <tr>
                      <th>交易日期</th>
                      <th>加權收盤</th>
                      <th>漲跌點數 (%)</th>
                      <th>成交額 (億)</th>
                      <th>外資 (億)</th>
                      <th>投信 (億)</th>
                      <th>自營商 (億)</th>
                      <th>三大法人合計 (億)</th>
                    </tr>
                  </thead>
                  <tbody></tbody>
                </table>
              </div>
            </div>
          </section>
        </div>

        <!-- Section 3: 台指期夜盤走勢 (15:00-05:00) -->
        <section id="sec-txf-night" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">TAIFEX NIGHT SESSION</span>
              <span id="txf-title">台指期夜盤走勢 (15:00-05:00)</span>
            </div>
            <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
              <span class="pill" id="txf-sub">--</span>
              <span id="txf-price-badge" style="font-weight:800; font-size:15px;"></span>
              <div class="tab-group">
                <button class="tab-btn active" onclick="switchTxfMode('line', this)">1分K收盤連線</button>
                <button class="tab-btn" onclick="switchTxfMode('candle', this)">1分K線 (OHLC)</button>
              </div>
            </div>
          </div>
          <div id="chart-txf" class="chart-box" style="height: 290px;"></div>
        </section>

        <!-- Section 4: Top 15 Value & Volume -->
        <section id="sec-top15" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">TOP 15 ACTIVE</span>
              台股每日成交值 & 成交量排名前 15 名 (含當日法人買賣超張數)
            </div>
          </div>
          <div class="grid-2">
            <div>
              <h3 style="font-size:14.5px; margin-bottom:10px; color:var(--accent);">🔥 每日成交值前 15 名 (依成交金額排序)</h3>
              <div class="table-wrap">
                <table id="table-top15-value">
                  <thead>
                    <tr>
                      <th>排名</th>
                      <th>代號</th>
                      <th>名稱</th>
                      <th>成交金額(億)</th>
                      <th>成交量(張)</th>
                      <th>收盤價</th>
                      <th>漲跌幅</th>
                      <th>外資(張)</th>
                      <th>投信(張)</th>
                      <th>自營(張)</th>
                    </tr>
                  </thead>
                  <tbody></tbody>
                </table>
              </div>
            </div>

            <div>
              <h3 style="font-size:14.5px; margin-bottom:10px; color:var(--accent);">📊 每日成交量前 15 名 (依成交張數排序)</h3>
              <div class="table-wrap">
                <table id="table-top15-volume">
                  <thead>
                    <tr>
                      <th>排名</th>
                      <th>代號</th>
                      <th>名稱</th>
                      <th>成交量(張)</th>
                      <th>成交金額(億)</th>
                      <th>收盤價</th>
                      <th>漲跌幅</th>
                      <th>外資(張)</th>
                      <th>投信(張)</th>
                      <th>自營(張)</th>
                    </tr>
                  </thead>
                  <tbody></tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <!-- Section 5: Institutional Top 50 -->
        <section id="sec-top50" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">TOP 50 FLOWS</span>
              外資、投信及自營商每日買賣超前 50 名
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
              <input type="text" id="top50-search" class="search-input" placeholder="搜尋股票代號或名稱..." oninput="renderTop50Tables()" />
              <div class="tab-group" id="inst-type-tabs">
                <button class="tab-btn active" onclick="selectInstTab('foreign', this)">外資買賣超前 50</button>
                <button class="tab-btn" onclick="selectInstTab('trust', this)">投信買賣超前 50</button>
                <button class="tab-btn" onclick="selectInstTab('dealer', this)">自營商買賣超前 50</button>
                <button class="tab-btn" onclick="selectInstTab('total', this)">三大法人合計前 50</button>
              </div>
            </div>
          </div>

          <div class="grid-2">
            <div>
              <h3 style="font-size:14.5px; margin-bottom:10px;" class="up" id="buy50-heading">▲ 外資買超前 50 名 (依買超張數排序)</h3>
              <div class="table-wrap">
                <table id="table-inst-buy50">
                  <thead>
                    <tr>
                      <th>排名</th>
                      <th>代號</th>
                      <th>名稱</th>
                      <th>收盤價</th>
                      <th>漲跌幅</th>
                      <th>買進(張)</th>
                      <th>賣出(張)</th>
                      <th>買超(張)</th>
                      <th>估算金額(百萬)</th>
                    </tr>
                  </thead>
                  <tbody></tbody>
                </table>
              </div>
            </div>

            <div>
              <h3 style="font-size:14.5px; margin-bottom:10px;" class="down" id="sell50-heading">▼ 外資賣超前 50 名 (依賣超張數排序)</h3>
              <div class="table-wrap">
                <table id="table-inst-sell50">
                  <thead>
                    <tr>
                      <th>排名</th>
                      <th>代號</th>
                      <th>名稱</th>
                      <th>收盤價</th>
                      <th>漲跌幅</th>
                      <th>買進(張)</th>
                      <th>賣出(張)</th>
                      <th>賣超(張)</th>
                      <th>估算金額(百萬)</th>
                    </tr>
                  </thead>
                  <tbody></tbody>
                </table>
              </div>
            </div>
          </div>
        </section>

        <!-- Section 6: Warrants Top 20 -->
        <section id="sec-warrants" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">WARRANTS TOP 20</span>
              權證交易量每日前 20 名次 (認購 / 認售權證)
            </div>
            <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
              <span class="pill" id="warrant-summary-pill">--</span>
              <div class="tab-group">
                <button class="tab-btn active" onclick="switchWarrantSort('volume', this)">依交易量 (張數) 前 20 名</button>
                <button class="tab-btn" onclick="switchWarrantSort('value', this)">依成交金額 (萬元) 前 20 名</button>
              </div>
            </div>
          </div>
          <div class="table-wrap">
            <table id="table-warrants">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>權證代號</th>
                  <th>權證名稱</th>
                  <th>類別</th>
                  <th>成交量 (張)</th>
                  <th>成交金額 (萬)</th>
                  <th>成交筆數</th>
                  <th>權證收盤</th>
                  <th>漲跌幅</th>
                  <th>標的代號</th>
                  <th>標的名稱</th>
                  <th>標的收盤價</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </section>
      </div>

      <!-- ==========================================================
           PAGE 2: 台股每日概念族群資金輪動圖與熱力圖
           ========================================================== -->
      <div id="page-sectors" class="page-view">

        <section id="sec-heatmap" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">CONCEPT TREEMAP</span>
              概念族群熱力圖（面積＝族群成交資金規模 · 顏色＝當日平均漲跌幅，紅漲綠跌）
            </div>
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <span style="font-size:12.5px; color:var(--text-secondary);">💡 點擊任一概念方塊可查看下方成分股與法人買賣超明細</span>
              <span class="pill" id="heatmap-date-label">--</span>
            </div>
          </div>
          <div id="treemap-container" class="treemap-wrapper"></div>
        </section>

        <section id="sec-rotation" class="card">
          <div class="card-header">
            <div class="card-title" style="gap:14px;">
              <span class="section-tag">SECTOR ROTATION</span>
              <span>台股概念股輪動</span>
              <button class="replay-btn" id="btn-replay" onclick="toggleRotationReplay()">↻ 重播</button>
            </div>
            <div style="display:flex; align-items:center; gap:14px; flex-wrap:wrap;">
              <span style="font-size:13px; color:var(--text-secondary);">
                🕒 當前日期 <strong id="rot-current-date" style="color:var(--text-primary);">--</strong> · <span id="rot-total-days">20</span> 個交易日
              </span>
              <input type="range" id="rot-day-slider" class="timeline-slider" min="0" max="19" value="19" oninput="onSliderChange(this.value)" />
              <div class="tab-group">
                <button class="tab-btn active" onclick="setQuadrantFilter('all', this)">全部族群</button>
                <button class="tab-btn" onclick="setQuadrantFilter('inflow', this)">★ 主力加速流入</button>
                <button class="tab-btn" onclick="setQuadrantFilter('rotate', this)">輪動</button>
                <button class="tab-btn" onclick="setQuadrantFilter('watch', this)">觀望</button>
                <button class="tab-btn" onclick="setQuadrantFilter('outflow', this)">退潮</button>
              </div>
            </div>
          </div>

          <div id="rotation-chart-container" class="rotation-box"></div>
        </section>

        <div class="grid-2" id="sec-sector-detail">
          <section class="card">
            <div class="card-header">
              <div class="card-title">
                <span class="section-tag">CONSTITUENTS</span>
                <span id="selected-sector-title">概念族群成分股明細</span>
              </div>
              <span class="pill" id="selected-sector-stats">--</span>
            </div>
            <div class="table-wrap">
              <table id="table-sector-stocks">
                <thead>
                  <tr>
                    <th>代號</th>
                    <th>名稱</th>
                    <th>收盤價</th>
                    <th>漲跌幅</th>
                    <th>成交額(億)</th>
                    <th>成交量(張)</th>
                    <th>外資(張)</th>
                    <th>投信(張)</th>
                    <th>自營(張)</th>
                  </tr>
                </thead>
                <tbody></tbody>
              </table>
            </div>
          </section>

          <section class="card">
            <div class="card-header">
              <div class="card-title">
                <span class="section-tag">ALL SECTORS</span>
                32 大概念族群資金流向與漲跌總表
              </div>
            </div>
            <div class="table-wrap">
              <table id="table-all-sectors">
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>概念族群名稱</th>
                    <th>象限狀態</th>
                    <th>平均漲跌幅</th>
                    <th>資金相對平均</th>
                    <th>族群成交額(億)</th>
                    <th>法人淨買賣(億)</th>
                  </tr>
                </thead>
                <tbody></tbody>
              </table>
            </div>
          </section>
        </div>

      </div>

      <!-- ==========================================================
           PAGE 3: 國際金融頁面（美股四大指數 · 日經225 & 韓國KOSPI · 小那斯達克 NQ & 布蘭特原油 · 台股四大 ADR）
           ========================================================== -->
      <div id="page-global" class="page-view">

        <!-- 1. 美股四大指數即時與日K走勢 -->
        <section id="sec-us-indices" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">US 4 MAJOR INDICES</span>
              美股四大指數即時與歷史走勢（道瓊工業 · 那斯達克 · 標普 500 · 費城半導體）
            </div>
            <div class="tab-group">
              <button class="tab-btn active" onclick="switchGlobalChartMode('intraday', this)">日內即時分時走勢</button>
              <button class="tab-btn" onclick="switchGlobalChartMode('daily', this)">60日 K 線走勢 (OHLC)</button>
              <button class="tab-btn" onclick="switchGlobalChartMode('line', this)">60日收盤走勢線</button>
            </div>
          </div>

          <div id="global-us-kpi-grid" class="kpi-grid" style="margin-bottom:20px;"></div>
          <div class="grid-2" id="us-indices-charts-grid"></div>
        </section>

        <!-- 2. 日經 225 指數 & 韓國綜合指數 (KOSPI) -->
        <section id="sec-asia-indices" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">JAPAN & KOREA INDICES</span>
              日韓主要股市指數即時與歷史走勢（日經 225 指數 · 韓國綜合指數 KOSPI）
            </div>
            <div class="tab-group">
              <button class="tab-btn active" onclick="switchAsiaChartMode('intraday', this)">日內即時分時走勢</button>
              <button class="tab-btn" onclick="switchAsiaChartMode('daily', this)">60日 K 線走勢 (OHLC)</button>
              <button class="tab-btn" onclick="switchAsiaChartMode('line', this)">60日收盤走勢線</button>
            </div>
          </div>

          <div id="global-asia-kpi-grid" class="grid-2" style="margin-bottom:20px;"></div>
          <div class="grid-2" id="asia-indices-charts-grid"></div>
        </section>

        <!-- 3. 小那斯達克期貨 (NQ) & 布蘭特原油期貨 (Brent) -->
        <section id="sec-global-futures" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">GLOBAL COMMODITY & INDEX FUTURES</span>
              小那斯達克期貨 (E-mini Nasdaq-100, NQ) · 布蘭特原油期貨 (Brent Crude)
            </div>
            <div class="tab-group">
              <button class="tab-btn active" onclick="switchFuturesMode('intraday', this)">日內即時分時走勢</button>
              <button class="tab-btn" onclick="switchFuturesMode('daily', this)">60日 K 線走勢 (OHLC)</button>
              <button class="tab-btn" onclick="switchFuturesMode('line', this)">60日收盤走勢線</button>
            </div>
          </div>

          <!-- NQ & Brent KPI 卡片 -->
          <div id="global-futures-kpi-grid" class="grid-2" style="margin-bottom:20px;"></div>

          <!-- NQ & Brent 雙欄走勢圖 -->
          <div class="grid-2">
            <div style="display:flex; flex-direction:column; gap:10px;">
              <div style="display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:6px;">
                <div>
                  <strong style="font-size:15.5px;">小那斯達克期貨 (E-mini Nasdaq-100)</strong>
                  <span id="nq-sub" style="font-size:12px; color:var(--text-secondary); margin-left:8px;"></span>
                </div>
                <div id="nq-price-badge" style="font-weight:700; font-size:14px;"></div>
              </div>
              <div id="chart-nq" class="chart-box" style="height: 280px;"></div>
            </div>

            <div style="display:flex; flex-direction:column; gap:10px;">
              <div style="display:flex; justify-content:space-between; align-items:baseline; flex-wrap:wrap; gap:6px;">
                <div>
                  <strong style="font-size:15.5px;">布蘭特原油期貨 (Brent Crude)</strong>
                  <span id="brent-sub" style="font-size:12px; color:var(--text-secondary); margin-left:8px;"></span>
                </div>
                <div id="brent-price-badge" style="font-weight:700; font-size:14px;"></div>
              </div>
              <div id="chart-brent" class="chart-box" style="height: 280px;"></div>
            </div>
          </div>
        </section>

        <!-- 4. 台積電、日月光、鴻海、聯電 ADR 即時走勢 -->
        <section id="sec-tw-adrs" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">TAIWAN KEY ADRs</span>
              台股四大權值股 ADR 即時走勢（台積電 TSM · 日月光 ASX · 鴻海 HNHPF · 聯電 UMC）
            </div>
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
              <span class="pill" id="fx-usdtwd-pill">匯率 USD/TWD：--</span>
              <div class="tab-group">
                <button class="tab-btn active" onclick="switchAdrChartMode('intraday', this)">日內即時分時走勢</button>
                <button class="tab-btn" onclick="switchAdrChartMode('daily', this)">60日 K 線走勢 (OHLC)</button>
                <button class="tab-btn" onclick="switchAdrChartMode('line', this)">60日收盤走勢線</button>
              </div>
            </div>
          </div>

          <div id="global-adr-kpi-grid" class="kpi-grid" style="margin-bottom:20px;"></div>
          <div class="grid-2" id="tw-adrs-charts-grid"></div>
        </section>

        <!-- 5. 台股 ADR 折溢價與母股對照表 -->
        <section id="sec-adr-table" class="card">
          <div class="card-header">
            <div class="card-title">
              <span class="section-tag">ADR PREMIUM / DISCOUNT</span>
              台股 ADR 換算台股價格與折溢價率對照表
            </div>
            <span style="font-size:12.5px; color:var(--text-secondary);">公式：折算台股價 ＝ (ADR 收盤價 × USD/TWD 匯率) ÷ 每單位 ADR 換算台股股數</span>
          </div>
          <div class="table-wrap">
            <table id="table-adr-comparison">
              <thead>
                <tr>
                  <th>ADR 代號</th>
                  <th>ADR 名稱</th>
                  <th>對應台股</th>
                  <th>ADR 最新價 (USD)</th>
                  <th>ADR 漲跌幅</th>
                  <th>換算比例</th>
                  <th>USD/TWD 匯率</th>
                  <th>折算台股價 (TWD)</th>
                  <th>台股母股收盤 (TWD)</th>
                  <th>台股母股漲跌</th>
                  <th>ADR 折溢價率</th>
                </tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </section>

      </div>

    </main>

  </div>

  <script>
    window.DASHBOARD_DATA = __EMBEDDED_DATA_JSON__;
  </script>
  <script>
    let DATA = window.DASHBOARD_DATA || {};
    let currentMainPage = 'overview';
    let currentTaiexMode = 'candle';
    let currentTxfMode = 'line';
    let currentFuturesMode = 'intraday';
    let currentInstType = 'foreign';
    let currentWarrantSort = 'volume';

    let selectedSectorId = null;
    let rotationQuadFilter = 'all';
    let rotationDayIdx = 19;
    let replayTimer = null;

    let currentGlobalChartMode = 'intraday';
    let currentAsiaChartMode = 'intraday';
    let currentAdrChartMode = 'intraday';
    let currentSelectedDate = null;

    function fmtNum(n, digits = 0) {
      if (n === null || n === undefined || isNaN(n)) return '--';
      return Number(n).toLocaleString('en-US', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
      });
    }

    function fmtSigned(n, digits = 2, suffix = '') {
      if (n === null || n === undefined || isNaN(n)) return '--';
      const val = Number(n);
      const sign = val > 0 ? '+' : '';
      return sign + val.toLocaleString('en-US', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits
      }) + suffix;
    }

    function clsUpDown(val) {
      const v = Number(val);
      if (v > 0) return 'up';
      if (v < 0) return 'down';
      return 'flat';
    }

    function badgeUpDown(val) {
      const v = Number(val);
      if (v > 0) return 'up-badge';
      if (v < 0) return 'down-badge';
      return 'flat-badge';
    }

    function rankBadge(r) {
      const cls = r <= 3 ? `rank-badge rank-${r}` : 'rank-badge';
      return `<span class="${cls}">${r}</span>`;
    }

    function renderTradingDaySelector() {
      const avail = DATA.available_dates || (DATA.twse_date ? [DATA.twse_date] : []);
      if (!currentSelectedDate || !avail.includes(currentSelectedDate)) {
        currentSelectedDate = avail[0] || DATA.twse_date || '';
      }

      const sel = document.getElementById('twse-date-select');
      if (sel && avail.length > 0) {
        sel.innerHTML = avail.map((d, idx) => {
          const suffix = idx === 0 ? ' (最新)' : ` (前${idx}交易日)`;
          const selectedAttr = d === currentSelectedDate ? 'selected' : '';
          return `<option value="${d}" ${selectedAttr}>${d}${suffix}</option>`;
        }).join('');
      }

      const chipsBox = document.getElementById('history-5d-chips');
      const barBox = document.getElementById('history-5d-bar');
      if (barBox) {
        barBox.style.display = 'flex';
      }
      if (chipsBox && avail.length > 0) {
        chipsBox.innerHTML = avail.map((d, idx) => {
          const label = idx === 0 ? `${d} (最新)` : d;
          const activeCls = d === currentSelectedDate ? 'active' : '';
          return `<button class="day-chip ${activeCls}" onclick="switchTradingDay('${d}')">${label}</button>`;
        }).join('');
      }
    }

    function switchTradingDay(dateIso) {
      const hist = (DATA.history_5d && DATA.history_5d[dateIso]) || null;
      currentSelectedDate = dateIso;
      if (hist) {
        DATA.twse_date = hist.twse_date || dateIso;
        DATA.twse_date_raw = hist.twse_date_raw || dateIso.replace(/-/g, '');
        if (!DATA.taiex) DATA.taiex = {};
        if (hist.taiex_latest) DATA.taiex.latest = hist.taiex_latest;
        if (hist.taiex_breadth) DATA.taiex.breadth = hist.taiex_breadth;
        if (hist.taiex_series) DATA.taiex.series = hist.taiex_series;
        if (hist.institutional_summary) DATA.institutional_summary = hist.institutional_summary;
        if (hist.institutional_top50) DATA.institutional_top50 = hist.institutional_top50;
        if (hist.top15_value) DATA.top15_value = hist.top15_value;
        if (hist.top15_volume) DATA.top15_volume = hist.top15_volume;
        if (hist.concept_sectors) {
          DATA.concept_sectors = hist.concept_sectors;
          const csDates = hist.concept_sectors.dates || [];
          const foundIdx = csDates.indexOf(dateIso);
          if (foundIdx >= 0) rotationDayIdx = foundIdx;
          else if (csDates.length > 0) rotationDayIdx = csDates.length - 1;
        }
        if (hist.warrants) DATA.warrants = hist.warrants;
        if (hist.txf_night) DATA.txf_night = hist.txf_night;
        if (hist.brent) DATA.brent = hist.brent;
        if (hist.nq) DATA.nq = hist.nq;
        if (hist.global_markets) DATA.global_markets = hist.global_markets;
      }

      renderTradingDaySelector();
      renderKPIs();
      renderTaiexSection();
      renderInstitutionalSummary();
      renderTxfNightSection();
      renderTop15Section();
      renderTop50Tables();
      renderWarrantsSection();
      if (currentMainPage === 'sectors') {
        renderConceptSectorsPage();
      } else if (currentMainPage === 'global') {
        renderGlobalMarketsPage();
      }
    }

    function redrawActivePageCharts() {
      if (currentMainPage === 'sectors') {
        renderTreemap();
        renderRotationChart();
      } else if (currentMainPage === 'global') {
        renderGlobalMarketsPage();
      } else {
        renderTaiexSection();
        renderTxfNightSection();
      }
    }

    function toggleSidebar() {
      if (window.innerWidth <= 1024) {
        document.body.classList.toggle('sidebar-open-mobile');
      } else {
        document.body.classList.toggle('sidebar-collapsed');
        setTimeout(() => {
          redrawActivePageCharts();
        }, 240);
      }
    }

    function navigateToSection(page, sectionId, linkBtn) {
      document.querySelectorAll('.sidebar-link').forEach(b => b.classList.remove('active'));
      if (linkBtn) {
        linkBtn.classList.add('active');
      } else {
        const match = document.querySelector(`.sidebar-link[data-target="${sectionId}"]`);
        if (match) match.classList.add('active');
      }

      if (currentMainPage !== page) {
        switchMainPage(page, false);
      }

      setTimeout(() => {
        const el = document.getElementById(sectionId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 40);

      if (window.innerWidth <= 1024) {
        document.body.classList.remove('sidebar-open-mobile');
      }
    }

    function switchMainPage(page, updateSidebarDefault = true) {
      currentMainPage = page;
      document.getElementById('page-overview').classList.toggle('active', page === 'overview');
      document.getElementById('page-sectors').classList.toggle('active', page === 'sectors');
      document.getElementById('page-global').classList.toggle('active', page === 'global');

      document.getElementById('btn-page-overview').classList.toggle('active', page === 'overview');
      document.getElementById('btn-page-sectors').classList.toggle('active', page === 'sectors');
      document.getElementById('btn-page-global').classList.toggle('active', page === 'global');

      const barBox = document.getElementById('history-5d-bar');
      if (barBox) {
        barBox.style.display = 'flex';
      }

      if (window.innerWidth <= 1024) {
        document.body.classList.remove('sidebar-open-mobile');
      }

      if (updateSidebarDefault) {
        document.querySelectorAll('.sidebar-link').forEach(b => b.classList.remove('active'));
        const defaultTarget = page === 'overview' ? 'sec-kpi' : (page === 'sectors' ? 'sec-heatmap' : 'sec-us-indices');
        const firstBtn = document.querySelector(`.sidebar-link[data-target="${defaultTarget}"]`);
        if (firstBtn) firstBtn.classList.add('active');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }

      if (page === 'sectors') {
        renderConceptSectorsPage();
      } else if (page === 'global') {
        renderGlobalMarketsPage();
      } else {
        renderTaiexSection();
        renderTxfNightSection();
      }
    }

    // =========================================================================
    // Page 3 Renderers: US 4 Major Indices, Asia Indices (Nikkei/KOSPI), NQ & Brent, Taiwan 4 ADRs
    // =========================================================================
    function buildRecent5dStripHtml(recentList, pricePrefix = '', isAdr = false) {
      if (!recentList || !recentList.length) return '';
      return `
        <div class="recent-5d-strip">
          <div class="recent-5d-title">📅 近 5 個交易日歷史紀錄</div>
          ${recentList.map((r, i) => `
            <div class="recent-5d-row ${i === 0 ? 'active-day' : ''}">
              <span style="color:var(--text-secondary);">${r.date || ''}</span>
              <span style="font-weight:700;">${pricePrefix}${fmtNum(r.close, 2)}${isAdr && r.implied_tw_price ? ` <span style="font-size:10px;color:var(--text-muted);">(折NT$${fmtNum(r.implied_tw_price, 0)})</span>` : ''}</span>
              <span class="${clsUpDown(r.change)}" style="font-weight:700;">${fmtSigned(r.change_pct, 2, '%')}</span>
            </div>
          `).join('')}
        </div>
      `;
    }

    function buildIndexKpiCardHtml(item, isAdr = false) {
      const cardCls = item.change > 0 ? 'up-card' : (item.change < 0 ? 'down-card' : '');
      const pricePrefix = isAdr ? '$' : '';
      const footLeft = isAdr
        ? `折算台股: NT$${fmtNum(item.implied_tw_price, 2)} (${item.tw_name} ${fmtNum(item.tw_close, 2)})`
        : `${item.en_name || item.symbol}`;
      const footRight = isAdr
        ? `折溢價: ${fmtSigned(item.premium_pct, 2, '%')}`
        : `高低 ${fmtNum(item.low, 2)} ~ ${fmtNum(item.high, 2)}`;

      return `
        <div class="kpi-card ${cardCls}">
          <div class="kpi-title">
            <span>${item.name} <span class="code-tag" style="margin-left:4px;">${item.code || item.symbol}</span></span>
            <span style="font-size:11px; color:var(--text-muted);">${item.date || ''}</span>
          </div>
          <div class="kpi-value ${clsUpDown(item.change)}">${pricePrefix}${fmtNum(item.last, 2)}</div>
          <div class="kpi-change ${badgeUpDown(item.change)}">
            ${fmtSigned(item.change, 2)} (${fmtSigned(item.change_pct, 2, '%')})
          </div>
          <div class="kpi-foot">
            <span>${footLeft}</span>
            <span class="${isAdr ? clsUpDown(item.premium_pct) : ''}" style="font-weight:${isAdr ? '700' : '400'};">${footRight}</span>
          </div>
          ${buildRecent5dStripHtml(item.recent_5d, pricePrefix, isAdr)}
        </div>
      `;
    }

    function renderGlobalFuturesSection() {
      const nq = DATA.nq || {};
      const brent = DATA.brent || {};

      const futuresCards = [
        {
          title: '小那斯達克期貨 (E-mini Nasdaq-100, NQ)',
          tag: nq.date || '',
          value: fmtNum(nq.last, 2),
          chg: `${fmtSigned(nq.change, 2)} (${fmtSigned(nq.change_pct, 2, '%')})`,
          rawChg: nq.change,
          footLeft: `成交量 ${fmtNum(nq.volume, 0)} 口`,
          footRight: `當日高低 ${fmtNum(nq.low, 2)} ~ ${fmtNum(nq.high, 2)}`,
          recent_5d: nq.recent_5d || [],
          prefix: ''
        },
        {
          title: '布蘭特原油期貨 (Brent Crude Oil)',
          tag: brent.date || '',
          value: `$${fmtNum(brent.last, 2)}`,
          chg: `${fmtSigned(brent.change, 2)} (${fmtSigned(brent.change_pct, 2, '%')})`,
          rawChg: brent.change,
          footLeft: `成交量 ${fmtNum(brent.volume, 0)} 口`,
          footRight: `當日高低 $${fmtNum(brent.low, 2)} ~ $${fmtNum(brent.high, 2)}`,
          recent_5d: brent.recent_5d || [],
          prefix: '$'
        }
      ];

      const kpiBox = document.getElementById('global-futures-kpi-grid');
      if (kpiBox) {
        kpiBox.innerHTML = futuresCards.map(c => {
          const cardCls = c.rawChg > 0 ? 'up-card' : (c.rawChg < 0 ? 'down-card' : '');
          return `
            <div class="kpi-card ${cardCls}">
              <div class="kpi-title">
                <span>${c.title}</span>
                <span style="font-size:11px; color:var(--text-muted);">${c.tag}</span>
              </div>
              <div class="kpi-value ${clsUpDown(c.rawChg)}">${c.value}</div>
              <div class="kpi-change ${badgeUpDown(c.rawChg)}">${c.chg}</div>
              <div class="kpi-foot">
                <span>${c.footLeft}</span>
                <span>${c.footRight}</span>
              </div>
              ${buildRecent5dStripHtml(c.recent_5d, c.prefix, false)}
            </div>
          `;
        }).join('');
      }

      document.getElementById('nq-sub').textContent = nq.date || '';
      document.getElementById('nq-price-badge').className = clsUpDown(nq.change);
      document.getElementById('nq-price-badge').textContent = `${fmtNum(nq.last, 2)} (${fmtSigned(nq.change, 2)} / ${fmtSigned(nq.change_pct, 2, '%')})`;

      document.getElementById('brent-sub').textContent = brent.date || '';
      document.getElementById('brent-price-badge').className = clsUpDown(brent.change);
      document.getElementById('brent-price-badge').textContent = `$${fmtNum(brent.last, 2)} (${fmtSigned(brent.change, 2)} / ${fmtSigned(brent.change_pct, 2, '%')})`;

      const nqSeries = currentFuturesMode === 'intraday' && (nq.intraday_bars || []).length
        ? nq.intraday_bars
        : (nq.daily_bars || []);
      renderInteractiveChart('chart-nq', nqSeries, {
        mode: currentFuturesMode === 'daily' ? 'candle' : 'line',
        decimals: 2
      });

      const brentSeries = currentFuturesMode === 'intraday' && (brent.intraday_bars || []).length
        ? brent.intraday_bars
        : (brent.daily_bars || []);
      renderInteractiveChart('chart-brent', brentSeries, {
        mode: currentFuturesMode === 'daily' ? 'candle' : 'line',
        decimals: 2
      });
    }

    function switchFuturesMode(mode, btn) {
      currentFuturesMode = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderGlobalFuturesSection();
    }

    function renderGlobalMarketsPage() {
      const gm = DATA.global_markets || {};
      const usIndices = gm.us_indices || [];
      const asiaIndices = gm.asia_indices || [];
      const twAdrs = gm.tw_adrs || [];
      const usdTwd = gm.usd_twd || 32.15;

      document.getElementById('fx-usdtwd-pill').innerHTML = `匯率 USD/TWD：<strong>${fmtNum(usdTwd, 3)}</strong>`;

      document.getElementById('global-us-kpi-grid').innerHTML =
        usIndices.map(it => buildIndexKpiCardHtml(it, false)).join('');
      const asiaKpiEl = document.getElementById('global-asia-kpi-grid');
      if (asiaKpiEl) {
        asiaKpiEl.innerHTML = asiaIndices.map(it => buildIndexKpiCardHtml(it, false)).join('');
      }
      document.getElementById('global-adr-kpi-grid').innerHTML =
        twAdrs.map(it => buildIndexKpiCardHtml(it, true)).join('');

      const usGrid = document.getElementById('us-indices-charts-grid');
      usGrid.innerHTML = usIndices.map((it, idx) => `
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;">
            <div>
              <strong style="font-size:15.5px;">${it.name} (${it.code})</strong>
              <span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">${it.en_name || ''} · ${it.date || ''}</span>
            </div>
            <div class="${clsUpDown(it.change)}" style="font-weight:700;font-size:14px;">
              ${fmtNum(it.last, 2)} (${fmtSigned(it.change, 2)} / ${fmtSigned(it.change_pct, 2, '%')})
            </div>
          </div>
          <div id="chart-us-idx-${idx}" class="chart-box" style="height:275px;"></div>
        </div>
      `).join('');

      usIndices.forEach((it, idx) => {
        const series = (currentGlobalChartMode === 'intraday' && (it.intraday_bars || []).length)
          ? it.intraday_bars
          : (it.daily_bars || []);
        const mode = currentGlobalChartMode === 'daily' ? 'candle' : 'line';
        renderInteractiveChart(`chart-us-idx-${idx}`, series, { mode, decimals: 2 });
      });

      // Render Japan Nikkei 225 & Korea KOSPI Indices
      const asiaGrid = document.getElementById('asia-indices-charts-grid');
      if (asiaGrid) {
        asiaGrid.innerHTML = asiaIndices.map((it, idx) => `
          <div style="display:flex;flex-direction:column;gap:8px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;">
              <div>
                <strong style="font-size:15.5px;">${it.name} (${it.code})</strong>
                <span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">${it.en_name || ''} · ${it.date || ''}</span>
              </div>
              <div class="${clsUpDown(it.change)}" style="font-weight:700;font-size:14px;">
                ${fmtNum(it.last, 2)} (${fmtSigned(it.change, 2)} / ${fmtSigned(it.change_pct, 2, '%')})
              </div>
            </div>
            <div id="chart-asia-idx-${idx}" class="chart-box" style="height:275px;"></div>
          </div>
        `).join('');

        asiaIndices.forEach((it, idx) => {
          const series = (currentAsiaChartMode === 'intraday' && (it.intraday_bars || []).length)
            ? it.intraday_bars
            : (it.daily_bars || []);
          const mode = currentAsiaChartMode === 'daily' ? 'candle' : 'line';
          renderInteractiveChart(`chart-asia-idx-${idx}`, series, { mode, decimals: 2 });
        });
      }

      // Render NQ & Brent Futures on Global Page
      renderGlobalFuturesSection();

      const adrGrid = document.getElementById('tw-adrs-charts-grid');
      adrGrid.innerHTML = twAdrs.map((it, idx) => `
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;">
            <div>
              <strong style="font-size:15.5px;">${it.name} (${it.code})</strong>
              <span style="font-size:12px;color:var(--text-secondary);margin-left:8px;">對應 ${it.tw_code} ${it.tw_name} · 折算 NT$${fmtNum(it.implied_tw_price, 2)}</span>
            </div>
            <div class="${clsUpDown(it.change)}" style="font-weight:700;font-size:14px;">
              $${fmtNum(it.last, 2)} (${fmtSigned(it.change, 2)} / ${fmtSigned(it.change_pct, 2, '%')})
            </div>
          </div>
          <div id="chart-tw-adr-${idx}" class="chart-box" style="height:275px;"></div>
        </div>
      `).join('');

      twAdrs.forEach((it, idx) => {
        const series = (currentAdrChartMode === 'intraday' && (it.intraday_bars || []).length)
          ? it.intraday_bars
          : (it.daily_bars || []);
        const mode = currentAdrChartMode === 'daily' ? 'candle' : 'line';
        renderInteractiveChart(`chart-tw-adr-${idx}`, series, { mode, decimals: 2 });
      });

      document.querySelector('#table-adr-comparison tbody').innerHTML = twAdrs.map(it => `
        <tr>
          <td><span class="code-tag">${it.code}</span></td>
          <td style="font-weight:700;">${it.name}</td>
          <td><span class="code-tag">${it.tw_code}</span> ${it.tw_name}</td>
          <td class="${clsUpDown(it.change)}" style="font-weight:700;">$${fmtNum(it.last, 2)}</td>
          <td><span class="kpi-change ${badgeUpDown(it.change_pct)}" style="font-size:12px;">${fmtSigned(it.change_pct, 2, '%')}</span></td>
          <td>1 ADR = ${it.ratio} 股</td>
          <td>${fmtNum(it.usd_twd, 3)}</td>
          <td style="font-weight:700;">NT$${fmtNum(it.implied_tw_price, 2)}</td>
          <td>NT$${fmtNum(it.tw_close, 2)}</td>
          <td class="${clsUpDown(it.tw_change_pct)}">${fmtSigned(it.tw_change_pct, 2, '%')}</td>
          <td><span class="kpi-change ${badgeUpDown(it.premium_pct)}" style="font-size:12px;">${fmtSigned(it.premium_pct, 2, '%')}</span></td>
        </tr>
      `).join('');
    }

    function switchGlobalChartMode(mode, btn) {
      currentGlobalChartMode = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderGlobalMarketsPage();
    }

    function switchAsiaChartMode(mode, btn) {
      currentAsiaChartMode = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderGlobalMarketsPage();
    }

    function switchAdrChartMode(mode, btn) {
      currentAdrChartMode = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderGlobalMarketsPage();
    }

    // =========================================================================
    // Squarified Treemap Algorithm & Renderer (Page 2)
    // =========================================================================
    function getTreemapColor(pct) {
      const v = Number(pct || 0);
      if (v >= 3.5) return '#7f1d1d';
      if (v >= 2.0) return '#991b1b';
      if (v >= 1.2) return '#dc2626';
      if (v > 0.0)  return '#f48fb1';
      if (v === 0)  return '#334155';
      if (v > -1.0) return '#7be3a6';
      if (v > -2.0) return '#16a34a';
      if (v > -3.5) return '#156d3b';
      if (v > -5.5) return '#14532d';
      return '#0f4726';
    }

    function computeTreemapLayout(items, x, y, w, h) {
      const results = [];
      function layoutRec(list, rx, ry, rw, rh) {
        if (!list.length || rw <= 0 || rh <= 0) return;
        if (list.length === 1) {
          results.push({ item: list[0], x: rx, y: ry, w: rw, h: rh });
          return;
        }
        const total = list.reduce((acc, it) => acc + it.display_weight, 0);
        if (total <= 0) return;

        let half = 0;
        let splitIdx = 0;
        for (let i = 0; i < list.length; i++) {
          half += list[i].display_weight;
          if (half >= total * 0.45 || i === list.length - 2) {
            splitIdx = i + 1;
            break;
          }
        }
        const leftList = list.slice(0, splitIdx);
        const rightList = list.slice(splitIdx);
        const leftSum = leftList.reduce((acc, it) => acc + it.display_weight, 0);
        const ratio = leftSum / total;

        if (rw >= rh) {
          const lw = rw * ratio;
          layoutRec(leftList, rx, ry, lw, rh);
          layoutRec(rightList, rx + lw, ry, rw - lw, rh);
        } else {
          const lh = rh * ratio;
          layoutRec(leftList, rx, ry, rw, lh);
          layoutRec(rightList, rx, ry + lh, rw, rh - lh);
        }
      }
      layoutRec(items, x, y, w, h);
      return results;
    }

    function renderTreemap() {
      const container = document.getElementById('treemap-container');
      if (!container) return;
      const cs = DATA.concept_sectors || {};
      const sectors = (cs.sectors || []).slice().sort((a, b) => b.display_weight - a.display_weight);
      document.getElementById('heatmap-date-label').textContent = `${DATA.twse_date || ''} · 共 ${sectors.length} 個概念族群`;

      if (!sectors.length) {
        container.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted);">暫無概念族群資料</div>';
        return;
      }

      const rect = container.getBoundingClientRect();
      const W = Math.max(rect.width, 250);
      const H = Math.max(rect.height, 420);
      const isMobile = W < 500;

      const boxes = computeTreemapLayout(sectors, 0, 0, W, H);
      container.innerHTML = boxes.map(b => {
        const s = b.item;
        const bg = getTreemapColor(s.avg_change_pct);
        const textDark = (s.avg_change_pct > -1.0 && s.avg_change_pct < 1.2 && s.avg_change_pct !== 0);
        const textColor = textDark ? '#0b1727' : '#ffffff';
        const minSide = Math.min(b.w, b.h);
        const maxNameFont = isMobile ? 15 : 26;
        const maxPctFont = isMobile ? 14 : 24;
        const nameFont = Math.max(9, Math.min(maxNameFont, Math.floor(minSide * 0.165)));
        const pctFont = Math.max(8.5, Math.min(maxPctFont, Math.floor(minSide * 0.155)));
        const isSelected = s.id === selectedSectorId ? 'selected-node' : '';
        const signStr = s.avg_change_pct > 0 ? `+${s.avg_change_pct}%` : `${s.avg_change_pct}%`;

        return `
          <div class="treemap-node ${isSelected}"
               style="left:${b.x.toFixed(1)}px;top:${b.y.toFixed(1)}px;width:${b.w.toFixed(1)}px;height:${b.h.toFixed(1)}px;background:${bg};"
               onclick="selectConceptSector('${s.id}')"
               title="${s.name} | 平均漲跌幅: ${signStr} | 成交額: ${s.turnover_100m}億 | 法人買賣超: ${fmtSigned(s.inst_net_100m, 2)}億">
            <div class="tm-name" style="font-size:${nameFont}px;color:${textColor};${textDark ? 'text-shadow:none;' : ''}">${s.name}</div>
            <div class="tm-pct" style="font-size:${pctFont}px;color:${textColor};${textDark ? 'text-shadow:none;' : ''}">${signStr}</div>
          </div>
        `;
      }).join('');
    }

    // =========================================================================
    // 4-Quadrant Concept Sector Capital Rotation Chart (Page 2)
    // =========================================================================
    function renderRotationChart() {
      const container = document.getElementById('rotation-chart-container');
      if (!container) return;
      const cs = DATA.concept_sectors || {};
      const dates = cs.dates || [DATA.twse_date || ''];
      const allSectors = cs.sectors || [];

      const slider = document.getElementById('rot-day-slider');
      if (slider && dates.length > 0) {
        slider.max = dates.length - 1;
        if (rotationDayIdx >= dates.length) rotationDayIdx = dates.length - 1;
        slider.value = rotationDayIdx;
      }

      const curDate = dates[rotationDayIdx] || DATA.twse_date || '--';
      document.getElementById('rot-current-date').textContent = curDate;
      document.getElementById('rot-total-days').textContent = dates.length;

      const rect = container.getBoundingClientRect();
      const W = Math.max(rect.width, 260);
      const H = Math.max(rect.height, 440);
      const isMobile = W < 520;
      const padL = isMobile ? 38 : 70;
      const padR = isMobile ? 12 : 36;
      const padT = isMobile ? 18 : 26;
      const padB = isMobile ? 42 : 56;
      const plotW = W - padL - padR;
      const plotH = H - padT - padB;

      const zeroX = padL + plotW * 0.62;
      const zeroY = padT + plotH * 0.50;

      function mapX(xPct) {
        const v = Number(xPct || 0);
        const edgePad = isMobile ? 14 : 25;
        if (v < 0) {
          const clamped = Math.max(-115, v);
          return zeroX + (clamped / 115) * (zeroX - (padL + edgePad));
        } else {
          const clamped = Math.min(440, v);
          return zeroX + (clamped / 440) * ((W - padR - edgePad) - zeroX);
        }
      }

      function mapY(yVal) {
        const v = Math.max(-350, Math.min(350, Number(yVal || 0)));
        return zeroY - (v / 350) * (plotH / 2);
      }

      let gridSvg = `
        <rect x="${padL}" y="${padT}" width="${zeroX - padL}" height="${zeroY - padT}" fill="#eef2ff" />
        <rect x="${zeroX}" y="${padT}" width="${W - padR - zeroX}" height="${zeroY - padT}" fill="#dcfce7" />
        <rect x="${padL}" y="${zeroY}" width="${zeroX - padL}" height="${H - padB - zeroY}" fill="#f8ede8" />
        <rect x="${zeroX}" y="${zeroY}" width="${W - padR - zeroX}" height="${H - padB - zeroY}" fill="#f6efe8" />
      `;

      const yTicks = isMobile ? [350, 200, 0, -200, -350] : [350, 300, 200, 100, 0, -100, -200, -300, -350];
      yTicks.forEach(yt => {
        const py = mapY(yt);
        const isZero = yt === 0;
        gridSvg += `<line x1="${padL}" y1="${py}" x2="${W - padR}" y2="${py}" stroke="${isZero ? '#94a3b8' : '#e2e8f0'}" stroke-width="${isZero ? 1.6 : 1}" />`;
        const lbl = yt > 0 ? `+${yt}` : (yt === 0 ? '+0' : `${yt}`);
        gridSvg += `<text x="${padL - 6}" y="${py + 4}" text-anchor="end" fill="#64748b" font-size="${isMobile ? '10' : '12.5'}" font-weight="600">${lbl}</text>`;
      });

      gridSvg += `<line x1="${zeroX}" y1="${padT}" x2="${zeroX}" y2="${H - padB}" stroke="#94a3b8" stroke-width="1.6" />`;

      (isMobile ? [-100, 200, 428] : [-100, -50, 200, 428]).forEach(xt => {
        const px = mapX(xt);
        const lbl = xt > 0 ? `+${xt}%` : `${xt}%`;
        gridSvg += `<line x1="${px}" y1="${zeroY}" x2="${px}" y2="${zeroY + 6}" stroke="#64748b" stroke-width="1.2" />`;
        gridSvg += `<text x="${px}" y="${zeroY + (isMobile ? 18 : 24)}" text-anchor="middle" fill="#334155" font-size="${isMobile ? '10.5' : '13'}" font-weight="600">${lbl}</text>`;
      });

      const qTitleSize = isMobile ? 14 : 20;
      const qSubSize = isMobile ? 10.5 : 13.5;
      const quadLabelsSvg = `
        <text x="${padL + 8}" y="${padT + (isMobile ? 18 : 26)}" fill="#6366f1" font-size="${qTitleSize}" font-weight="800">觀望</text>
        <text x="${padL + 8}" y="${padT + (isMobile ? 33 : 46)}" fill="#818cf8" font-size="${qSubSize}" font-weight="600">資金來但沒人接</text>

        <text x="${W - padR - 8}" y="${padT + (isMobile ? 18 : 26)}" text-anchor="end" fill="#10b981" font-size="${qTitleSize}" font-weight="800">主力加速流入 ★</text>
        <text x="${W - padR - 8}" y="${padT + (isMobile ? 33 : 46)}" text-anchor="end" fill="#34d399" font-size="${qSubSize}" font-weight="600">錢正大力進場</text>

        <text x="${padL + 8}" y="${H - padB - (isMobile ? 20 : 26)}" fill="#ea580c" font-size="${qTitleSize}" font-weight="800">退潮</text>
        <text x="${padL + 8}" y="${H - padB - 6}" fill="#f97316" font-size="${qSubSize}" font-weight="600">資金流出，別追</text>

        <text x="${W - padR - 8}" y="${H - padB - (isMobile ? 20 : 26)}" text-anchor="end" fill="#d97706" font-size="${qTitleSize}" font-weight="800">輪動</text>
        <text x="${W - padR - 8}" y="${H - padB - 6}" text-anchor="end" fill="#f59e0b" font-size="${qSubSize}" font-weight="600">熱度開始轉移</text>

        <text x="${padL + (isMobile ? 8 : 40)}" y="${H - 12}" fill="#64748b" font-size="${isMobile ? '11' : '14'}" font-weight="700">← 資金流出</text>
        <text x="${W - padR - (isMobile ? 8 : 40)}" y="${H - 12}" text-anchor="end" fill="#64748b" font-size="${isMobile ? '11' : '14'}" font-weight="700">資金流入 →</text>
      `;

      let bubblesSvg = '';
      allSectors.forEach(s => {
        const trail = s.trail || [];
        const pt = trail[rotationDayIdx] || { x: s.flow_rel_pct, y: s.momentum_y };
        const xVal = pt.x;
        const yVal = pt.y;

        let qType = 'rotate';
        if (xVal >= 0 && yVal >= 0) qType = 'inflow';
        else if (xVal < 0 && yVal >= 0) qType = 'watch';
        else if (xVal < 0 && yVal < 0) qType = 'outflow';

        if (rotationQuadFilter !== 'all' && rotationQuadFilter !== qType) return;

        const cx = mapX(xVal);
        const cy = mapY(yVal);
        const rBase = Math.max(20, Math.min(54, Math.sqrt(s.display_weight) * 3.2));
        const r = isMobile ? rBase * 0.62 : rBase;

        const styleMap = {
          inflow:  { fill: 'rgba(16, 185, 129, 0.42)', stroke: '#059669' },
          watch:   { fill: 'rgba(129, 140, 248, 0.42)', stroke: '#6366f1' },
          outflow: { fill: 'rgba(249, 115, 22, 0.42)',  stroke: '#ea580c' },
          rotate:  { fill: 'rgba(245, 158, 11, 0.42)',  stroke: '#d97706' }
        };
        const st = styleMap[qType];

        let trailSvg = '';
        if (rotationDayIdx > 0 && trail.length > 1) {
          const prevIdx = Math.max(0, rotationDayIdx - 3);
          const pts = trail.slice(prevIdx, rotationDayIdx + 1).map(p => `${mapX(p.x).toFixed(1)},${mapY(p.y).toFixed(1)}`).join(' ');
          trailSvg = `<polyline points="${pts}" fill="none" stroke="${st.stroke}" stroke-width="2" stroke-opacity="0.45" stroke-dasharray="3,2" />`;
        }

        const shortName = s.name.length > (isMobile ? 5 : 7) ? s.name.slice(0, isMobile ? 4 : 6) + '…' : s.name;
        const xStr = xVal > 0 ? `+${Math.round(xVal)}%` : `${Math.round(xVal)}%`;
        const isSel = s.id === selectedSectorId;
        const lblFontSize = isMobile ? 10 : 12.5;

        bubblesSvg += `
          <g style="cursor:pointer;" onclick="selectConceptSector('${s.id}')">
            ${trailSvg}
            <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${r.toFixed(1)}"
                    fill="${st.fill}" stroke="${isSel ? '#0284c7' : st.stroke}" stroke-width="${isSel ? 3.5 : 1.8}" />
            <text x="${cx.toFixed(1)}" y="${(cy - (xVal >= 0 && !isMobile ? 3 : -3.5)).toFixed(1)}"
                  text-anchor="middle" fill="#ffffff" font-size="${lblFontSize}" font-weight="800"
                  style="paint-order:stroke;stroke:#1e293b;stroke-width:2.5px;stroke-linejoin:round;">${shortName}</text>
            ${xVal >= 0 && !isMobile ? `<text x="${cx.toFixed(1)}" y="${(cy + 13).toFixed(1)}"
                  text-anchor="middle" fill="#ffffff" font-size="11" font-weight="700"
                  style="paint-order:stroke;stroke:#1e293b;stroke-width:2.5px;stroke-linejoin:round;">${xStr}</text>` : ''}
            <title>${s.name} | 資金相對平均: ${xStr} | 動能Y: ${yVal} | 當日平均漲跌: ${fmtSigned(s.avg_change_pct, 2, '%')} | 成交額: ${s.turnover_100m}億</title>
          </g>
        `;
      });

      container.innerHTML = `
        <svg width="100%" height="${H}" viewBox="0 0 ${W} ${H}" style="display:block;">
          ${gridSvg}
          ${quadLabelsSvg}
          ${bubblesSvg}
        </svg>
      `;
    }

    function setQuadrantFilter(q, btn) {
      rotationQuadFilter = q;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderRotationChart();
    }

    function onSliderChange(val) {
      rotationDayIdx = Number(val);
      renderRotationChart();
    }

    function toggleRotationReplay() {
      const btn = document.getElementById('btn-replay');
      const cs = DATA.concept_sectors || {};
      const totalDays = (cs.dates || []).length || 20;

      if (replayTimer) {
        clearInterval(replayTimer);
        replayTimer = null;
        btn.textContent = '↻ 重播';
        return;
      }

      rotationDayIdx = 0;
      btn.textContent = '⏸ 暫停';
      renderRotationChart();

      replayTimer = setInterval(() => {
        rotationDayIdx++;
        if (rotationDayIdx >= totalDays) {
          rotationDayIdx = totalDays - 1;
          clearInterval(replayTimer);
          replayTimer = null;
          btn.textContent = '↻ 重播';
        }
        renderRotationChart();
      }, 320);
    }

    function selectConceptSector(sectorId) {
      selectedSectorId = sectorId;
      renderTreemap();
      renderRotationChart();
      renderSectorDetailTables();
    }

    function renderSectorDetailTables() {
      const cs = DATA.concept_sectors || {};
      const sectors = cs.sectors || [];
      if (!sectors.length) return;

      if (!selectedSectorId) {
        selectedSectorId = sectors[0].id;
      }
      const sec = sectors.find(s => s.id === selectedSectorId) || sectors[0];

      document.getElementById('selected-sector-title').textContent = `${sec.name} — 成分股明細 (${sec.stock_count} 檔)`;
      document.getElementById('selected-sector-stats').innerHTML =
        `平均漲跌：<strong class="${clsUpDown(sec.avg_change_pct)}">${fmtSigned(sec.avg_change_pct, 2, '%')}</strong> · 總成交額：<strong>${fmtNum(sec.turnover_100m, 2)} 億</strong> · 法人買賣超：<strong class="${clsUpDown(sec.inst_net_100m)}">${fmtSigned(sec.inst_net_100m, 2)} 億</strong>`;

      document.querySelector('#table-sector-stocks tbody').innerHTML = (sec.stocks || []).map(st => `
        <tr>
          <td><span class="code-tag">${st.code}</span></td>
          <td style="font-weight:600;">${st.name}</td>
          <td class="${clsUpDown(st.change)}" style="font-weight:700;">${fmtNum(st.close, 2)}</td>
          <td><span class="kpi-change ${badgeUpDown(st.change_pct)}" style="font-size:12px;">${fmtSigned(st.change_pct, 2, '%')}</span></td>
          <td style="font-weight:700;">${fmtNum(st.turnover_100m, 2)}</td>
          <td>${fmtNum(st.volume_lots, 0)}</td>
          <td class="${clsUpDown(st.foreign_net_lots)}">${fmtSigned(st.foreign_net_lots, 0)}</td>
          <td class="${clsUpDown(st.trust_net_lots)}">${fmtSigned(st.trust_net_lots, 0)}</td>
          <td class="${clsUpDown(st.dealer_net_lots)}">${fmtSigned(st.dealer_net_lots, 0)}</td>
        </tr>
      `).join('');

      const quadBadgeMap = {
        inflow:  '<span style="background:rgba(16,185,129,0.18);color:#34d399;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11.5px;">★ 主力加速流入</span>',
        watch:   '<span style="background:rgba(99,102,241,0.18);color:#818cf8;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11.5px;">觀望</span>',
        rotate:  '<span style="background:rgba(245,158,11,0.18);color:#fbbf24;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11.5px;">輪動</span>',
        outflow: '<span style="background:rgba(249,115,22,0.18);color:#fb923c;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11.5px;">退潮</span>'
      };

      const sortedByChg = sectors.slice().sort((a, b) => b.avg_change_pct - a.avg_change_pct);
      document.querySelector('#table-all-sectors tbody').innerHTML = sortedByChg.map((s, idx) => `
        <tr style="cursor:pointer;${s.id === selectedSectorId ? 'background:rgba(56,189,248,0.12);' : ''}" onclick="selectConceptSector('${s.id}')">
          <td>${rankBadge(idx + 1)}</td>
          <td style="font-weight:700;">${s.name}</td>
          <td>${quadBadgeMap[s.quadrant] || ''}</td>
          <td class="${clsUpDown(s.avg_change_pct)}" style="font-weight:700;">${fmtSigned(s.avg_change_pct, 2, '%')}</td>
          <td class="${clsUpDown(s.flow_rel_pct)}">${fmtSigned(s.flow_rel_pct, 0, '%')}</td>
          <td>${fmtNum(s.turnover_100m, 2)}</td>
          <td class="${clsUpDown(s.inst_net_100m)}" style="font-weight:700;">${fmtSigned(s.inst_net_100m, 2)}</td>
        </tr>
      `).join('');
    }

    function renderConceptSectorsPage() {
      const cs = DATA.concept_sectors || {};
      const dates = cs.dates || [];
      if (dates.length > 0 && rotationDayIdx >= dates.length) {
        rotationDayIdx = dates.length - 1;
      }
      renderTreemap();
      renderRotationChart();
      renderSectorDetailTables();
    }

    // =========================================================================
    // Page 1 Renderers (Overview - Taiwan Market Focus)
    // =========================================================================
    function renderKPIs() {
      const t = (DATA.taiex && DATA.taiex.latest) || {};
      const instItems = (DATA.institutional_summary && DATA.institutional_summary.items) || [];
      const instTotal = instItems.find(x => x.name.includes('合計')) || {};
      const instForeign = instItems.find(x => x.name.includes('外資及陸資')) || {};
      const instTrust = instItems.find(x => x.name.includes('投信')) || {};
      const txf = DATA.txf_night || {};
      const war = DATA.warrants || {};

      const metaDateEl = document.getElementById('meta-twse-date');
      if (metaDateEl) metaDateEl.textContent = DATA.twse_date || '--';
      document.getElementById('meta-updated-at').textContent = DATA.updated_at || '--';

      const cards = [
        {
          title: '台股加權指數 (TAIEX)',
          tag: t.date || '',
          value: fmtNum(t.close, 2),
          chg: `${fmtSigned(t.change, 2)} (${fmtSigned(t.change_pct, 2, '%')})`,
          rawChg: t.change,
          footLeft: `成交額 ${fmtNum(t.turnover_100m, 2)} 億`,
          footRight: `高低 ${fmtNum(t.low, 0)} ~ ${fmtNum(t.high, 0)}`
        },
        {
          title: '三大法人買賣超合計',
          tag: DATA.twse_date || '',
          value: `${fmtSigned(instTotal.net_100m, 2)} 億`,
          chg: `買 ${fmtNum(instTotal.buy_100m, 1)}億 / 賣 ${fmtNum(instTotal.sell_100m, 1)}億`,
          rawChg: instTotal.net_100m,
          footLeft: '外資/投信/自營合計',
          footRight: '單位：億元'
        },
        {
          title: '外資及陸資買賣超',
          tag: DATA.twse_date || '',
          value: `${fmtSigned(instForeign.net_100m, 2)} 億`,
          chg: `買 ${fmtNum(instForeign.buy_100m, 1)}億 / 賣 ${fmtNum(instForeign.sell_100m, 1)}億`,
          rawChg: instForeign.net_100m,
          footLeft: '不含外資自營商',
          footRight: '單位：億元'
        },
        {
          title: '投信法人買賣超',
          tag: DATA.twse_date || '',
          value: `${fmtSigned(instTrust.net_100m, 2)} 億`,
          chg: `買 ${fmtNum(instTrust.buy_100m, 1)}億 / 賣 ${fmtNum(instTrust.sell_100m, 1)}億`,
          rawChg: instTrust.net_100m,
          footLeft: '投信基金動向',
          footRight: '單位：億元'
        },
        {
          title: `${txf.name || '台指期夜盤'} (${txf.symbol_id || 'TXF'})`,
          tag: '15:00-05:00',
          value: fmtNum(txf.last, 0),
          chg: `${fmtSigned(txf.change, 0)} (${fmtSigned(txf.change_pct, 2, '%')})`,
          rawChg: txf.change,
          footLeft: `總量 ${fmtNum(txf.volume, 0)} 口`,
          footRight: `高低 ${fmtNum(txf.low, 0)} ~ ${fmtNum(txf.high, 0)}`
        },
        {
          title: '權證市場總成交表現',
          tag: DATA.twse_date || '',
          value: `${fmtNum(war.total_turnover_100m, 2)} 億`,
          chg: `總量 ${fmtNum(war.total_volume_lots, 0)} 張`,
          rawChg: 1,
          footLeft: `成交 ${fmtNum(war.active_count, 0)} 檔`,
          footRight: '認購 + 認售合計'
        }
      ];

      document.getElementById('sec-kpi').innerHTML = cards.map(c => {
        const cardCls = c.rawChg > 0 ? 'up-card' : (c.rawChg < 0 ? 'down-card' : '');
        return `
          <div class="kpi-card ${cardCls}">
            <div class="kpi-title">
              <span>${c.title}</span>
              <span style="font-size:11px; color:var(--text-muted);">${c.tag}</span>
            </div>
            <div class="kpi-value ${clsUpDown(c.rawChg)}">${c.value}</div>
            <div class="kpi-change ${badgeUpDown(c.rawChg)}">${c.chg}</div>
            <div class="kpi-foot">
              <span>${c.footLeft}</span>
              <span>${c.footRight}</span>
            </div>
          </div>
        `;
      }).join('');
    }

    function renderInteractiveChart(containerId, items, options = {}) {
      const container = document.getElementById(containerId);
      if (!container) return;
      if (!items || items.length === 0) {
        container.innerHTML = '<div style="display:flex;height:100%;align-items:center;justify-content:center;color:var(--text-muted);">暫無走勢資料</div>';
        return;
      }

      const rect = container.getBoundingClientRect();
      const W = Math.max(rect.width - 20, 220);
      const H = Math.max(rect.height - 20, 175);
      const isCompact = W < 420;
      const padL = isCompact ? 46 : 58;
      const padR = isCompact ? 8 : 16;
      const padT = 14, padB = 26;
      const priceH = Math.floor((H - padT - padB) * 0.72);
      const volTop = padT + priceH + 8;
      const volH = (H - padB) - volTop;
      const plotW = Math.max(40, W - padL - padR);

      const highs = items.map(d => Number(d.high || d.close));
      const lows = items.map(d => Number(d.low || d.close));
      const closes = items.map(d => Number(d.close));
      const vols = items.map(d => Number(d.turnover_100m || d.volume || 0));

      let minP = Math.min(...lows);
      let maxP = Math.max(...highs);
      if (maxP === minP) { maxP += 1; minP -= 1; }
      const pRange = maxP - minP;
      minP -= pRange * 0.05;
      maxP += pRange * 0.05;

      const maxV = Math.max(...vols, 1);

      const xAt = (i) => padL + (items.length === 1 ? plotW / 2 : (i / (items.length - 1)) * plotW);
      const yAt = (p) => padT + (1 - (p - minP) / (maxP - minP)) * priceH;
      const vAt = (v) => volTop + volH - (v / maxV) * volH;

      let gridSvg = '';
      for (let g = 0; g <= 4; g++) {
        const py = padT + (g / 4) * priceH;
        const pVal = maxP - (g / 4) * (maxP - minP);
        gridSvg += `<line x1="${padL}" y1="${py}" x2="${W - padR}" y2="${py}" stroke="rgba(148,163,184,0.12)" stroke-dasharray="3,3" />`;
        gridSvg += `<text x="${padL - 5}" y="${py + 4}" text-anchor="end" fill="#64748b" font-size="${isCompact ? '10' : '11'}">${fmtNum(pVal, options.decimals ?? 0)}</text>`;
      }

      const tickCount = isCompact ? 4 : 5;
      const step = Math.max(1, Math.floor(items.length / tickCount));
      for (let i = 0; i < items.length; i += step) {
        const x = xAt(i);
        const lbl = (items[i].date || items[i].time || '').slice(-5);
        gridSvg += `<text x="${x}" y="${H - 5}" text-anchor="middle" fill="#64748b" font-size="${isCompact ? '10' : '11'}">${lbl}</text>`;
      }

      let mainSvg = '';
      const barW = Math.max(1.8, Math.min(14, (plotW / items.length) * 0.65));

      if (options.mode === 'candle') {
        items.forEach((d, i) => {
          const x = xAt(i);
          const o = Number(d.open || d.close);
          const c = Number(d.close);
          const h = Number(d.high || c);
          const l = Number(d.low || c);
          const isUp = c >= o;
          const color = isUp ? '#f43f5e' : '#10b981';
          const yTop = yAt(Math.max(o, c));
          const yBot = yAt(Math.min(o, c));
          const bodyH = Math.max(1.5, yBot - yTop);
          mainSvg += `<line x1="${x}" y1="${yAt(h)}" x2="${x}" y2="${yAt(l)}" stroke="${color}" stroke-width="1.2" />`;
          mainSvg += `<rect x="${x - barW / 2}" y="${yTop}" width="${barW}" height="${bodyH}" fill="${color}" rx="1" />`;
        });
      } else {
        const firstC = closes[0];
        const lastC = closes[closes.length - 1];
        const lineColor = options.color || (lastC >= firstC ? '#f43f5e' : '#10b981');
        const pts = items.map((d, i) => `${xAt(i).toFixed(1)},${yAt(d.close).toFixed(1)}`).join(' ');
        const areaPts = `${xAt(0).toFixed(1)},${(padT + priceH).toFixed(1)} ${pts} ${xAt(items.length - 1).toFixed(1)},${(padT + priceH).toFixed(1)}`;
        const gradId = `grad-${containerId}`;
        mainSvg += `
          <defs>
            <linearGradient id="${gradId}" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="${lineColor}" stop-opacity="0.32"/>
              <stop offset="100%" stop-color="${lineColor}" stop-opacity="0.0"/>
            </linearGradient>
          </defs>
          <polygon points="${areaPts}" fill="url(#${gradId})" />
          <polyline fill="none" stroke="${lineColor}" stroke-width="2.2" points="${pts}" />
        `;
      }

      let volSvg = '';
      items.forEach((d, i) => {
        const x = xAt(i);
        const v = Number(d.turnover_100m || d.volume || 0);
        const vy = vAt(v);
        const vh = Math.max(1, (volTop + volH) - vy);
        const isUp = Number(d.close) >= Number(d.open || d.close);
        const vColor = isUp ? 'rgba(244,63,94,0.45)' : 'rgba(16,185,129,0.45)';
        volSvg += `<rect x="${x - barW / 2}" y="${vy}" width="${barW}" height="${vh}" fill="${vColor}" />`;
      });

      container.innerHTML = `
        <svg width="100%" height="${H}" viewBox="0 0 ${W} ${H}" style="overflow:visible;cursor:crosshair;touch-action:pan-y;" id="svg-${containerId}">
          ${gridSvg}
          ${volSvg}
          ${mainSvg}
          <line id="cross-v-${containerId}" x1="0" y1="${padT}" x2="0" y2="${H - padB}" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,3" visibility="hidden" />
        </svg>
        <div class="chart-tooltip" id="tip-${containerId}"></div>
      `;

      const svgEl = document.getElementById(`svg-${containerId}`);
      const crossV = document.getElementById(`cross-v-${containerId}`);
      const tipEl = document.getElementById(`tip-${containerId}`);

      function showTooltipAtClientX(clientX) {
        const b = svgEl.getBoundingClientRect();
        const mx = clientX - b.left;
        const ratio = Math.max(0, Math.min(1, (mx - padL) / plotW));
        const idx = Math.round(ratio * (items.length - 1));
        const d = items[idx];
        if (!d) return;
        const cx = xAt(idx);
        crossV.setAttribute('x1', cx);
        crossV.setAttribute('x2', cx);
        crossV.setAttribute('visibility', 'visible');

        const label = d.date || d.time || '';
        const volLabel = d.turnover_100m !== undefined
          ? `成交額: ${fmtNum(d.turnover_100m, 2)} 億`
          : `成交量: ${fmtNum(d.volume, 0)}`;
        tipEl.innerHTML = `
          <div style="font-weight:700;margin-bottom:3px;color:#38bdf8;">${label}</div>
          <div>開: <b>${fmtNum(d.open, options.decimals ?? 2)}</b> · 高: <b>${fmtNum(d.high, options.decimals ?? 2)}</b></div>
          <div>低: <b>${fmtNum(d.low, options.decimals ?? 2)}</b> · 收: <b>${fmtNum(d.close, options.decimals ?? 2)}</b></div>
          <div style="color:#94a3b8;margin-top:2px;">${volLabel}</div>
        `;
        tipEl.style.display = 'block';
        const tipLeft = Math.min(Math.max(8, W - 185), Math.max(8, cx - 70));
        tipEl.style.left = `${tipLeft}px`;
        tipEl.style.top = '10px';
      }

      svgEl.addEventListener('mousemove', (e) => showTooltipAtClientX(e.clientX));
      svgEl.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches[0]) showTooltipAtClientX(e.touches[0].clientX);
      }, { passive: true });
      svgEl.addEventListener('touchmove', (e) => {
        if (e.touches && e.touches[0]) showTooltipAtClientX(e.touches[0].clientX);
      }, { passive: true });

      svgEl.addEventListener('mouseleave', () => {
        crossV.setAttribute('visibility', 'hidden');
        tipEl.style.display = 'none';
      });
    }

    function renderTaiexSection() {
      const series = (DATA.taiex && DATA.taiex.series) || [];
      renderInteractiveChart('taiex-chart-container', series, {
        mode: currentTaiexMode,
        decimals: 2
      });

      const breadth = (DATA.taiex && DATA.taiex.breadth) || {};
      const entries = Object.entries(breadth);
      if (entries.length > 0) {
        document.getElementById('taiex-breadth').innerHTML = entries.map(([k, v]) => {
          let cls = 'flat';
          if (k.includes('上漲')) cls = 'up';
          if (k.includes('下跌')) cls = 'down';
          return `
            <div class="breadth-item">
              <span class="breadth-label">${k} (整體 / 股票)</span>
              <span class="breadth-val ${cls}">${v.all_market} / ${v.stocks}</span>
            </div>
          `;
        }).join('');
      }
    }

    function switchTaiexChart(mode, btn) {
      currentTaiexMode = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTaiexSection();
    }

    function renderInstitutionalSummary() {
      const sum = DATA.institutional_summary || {};
      const items = sum.items || [];
      document.getElementById('inst-date-pill').textContent = sum.title || DATA.twse_date || '';

      const tbody = document.querySelector('#inst-summary-table tbody');
      tbody.innerHTML = items.map(it => {
        const isTotal = it.name.includes('合計');
        const rowStyle = isTotal ? 'font-weight:700;background:rgba(56,189,248,0.06);' : '';
        const dirText = it.net_100m > 0 ? '買超 ▲' : (it.net_100m < 0 ? '賣超 ▼' : '持平');
        return `
          <tr style="${rowStyle}">
            <td>${it.name}</td>
            <td>${fmtNum(it.buy_100m, 2)}</td>
            <td>${fmtNum(it.sell_100m, 2)}</td>
            <td class="${clsUpDown(it.net_100m)}" style="font-weight:700;">${fmtSigned(it.net_100m, 2)}</td>
            <td><span class="kpi-change ${badgeUpDown(it.net_100m)}" style="font-size:12px;">${dirText}</span></td>
          </tr>
        `;
      }).join('');

      const box = document.getElementById('inst-bar-chart');
      const maxAbs = Math.max(...items.map(i => Math.abs(i.net_100m)), 1);
      box.innerHTML = `
        <div style="display:flex;flex-direction:column;justify-content:space-around;height:100%;gap:6px;">
          ${items.map(it => {
            const pct = Math.min(100, (Math.abs(it.net_100m) / maxAbs) * 100);
            const isPos = it.net_100m >= 0;
            const color = isPos ? 'var(--up)' : 'var(--down)';
            return `
              <div class="inst-bar-row">
                <div style="color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${it.name}</div>
                <div style="background:rgba(255,255,255,0.05);height:12px;border-radius:99px;overflow:hidden;position:relative;">
                  <div style="width:${pct.toFixed(1)}%;height:100%;background:${color};border-radius:99px;"></div>
                </div>
                <div class="${clsUpDown(it.net_100m)}" style="text-align:right;font-weight:700;">${fmtSigned(it.net_100m, 2)} 億</div>
              </div>
            `;
          }).join('')}
        </div>
      `;

      const tbody5d = document.querySelector('#twse-5d-summary-table tbody');
      if (tbody5d) {
        const list5d = DATA.twse_5d_overview || [];
        tbody5d.innerHTML = list5d.map(r => {
          const isCur = r.date === (currentSelectedDate || DATA.twse_date);
          const rowSt = isCur ? 'background:rgba(56,189,248,0.14);font-weight:700;cursor:pointer;' : 'cursor:pointer;';
          return `
            <tr style="${rowSt}" onclick="switchTradingDay('${r.date}')" title="點擊切換至 ${r.date} 全儀表板資料">
              <td><span class="code-tag">${r.date}</span> ${isCur ? '<span style="font-size:10.5px;color:#38bdf8;">(檢視中)</span>' : ''}</td>
              <td class="${clsUpDown(r.taiex_change)}" style="font-weight:700;">${fmtNum(r.taiex_close, 2)}</td>
              <td class="${clsUpDown(r.taiex_change)}">${fmtSigned(r.taiex_change, 2)} (${fmtSigned(r.taiex_change_pct, 2, '%')})</td>
              <td>${fmtNum(r.turnover_100m, 2)}</td>
              <td class="${clsUpDown(r.foreign_net_100m)}">${fmtSigned(r.foreign_net_100m, 2)}</td>
              <td class="${clsUpDown(r.trust_net_100m)}">${fmtSigned(r.trust_net_100m, 2)}</td>
              <td class="${clsUpDown(r.dealer_net_100m)}">${fmtSigned(r.dealer_net_100m, 2)}</td>
              <td class="${clsUpDown(r.total_net_100m)}" style="font-weight:700;">${fmtSigned(r.total_net_100m, 2)}</td>
            </tr>
          `;
        }).join('');
      }
    }

    function renderTxfNightSection() {
      const txf = DATA.txf_night || {};
      document.getElementById('txf-title').textContent = `${txf.name || '臺指期夜盤走勢'} (${txf.symbol_id || ''} · 15:00-05:00)`;
      document.getElementById('txf-sub').innerHTML =
        `夜盤總量：<strong>${fmtNum(txf.volume, 0)} 口</strong> · 開 <strong>${fmtNum(txf.open, 0)}</strong> / 高 <strong>${fmtNum(txf.high, 0)}</strong> / 低 <strong>${fmtNum(txf.low, 0)}</strong>`;
      document.getElementById('txf-price-badge').className = clsUpDown(txf.change);
      document.getElementById('txf-price-badge').textContent = `${fmtNum(txf.last, 0)} (${fmtSigned(txf.change, 0)} / ${fmtSigned(txf.change_pct, 2, '%')})`;

      renderInteractiveChart('chart-txf', txf.ticks || [], {
        mode: currentTxfMode,
        decimals: 0
      });
    }

    function switchTxfMode(mode, btn) {
      currentTxfMode = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTxfNightSection();
    }

    function renderTop15Section() {
      const valList = DATA.top15_value || [];
      const volList = DATA.top15_volume || [];
      const maxVal = Math.max(...valList.map(x => x.turnover_100m), 1);
      const maxVol = Math.max(...volList.map(x => x.volume_lots), 1);

      document.querySelector('#table-top15-value tbody').innerHTML = valList.map((r, idx) => {
        const pct = Math.min(100, (r.turnover_100m / maxVal) * 100);
        return `
          <tr>
            <td>${rankBadge(idx + 1)}</td>
            <td><span class="code-tag">${r.code}</span></td>
            <td style="font-weight:600;">${r.name}</td>
            <td>
              <div class="bar-cell">
                <span style="font-weight:700;">${fmtNum(r.turnover_100m, 2)}</span>
                <div class="mini-bar-track"><div class="mini-bar-fill" style="width:${pct}%;background:#38bdf8;"></div></div>
              </div>
            </td>
            <td>${fmtNum(r.volume_lots, 0)}</td>
            <td class="${clsUpDown(r.change)}" style="font-weight:700;">${fmtNum(r.close, 2)}</td>
            <td><span class="kpi-change ${badgeUpDown(r.change_pct)}" style="font-size:12px;">${fmtSigned(r.change_pct, 2, '%')}</span></td>
            <td class="${clsUpDown(r.foreign_net_lots)}">${fmtSigned(r.foreign_net_lots, 0)}</td>
            <td class="${clsUpDown(r.trust_net_lots)}">${fmtSigned(r.trust_net_lots, 0)}</td>
            <td class="${clsUpDown(r.dealer_net_lots)}">${fmtSigned(r.dealer_net_lots, 0)}</td>
          </tr>
        `;
      }).join('');

      document.querySelector('#table-top15-volume tbody').innerHTML = volList.map((r, idx) => {
        const pct = Math.min(100, (r.volume_lots / maxVol) * 100);
        return `
          <tr>
            <td>${rankBadge(idx + 1)}</td>
            <td><span class="code-tag">${r.code}</span></td>
            <td style="font-weight:600;">${r.name}</td>
            <td>
              <div class="bar-cell">
                <span style="font-weight:700;">${fmtNum(r.volume_lots, 0)}</span>
                <div class="mini-bar-track"><div class="mini-bar-fill" style="width:${pct}%;background:#818cf8;"></div></div>
              </div>
            </td>
            <td>${fmtNum(r.turnover_100m, 2)}</td>
            <td class="${clsUpDown(r.change)}" style="font-weight:700;">${fmtNum(r.close, 2)}</td>
            <td><span class="kpi-change ${badgeUpDown(r.change_pct)}" style="font-size:12px;">${fmtSigned(r.change_pct, 2, '%')}</span></td>
            <td class="${clsUpDown(r.foreign_net_lots)}">${fmtSigned(r.foreign_net_lots, 0)}</td>
            <td class="${clsUpDown(r.trust_net_lots)}">${fmtSigned(r.trust_net_lots, 0)}</td>
            <td class="${clsUpDown(r.dealer_net_lots)}">${fmtSigned(r.dealer_net_lots, 0)}</td>
          </tr>
        `;
      }).join('');
    }

    function selectInstTab(instKey, btn) {
      currentInstType = instKey;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderTop50Tables();
    }

    function renderTop50Tables() {
      const top50Data = (DATA.institutional_top50 && DATA.institutional_top50[currentInstType]) || { buy50: [], sell50: [] };
      const q = (document.getElementById('top50-search').value || '').trim().toLowerCase();

      const labelMap = {
        foreign: '外資及陸資',
        trust: '投信法人',
        dealer: '自營商合計',
        total: '三大法人合計'
      };
      const titleName = labelMap[currentInstType] || '法人';
      document.getElementById('buy50-heading').textContent = `▲ ${titleName}買超前 50 名 (單位：張)`;
      document.getElementById('sell50-heading').textContent = `▼ ${titleName}賣超前 50 名 (單位：張)`;

      function getFields(r) {
        if (currentInstType === 'foreign') {
          return { buy: r.foreign_buy_lots, sell: r.foreign_sell_lots, net: r.foreign_net_lots, est: r.foreign_est_m };
        } else if (currentInstType === 'trust') {
          return { buy: r.trust_buy_lots, sell: r.trust_sell_lots, net: r.trust_net_lots, est: r.trust_est_m };
        } else if (currentInstType === 'dealer') {
          return { buy: r.dealer_buy_lots, sell: r.dealer_sell_lots, net: r.dealer_net_lots, est: r.dealer_est_m };
        } else {
          return {
            buy: r.foreign_buy_lots + r.trust_buy_lots + r.dealer_buy_lots,
            sell: r.foreign_sell_lots + r.trust_sell_lots + r.dealer_sell_lots,
            net: r.total_net_lots,
            est: r.total_est_m
          };
        }
      }

      const buyList = (top50Data.buy50 || []).filter(r => !q || r.code.toLowerCase().includes(q) || r.name.toLowerCase().includes(q));
      const sellList = (top50Data.sell50 || []).filter(r => !q || r.code.toLowerCase().includes(q) || r.name.toLowerCase().includes(q));

      document.querySelector('#table-inst-buy50 tbody').innerHTML = buyList.map((r, idx) => {
        const f = getFields(r);
        return `
          <tr>
            <td>${rankBadge(idx + 1)}</td>
            <td><span class="code-tag">${r.code}</span></td>
            <td style="font-weight:600;">${r.name}</td>
            <td class="${clsUpDown(r.change_pct)}">${fmtNum(r.close, 2)}</td>
            <td class="${clsUpDown(r.change_pct)}">${fmtSigned(r.change_pct, 2, '%')}</td>
            <td>${fmtNum(f.buy, 0)}</td>
            <td>${fmtNum(f.sell, 0)}</td>
            <td class="up" style="font-weight:700;">+${fmtNum(f.net, 0)}</td>
            <td class="up">+${fmtNum(f.est, 1)}</td>
          </tr>
        `;
      }).join('');

      document.querySelector('#table-inst-sell50 tbody').innerHTML = sellList.map((r, idx) => {
        const f = getFields(r);
        return `
          <tr>
            <td>${rankBadge(idx + 1)}</td>
            <td><span class="code-tag">${r.code}</span></td>
            <td style="font-weight:600;">${r.name}</td>
            <td class="${clsUpDown(r.change_pct)}">${fmtNum(r.close, 2)}</td>
            <td class="${clsUpDown(r.change_pct)}">${fmtSigned(r.change_pct, 2, '%')}</td>
            <td>${fmtNum(f.buy, 0)}</td>
            <td>${fmtNum(f.sell, 0)}</td>
            <td class="down" style="font-weight:700;">${fmtNum(f.net, 0)}</td>
            <td class="down">${fmtNum(f.est, 1)}</td>
          </tr>
        `;
      }).join('');
    }

    function switchWarrantSort(mode, btn) {
      currentWarrantSort = mode;
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderWarrantsSection();
    }

    function renderWarrantsSection() {
      const war = DATA.warrants || {};
      document.getElementById('warrant-summary-pill').innerHTML =
        `權證總成交額：<strong>${fmtNum(war.total_turnover_100m, 2)} 億</strong> · 總張數：<strong>${fmtNum(war.total_volume_lots, 0)} 張</strong>`;

      const list = currentWarrantSort === 'value'
        ? (war.top20_value || [])
        : (war.top20_volume || []);

      const maxVol = Math.max(...list.map(x => x.volume_lots), 1);

      document.querySelector('#table-warrants tbody').innerHTML = list.map((w, idx) => {
        const typeCls = w.type === '認購' ? 'w-call' : 'w-put';
        const pct = Math.min(100, (w.volume_lots / maxVol) * 100);
        return `
          <tr>
            <td>${rankBadge(idx + 1)}</td>
            <td><span class="code-tag">${w.code}</span></td>
            <td style="font-weight:600;">${w.name}</td>
            <td><span class="${typeCls}">${w.type}</span></td>
            <td>
              <div class="bar-cell">
                <span style="font-weight:700;">${fmtNum(w.volume_lots, 0)}</span>
                <div class="mini-bar-track"><div class="mini-bar-fill" style="width:${pct}%;background:#f59e0b;"></div></div>
              </div>
            </td>
            <td style="font-weight:700;">${fmtNum(w.turnover_10k, 1)}</td>
            <td>${fmtNum(w.transactions, 0)}</td>
            <td class="${clsUpDown(w.change)}">${fmtNum(w.close, 2)}</td>
            <td><span class="kpi-change ${badgeUpDown(w.change_pct)}" style="font-size:12px;">${fmtSigned(w.change_pct, 2, '%')}</span></td>
            <td><span class="code-tag">${w.target_code}</span></td>
            <td>${w.target_name}</td>
            <td>${fmtNum(w.target_close, 2)}</td>
          </tr>
        `;
      }).join('');
    }

    function renderAll() {
      const cs = DATA.concept_sectors || {};
      const dates = cs.dates || [];
      if (dates.length > 0) {
        rotationDayIdx = dates.length - 1;
      }
      renderTradingDaySelector();
      renderKPIs();
      renderTaiexSection();
      renderInstitutionalSummary();
      renderTxfNightSection();
      renderTop15Section();
      renderTop50Tables();
      renderWarrantsSection();
      if (currentMainPage === 'sectors') {
        renderConceptSectorsPage();
      } else if (currentMainPage === 'global') {
        renderGlobalMarketsPage();
      }
    }

    window.addEventListener('DOMContentLoaded', () => {
      renderAll();
      fetch('data.json', { cache: 'no-store' })
        .then(r => r.ok ? r.json() : null)
        .then(fresh => {
          if (fresh && fresh.updated_at) {
            DATA = fresh;
            renderAll();
          }
        })
        .catch(() => {});
    });

    let lastWindowWidth = window.innerWidth;
    window.addEventListener('resize', () => {
      if (Math.abs(window.innerWidth - lastWindowWidth) < 8) return;
      lastWindowWidth = window.innerWidth;
      redrawActivePageCharts();
    });
  </script>
</body>
</html>
"""


def build_html(payload, output_path):
    embedded_json = json.dumps(payload, ensure_ascii=False)
    html = HTML_TEMPLATE.replace("__EMBEDDED_DATA_JSON__", embedded_json)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(base, "data.json")
    out_file = os.path.join(base, "index.html")
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        build_html(data, out_file)
        print(f"Built {out_file}")
