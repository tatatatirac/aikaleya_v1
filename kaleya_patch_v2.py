#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch v2 — US-focused landing (preview + friend's feedback)"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FILE = r'C:\Users\taxi0\Documents\Claude\Projects\KALEYA PROJEKAT\frontend\index.html'

with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# ─── NEW CSS (kv- prefixed, matches preview) ────────────────────────────────
NEW_CSS = r"""        /* ===== KALEYA LANDING DARK v3 — US-focused (preview + friend feedback) ===== */
        #landing-view {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #0A0A0B;
            color: #FFFFFF;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
            line-height: 1.6;
        }
        #landing-view *, #landing-view *::before, #landing-view *::after { box-sizing: border-box; }
        #landing-view a { color: inherit; text-decoration: none; }
        #landing-view img { max-width: 100%; display: block; }
        #landing-view #theme-toggle { display: none !important; }

        /* Header */
        .kv-header {
            position: sticky; top: 0; z-index: 100;
            backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            background: rgba(10,10,11,0.7); border-bottom: 1px solid #27272A;
        }
        .kv-header-inner {
            max-width: 1200px; margin: 0 auto; height: 68px; padding: 0 24px;
            display: flex; align-items: center; justify-content: space-between; gap: 24px;
        }
        .kv-logo-wrap { display: flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
        .kv-logo-img { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; }
        .kv-logo-name { font-weight: 800; font-size: 20px; letter-spacing: -0.02em; color: #FFF; }
        .kv-logo-name span { color: #A1A1AA; font-weight: 600; }
        .kv-nav { display: flex; gap: 32px; }
        .kv-nav a { color: #A1A1AA; font-size: 14px; font-weight: 500; transition: color .2s; }
        .kv-nav a:hover { color: #FFF; }
        .kv-header-right { display: flex; align-items: center; gap: 16px; }
        .kv-lang-wrap { position: relative; }
        #landing-view #langToggleBtn {
            background: #111113 !important; border: 1px solid #27272A !important; color: #FFF !important;
            border-radius: 999px; padding: 6px 12px; font-size: 12px; font-weight: 600;
            display: flex; align-items: center; gap: 6px; cursor: pointer;
        }
        #landing-view #langToggleBtn:hover { background: #18181B !important; }
        #landing-view #langDropdown {
            background: #111113 !important; border: 1px solid #27272A !important;
            border-radius: 12px; color: #FFF;
        }
        #landing-view #langDropdown .lang-btn { color: #FFF !important; }
        #landing-view #langDropdown .lang-btn:hover { background: #18181B !important; }
        .kv-login-link { color: #A1A1AA; font-size: 14px; font-weight: 500; cursor: pointer; background: none; border: none; font-family: inherit; }
        .kv-login-link:hover { color: #FFF; }
        .kv-btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            padding: 10px 16px; border-radius: 12px; font-weight: 600; font-size: 14px;
            transition: all .2s; border: 1px solid transparent; cursor: pointer; white-space: nowrap;
            text-decoration: none; font-family: inherit;
        }
        .kv-btn-primary {
            background: #2563EB; color: white;
            box-shadow: 0 1px 2px rgba(0,0,0,.2), inset 0 1px 0 rgba(255,255,255,.1);
        }
        .kv-btn-primary:hover { background: #1D4ED8; transform: translateY(-1px); }
        .kv-btn-secondary {
            background: rgba(255,255,255,0.06); border-color: #27272A; color: #FFF;
            backdrop-filter: blur(8px);
        }
        .kv-btn-secondary:hover { background: rgba(255,255,255,0.1); }
        .kv-btn-large { padding: 14px 24px; font-size: 16px; border-radius: 12px; }

        /* Hero */
        .kv-hero {
            position: relative; min-height: 780px; padding: 120px 24px 72px;
            display: flex; align-items: center; justify-content: center; overflow: hidden;
        }
        .kv-slides { position: absolute; inset: 0; z-index: 0; }
        .kv-slide {
            position: absolute; inset: 0; background-size: cover; background-position: center;
            opacity: 0; transition: opacity 1.2s ease; filter: brightness(0.55) saturate(1.1); transform: scale(1.05);
        }
        .kv-slide.kv-active { opacity: 1; transform: scale(1); transition: opacity 1.2s ease, transform 8s linear; }
        .kv-hero::after {
            content: ''; position: absolute; inset: 0; z-index: 1;
            background: radial-gradient(ellipse at center, transparent 20%, rgba(10,10,11,.58) 100%),
                        linear-gradient(180deg, rgba(10,10,11,.45) 0%, rgba(10,10,11,.78) 72%, #0A0A0B 100%);
        }
        .kv-hero-glow { position: absolute; border-radius: 999px; filter: blur(70px); opacity: .55; pointer-events: none; z-index: 1; }
        .kv-glow-l { width: 320px; height: 320px; left: -120px; top: 120px; background: rgba(167,139,250,.12); }
        .kv-glow-r { width: 420px; height: 420px; right: -120px; bottom: 10px; background: rgba(37,99,235,.10); }
        .kv-hero-split {
            position: relative; z-index: 2; max-width: 1160px; width: 100%;
            display: grid; grid-template-columns: minmax(0,1fr) minmax(360px,520px); gap: 64px; align-items: center;
        }
        .kv-hero-copy { text-align: left; max-width: 560px; }
        .kv-badge {
            display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px 6px 10px;
            background: rgba(17,17,19,.76); border: 1px solid #27272A; border-radius: 999px;
            font-size: 12px; font-weight: 500; color: #A1A1AA; margin-bottom: 26px;
            backdrop-filter: blur(8px); text-transform: uppercase; letter-spacing: .05em;
        }
        .kv-dot {
            width: 8px; height: 8px; border-radius: 50%; background: #10B981; flex-shrink: 0;
            animation: kv-pulse 2s infinite;
        }
        @keyframes kv-pulse {
            0%{box-shadow:0 0 0 0 rgba(16,185,129,.7)} 70%{box-shadow:0 0 0 8px rgba(16,185,129,0)} 100%{box-shadow:0 0 0 0 rgba(16,185,129,0)}
        }
        .kv-hero-text { transition: opacity .4s ease; }
        .kv-hero-copy h1 {
            font-size: clamp(42px,5.6vw,72px); font-weight: 800; line-height: .96;
            letter-spacing: -0.055em; margin-bottom: 22px; color: #FFF;
        }
        .kv-hero-copy > p, .kv-hero-text p {
            font-size: clamp(18px,2vw,22px); color: #A1A1AA; max-width: 520px; margin: 0 0 34px;
        }
        .kv-hero-cta { display: flex; gap: 12px; flex-wrap: wrap; }

        /* Social proof bar under hero CTA */
        .kv-trust-bar {
            display: flex; align-items: center; gap: 16px; margin-top: 24px;
            color: #71717A; font-size: 13px;
        }
        .kv-trust-bar .kv-trust-stars { color: #FBB724; font-size: 14px; letter-spacing: 1px; }
        .kv-trust-bar strong { color: #E4E4E7; font-weight: 600; }

        /* Phone mockup */
        .kv-hero-visual {
            position: relative; min-height: 640px; display: flex; align-items: center; justify-content: center;
        }
        .kv-phone-device {
            width: 378px; height: 640px; padding: 18px; border-radius: 58px; background: #030306;
            box-shadow: 0 30px 80px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.06);
        }
        .kv-phone-screen {
            height: 100%; overflow: hidden; border-radius: 43px;
            background: #030715; border: 1px solid rgba(255,255,255,.06);
        }
        .kv-phone-top {
            height: 122px; padding: 34px 36px; display: flex; align-items: flex-start;
            justify-content: space-between; color: #fff;
            background: linear-gradient(135deg, #16B6A2 0%, #1B9FB4 46%, #3B82F6 100%);
        }
        .kv-phone-status { display: flex; align-items: center; gap: 12px; font-weight: 800; letter-spacing: -.02em; }
        .kv-phone-online { width: 14px; height: 14px; border-radius: 50%; background: #34D399; box-shadow: 0 0 0 7px rgba(52,211,153,.10); }
        .kv-phone-body {
            min-height: calc(100% - 122px); padding: 34px 26px 26px;
            display: flex; flex-direction: column; align-items: center;
        }
        .kv-logo-orbit {
            width: 210px; height: 210px; border-radius: 999px; display: grid; place-items: center;
            border: 4px solid transparent; margin-bottom: 22px;
            background: linear-gradient(#030715,#030715) padding-box, linear-gradient(135deg,#C4B5FD,#60A5FA) border-box;
            box-shadow: 0 0 44px rgba(59,130,246,.18);
        }
        .kv-phone-logo { width: 138px; height: 138px; border-radius: 999px; object-fit: cover; background: #fff; }
        .kv-phone-kicker { text-transform: uppercase; letter-spacing: .16em; font-size: 13px; font-weight: 700; color: #8B94A7; margin-bottom: 6px; }
        .kv-phone-title { font-size: 44px; font-weight: 800; letter-spacing: -.045em; line-height: 1; color: #fff; }
        .kv-phone-subtitle { font-size: 20px; color: #8B94A7; margin-top: 8px; }
        .kv-mic-btn {
            width: 108px; height: 108px; border-radius: 999px; border: none; color: white;
            background: linear-gradient(135deg,#8B5CF6,#2563EB); display: grid; place-items: center;
            margin-top: 26px; cursor: pointer;
            box-shadow: 0 16px 42px rgba(37,99,235,.32), 0 0 0 20px rgba(59,130,246,.10);
        }
        .kv-mic-btn svg { width: 46px; height: 46px; }
        .kv-voice-bars { height: 40px; display: flex; align-items: flex-end; gap: 8px; margin: 22px 0 8px; }
        .kv-voice-bars span { width: 9px; border-radius: 999px; background: #C4B5FD; }
        .kv-voice-bars span:nth-child(1) { height: 14px; }
        .kv-voice-bars span:nth-child(2) { height: 28px; }
        .kv-voice-bars span:nth-child(3) { height: 40px; background: #8B5CF6; }
        .kv-voice-bars span:nth-child(4) { height: 28px; background: #60A5FA; }
        .kv-voice-bars span:nth-child(5) { height: 14px; }
        .kv-call-bubble {
            width: 100%; border-radius: 28px; background: #121827; border: 1px solid #283246;
            padding: 24px; box-shadow: 0 18px 40px rgba(0,0,0,.25);
        }
        .kv-bubble-label { color: #B8C0D3; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; font-weight: 700; margin-bottom: 10px; }
        .kv-call-bubble p { margin: 0; color: #F8FAFC; font-size: 16px; line-height: 1.55; }

        /* Floating cards */
        .kv-floating-card {
            position: absolute; display: flex; gap: 16px; align-items: flex-start;
            width: 300px; padding: 18px; border-radius: 24px;
            background: rgba(255,255,255,.96); color: #0F172A;
            box-shadow: 0 24px 70px rgba(0,0,0,.28); border: 1px solid rgba(255,255,255,.68);
        }
        .kv-floating-card strong { display: block; font-size: 19px; line-height: 1.1; margin-bottom: 8px; }
        .kv-floating-card p { margin: 0; color: #64748B; font-size: 14px; line-height: 1.45; }
        .kv-fc-tag {
            display: inline-flex; margin-top: 10px; padding: 6px 11px; border-radius: 999px;
            background: #F1E8FF; color: #7C3AED; font-size: 12px; font-weight: 700;
        }
        .kv-card-icon {
            width: 44px; height: 44px; flex: 0 0 auto; border-radius: 12px;
            display: grid; place-items: center; background: #DBEAFE; color: #2563EB;
        }
        .kv-card-icon svg { width: 21px; height: 21px; }
        .kv-card-icon-dark { background: #0F172A !important; color: #fff !important; }
        .kv-cal-card { right: -34px; top: 96px; }
        .kv-sms-card { left: -42px; bottom: 112px; width: 275px; }

        /* Sections */
        .kv-section { padding: 100px 24px; position: relative; }
        .kv-container { max-width: 1160px; margin: 0 auto; }
        .kv-section-head { text-align: center; margin-bottom: 56px; }
        .kv-eyebrow { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: #71717A; margin-bottom: 12px; }
        .kv-section-title { font-size: clamp(28px,4vw,40px); font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; color: #FFF; }
        .kv-section-sub { color: #A1A1AA; margin-top: 12px; font-size: 18px; }

        /* Works */
        .kv-works {
            padding: 60px 24px 40px;
            background: linear-gradient(180deg, #0A0A0B 0%, rgba(105,0,204,.2) 100%);
            border-top: 1px solid rgba(39,39,42,.5);
        }
        .kv-works-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 16px; max-width: 1000px; margin: 40px auto 0; }
        .kv-work-item {
            background: #111113; border: 1px solid #27272A; border-radius: 12px;
            padding: 24px 16px; text-align: center; transition: all .2s;
        }
        .kv-work-item:hover { transform: translateY(-2px); border-color: rgba(196,181,253,.45); }
        .kv-work-item:hover .kv-work-icon { color: #DDD6FE; }
        .kv-work-icon { width: 34px; height: 34px; margin: 0 auto 14px; color: #C4B5FD; }
        .kv-work-icon svg { width: 100%; height: 100%; stroke-width: 1.8; fill: none; }
        .kv-work-item span { font-weight: 600; font-size: 14px; color: #FFF; }

        /* Problem stats */
        .kv-problem-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; }
        .kv-problem-card {
            background: #111113; border: 1px solid #27272A; border-radius: 16px;
            padding: 32px; position: relative; overflow: hidden;
        }
        .kv-problem-card::before {
            content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        }
        .kv-problem-num {
            font-size: 40px; font-weight: 800; letter-spacing: -0.02em; line-height: 1; margin-bottom: 12px;
            background: linear-gradient(180deg, #fff 0%, #A1A1AA 100%);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .kv-problem-desc { color: #A1A1AA; font-size: 15px; }
        .kv-problem-desc strong { color: #FFF; font-weight: 600; }

        /* Dashboard mockup */
        .kv-dash { background: linear-gradient(180deg, #0A0A0B 0%, #0E0E10 100%); }
        .kv-dash-mock {
            max-width: 1080px; margin: 0 auto; background: #0F1014;
            border: 1px solid #27272A; border-radius: 18px; overflow: hidden;
            box-shadow: 0 40px 100px rgba(0,0,0,.5), 0 0 0 1px rgba(255,255,255,.04);
        }
        .kv-dash-topbar {
            display: flex; align-items: center; justify-content: space-between;
            padding: 14px 22px; background: #131419; border-bottom: 1px solid #27272A;
        }
        .kv-dash-dots { display: flex; gap: 7px; }
        .kv-dash-dots span { width: 12px; height: 12px; border-radius: 50%; background: #3F3F46; }
        .kv-dash-dots span:nth-child(1) { background: #EF4444; }
        .kv-dash-dots span:nth-child(2) { background: #F59E0B; }
        .kv-dash-dots span:nth-child(3) { background: #10B981; }
        .kv-dash-url { color: #71717A; font-size: 13px; font-family: 'SF Mono', Monaco, monospace; }
        .kv-dash-body { display: grid; grid-template-columns: 220px 1fr; min-height: 480px; }
        .kv-dash-side { background: #0B0C10; border-right: 1px solid #27272A; padding: 20px 14px; }
        .kv-dash-side-logo { display: flex; align-items: center; gap: 8px; padding: 6px 8px 16px; }
        .kv-dash-side-logo img { width: 24px; height: 24px; border-radius: 50%; }
        .kv-dash-side-logo span { font-weight: 700; font-size: 14px; color: #FFF; }
        .kv-dash-side-section { font-size: 11px; text-transform: uppercase; color: #52525B; letter-spacing: .08em; margin: 16px 8px 8px; font-weight: 600; }
        .kv-dash-side ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 2px; }
        .kv-dash-side ul li {
            display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px;
            color: #A1A1AA; font-size: 13px; font-weight: 500; cursor: pointer; transition: background .15s;
        }
        .kv-dash-side ul li.kv-active { background: rgba(37,99,235,.15); color: #93C5FD; }
        .kv-dash-side ul li:hover:not(.kv-active) { background: rgba(255,255,255,.04); color: #E4E4E7; }
        .kv-dash-side svg { width: 16px; height: 16px; flex-shrink: 0; }
        .kv-dash-main { padding: 24px 28px; }
        .kv-dash-h { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .kv-dash-h h3 { font-size: 18px; font-weight: 700; color: #FFF; }
        .kv-dash-h-actions { display: flex; gap: 8px; }
        .kv-dash-pill {
            padding: 6px 12px; border-radius: 8px; background: #1A1B22; border: 1px solid #27272A;
            color: #A1A1AA; font-size: 12px; font-weight: 500;
        }
        .kv-dash-pill-blue { background: #2563EB; border-color: transparent; color: white; }
        .kv-dash-stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 24px; }
        .kv-dash-stat { background: #131419; border: 1px solid #27272A; border-radius: 12px; padding: 14px; }
        .kv-dash-stat-label { font-size: 11px; text-transform: uppercase; color: #71717A; margin-bottom: 6px; letter-spacing: .05em; font-weight: 600; }
        .kv-dash-stat-val { font-size: 22px; font-weight: 800; color: #FFF; letter-spacing: -0.02em; }
        .kv-dash-stat-val .kv-up { color: #10B981; font-size: 12px; font-weight: 600; margin-left: 6px; }
        .kv-dash-list { background: #131419; border: 1px solid #27272A; border-radius: 12px; overflow: hidden; }
        .kv-dash-row {
            display: grid; grid-template-columns: 1fr auto auto auto; gap: 12px; align-items: center;
            padding: 14px 18px; border-bottom: 1px solid #1F2028;
        }
        .kv-dash-row:last-child { border-bottom: none; }
        .kv-dash-row-name { display: flex; align-items: center; gap: 12px; color: #FFF; font-size: 14px; font-weight: 500; }
        .kv-dash-avatar {
            width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
            font-weight: 700; font-size: 12px; color: white;
        }
        .kv-dash-av-1 { background: linear-gradient(135deg, #F87171, #EC4899); }
        .kv-dash-av-2 { background: linear-gradient(135deg, #34D399, #2563EB); }
        .kv-dash-av-3 { background: linear-gradient(135deg, #FBBF24, #F87171); }
        .kv-dash-av-4 { background: linear-gradient(135deg, #A78BFA, #60A5FA); }
        .kv-dash-row-service { color: #A1A1AA; font-size: 13px; }
        .kv-dash-row-time { color: #E4E4E7; font-size: 13px; font-weight: 500; }
        .kv-dash-row-status {
            padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em;
        }
        .kv-status-confirmed { background: rgba(16,185,129,.15); color: #34D399; }
        .kv-status-pending { background: rgba(251,191,36,.15); color: #FBBF24; }
        .kv-status-booked { background: rgba(37,99,235,.15); color: #93C5FD; }

        /* How */
        .kv-how { background: radial-gradient(800px 400px at 50% -100px, rgba(37,99,235,.15), transparent); }
        .kv-how-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 28px; max-width: 1000px; margin: 0 auto; }
        .kv-step { background: #111113; border: 1px solid #27272A; border-radius: 16px; padding: 32px; }
        .kv-step-num {
            width: 36px; height: 36px; border-radius: 10px; background: rgba(37,99,235,.15);
            border: 1px solid rgba(37,99,235,.3); color: #93C5FD;
            display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; margin-bottom: 20px;
        }
        .kv-step h3 { font-size: 20px; font-weight: 700; margin-bottom: 8px; letter-spacing: -0.01em; color: #FFF; }
        .kv-step p { color: #A1A1AA; font-size: 15px; line-height: 1.6; }

        /* No-show */
        .kv-noshow { background: #EFF6FF; color: #0F172A; padding: 80px 24px; }
        .kv-noshow-inner { max-width: 1000px; margin: 0 auto; display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 60px; align-items: center; }
        .kv-noshow h2 { font-size: clamp(28px,3.5vw,36px); font-weight: 800; letter-spacing: -0.02em; color: #0A0A0B; line-height: 1.2; margin-bottom: 16px; }
        .kv-noshow-sub { color: #475569; margin-bottom: 28px; font-size: 17px; }
        .kv-noshow-list { display: flex; flex-direction: column; gap: 16px; }
        .kv-noshow-item { display: flex; gap: 12px; align-items: flex-start; }
        .kv-check {
            flex-shrink: 0; width: 24px; height: 24px; border-radius: 50%;
            background: #DBEAFE; color: #2563EB; display: flex; align-items: center; justify-content: center; margin-top: 2px;
        }
        .kv-noshow-item p { color: #1E293B; font-size: 15px; line-height: 1.5; }
        .kv-noshow-item strong { color: #0A0A0B; font-weight: 600; }
        .kv-noshow-card { background: white; border: 1px solid #BFDBFE; border-radius: 16px; padding: 28px; box-shadow: 0 10px 40px rgba(37,99,235,.1); }
        .kv-noshow-card h4 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: #64748B; margin-bottom: 12px; font-weight: 700; }
        .kv-sms-demo { background: #F1F5F9; border-radius: 12px; padding: 14px; font-size: 14px; margin-bottom: 10px; border: 1px solid #E2E8F0; color: #1E293B; }
        .kv-sms-label { font-size: 11px; color: #64748B; text-transform: uppercase; font-weight: 600; letter-spacing: .05em; margin-bottom: 4px; }

        /* Comparison (vs Vagaro / Booksy) */
        .kv-vs { background: #0E0E10; }
        .kv-vs-table {
            max-width: 880px; margin: 0 auto; background: #111113; border: 1px solid #27272A;
            border-radius: 18px; overflow: hidden;
        }
        .kv-vs-row {
            display: grid; grid-template-columns: 1.4fr 1fr 1fr 1fr;
            border-bottom: 1px solid #1F2028;
        }
        .kv-vs-row:last-child { border-bottom: none; }
        .kv-vs-row.kv-vs-head { background: #161719; }
        .kv-vs-row.kv-vs-head > div { padding: 16px 18px; font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: #A1A1AA; text-align: center; }
        .kv-vs-row.kv-vs-head > div:first-child { text-align: left; color: #71717A; }
        .kv-vs-row.kv-vs-head .kv-vs-us { color: #93C5FD; }
        .kv-vs-row > div { padding: 16px 18px; font-size: 14px; color: #E4E4E7; display: flex; align-items: center; justify-content: center; }
        .kv-vs-row > div:first-child { justify-content: flex-start; color: #A1A1AA; font-weight: 500; }
        .kv-vs-yes { color: #10B981; font-weight: 700; }
        .kv-vs-no { color: #52525B; }
        .kv-vs-row.kv-vs-us-row { background: rgba(37,99,235,.06); }
        .kv-vs-foot {
            text-align: center; color: #71717A; font-size: 13px; max-width: 720px;
            margin: 20px auto 0; line-height: 1.6;
        }

        /* Pricing */
        .kv-pricing-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 24px; max-width: 900px; margin: 0 auto; }
        .kv-price-card {
            background: linear-gradient(180deg,#141416 0%,#111113 100%); border: 1px solid #27272A;
            border-radius: 20px; padding: 32px; position: relative; transition: all .3s;
            display: flex; flex-direction: column;
        }
        .kv-price-card:hover { transform: translateY(-4px); border-color: #3f3f46; box-shadow: 0 20px 40px rgba(0,0,0,.3); }
        .kv-pc-popular { border-color: rgba(37,99,235,.5) !important; box-shadow: 0 0 0 1px rgba(37,99,235,.2), 0 20px 60px rgba(37,99,235,.15); }
        .kv-pop-badge {
            position: absolute; top: -12px; right: 24px; background: #2563EB; color: white;
            font-size: 11px; font-weight: 700; padding: 5px 10px; border-radius: 999px; text-transform: uppercase; letter-spacing: .05em;
        }
        .kv-price-name { font-size: 18px; font-weight: 700; margin-bottom: 4px; color: #FFF; }
        .kv-price-desc { color: #A1A1AA; font-size: 14px; margin-bottom: 20px; }
        .kv-price-amount { font-size: 44px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; margin-bottom: 24px; color: #FFF; }
        .kv-price-amount span { font-size: 16px; font-weight: 500; color: #71717A; margin-left: 4px; }
        .kv-price-feats { list-style: none; padding: 0; margin: 0 0 28px; display: flex; flex-direction: column; gap: 12px; flex: 1; }
        .kv-price-feats li { display: flex; align-items: center; gap: 10px; font-size: 14px; color: #A1A1AA; }
        .kv-price-feats svg { width: 18px; height: 18px; color: #10B981; flex-shrink: 0; }
        .kv-price-btn {
            width: 100%; padding: 14px 0; border-radius: 12px; font-size: 16px; font-weight: 600;
            text-align: center; border: 1px solid #27272A; color: #FFF; background: rgba(255,255,255,0.06);
            cursor: pointer; transition: all .2s; text-decoration: none; display: block; font-family: inherit;
        }
        .kv-price-btn:hover { background: rgba(255,255,255,0.1); transform: translateY(-1px); }
        .kv-price-btn-blue { background: #2563EB !important; border-color: transparent !important; color: #fff !important; }
        .kv-price-btn-blue:hover { background: #1D4ED8 !important; }
        .kv-price-note {
            text-align: center; max-width: 720px; margin: 32px auto 0; color: #71717A; font-size: 13px; line-height: 1.5;
        }
        .kv-demo-box {
            margin-top: 48px; max-width: 720px; margin-left: auto; margin-right: auto;
            background: #111113; border: 1px dashed #27272A; border-radius: 16px; padding: 24px; text-align: center;
        }
        .kv-demo-box p { color: #A1A1AA; font-size: 14px; }
        .kv-demo-box strong { color: #FFF; }

        /* FAQ */
        .kv-faq-wrap { max-width: 800px; margin: 0 auto; }
        .kv-faq-item { border-bottom: 1px solid #27272A; }
        .kv-faq-q {
            width: 100%; background: none; border: none; color: #FFF; text-align: left; padding: 22px 0;
            font-size: 17px; font-weight: 600; display: flex; justify-content: space-between; align-items: center;
            cursor: pointer; font-family: inherit; transition: color .2s;
        }
        .kv-faq-q:hover { color: #E4E4E7; }
        .kv-faq-icon { width: 20px; height: 20px; color: #71717A; transition: transform .3s; flex-shrink: 0; margin-left: 16px; }
        .kv-faq-item.kv-open .kv-faq-icon { transform: rotate(45deg); color: #FFF; }
        .kv-faq-a { max-height: 0; overflow: hidden; transition: max-height .35s ease; }
        .kv-faq-a p { padding-bottom: 22px; color: #A1A1AA; font-size: 15px; line-height: 1.6; margin: 0; }
        .kv-faq-item.kv-open .kv-faq-a { max-height: 300px; }

        /* Final CTA */
        .kv-final-cta {
            padding: 80px 24px; text-align: center;
            background: radial-gradient(600px 300px at 50% 0%, rgba(37,99,235,.15), transparent);
            border-top: 1px solid #1F2028;
        }
        .kv-final-cta h2 {
            font-size: clamp(30px,4vw,46px); font-weight: 800; letter-spacing: -0.03em; line-height: 1.1;
            color: #FFF; margin-bottom: 16px; max-width: 760px; margin-left: auto; margin-right: auto;
        }
        .kv-final-cta p { color: #A1A1AA; font-size: 18px; max-width: 600px; margin: 0 auto 32px; }

        /* Footer */
        .kv-footer { border-top: 1px solid #27272A; padding: 40px 24px; background: #0A0A0B; }
        .kv-footer-inner { max-width: 1160px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
        .kv-footer-left { color: #71717A; font-size: 13px; display: flex; align-items: center; gap: 10px; }
        .kv-footer-left img { width: 26px; height: 26px; border-radius: 50%; }
        .kv-footer-right { display: flex; gap: 20px; }
        .kv-footer-right a { color: #71717A; font-size: 13px; transition: color .2s; }
        .kv-footer-right a:hover { color: #A1A1AA; }

        /* Responsive */
        @media (max-width: 980px) {
            .kv-hero-split { grid-template-columns: 1fr; gap: 44px; }
            .kv-hero-copy { text-align: center; margin: 0 auto; }
            .kv-hero-copy > p, .kv-hero-text p { margin-left: auto; margin-right: auto; }
            .kv-hero-cta { justify-content: center; }
            .kv-trust-bar { justify-content: center; }
            .kv-hero-visual { min-height: 590px; }
        }
        @media (max-width: 900px) {
            .kv-nav { display: none; }
            .kv-works-grid { grid-template-columns: repeat(3,1fr); }
            .kv-problem-grid { grid-template-columns: 1fr; }
            .kv-how-grid { grid-template-columns: 1fr; }
            .kv-noshow-inner { grid-template-columns: 1fr; gap: 40px; }
            .kv-pricing-grid { grid-template-columns: 1fr; max-width: 420px; }
            .kv-dash-body { grid-template-columns: 1fr; }
            .kv-dash-side { display: none; }
            .kv-dash-stats { grid-template-columns: repeat(2,1fr); }
            .kv-vs-row { grid-template-columns: 1.4fr 1fr 1fr; }
            .kv-vs-row > div:nth-child(4) { display: none; }
        }
        @media (max-width: 640px) {
            .kv-header-inner { height: 60px; padding: 0 16px; }
            .kv-login-link { display: none; }
            .kv-hero { min-height: 640px; padding: 96px 18px 54px; }
            .kv-hero-copy h1 { font-size: 38px; }
            .kv-hero-cta { flex-direction: column; align-items: stretch; max-width: 320px; margin: 0 auto; }
            .kv-phone-device { width: 310px; height: 560px; padding: 14px; border-radius: 46px; }
            .kv-phone-screen { border-radius: 34px; }
            .kv-phone-top { height: 102px; padding: 28px 26px; }
            .kv-phone-body { padding: 26px 20px 20px; }
            .kv-logo-orbit { width: 164px; height: 164px; }
            .kv-phone-logo { width: 110px; height: 110px; }
            .kv-phone-title { font-size: 36px; }
            .kv-mic-btn { width: 86px; height: 86px; margin-top: 20px; }
            .kv-cal-card { right: -8px; top: 82px; width: 245px; }
            .kv-sms-card { left: -8px; bottom: 92px; width: 235px; }
            .kv-works-grid { grid-template-columns: repeat(2,1fr); gap: 12px; }
            .kv-section { padding: 72px 20px; }
            .kv-footer-inner { flex-direction: column; text-align: center; }
            .kv-dash-stats { grid-template-columns: 1fr; }
            .kv-dash-row { grid-template-columns: 1fr auto; }
            .kv-dash-row-service, .kv-dash-row-time { display: none; }
        }"""

