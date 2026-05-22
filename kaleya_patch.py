#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch: replace bad CSS + landing HTML in index.html"""
import re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

FILE = r'C:\Users\taxi0\Documents\Claude\Projects\KALEYA PROJEKAT\frontend\index.html'

# ─── 1. Read file ──────────────────────────────────────────────────────────────
with open(FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# ─── 2. NEW CSS (kv- prefix) ──────────────────────────────────────────────────
NEW_CSS = r"""        /* ===== KALEYA LANDING DARK v2 — kv- prefix, no Tailwind conflicts ===== */
        #landing-view {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #0A0A0B;
            color: #FFFFFF;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }
        #landing-view *, #landing-view *::before, #landing-view *::after { box-sizing: border-box; }
        #landing-view a { color: inherit; text-decoration: none; }
        #landing-view img { max-width: 100%; display: block; }

        /* Header */
        .kv-header {
            position: sticky; top: 0; z-index: 100;
            backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
            background: rgba(10,10,11,0.75); border-bottom: 1px solid #27272A;
        }
        .kv-header-inner {
            max-width: 1200px; margin: 0 auto; height: 68px; padding: 0 24px;
            display: flex; align-items: center; justify-content: space-between; gap: 24px;
        }
        .kv-logo-wrap { display: flex; align-items: center; gap: 10px; cursor: pointer; user-select: none; }
        .kv-logo-img { width: 36px; height: 36px; border-radius: 50%; object-fit: cover; }
        .kv-logo-name { font-weight: 800; font-size: 20px; letter-spacing: -0.02em; color: #FFF; }
        .kv-nav { display: flex; gap: 32px; }
        .kv-nav a { color: #A1A1AA; font-size: 14px; font-weight: 500; transition: color .2s; text-decoration: none; }
        .kv-nav a:hover { color: #FFF; }
        .kv-header-right { display: flex; align-items: center; gap: 12px; }
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
        #landing-view #theme-toggle {
            width: 36px; height: 36px; border-radius: 50%;
            background: #111113 !important; border: 1px solid #27272A !important; color: #FFF !important;
            display: grid; place-items: center; cursor: pointer; transition: background .2s;
        }
        #landing-view #theme-toggle:hover { background: #18181B !important; }
        .kv-login-btn {
            background: #2563EB; color: #fff; border: none; border-radius: 10px;
            padding: 9px 18px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all .2s;
            white-space: nowrap;
        }
        .kv-login-btn:hover { background: #1D4ED8; transform: translateY(-1px); }

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
        .kv-hero-copy h1 {
            font-size: clamp(42px,5.6vw,72px); font-weight: 800; line-height: .96;
            letter-spacing: -0.055em; margin-bottom: 22px; color: #FFF;
        }
        .kv-hero-copy > p {
            font-size: clamp(17px,2vw,21px); color: #A1A1AA; max-width: 520px; margin: 0 0 34px;
        }
        .kv-hero-cta { display: flex; gap: 12px; flex-wrap: wrap; }
        .kv-btn {
            display: inline-flex; align-items: center; justify-content: center; gap: 8px;
            border-radius: 12px; font-weight: 600; font-size: 16px; padding: 14px 24px;
            transition: all .2s; border: 1px solid transparent; cursor: pointer; white-space: nowrap;
            text-decoration: none; font-family: inherit;
        }
        .kv-btn-primary { background: #2563EB; color: #fff; }
        .kv-btn-primary:hover { background: #1D4ED8; transform: translateY(-1px); }
        .kv-btn-secondary { background: rgba(255,255,255,.06); border-color: #27272A; color: #FFF; }
        .kv-btn-secondary:hover { background: rgba(255,255,255,.1); }

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
            display: flex; flex-direction: column; align-items: center; cursor: pointer;
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
        .kv-floating-card strong { display: block; font-size: 17px; line-height: 1.2; margin-bottom: 6px; }
        .kv-floating-card p { margin: 0; color: #64748B; font-size: 13px; line-height: 1.45; }
        .kv-fc-tag {
            display: inline-flex; margin-top: 10px; padding: 5px 10px; border-radius: 999px;
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
        .kv-section { padding: 100px 24px; }
        .kv-container { max-width: 1160px; margin: 0 auto; }
        .kv-section-head { text-align: center; margin-bottom: 56px; }
        .kv-eyebrow { font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: #71717A; margin-bottom: 12px; }
        .kv-section-title { font-size: clamp(28px,4vw,40px); font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; color: #FFF; }
        .kv-section-sub { color: #A1A1AA; margin-top: 12px; font-size: 18px; }

        /* Works */
        .kv-works {
            padding: 60px 24px 40px;
            background: linear-gradient(180deg, #0A0A0B 0%, rgba(105,0,204,.1) 100%);
            border-top: 1px solid rgba(39,39,42,.5);
        }
        .kv-works-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 16px; max-width: 1000px; margin: 40px auto 0; }
        .kv-work-item {
            background: #111113; border: 1px solid #27272A; border-radius: 12px;
            padding: 24px 16px; text-align: center; transition: all .2s;
        }
        .kv-work-item:hover { transform: translateY(-2px); border-color: #3f3f46; }
        .kv-work-icon { width: 28px; height: 28px; margin: 0 auto 12px; color: #A1A1AA; }
        .kv-work-icon svg { width: 100%; height: 100%; stroke-width: 1.5; }
        .kv-work-item span { font-weight: 600; font-size: 14px; color: #FFF; }

        /* Features */
        .kv-features { background: #0E0E10; }
        .kv-features-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; }
        .kv-feat-card {
            background: #111113; border: 1px solid #27272A; border-radius: 16px; padding: 32px; transition: all .2s;
        }
        .kv-feat-card:hover { border-color: #2563EB; transform: translateY(-2px); }
        .kv-feat-icon {
            width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; margin-bottom: 16px;
        }
        .kv-feat-card h3 { font-size: 18px; font-weight: 700; margin-bottom: 8px; color: #FFF; }
        .kv-feat-card p { color: #A1A1AA; font-size: 15px; line-height: 1.6; }

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
        .kv-chat-demo { margin-top: 24px; display: flex; flex-direction: column; gap: 8px; }
        .kv-chat-c {
            background: rgba(255,255,255,.07); border-radius: 12px; padding: 12px 16px; font-size: 14px; color: #A1A1AA;
        }
        .kv-chat-k {
            background: linear-gradient(135deg,rgba(20,184,166,.25),rgba(37,99,235,.25)); border-radius: 12px; padding: 12px 16px; font-size: 14px; color: #FFF; border: 1px solid rgba(37,99,235,.2);
        }

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

        /* Pricing */
        .kv-pricing-grid { display: grid; grid-template-columns: repeat(5,1fr); gap: 16px; }
        .kv-price-card {
            background: linear-gradient(180deg,#141416 0%,#111113 100%); border: 1px solid #27272A;
            border-radius: 20px; padding: 26px; position: relative; transition: all .3s;
            display: flex; flex-direction: column;
        }
        .kv-price-card:hover { transform: translateY(-4px); border-color: #3f3f46; box-shadow: 0 20px 40px rgba(0,0,0,.3); }
        .kv-pc-popular { border-color: rgba(37,99,235,.5) !important; box-shadow: 0 0 0 1px rgba(37,99,235,.2), 0 20px 60px rgba(37,99,235,.15); }
        .kv-pop-badge {
            position: absolute; top: -12px; right: 18px; background: #2563EB; color: white;
            font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 999px; text-transform: uppercase; letter-spacing: .05em;
        }
        .kv-price-card-dark { background: #050507 !important; }
        .kv-price-name { font-size: 17px; font-weight: 700; margin-bottom: 4px; color: #FFF; }
        .kv-price-desc { color: #A1A1AA; font-size: 13px; margin-bottom: 16px; }
        .kv-price-amount { font-size: 38px; font-weight: 800; letter-spacing: -0.03em; line-height: 1; margin-bottom: 18px; color: #FFF; }
        .kv-price-amount span { font-size: 14px; font-weight: 500; color: #71717A; margin-left: 3px; }
        .kv-price-feats { list-style: none; padding: 0; margin: 0 0 22px; display: flex; flex-direction: column; gap: 9px; flex: 1; }
        .kv-price-feats li { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: #A1A1AA; }
        .kv-price-feats svg { width: 15px; height: 15px; color: #10B981; flex-shrink: 0; margin-top: 2px; }
        .kv-price-btn {
            width: 100%; padding: 10px 0; border-radius: 10px; font-size: 14px; font-weight: 600;
            text-align: center; border: 1px solid #3F3F46; color: #FFF; background: transparent;
            cursor: pointer; transition: all .2s; text-decoration: none; display: block; font-family: inherit;
        }
        .kv-price-btn:hover { background: #18181B; }
        .kv-price-btn-blue { background: #2563EB !important; border-color: transparent !important; color: #fff !important; }
        .kv-price-btn-blue:hover { background: #1D4ED8 !important; }
        .kv-price-btn-white { background: #FFF !important; border-color: transparent !important; color: #0A0A0B !important; }
        .kv-price-btn-white:hover { background: #F1F5F9 !important; }

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
            .kv-hero-copy > p { margin-left: auto; margin-right: auto; }
            .kv-hero-cta { justify-content: center; }
            .kv-hero-visual { min-height: 590px; }
        }
        @media (max-width: 900px) {
            .kv-nav { display: none; }
            .kv-works-grid { grid-template-columns: repeat(3,1fr); }
            .kv-features-grid { grid-template-columns: 1fr; }
            .kv-how-grid { grid-template-columns: 1fr; }
            .kv-noshow-inner { grid-template-columns: 1fr; gap: 40px; }
            .kv-pricing-grid { grid-template-columns: repeat(2,1fr); }
        }
        @media (max-width: 640px) {
            .kv-header-inner { height: 60px; padding: 0 16px; }
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
            .kv-pricing-grid { grid-template-columns: 1fr; max-width: 420px; margin-left: auto; margin-right: auto; }
            .kv-section { padding: 72px 20px; }
            .kv-footer-inner { flex-direction: column; text-align: center; }
        }"""

# ─── 3. NEW HTML for #landing-view ────────────────────────────────────────────
NEW_HTML = r"""        <div id="landing-view" class="">

            <!-- ══ HEADER ══════════════════════════════════════════════ -->
            <header class="kv-header">
                <div class="kv-header-inner">
                    <div class="kv-logo-wrap" onclick="logoTap()" role="button" tabindex="0" aria-label="Kaleya">
                        <img id="kv-header-logo" class="kv-logo-img" src="" alt="Kaleya">
                        <span class="kv-logo-name">Kaleya <span style="font-weight:600;color:#A1A1AA">AI</span></span>
                    </div>
                    <nav class="kv-nav">
                        <a href="#kv-features" data-i18n="nav_features">Features</a>
                        <a href="#kv-how" data-i18n="nav_how">How it works</a>
                        <a href="#kv-pricing" data-i18n="nav_pricing">Pricing</a>
                    </nav>
                    <div class="kv-header-right">
                        <div class="kv-lang-wrap">
                            <button id="langToggleBtn" onclick="toggleLangMenu()" aria-label="Language" class="flex items-center gap-1">
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
                        <button onclick="showView('login')" class="kv-login-btn" data-i18n="nav_login">Login</button>
                    </div>
                </div>
            </header>

            <main>
                <!-- ══ HERO ════════════════════════════════════════════ -->
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
                        <!-- Left: copy -->
                        <div class="kv-hero-copy">
                            <div class="kv-badge">
                                <span class="kv-dot"></span>
                                <span data-i18n="hero_badge">AI receptionist · active 24/7</span>
                            </div>
                            <h1>
                                <span data-i18n="hero_title_1">Kaleya</span><br>
                                <span data-i18n="hero_title_2">AI receptionist 24/7</span>
                            </h1>
                            <p data-i18n="hero_sub">Kaleya answers, schedules, cancels and alerts staff with a natural voice. Works through calls, WhatsApp, Viber, Telegram and SMS.</p>
                            <div class="kv-hero-cta">
                                <button class="kv-btn kv-btn-primary" onclick="goDemo('client')" data-i18n="hero_cta_demo">Try for free</button>
                                <button class="kv-btn kv-btn-secondary" onclick="showView('how'); return false;" data-i18n="hero_cta_how">See how it works</button>
                            </div>
                        </div>

                        <!-- Right: phone mockup -->
                        <div class="kv-hero-visual" aria-label="Kaleya AI phone preview">
                            <div class="kv-phone-device">
                                <div class="kv-phone-screen">
                                    <div class="kv-phone-top">
                                        <div class="kv-phone-status">
                                            <span class="kv-phone-online"></span>
                                            <span data-i18n="hero_wake">hey Kaleya</span>
                                        </div>
                                        <span style="font-size:13px;opacity:.75" data-i18n="sms_call">SMS/Call</span>
                                    </div>
                                    <div class="kv-phone-body" onclick="goDemo('client')">
                                        <div class="kv-logo-orbit" onclick="event.stopPropagation();logoTap()">
                                            <img class="kv-phone-logo" src="" alt="Kaleya">
                                        </div>
                                        <div class="kv-phone-kicker" data-i18n="hero_tap">Tap the logo</div>
                                        <div class="kv-phone-title">Kaleya</div>
                                        <div class="kv-phone-subtitle" data-i18n="hero_intro_hint">Kaleya introduces itself</div>
                                        <button class="kv-mic-btn" onclick="event.stopPropagation();goDemo('client')">
                                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                                <path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z"/>
                                            </svg>
                                        </button>
                                        <div class="kv-voice-bars">
                                            <span></span><span></span><span></span><span></span><span></span>
                                        </div>
                                        <div class="kv-call-bubble">
                                            <div class="kv-bubble-label">Kaleya</div>
                                            <p data-i18n="hero_demo_msg">"Hello, how can I help?"</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Floating cards -->
                            <div class="kv-floating-card kv-cal-card">
                                <div class="kv-card-icon">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                                </div>
                                <div>
                                    <strong data-i18n="integrates_with">Integrations:</strong>
                                    <p>Google Cal, Calendly, Acuity</p>
                                    <span class="kv-fc-tag">Auto-booking</span>
                                </div>
                            </div>

                            <div class="kv-floating-card kv-sms-card">
                                <div class="kv-card-icon kv-card-icon-dark">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.862 9.862 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                                </div>
                                <div>
                                    <strong data-i18n="sms_call">SMS/Call</strong>
                                    <p>WhatsApp · Viber · Telegram · SMS</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- ══ WORKS WITH ═══════════════════════════════════ -->
                <section class="kv-works">
                    <div class="kv-container">
                        <p class="kv-eyebrow" style="text-align:center">WORKS WITH EVERY SHOP</p>
                        <div class="kv-works-grid">
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg></div>
                                <span>Barbershop</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg></div>
                                <span>Hair Salon</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"/></svg></div>
                                <span>Nail Studio</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg></div>
                                <span>Day Spa</span>
                            </div>
                            <div class="kv-work-item">
                                <div class="kv-work-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/></svg></div>
                                <span>Med Spa</span>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- ══ FEATURES ═══════════════════════════════════════ -->
                <section id="kv-features" class="kv-section kv-features">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">FEATURES</p>
                            <h2 class="kv-section-title" data-i18n="feat_title">Everything a real receptionist does, only better</h2>
                            <p class="kv-section-sub" data-i18n="feat_sub">Kaleya understands clients, remembers rules and works in the selected language.</p>
                        </div>
                        <div class="kv-features-grid">
                            <div class="kv-feat-card">
                                <div class="kv-feat-icon" style="background:rgba(37,99,235,.15)">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#60A5FA" stroke-width="2"><path d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"/></svg>
                                </div>
                                <h3 data-i18n="f_lang_t">7 languages</h3>
                                <p data-i18n="f_lang_d">Serbian, English, Spanish, Portuguese, Russian, French and Italian with manual selection.</p>
                            </div>
                            <div class="kv-feat-card">
                                <div class="kv-feat-icon" style="background:rgba(16,185,129,.15)">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                                </div>
                                <h3 data-i18n="f2_t">Smart scheduling</h3>
                                <p data-i18n="f2_d">Checks the calendar and suggests available slots.</p>
                            </div>
                            <div class="kv-feat-card">
                                <div class="kv-feat-icon" style="background:rgba(139,92,246,.15)">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#A78BFA" stroke-width="2"><path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/></svg>
                                </div>
                                <h3 data-i18n="f3_t">Natural voice</h3>
                                <p data-i18n="f3_d">ElevenLabs voice for more natural conversations.</p>
                            </div>
                            <div class="kv-feat-card">
                                <div class="kv-feat-icon" style="background:rgba(251,191,36,.15)">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FBB724" stroke-width="2"><path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/></svg>
                                </div>
                                <h3 data-i18n="f_alarm_t">Staff alarms</h3>
                                <p data-i18n="f_alarm_d">Next-client announcement and urgent call request.</p>
                            </div>
                            <div class="kv-feat-card">
                                <div class="kv-feat-icon" style="background:rgba(34,197,94,.15)">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#4ADE80" stroke-width="2"><path d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.862 9.862 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
                                </div>
                                <h3 data-i18n="f_msg_t">Messaging channels</h3>
                                <p data-i18n="f_msg_d">WhatsApp, Viber, Telegram, SMS and phone calls.</p>
                            </div>
                            <div class="kv-feat-card">
                                <div class="kv-feat-icon" style="background:rgba(239,68,68,.15)">
                                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#F87171" stroke-width="2"><path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><circle cx="12" cy="12" r="3"/></svg>
                                </div>
                                <h3 data-i18n="f6_t">Admin control</h3>
                                <p data-i18n="f6_d">Global API and separate settings per client.</p>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- ══ HOW IT WORKS ═══════════════════════════════════ -->
                <section id="kv-how" class="kv-section kv-how">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">SETUP</p>
                            <h2 class="kv-section-title" data-i18n="how_t">Kaleya learns your business in 1 day</h2>
                        </div>
                        <div class="kv-how-grid">
                            <div class="kv-step">
                                <div class="kv-step-num">1</div>
                                <h3 data-i18n="how1_t">Connect a channel</h3>
                                <p data-i18n="how1_d">Phone, WhatsApp, Telegram, Viber or SMS.</p>
                            </div>
                            <div class="kv-step">
                                <div class="kv-step-num">2</div>
                                <h3 data-i18n="how2_t">Teach Kaleya</h3>
                                <p data-i18n="how2_d">Add working hours, services and scheduling rules.</p>
                            </div>
                            <div class="kv-step">
                                <div class="kv-step-num">3</div>
                                <h3 data-i18n="how3_t">Choose language and voice</h3>
                                <p data-i18n="how3_d">Kaleya speaks the language the client selects.</p>
                                <div class="kv-chat-demo">
                                    <div class="kv-chat-c"><span style="opacity:.6" data-i18n="chat_client">Client:</span> <span data-i18n="how_chat_c1">Hi, I need an appointment for tomorrow</span></div>
                                    <div class="kv-chat-k"><span style="opacity:.7" data-i18n="chat_kaleya">Kaleya:</span> <span data-i18n="how_chat_k1">Of course. Which service do you need?</span></div>
                                    <div class="kv-chat-c"><span style="opacity:.6" data-i18n="chat_client">Client:</span> <span data-i18n="how_chat_c2">Haircut, around 5 PM</span></div>
                                    <div class="kv-chat-k"><span style="opacity:.7" data-i18n="chat_kaleya">Kaleya:</span> <span data-i18n="how_chat_k2">I have 5:00 PM and 5:30 PM available. Which works for you?</span></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- ══ NO-SHOW ═════════════════════════════════════════ -->
                <section class="kv-noshow">
                    <div class="kv-noshow-inner">
                        <div>
                            <h2>Stop losing $1,200/mo to no-shows</h2>
                            <p class="kv-noshow-sub">Kaleya sends automatic reminders and handles rescheduling so your chairs stay full.</p>
                            <div class="kv-noshow-list">
                                <div class="kv-noshow-item">
                                    <div class="kv-check"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></div>
                                    <p><strong>24-hour reminder</strong> — automated SMS or WhatsApp before every appointment</p>
                                </div>
                                <div class="kv-noshow-item">
                                    <div class="kv-check"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></div>
                                    <p><strong>1-tap reschedule</strong> — client replies and Kaleya finds a new slot instantly</p>
                                </div>
                                <div class="kv-noshow-item">
                                    <div class="kv-check"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg></div>
                                    <p><strong>Staff alert</strong> — you get notified the moment a cancellation happens</p>
                                </div>
                            </div>
                        </div>
                        <div class="kv-noshow-card">
                            <h4>Kaleya reminder</h4>
                            <div class="kv-sms-demo">
                                <div class="kv-sms-label">Tomorrow · 3:00 PM</div>
                                Hi! Just a reminder about your appointment tomorrow at 3 PM. Reply <strong>C</strong> to confirm or <strong>R</strong> to reschedule.
                            </div>
                            <div class="kv-sms-demo" style="background:#DBEAFE;border-color:#BFDBFE">
                                <div class="kv-sms-label" style="color:#1D4ED8">Client reply</div>
                                <strong style="color:#1E40AF">C</strong>
                            </div>
                            <div class="kv-sms-demo" style="background:#D1FAE5;border-color:#A7F3D0">
                                <div class="kv-sms-label" style="color:#065F46">Kaleya</div>
                                <strong style="color:#065F46">✓ Confirmed</strong> — see you tomorrow at 3 PM!
                            </div>
                        </div>
                    </div>
                </section>

                <!-- ══ PRICING ════════════════════════════════════════ -->
                <section id="kv-pricing" class="kv-section">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">PLANS</p>
                            <h2 class="kv-section-title" data-i18n="price_t">Simple pricing</h2>
                            <p class="kv-section-sub" data-i18n="price_s">Five packages for different automation levels.</p>
                        </div>
                        <div class="kv-pricing-grid">
                            <!-- Basic -->
                            <div class="kv-price-card">
                                <div class="kv-price-name">Basic</div>
                                <div class="kv-price-desc" data-i18n="p_basic_d">For small teams</div>
                                <div class="kv-price-amount">$59<span>/mo</span></div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_basic_f1">AI Kaleya scheduling</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_basic_f2">Owner Kaleya APP</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_basic_f3">Owner scheduling</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_basic_f4">WA + Viber + Telegram</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_basic_f5">AI voice</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_basic_f6">Alarms &amp; notifications</span></li>
                                </ul>
                                <a href="register-basic.html" class="kv-price-btn" data-i18n="trial_btn">Try 14 days</a>
                            </div>
                            <!-- Pro (popular) -->
                            <div class="kv-price-card kv-pc-popular">
                                <div class="kv-pop-badge" data-i18n="popular">MOST POPULAR</div>
                                <div class="kv-price-name">Pro</div>
                                <div class="kv-price-desc" data-i18n="p_pro_d">Owner + 1 staff</div>
                                <div class="kv-price-amount">$99<span>/mo</span></div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_pro_f1">Everything in Basic</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_pro_f2">1 staff member</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_pro_f3">Staff scheduling</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_pro_f4">Staff Kaleya APP</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_pro_f5">Time blocking</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_pro_f6">Instagram DM + TikTok DM</span></li>
                                </ul>
                                <a href="register-pro.html" class="kv-price-btn kv-price-btn-blue" data-i18n="trial_btn">Try 14 days</a>
                            </div>
                            <!-- Business -->
                            <div class="kv-price-card">
                                <div class="kv-price-name">Business</div>
                                <div class="kv-price-desc" data-i18n="p_business_d">Up to 5 staff</div>
                                <div class="kv-price-amount">$349<span>/mo</span></div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_f1">All from Basic + Pro</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_f2">Up to 5 staff</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_f3">Staff Kaleya APP</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_f4">More languages by agreement</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_f5">Company API</span></li>
                                </ul>
                                <a href="register-business.html" class="kv-price-btn" data-i18n="trial_btn">Try 14 days</a>
                            </div>
                            <!-- Business+ -->
                            <div class="kv-price-card">
                                <div class="kv-price-name">Business+</div>
                                <div class="kv-price-desc" data-i18n="p_business_plus_d">Up to 15 staff</div>
                                <div class="kv-price-amount">$579<span>/mo</span></div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_plus_f1">All from Basic + Pro + Business</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_plus_f2">Up to 15 staff</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_plus_f3">Phone calls &amp; SMS</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_plus_f4">ElevenLabs AI voice</span></li>
                                </ul>
                                <a href="register-business-plus.html" class="kv-price-btn" data-i18n="trial_btn">Try 14 days</a>
                            </div>
                            <!-- BusinessPro+ -->
                            <div class="kv-price-card kv-price-card-dark">
                                <div class="kv-price-name">BusinessPro+</div>
                                <div class="kv-price-desc" data-i18n="p_business_pro_d">15+ staff</div>
                                <div class="kv-price-amount" data-i18n="custom_price">Custom</div>
                                <ul class="kv-price-feats">
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_pro_f1">All from previous plans</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_pro_f2">15+ staff</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_pro_f3">Custom integrations</span></li>
                                    <li><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg><span data-i18n="p_business_pro_f4">Advanced architecture</span></li>
                                </ul>
                                <a href="register-business-pro-plus.html" class="kv-price-btn kv-price-btn-white" data-i18n="price_contact">Contact</a>
                            </div>
                        </div>
                    </div>
                </section>

                <!-- ══ FAQ ════════════════════════════════════════════ -->
                <section id="kv-faq" class="kv-section">
                    <div class="kv-container">
                        <div class="kv-section-head">
                            <p class="kv-eyebrow">FAQ</p>
                            <h2 class="kv-section-title">Frequently asked questions</h2>
                        </div>
                        <div class="kv-faq-wrap">
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    Does Kaleya work after hours?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Yes — Kaleya is active 24/7. It answers calls, books appointments and sends reminders even when your shop is closed. You wake up to a full schedule.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    Which messaging channels are supported?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>WhatsApp, Viber, Telegram, SMS and voice calls. Instagram DM and TikTok DM are available on the Pro plan and above.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    How long does setup take?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Most shops are live within 24 hours. You connect a channel, add your services and working hours, and Kaleya starts answering immediately.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    Can I try it for free?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>Yes — every plan includes a 14-day free trial, no credit card required. Click "Try 14 days" on any plan to get started.</p></div>
                            </div>
                            <div class="kv-faq-item">
                                <button class="kv-faq-q">
                                    What languages does Kaleya speak?
                                    <svg class="kv-faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                </button>
                                <div class="kv-faq-a"><p>English, Spanish, Portuguese, Russian, French, Italian and Serbian. Kaleya detects the client's language automatically and responds in kind.</p></div>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <footer class="kv-footer">
                <div class="kv-footer-inner">
                    <div class="kv-footer-left">
                        <img id="kv-footer-logo" src="" alt="Kaleya">
                        <span><strong>Kaleya</strong> AI</span>
                        <span>© 2025 Kaleya AI · aikaleya.com</span>
                    </div>
                    <div class="kv-footer-right">
                        <a href="privacy.html" data-i18n="footer_privacy">Privacy</a>
                        <a href="terms.html" data-i18n="footer_terms">Terms</a>
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
                    ['kv-header-logo','kv-footer-logo'].forEach(function(id){
                        var el = document.getElementById(id);
                        if(el) el.src = ref.src;
                    });
                    document.querySelectorAll('.kv-phone-logo').forEach(function(img){ img.src = ref.src; });
                }

                // Slideshow
                var slides = document.querySelectorAll('#landing-view .kv-slide');
                var idx = 0;
                if(slides.length > 1){
                    setInterval(function(){
                        slides[idx].classList.remove('kv-active');
                        idx = (idx+1) % slides.length;
                        slides[idx].classList.add('kv-active');
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

# ─── 4. EDIT A — Replace bad CSS ──────────────────────────────────────────────
# Match from the "placeholder start" comment to the last rule before </style>
css_pattern = re.compile(
    r'/\* LANDING DARK – placeholder start \*/[\s\S]*?/\* Sekcijski "border-y"[^}]*\}',
    re.DOTALL
)

if css_pattern.search(content):
    content = css_pattern.sub(NEW_CSS, content, count=1)
    print("✓ CSS replaced")
else:
    print("✗ CSS pattern NOT found — check anchors")
    sys.exit(1)

# ─── 5. EDIT B — Replace landing HTML ─────────────────────────────────────────
# Match from the opening landing-view div to its closing </div>
# The closing </div> at line 715 is followed by a blank line then <!-- LOGIN VIEW -->
html_pattern = re.compile(
    r'<div id="landing-view" class="">[\s\S]*?</div>(?=\s*\n\s*<!-- LOGIN VIEW -->)',
    re.DOTALL
)

if html_pattern.search(content):
    content = html_pattern.sub(NEW_HTML, content, count=1)
    print("✓ Landing HTML replaced")
else:
    print("✗ HTML pattern NOT found — check anchors")
    sys.exit(1)

# ─── 6. Write back ────────────────────────────────────────────────────────────
with open(FILE, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ File written successfully")
print("Done!")