# ─── NEW HTML — US-focused ────────────────────────────────────────────────
NEW_HTML = r"""        <div id="landing-view" class="">

            <!-- HEADER -->
            <header class="kv-header">
                <div class="kv-header-inner">
                    <div class="kv-logo-wrap" onclick="logoTap()" role="button" tabindex="0" aria-label="Kaleya">
                        <img id="kv-header-logo" class="kv-logo-img" src="" alt="Kaleya">
                        <span class="kv-logo-name">Kaleya <span>AI</span></span>
                    </div>
                    <nav class="kv-nav">
                        <a href="#kv-how">How it works</a>
                        <a href="#kv-pricing">Pricing</a>
                        <a href="#kv-faq">FAQ</a>
                    </nav>
                    <div class="kv-header-right">
                        <div class="kv-lang-wrap">
                            <button id="langToggleBtn" onclick="toggleLangMenu()" aria-label="Language">
                                <span id="currentLangLabel">EN</span>
                                <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor"><path d="M2 3.5l3 3 3-3"/></svg>
                            </button>
                            <div id="langDropdown" class="absolute right-0 top-10 z-50 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl shadow-xl p-2 min-w-[150px]" style="display:none">
                                <button onclick="setLang('en')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">English</button>
                                <button onclick="setLang('sr')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Srpski</button>
                                <button onclick="setLang('es')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Español</button>
                                <button onclick="setLang('pt')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Português</button>
                                <button onclick="setLang('ru')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Русский</button>
                                <button onclick="setLang('fr')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Français</button>
                                <button onclick="setLang('it')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Italiano</button>
                                <button onclick="setLang('de')" class="lang-btn w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-50 dark:hover:bg-slate-800">Deutsch</button>
                            </div>
                        </div>
                        <button id="theme-toggle" aria-label="Toggle theme">
                            <svg class="sun w-4 h-4 dark:hidden" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                            <svg class="moon w-4 h-4 hidden dark:block" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
                        </button>
                        <button onclick="showView('login')" class="kv-login-link">Login</button>
                        <a href="#kv-pricing" class="kv-btn kv-btn-primary">Start Free 14-Day Trial</a>
                    </div>
                </div>
            </header>

            <main>
                <!-- HERO -->
                <section class="kv-hero">
                    <div class="kv-slides">
                        <div class="kv-slide kv-active" style="background-image:url('https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=1920&q=80&auto=format')"></div>
                        <div class="kv-slide" style="background-image:url('https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=1920&q=80&auto=format')"></div>
                        <div class="kv-slide" style="background-image:url('https://images.unsplash.com/photo-1604654894610-df63bc536371?w=1920&q=80&auto=format')"></div>
                        <div class="kv-slide" style="background-image:url('https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=1920&q=80&auto=format')"></div>
                        <div class="kv-slide" style="background-image:url('https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=1920&q=80&auto=format')"></div>
                    </div>
                    <div class="kv-hero-glow kv-glow-l"></div>
                    <div class="kv-hero-glow kv-glow-r"></div>

                    <div class="kv-hero-split">
                        <div class="kv-hero-copy">
                            <div class="kv-badge">
                                <span class="kv-dot"></span>
                                <span>LIVE · Answering calls right now</span>
                            </div>
                            <div class="kv-hero-text" id="kv-hero-text-wrap">
                                <h1 id="kv-hero-title">AI Receptionist for Busy Salons — Stop No-Shows, Fill Your Books</h1>
                                <p id="kv-hero-subtitle">Kaleya answers at 9PM, books the fade, and texts the confirmation. You wake up to a full chair.</p>
                            </div>
                            <div class="kv-hero-cta">
                                <a href="#kv-pricing" class="kv-btn kv-btn-primary kv-btn-large">Start Free 14-Day Trial</a>
                                <button class="kv-btn kv-btn-secondary kv-btn-large" onclick="goDemo('client')">Try Live Demo</button>
                            </div>
                            <div class="kv-trust-bar">
                                <span class="kv-trust-stars">★★★★★</span>
                                <span><strong>Built for US salons</strong> · Google Calendar + Square ready · Cancel anytime</span>
                            </div>
                        </div>

                        <div class="kv-hero-visual" aria-label="Kaleya AI phone preview">
                            <div class="kv-phone-device">
                                <div class="kv-phone-screen">
                                    <div class="kv-phone-top">
                                        <div class="kv-phone-status">
                                            <span class="kv-phone-online"></span>
                                            <span>Kaleya online</span>
                                        </div>
                                        <span style="font-size:13px;opacity:.75">24/7</span>
                                    </div>
                                    <div class="kv-phone-body">
                                        <div class="kv-logo-orbit" onclick="logoTap()">
                                            <img class="kv-phone-logo" src="" alt="Kaleya">
                                        </div>
                                        <div class="kv-phone-kicker">Incoming call</div>
                                        <div class="kv-phone-title">Kaleya AI</div>
                                        <div class="kv-phone-subtitle">for Mike's Barbershop</div>
                                        <button class="kv-mic-btn" onclick="event.stopPropagation();goDemo('client')">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                                                <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"/>
                                                <path d="M19 10v1a7 7 0 0 1-14 0v-1"/>
                                                <path d="M12 18v3"/>
                                                <path d="M8 21h8"/>
                                            </svg>
                                        </button>
                                        <div class="kv-voice-bars"><span></span><span></span><span></span><span></span><span></span></div>
                                        <div class="kv-call-bubble">
                                            <div class="kv-bubble-label">Kaleya introduces itself</div>
                                            <p>"Thanks for calling Mike's! I can book you for a fade tomorrow at 3pm with Carlos. Does that work?"</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="kv-floating-card kv-cal-card">
                                <div class="kv-card-icon">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
                                </div>
                                <div>
                                    <strong>Google Calendar</strong>
                                    <p>Fade · Tomorrow 3:00 PM · Carlos</p>
                                    <span class="kv-fc-tag">Booked by Kaleya</span>
                                </div>
                            </div>

                            <div class="kv-floating-card kv-sms-card">
                                <div class="kv-card-icon kv-card-icon-dark">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v12H7l-3 3V4Z"/></svg>
                                </div>
                                <div>
                                    <strong>SMS Sent</strong>
                                    <p>"Your cut is confirmed for tomorrow at 3pm. Reply YES to confirm."</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- WORKS -->
                <section class="kv-works">
                    <div class="kv-container">
                        <div class="kv-section-head" style="margin-bottom:24px">
                            <p class="kv-eyebrow">Purpose-built</p>
                            <h2 class="kv-section-title" style="font-size:24px">Works for every appointment business</h2>
                        </div>
                        <div class="kv-works-grid">
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" fill="none"><circle cx="6" cy="7" r="2.4"/><circle cx="6" cy="17" r="2.4"/><path d="M8.1 8.2 20 19.5"/><path d="M8.1 15.8 20 4.5"/><path d="M13.5 12h4.2"/></svg></div>
                                <span>Barbershops</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" fill="none"><path d="M4 18.5c3.8-2 3.2-6.7 6.8-9.8 2.7-2.4 6.4-2.1 9.2.2"/><path d="M5.5 21c5.2-1.4 5.3-5.6 8.1-8.2 1.8-1.7 4.3-2.2 6.9-1.1"/><path d="M8.2 6.2c2.6-2 6.8-2.5 10.3.2"/><path d="M16 5.2c.8 1.9.6 3.7-.4 5.3"/></svg></div>
                                <span>Hair Salons</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" fill="none"><path d="M9 3h6v4H9z"/><path d="M10 7h4l1.2 4.4c.2.8.8 1.5 1.5 1.9l1.1.7c.8.5 1.2 1.3 1.2 2.2V21H5v-4.8c0-.9.4-1.7 1.2-2.2l1.1-.7c.7-.4 1.3-1.1 1.5-1.9L10 7z"/><path d="M8 17h8"/><path d="M12 13.5v4.8"/></svg></div>
                                <span>Nail Studios</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" fill="none"><path d="M12 20c4-2.2 6-5.3 6-9.4 0-2.2-.7-4.1-2-5.6-2.2 1.1-3.5 2.8-4 5-.5-2.2-1.8-3.9-4-5-1.3 1.5-2 3.4-2 5.6 0 4.1 2 7.2 6 9.4z"/><path d="M4 12.5c1.9.1 3.7.9 5.2 2.4"/><path d="M20 12.5c-1.9.1-3.7.9-5.2 2.4"/><path d="M12 10v10"/></svg></div>
                                <span>Massage & Spa</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" fill="none"><path d="M15.5 4.5 20 9l-8.5 8.5L7 13z"/><path d="M6.8 13.2 4.7 15.3c-.9.9-.9 2.4 0 3.3l.7.7c.9.9 2.4.9 3.3 0l2.1-2.1"/><path d="M14.2 5.8 18.2 9.8"/><path d="M4.2 20.8 3 22"/></svg></div>
                                <span>Makeup Artists</span>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- PROBLEM -->
                <section class="kv-section">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">The math hurts</p>
                            <h2 class="kv-section-title">Your phone is leaking money</h2>
                        </div>
                        <div class="kv-problem-grid">
                            <div class="kv-problem-card">
                                <div class="kv-problem-num">60%</div>
                                <p class="kv-problem-desc"><strong>of calls go to voicemail after 5PM</strong> — That's $50-$150 per missed call.</p>
                            </div>
                            <div class="kv-problem-card">
                                <div class="kv-problem-num">$75</div>
                                <p class="kv-problem-desc"><strong>average no-show cost</strong> — 8 no-shows = $600 burned monthly.</p>
                            </div>
                            <div class="kv-problem-card">
                                <div class="kv-problem-num">6 hrs</div>
                                <p class="kv-problem-desc"><strong>staff spends on phones / week</strong> — "What times you got?" 22× a day.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- DASHBOARD MOCKUP -->
                <section class="kv-section kv-dash">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">Your dashboard</p>
                            <h2 class="kv-section-title">Run your salon from your phone</h2>
                            <p class="kv-section-sub">See every booking, every cancellation, every dollar in one place.</p>
                        </div>
                        <div class="kv-dash-mock">
                            <div class="kv-dash-topbar">
                                <div class="kv-dash-dots"><span></span><span></span><span></span></div>
                                <div class="kv-dash-url">app.aikaleya.com / dashboard</div>
                                <div style="width:48px"></div>
                            </div>
                            <div class="kv-dash-body">
                                <aside class="kv-dash-side">
                                    <div class="kv-dash-side-logo">
                                        <img id="kv-dash-logo" src="" alt="Kaleya">
                                        <span>Kaleya</span>
                                    </div>
                                    <div class="kv-dash-side-section">Main</div>
                                    <ul>
                                        <li class="kv-active">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
                                            Calendar
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                                            Clients
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3h18v4H3z"/><path d="M5 7v12h14V7"/></svg>
                                            Services
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
                                            Call log
                                        </li>
                                    </ul>
                                    <div class="kv-dash-side-section">Settings</div>
                                    <ul>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4"/></svg>
                                            Preferences
                                        </li>
                                        <li>
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                                            Messages
                                        </li>
                                    </ul>
                                </aside>
                                <div class="kv-dash-main">
                                    <div class="kv-dash-h">
                                        <h3>Today · Tuesday, May 19</h3>
                                        <div class="kv-dash-h-actions">
                                            <span class="kv-dash-pill">Filter</span>
                                            <span class="kv-dash-pill kv-dash-pill-blue">+ Block time</span>
                                        </div>
                                    </div>
                                    <div class="kv-dash-stats">
                                        <div class="kv-dash-stat">
                                            <div class="kv-dash-stat-label">Today's bookings</div>
                                            <div class="kv-dash-stat-val">14 <span class="kv-up">↑ 22%</span></div>
                                        </div>
                                        <div class="kv-dash-stat">
                                            <div class="kv-dash-stat-label">Calls answered</div>
                                            <div class="kv-dash-stat-val">37 <span class="kv-up">↑ 100%</span></div>
                                        </div>
                                        <div class="kv-dash-stat">
                                            <div class="kv-dash-stat-label">Revenue today</div>
                                            <div class="kv-dash-stat-val">$1,290</div>
                                        </div>
                                        <div class="kv-dash-stat">
                                            <div class="kv-dash-stat-label">No-shows saved</div>
                                            <div class="kv-dash-stat-val">3 <span class="kv-up">$225</span></div>
                                        </div>
                                    </div>
                                    <div class="kv-dash-list">
                                        <div class="kv-dash-row">
                                            <div class="kv-dash-row-name">
                                                <div class="kv-dash-avatar kv-dash-av-1">MJ</div>
                                                Maya Johnson
                                            </div>
                                            <div class="kv-dash-row-service">Gel Manicure</div>
                                            <div class="kv-dash-row-time">3:00 PM · Lena</div>
                                            <div class="kv-dash-row-status kv-status-confirmed">Confirmed</div>
                                        </div>
                                        <div class="kv-dash-row">
                                            <div class="kv-dash-row-name">
                                                <div class="kv-dash-avatar kv-dash-av-2">DR</div>
                                                David Rodriguez
                                            </div>
                                            <div class="kv-dash-row-service">Fade + Beard</div>
                                            <div class="kv-dash-row-time">3:30 PM · Carlos</div>
                                            <div class="kv-dash-row-status kv-status-booked">Booked by AI</div>
                                        </div>
                                        <div class="kv-dash-row">
                                            <div class="kv-dash-row-name">
                                                <div class="kv-dash-avatar kv-dash-av-3">SL</div>
                                                Sarah Lee
                                            </div>
                                            <div class="kv-dash-row-service">Balayage · 3h</div>
                                            <div class="kv-dash-row-time">4:00 PM · Anna</div>
                                            <div class="kv-dash-row-status kv-status-pending">Pending card</div>
                                        </div>
                                        <div class="kv-dash-row">
                                            <div class="kv-dash-row-name">
                                                <div class="kv-dash-avatar kv-dash-av-4">JM</div>
                                                James Miller
                                            </div>
                                            <div class="kv-dash-row-service">60-min Deep Tissue</div>
                                            <div class="kv-dash-row-time">5:30 PM · Sofia</div>
                                            <div class="kv-dash-row-status kv-status-confirmed">Confirmed</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- HOW -->
                <section id="kv-how" class="kv-section kv-how">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">How it works</p>
                            <h2 class="kv-section-title">Live in 3 minutes. No new number needed.</h2>
                            <p class="kv-section-sub">Forward your existing business line. US numbers only.</p>
                        </div>
                        <div class="kv-how-grid">
                            <div class="kv-step">
                                <div class="kv-step-num">1</div>
                                <h3>Forward your number (*72)</h3>
                                <p>Dial *72 from your shop phone. Takes 10 seconds. We give you the forwarding number instantly.</p>
                            </div>
                            <div class="kv-step">
                                <div class="kv-step-num">2</div>
                                <h3>Kaleya learns your menu in 90s</h3>
                                <p>Tell her your services, prices, and hours. She understands "fade, balayage, gel mani, 60-min deep tissue".</p>
                            </div>
                            <div class="kv-step">
                                <div class="kv-step-num">3</div>
                                <h3>Books to Google Calendar + Square</h3>
                                <p>Real-time availability, automatic SMS confirmations, and deposits for high-value slots. No double-books.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- NO-SHOW -->
                <section class="kv-noshow">
                    <div class="kv-noshow-inner">
                        <div>
                            <h2>Stop No-Shows For Good — This is standard in the US</h2>
                            <p class="kv-noshow-sub">US clients expect to leave a card. Kaleya makes it frictionless and compliant.</p>
                            <div class="kv-noshow-list">
                                <div class="kv-noshow-item">
                                    <div class="kv-check"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg></div>
                                    <p><strong>Card vault via Lemon Squeezy</strong> — PCI-compliant, not stored on our servers. No charge today.</p>
                                </div>
                                <div class="kv-noshow-item">
                                    <div class="kv-check"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg></div>
                                    <p><strong>If they don't show, charge fee in 1 click</strong> ($25/$50) — you set the policy, we enforce it.</p>
                                </div>
                                <div class="kv-noshow-item">
                                    <div class="kv-check"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6 9 17l-5-5"/></svg></div>
                                    <p><strong>SMS reminders 24h + 2h before</strong> — no-shows drop 73% on average.</p>
                                </div>
                            </div>
                        </div>
                        <div class="kv-noshow-card">
                            <h4>Example SMS flow</h4>
                            <div class="kv-sms-demo">
                                <div class="kv-sms-label">Kaleya · 24h before</div>
                                Hi Maya, reminder: Gel Manicure tomorrow Tue at 3:00 PM with Lena at Glow Nails. Reply <strong>C</strong> to confirm or <strong>R</strong> to reschedule.
                            </div>
                            <div class="kv-sms-demo" style="background:#DBEAFE;border-color:#BFDBFE">
                                <div class="kv-sms-label" style="color:#1D4ED8">Client</div>
                                <strong style="color:#1E40AF">C</strong>
                            </div>
                            <div class="kv-sms-demo" style="background:#D1FAE5;border-color:#A7F3D0">
                                <div class="kv-sms-label" style="color:#065F46">Kaleya · 2h before</div>
                                See you at 3 PM! Card on file for no-show ($25). Street parking in back.
                            </div>
                        </div>
                    </div>
                </section>

                <!-- COMPARISON -->
                <section class="kv-section kv-vs">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">Why salons switch</p>
                            <h2 class="kv-section-title">Better than Vagaro and Booksy at half the price</h2>
                            <p class="kv-section-sub">Booking apps don't answer the phone. Kaleya does.</p>
                        </div>
                        <div class="kv-vs-table">
                            <div class="kv-vs-row kv-vs-head">
                                <div>Feature</div>
                                <div class="kv-vs-us">Kaleya</div>
                                <div>Vagaro</div>
                                <div>Booksy</div>
                            </div>
                            <div class="kv-vs-row kv-vs-us-row">
                                <div>Answers your phone 24/7 in human voice</div>
                                <div class="kv-vs-yes">✓</div>
                                <div class="kv-vs-no">—</div>
                                <div class="kv-vs-no">—</div>
                            </div>
                            <div class="kv-vs-row kv-vs-us-row">
                                <div>Books appointments during the call</div>
                                <div class="kv-vs-yes">✓</div>
                                <div class="kv-vs-no">—</div>
                                <div class="kv-vs-no">—</div>
                            </div>
                            <div class="kv-vs-row">
                                <div>SMS reminders + no-show fees</div>
                                <div class="kv-vs-yes">✓</div>
                                <div class="kv-vs-yes">✓</div>
                                <div class="kv-vs-yes">✓</div>
                            </div>
                            <div class="kv-vs-row">
                                <div>Syncs with Google Calendar + Square</div>
                                <div class="kv-vs-yes">✓</div>
                                <div class="kv-vs-no">Partial</div>
                                <div class="kv-vs-no">Partial</div>
                            </div>
                            <div class="kv-vs-row kv-vs-us-row">
                                <div>Works with your existing phone number</div>
                                <div class="kv-vs-yes">✓</div>
                                <div class="kv-vs-no">—</div>
                                <div class="kv-vs-no">—</div>
                            </div>
                            <div class="kv-vs-row">
                                <div>Monthly price (starting)</div>
                                <div class="kv-vs-yes">$29</div>
                                <div>$30 + per-staff</div>
                                <div>$30 + per-staff</div>
                            </div>
                        </div>
                        <p class="kv-vs-foot">Use Kaleya alongside Vagaro/Booksy — it just plugs in. Or replace them entirely.</p>
                    </div>
                </section>

                <!-- PRICING -->
                <section id="kv-pricing" class="kv-section">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">Simple pricing</p>
                            <h2 class="kv-section-title">Start free. Cancel anytime.</h2>
                            <p class="kv-section-sub">Built for US shops. Billed in USD. 14-day free trial, no credit card.</p>
                        </div>
                        <div class="kv-pricing-grid">
                            <div class="kv-price-card">
                                <div class="kv-price-name">Starter</div>
                                <p class="kv-price-desc">Perfect for solo artists</p>
                                <div class="kv-price-amount">$29<span>/mo</span></div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>300 talk minutes included</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>After-hours only (5PM – 9AM)</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>Google Calendar sync</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>SMS confirmations</li>
                                </ul>
                                <a href="register-basic.html" class="kv-price-btn">Start Free 14-Day Trial</a>
                            </div>
                            <div class="kv-price-card kv-pc-popular">
                                <div class="kv-pop-badge">Most Popular</div>
                                <div class="kv-price-name">Pro</div>
                                <p class="kv-price-desc">For busy shops & teams</p>
                                <div class="kv-price-amount">$79<span>/mo</span></div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>1,200 minutes included</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>24/7 answering</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>Square + Google Calendar</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>No-show card vault via Lemon Squeezy</li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6 9 17l-5-5"/></svg>Priority support 9AM – 6PM ET</li>
                                </ul>
                                <a href="register-pro.html" class="kv-price-btn kv-price-btn-blue">Start Free 14-Day Trial</a>
                            </div>
                        </div>
                        <p class="kv-price-note">Payments processed by Lemon Squeezy (Merchant of Record handles US sales tax). Stripe support after our Delaware LLC is finalized — current subscriptions migrate automatically.</p>
                        <div class="kv-demo-box">
                            <p><strong>Free 2-min demo calls.</strong> We limit to 2 minutes so everyone can try. Costs us ~$0.02 per call. Saves you $1,200/month. Fair trade.</p>
                        </div>
                    </div>
                </section>

                <!-- FAQ -->
                <section id="kv-faq" class="kv-section">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">FAQ</p>
                            <h2 class="kv-section-title">Built for the US, from the EU</h2>
                        </div>
                        <div class="kv-faq-wrap">
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    You're based in Serbia — why Lemon Squeezy?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Lemon Squeezy is our Merchant of Record. They handle US sales tax, compliance, and payouts. It works today with no LLC needed, which lets us serve US shops immediately while our Delaware entity is being set up.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    Will you add Stripe later?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Yes. After our Delaware LLC is formed, we'll add Stripe for direct US processing. Current Lemon Squeezy subscriptions migrate automatically — nothing changes for you.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    Is charging no-show fees legal in the US?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Yes — it's standard practice across the US service industry. You must clearly disclose the policy at booking (Kaleya does this automatically). All major platforms like Vagaro, Square, and Booksy support it.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    What integrations are live today?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Live today: Google Calendar and Square Appointments. Coming next: Vagaro and Booksy (Q1 2026). We sync real-time availability to prevent double bookings.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    Support hours for US time zones?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Email support 24/7 with under 4-hour response. Phone support 9AM – 6PM ET for Pro customers. We're 6 hours ahead in Serbia, so we cover US mornings perfectly.</p></div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- FINAL CTA -->
                <section class="kv-final-cta">
                    <h2>Stop losing $1,200/month to missed calls and no-shows</h2>
                    <p>Set up takes 3 minutes. Cancel anytime in 1 click.</p>
                    <div class="kv-hero-cta" style="justify-content:center">
                        <a href="#kv-pricing" class="kv-btn kv-btn-primary kv-btn-large">Start Free 14-Day Trial</a>
                        <button class="kv-btn kv-btn-secondary kv-btn-large" onclick="goDemo('client')">Try Live Demo</button>
                    </div>
                </section>
            </main>

            <footer class="kv-footer">
                <div class="kv-footer-inner">
                    <div class="kv-footer-left">
                        <img id="kv-footer-logo" src="" alt="Kaleya">
                        <span><strong>Kaleya</strong> AI</span>
                        <span>© 2026 Kaleya AI · Made for US salons · Operated from EU</span>
                    </div>
                    <div class="kv-footer-right">
                        <a href="privacy.html">Privacy</a>
                        <a href="terms.html">Terms</a>
                        <a href="mailto:hello@aikaleya.com">hello@aikaleya.com</a>
                    </div>
                </div>
            </footer>

            <!-- Kaleya Landing Scripts -->
            <script>
            (function(){
                // Inject logo from preload
                var ref = document.getElementById('logo-preload');
                if(ref && ref.src){
                    ['kv-header-logo','kv-footer-logo','kv-dash-logo'].forEach(function(id){
                        var el = document.getElementById(id);
                        if(el) el.src = ref.src;
                    });
                    document.querySelectorAll('.kv-phone-logo').forEach(function(img){ img.src = ref.src; });
                }

                // Hero rotating titles + slideshow
                var slides = document.querySelectorAll('#landing-view .kv-slide');
                var slidesData = [
                    { title: "AI Receptionist for Busy Salons — Stop No-Shows, Fill Your Books", text: "Kaleya answers at 9PM, books the fade, and texts the confirmation. You wake up to a full chair." },
                    { title: "Hair salons miss 34% of calls during color jobs", text: "Kaleya books while you're foiling. No voicemail, no lost $85 appointments." },
                    { title: "Nail studios waste 8 hours/week on phone tag", text: "Kaleya texts back in 2 seconds with real openings. Fill gaps automatically." },
                    { title: "Massage & spas lose $600/mo to no-shows", text: "Kaleya saves cards at booking. Charge no-show fees in one click." },
                    { title: "Makeup artists lose $250 bridal trials while with clients", text: "Kaleya captures every inquiry. Even on a wedding day." }
                ];
                var titleEl = document.getElementById('kv-hero-title');
                var textEl = document.getElementById('kv-hero-subtitle');
                var wrapEl = document.getElementById('kv-hero-text-wrap');
                var current = 0;
                if(slides.length > 1){
                    setInterval(function(){
                        slides[current].classList.remove('kv-active');
                        current = (current + 1) % slides.length;
                        slides[current].classList.add('kv-active');
                        if(titleEl && textEl && wrapEl){
                            wrapEl.style.opacity = '0';
                            setTimeout(function(){
                                titleEl.textContent = slidesData[current].title;
                                textEl.textContent = slidesData[current].text;
                                wrapEl.style.opacity = '1';
                            }, 300);
                        }
                    }, 6000);
                }

                // FAQ accordion
                document.querySelectorAll('#landing-view .kv-faq-q').forEach(function(btn){
                    btn.addEventListener('click', function(){
                        var item = btn.closest('.kv-faq-item');
                        var isOpen = item.classList.contains('kv-open');
                        document.querySelectorAll('#landing-view .kv-faq-item').forEach(function(i){ i.classList.remove('kv-open'); });
                        if(!isOpen) item.classList.add('kv-open');
                    });
                });
            })();
            </script>
        </div>"""

# ─── Apply CSS patch ─────────────────────────────────────────────────────
css_pattern = re.compile(
    r'/\* ===== KALEYA LANDING DARK v2 [\s\S]*?\.kv-footer-inner \{ flex-direction: column; text-align: center; \}\s*\}',
    re.DOTALL
)
if css_pattern.search(content):
    content = css_pattern.sub(NEW_CSS, content, count=1)
    print("CSS replaced (v2 -> v3)")
else:
    print("CSS pattern NOT found")
    sys.exit(1)

# ─── Apply HTML patch ────────────────────────────────────────────────────
html_pattern = re.compile(
    r'<div id="landing-view" class="">[\s\S]*?</div>(?=\s*\n\s*<!-- LOGIN VIEW -->)',
    re.DOTALL
)
if html_pattern.search(content):
    content = html_pattern.sub(NEW_HTML, content, count=1)
    print("Landing HTML replaced")
else:
    print("HTML pattern NOT found")
    sys.exit(1)

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("File written. Done!")
