"""
천명도 (天命圖) v3.0 Ultimate Edition
15탭 풀스펙 완전판
Modules: A(만세력) B(명리연산) C(동적변수) D(성명·풍수) E(조후·용신)
         F(직업·건강) G(귀인·삼재) H(육친) I(궁합) J(택일) K(별자리) L(종합점수)
Tech: Python + Streamlit + Google Gemini API
"""

import streamlit as st
import json, math, calendar
from datetime import datetime, date
import google.generativeai as genai
import pathlib, base64

# ── API 키 로컬 저장/로드 ──
_CONFIG_PATH = pathlib.Path.home() / ".saju_hobbang_config.json"

def load_api_key() -> str:
    try:
        import json
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            raw  = data.get("gemini_api_key", "")
            # base64 디코딩 (간단 난독화)
            return base64.b64decode(raw.encode()).decode() if raw else ""
    except Exception:
        pass
    return ""

def save_api_key(key: str):
    try:
        import json
        encoded = base64.b64encode(key.encode()).decode()
        _CONFIG_PATH.write_text(
            json.dumps({"gemini_api_key": encoded}, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception:
        pass

# 음력→양력 변환 (korean_lunar_calendar 설치 시 동작)
try:
    from korean_lunar_calendar import KoreanLunarCalendar as _KLC
    _klc = _KLC()
    def lunar_to_solar(year: int, month: int, day: int) -> tuple:
        _klc.setLunarDate(year, month, day, False)
        # SolarIsoFormat()은 모든 버전에서 안전 ("YYYY-MM-DD")
        iso = _klc.SolarIsoFormat()
        parts = iso.split('-')
        return int(parts[0]), int(parts[1]), int(parts[2])
    _LUNAR_AVAILABLE = True
except ImportError:
    _LUNAR_AVAILABLE = False
    def lunar_to_solar(year, month, day):
        return year, month, day  # 변환 불가 시 그대로 반환

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAGE CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(
    page_title="HS사주방 | 천명도 사주 분석",
    page_icon="☯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBAL CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;600;700&family=Noto+Sans+KR:wght@400;500;600&display=swap');

/* ── 기본 ── */
html,body,[class*="css"]{
  font-family:'Noto Sans KR',sans-serif;
  font-size:15px;
  color:#1a1a1a;
}
.stApp{background:linear-gradient(180deg,#faf6ed 0%,#f5efe0 100%);min-height:100vh;}

/* ── 헤더 ── */
.saju-header{
  text-align:center;padding:1.4rem 1rem 1rem;
  background:white;border-bottom:3px solid #c0392b;
  margin-bottom:1.2rem;box-shadow:0 2px 8px rgba(0,0,0,.06);
}
.saju-header h1{
  font-family:'Noto Serif KR',serif;font-size:2rem;
  font-weight:700;color:#c0392b;letter-spacing:.12em;margin:0;
}
.saju-header .sub{font-size:.82rem;color:#666;margin-top:.25rem;}

/* ── 섹션 제목 ── */
.stitle{
  font-family:'Noto Serif KR',serif;font-size:1rem;font-weight:700;
  color:#c0392b;border-left:4px solid #c0392b;padding-left:.65rem;
  margin:1.2rem 0 .75rem;letter-spacing:.03em;
}

/* ── 사주 8자 카드 ── */
.pillar-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin:.75rem 0;}
.pillar-card{
  background:#ffffff;
  border:2px solid #e8dfc8;border-radius:10px;
  padding:1rem .6rem;text-align:center;
  box-shadow:0 2px 8px rgba(0,0,0,.06);transition:box-shadow .2s;
}
.pillar-card:hover{box-shadow:0 4px 14px rgba(0,0,0,.12);}
.pillar-card.day-col{border-color:#8b1a1a;background:#fffdf7;box-shadow:0 2px 14px rgba(139,26,26,.25);}
.p-label{font-size:.68rem;color:#888;letter-spacing:.1em;margin-bottom:.35rem;font-weight:500;}
.p-stem{font-family:'Noto Serif KR',serif;font-size:2rem;font-weight:700;line-height:1.1;}
.p-branch{font-family:'Noto Serif KR',serif;font-size:2rem;font-weight:700;margin-top:.05rem;line-height:1.1;}
.p-sub{font-size:.72rem;color:#555;margin-top:.35rem;font-weight:500;}
.p-fort{font-size:.72rem;color:#c0392b;margin-top:.15rem;font-weight:600;}
.p-naeum{font-size:.68rem;color:#777;margin-top:.1rem;}
.p-gm{font-size:.72rem;color:#e53935;margin-top:.1rem;font-weight:600;}

/* ── 오행 색상 ── */
.oh-목{color:#2e7d32!important;} .oh-화{color:#c62828!important;}
.oh-토{color:#e65100!important;} .oh-금{color:#546e7a!important;}
.oh-수{color:#1565c0!important;}

/* ── 정보 카드 ── */
.icard{
  background:#fffdf7;border:1px solid #e5dec8;border-radius:8px;
  padding:.85rem 1rem;margin-bottom:.6rem;
  box-shadow:0 1px 4px rgba(0,0,0,.05);
}
.icard-t{font-size:.72rem;color:#888;letter-spacing:.08em;margin-bottom:.3rem;font-weight:500;text-transform:uppercase;}
.icard-v{font-size:.97rem;font-weight:600;color:#1a1a1a;}

/* ── 오행 바 ── */
.oh-bar-wrap{margin:.4rem 0;}
.oh-bar-row{display:flex;justify-content:space-between;font-size:.82rem;margin-bottom:.15rem;font-weight:500;}
.oh-bar-bg{background:#eeeeee;border-radius:3px;height:10px;overflow:hidden;}
.oh-bar-fill{height:100%;border-radius:3px;}

/* ── 용신 배지 ── */
.ys-badge{display:inline-block;padding:.22rem .7rem;border-radius:20px;font-size:.8rem;font-weight:600;margin:.2rem;}
.ys-용신{background:#fdecea;color:#b71c1c;border:1.5px solid #ef9a9a;}
.ys-희신{background:#e8f5e9;color:#1b5e20;border:1.5px solid #a5d6a7;}
.ys-기신{background:#fff3e0;color:#bf360c;border:1.5px solid #ffcc80;}
.ys-한신{background:#f5f5f5;color:#424242;border:1.5px solid #bdbdbd;}
.ys-구신{background:#ede7f6;color:#311b92;border:1.5px solid #b39ddb;}

/* ── 관계 배지 ── */
.rel-badge{display:inline-block;padding:.18rem .6rem;border-radius:4px;font-size:.78rem;margin:.15rem;font-weight:500;}
.rel-합{background:#e8f5e9;color:#1b5e20;} .rel-삼합{background:#e0f7fa;color:#006064;}
.rel-방합{background:#e0f2f1;color:#004d40;} .rel-충{background:#fdecea;color:#b71c1c;}
.rel-형{background:#fff8e1;color:#e65100;} .rel-파{background:#f3e5f5;color:#4a148c;}
.rel-해{background:#e8eaf6;color:#1a237e;} .rel-원진{background:#fce4ec;color:#880e4f;}
.rel-stem{background:#f9fbe7;color:#33691e;}

/* ── 신살 그리드 ── */
.sisal-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:.45rem;margin:.75rem 0;}
.sisal-cell{border-radius:6px;padding:.5rem .3rem;text-align:center;font-size:.73rem;}
.sisal-on{background:#fdecea;border:1.5px solid #ef5350;color:#b71c1c;}
.sisal-off{background:#fafafa;border:1px solid #e0e0e0;color:#9e9e9e;}
.sisal-name{font-weight:600;display:block;font-size:.76rem;}
.sisal-branch{font-size:.68rem;display:block;margin-top:.1rem;}

/* ── 대운 ── */
.daeun-grid{display:grid;grid-template-columns:repeat(10,1fr);gap:.35rem;margin:.7rem 0;}
.daeun-cell{
  background:#fefbf3;border:1.5px solid #d4c4a8;border-radius:6px;
  padding:.45rem .1rem;text-align:center;
}
.daeun-cell.cur{border-color:#8b1a1a;background:#fbe9e7;box-shadow:0 0 0 2px rgba(139,26,26,.3);}
.daeun-char{font-family:'Noto Serif KR',serif;font-size:.95rem;font-weight:700;}
.daeun-age{font-size:.6rem;color:#888;margin-top:.08rem;}

/* ── 월운 ── */
.weol-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:.35rem;margin:.65rem 0;}
.weol-cell{background:#fefbf3;border:1.5px solid #d4c4a8;border-radius:6px;padding:.45rem .15rem;text-align:center;}
.weol-cell.cur-m{border-color:#1565c0;background:#e3f2fd;}
.weol-mo{font-size:.65rem;color:#888;margin-bottom:.2rem;}

/* ── 수리 테이블 ── */
.suri-table{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.82rem;}
.suri-table th{background:#8b1a1a;color:#fef9e7;font-family:'Noto Serif KR',serif;padding:.55rem .7rem;border:1px solid #6b1111;font-weight:700;}
.suri-table td{padding:.5rem .7rem;border:1px solid #e0e0e0;color:#1a1a1a;}
.suri-table tr:nth-child(even){background:#f9f9f9;}
.suri-good{color:#1b5e20;font-weight:600;} .suri-bad{color:#b71c1c;font-weight:600;}

/* ── 나경 컴퍼스 ── */
.compass-wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:.4rem;max-width:300px;margin:.7rem auto;}
.compass-cell{border-radius:6px;padding:.6rem .3rem;text-align:center;font-size:.73rem;border:1px solid #e0e0e0;font-weight:500;}
.compass-center{background:#c0392b;color:white;font-family:'Noto Serif KR',serif;font-weight:700;}
.comp-생기{background:#e8f5e9;color:#1b5e20;border-color:#a5d6a7;}
.comp-천을{background:#e3f2fd;color:#0d47a1;border-color:#90caf9;}
.comp-연년{background:#e8eaf6;color:#283593;border-color:#9fa8da;}
.comp-복위{background:#f9fbe7;color:#33691e;border-color:#c5e1a5;}
.comp-절명{background:#fdecea;color:#b71c1c;border-color:#ef9a9a;}
.comp-오귀{background:#fff8e1;color:#e65100;border-color:#ffe082;}
.comp-육살{background:#f3e5f5;color:#4a148c;border-color:#ce93d8;}
.comp-화해{background:#fce4ec;color:#880e4f;border-color:#f48fb1;}

/* ── AI 리포트 ── */
.llm-report-box{
  background:#fffdf7;border:1px solid #e5dec8;border-left:5px solid #8b1a1a;
  border-radius:10px;padding:1.8rem 2rem;margin:.5rem 0;
  box-shadow:0 2px 12px rgba(139,26,26,.08);
}
/* 리포트 본문 글씨 — 크게 */
.llm-report-box p, .llm-report-box li{
  font-size:1.15rem !important;line-height:2 !important;color:#1a1a1a !important;
}
/* 리포트 소제목 — 더 크게 */
.llm-report-box h2{
  font-size:1.55rem !important;color:#8b1a1a !important;
  margin:1.6rem 0 .7rem !important;font-weight:700 !important;
  border-bottom:2px solid #f0e0d0;padding-bottom:.3rem;
}
.llm-report-box h1{font-size:1.7rem !important;color:#8b1a1a !important;}
.llm-report-box h3{font-size:1.3rem !important;color:#a93226 !important;font-weight:700 !important;}
.llm-report-box strong, .llm-report-box b{color:#8b1a1a !important;font-weight:700 !important;}

/* ── 귀인 배지 ── */
.guiin-badge{display:inline-block;padding:.2rem .7rem;border-radius:4px;font-size:.78rem;margin:.18rem;font-weight:500;}
.guiin-on{background:#fff8e1;color:#e65100;border:1.5px solid #ffcc02;font-weight:600;}
.guiin-off{background:#fafafa;color:#9e9e9e;border:1px solid #e0e0e0;}

/* ── 육친 테이블 ── */
.yukchins-table{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.82rem;}
.yukchins-table th{background:#5d4037;color:#fef9e7;padding:.5rem .65rem;border:1px solid #3e2723;font-weight:700;}
.yukchins-table td{padding:.45rem .65rem;border:1px solid #e0e0e0;color:#1a1a1a;}

/* ── 궁합 점수 ── */
.goonghap-score{text-align:center;padding:1.2rem;background:white;border-radius:10px;border:1px solid #e0e0e0;box-shadow:0 2px 8px rgba(0,0,0,.06);}
.goonghap-num{font-family:'Noto Serif KR',serif;font-size:3rem;font-weight:700;}

/* ── 택일 달력 ── */
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:.25rem;margin:.6rem 0;}
.cal-cell{border-radius:6px;padding:.4rem .2rem;text-align:center;font-size:.72rem;border:1px solid #e0e0e0;}
.cal-cell .day-num{font-size:.68rem;color:#666;margin-bottom:.1rem;font-weight:500;}
.cal-cell .gan{font-family:'Noto Serif KR',serif;font-size:.9rem;font-weight:700;}
.cal-길{background:#e8f5e9;border-color:#a5d6a7;}
.cal-흉{background:#fdecea;border-color:#ef9a9a;}
.cal-보통{background:#fafafa;}
.cal-empty{background:transparent;border:none;}

/* ── 별자리 카드 ── */
.zodiac-card{background:white;border:1px solid #e0e0e0;border-radius:10px;padding:1.2rem;margin:.7rem 0;box-shadow:0 2px 6px rgba(0,0,0,.05);}

/* ── 태그 ── */
.tag{display:inline-block;padding:.15rem .6rem;border-radius:12px;font-size:.78rem;margin:.12rem;background:#f5f5f5;border:1px solid #e0e0e0;color:#333;font-weight:500;}

/* ── 버튼 ── */
.stButton>button{
  background:#c0392b;color:white;border:none;border-radius:6px;
  padding:.6rem 1.5rem;font-family:'Noto Sans KR',sans-serif;
  font-size:.9rem;font-weight:600;width:100%;
  box-shadow:0 2px 6px rgba(192,57,43,.3);transition:background .2s;
}
.stButton>button:hover{background:#a93226;}

/* ── 탭 (핵심 수정) ── */
.stTabs [data-baseweb="tab-list"]{
  background:white !important;
  border-bottom:2px solid #e0e0e0 !important;
  gap:2px;
}
.stTabs [data-baseweb="tab"]{
  color:#333333 !important;
  font-size:.83rem !important;
  font-weight:500 !important;
  padding:.45rem .75rem !important;
  background:transparent !important;
}
.stTabs [data-baseweb="tab"]:hover{
  color:#c0392b !important;
  background:#fff5f5 !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"]{
  color:#c0392b !important;
  font-weight:700 !important;
  border-bottom:3px solid #c0392b !important;
  background:white !important;
}
/* ── 전체 텍스트 가시성 강화 ── */
p, span, div, label, li{color:#1a1a1a;}
.stMarkdown p{color:#1a1a1a !important;font-size:.92rem;line-height:1.7;}
.stCaption, .caption{color:#555555 !important;font-size:.8rem !important;}
h1,h2,h3{color:#1a1a1a !important;}
/* 사이드바 텍스트 */
section[data-testid="stSidebar"] label{color:#1a1a1a !important;font-size:.85rem !important;}
section[data-testid="stSidebar"] p{color:#333 !important;}
section[data-testid="stSidebar"] .stMarkdown{color:#1a1a1a !important;}
/* 입력 위젯 */
.stTextInput input, .stNumberInput input{
  color:#1a1a1a !important;font-size:.9rem !important;
  background:white !important;border:1px solid #ccc !important;
}
.stSelectbox [data-baseweb="select"] div{
  color:#1a1a1a !important;font-size:.88rem !important;
}
/* expander */
.streamlit-expanderHeader{color:#1a1a1a !important;font-weight:600 !important;}
/* success/warning/error */
.stAlert p{font-size:.88rem !important;}

/* ── 기타 ── */

.ai-section{margin:1.2rem 0;}
.ai-banner{background:linear-gradient(135deg,#fff5f5 0%,#fef3e2 100%);
  border:2px solid #c0392b;border-radius:12px;padding:1.2rem 1.4rem;
  margin-bottom:1rem;box-shadow:0 3px 12px rgba(139,26,26,.1);}
.ai-banner-title{font-family:'Noto Serif KR',serif;font-size:1.25rem;
  font-weight:700;color:#8b1a1a;letter-spacing:.04em;}
.ai-banner-sub{font-size:.85rem;color:#666;margin-top:.3rem;}
/* AI 리포트 제목 — 헤더 스타일(천명도 아래에 자연스럽게) */
.ai-header-block{text-align:center;padding:.3rem 0 1rem;margin-bottom:.5rem;}
.ai-header-title{font-family:'Noto Serif KR',serif;font-size:1.5rem;
  font-weight:700;color:#8b1a1a;letter-spacing:.05em;}
.ai-header-sub{font-size:.9rem;color:#777;margin-top:.4rem;}
/* ── 채팅 상담실 ── */
.chat-header{font-family:'Noto Serif KR',serif;font-size:1.3rem;font-weight:700;
  color:#8b1a1a;margin-top:.5rem;}
.chat-sub{font-size:.83rem;color:#777;margin:.3rem 0 .8rem;line-height:1.5;}
.chat-box{background:#f0e8d8;border:1px solid #d4c4a8;border-radius:12px;
  padding:1rem;min-height:120px;max-height:500px;overflow-y:auto;margin-bottom:.6rem;}
.chat-empty{text-align:center;color:#999;padding:2rem 0;font-size:.9rem;line-height:1.8;}
.chat-row{display:flex;margin-bottom:.7rem;}
.chat-row.right{justify-content:flex-end;}
.chat-row.left{justify-content:flex-start;}
.bubble{max-width:80%;padding:.8rem 1.1rem;border-radius:16px;font-size:1.05rem;
  line-height:1.7;word-break:break-word;white-space:pre-wrap;}
.bubble.user{background:#ffe44d;color:#1a1a1a;border-bottom-right-radius:4px;
  box-shadow:0 1px 3px rgba(0,0,0,.1);}
.bubble.ai{background:#ffffff;color:#1a1a1a;border:1px solid #e0d5b8;
  border-bottom-left-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.08);}
/* AI 리포트 생성 버튼(primary) 강조 — 전역 강력 선택자 */
button[kind="primary"],
button[data-testid="stBaseButton-primary"],
.stButton > button[kind="primary"],
div[data-testid="stButton"] button[kind="primary"]{
  background:linear-gradient(135deg,#c0392b 0%,#a93226 100%) !important;
  color:#ffffff !important;
  border:4px solid #f1c40f !important;
  border-radius:12px !important;
  font-size:1.35rem !important;
  font-weight:800 !important;
  letter-spacing:.04em !important;
  padding:1.3rem 1rem !important;
  min-height:98px !important;
  box-shadow:0 4px 16px rgba(192,57,43,.4) !important;
  transition:all .2s !important;
}
button[kind="primary"] *,
button[data-testid="stBaseButton-primary"] *{
  color:#ffffff !important;
  font-size:1.35rem !important;
  font-weight:800 !important;
}
button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover{
  background:linear-gradient(135deg,#a93226 0%,#922b21 100%) !important;
  border-color:#f39c12 !important;
  box-shadow:0 6px 24px rgba(241,196,15,.5) !important;
  transform:translateY(-2px) !important;
}
/* 삭제 버튼 — key 클래스(st-key-del_report) 기반 회색 + 흰글씨 */
[class*="st-key-del_report"] button{
  background:#6c757d !important;
  color:#ffffff !important;
  border:none !important;
  border-radius:8px !important;
  font-size:1.05rem !important;
  font-weight:700 !important;
  min-height:42px !important;
  padding:.62rem !important;
  box-shadow:none !important;
}
[class*="st-key-del_report"] button *,
[class*="st-key-del_report"] button *{color:#ffffff !important;}
[class*="st-key-del_report"] button:hover,
[class*="st-key-del_report"] button:hover{background:#5a6268 !important;}
/* 복사 버튼(iframe)을 위 버튼과 붙이기 */
.ai-section iframe{margin-top:-14px !important;display:block !important;}
.ai-section [data-testid="stIFrame"]{margin-top:-14px !important;}
/* iframe 컨테이너 여백 제거 */
.ai-section div[data-testid="element-container"]:has(iframe){
  margin-top:-14px !important;margin-bottom:0 !important;
}

.divider{border:none;border-top:1px solid #e8e8e8;margin:1.2rem 0;}
#MainMenu{visibility:hidden;} footer{visibility:hidden;}
/* ════════════════════════════════════════════════
   사이드바 시인성 완전 개선 (검은 배경 박멸)
   ════════════════════════════════════════════════ */
/* 사이드바 본체 */
section[data-testid="stSidebar"]{
  background:#fdfaf2 !important;
}
section[data-testid="stSidebar"] > div{background:#fdfaf2 !important;}
/* 사이드바 토글 버튼 — 잘 보이게 강조 */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[aria-label="Close sidebar"],
button[aria-label="Collapse sidebar"],
button[aria-label="Open sidebar"]{
  display:flex!important;visibility:visible!important;
  color:#c0392b !important;background:#fff !important;
  border:1px solid #e0d5b8 !important;border-radius:6px !important;
}
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] svg,
button[aria-label="Open sidebar"] svg,
button[aria-label="Close sidebar"] svg{fill:#c0392b !important;color:#c0392b !important;}

/* 사이드바 모든 텍스트 강제 진한색 */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] *:not(.stButton button):not([data-baseweb="tag"]){
  color:#1a1a1a !important;
}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span:not([data-baseweb="tag"] span){
  color:#1a1a1a !important;font-size:.86rem;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3{
  color:#c0392b !important;font-size:.95rem !important;font-weight:700 !important;
}
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"]{
  color:#666 !important;
}

/* ── 텍스트 입력창 ── */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea{
  background:#ffffff !important;color:#1a1a1a !important;
  border:1px solid #c8c8c8 !important;
}
section[data-testid="stSidebar"] input::placeholder{color:#999 !important;}

/* ── 셀렉트박스(드롭다운) 닫힌 상태 ── */
section[data-testid="stSidebar"] [data-baseweb="select"],
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="select"] div,
section[data-testid="stSidebar"] [data-baseweb="select"] span{
  background:#ffffff !important;color:#1a1a1a !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div{
  border:1px solid #c8c8c8 !important;
}
/* 셀렉트박스 화살표 아이콘 */
section[data-testid="stSidebar"] [data-baseweb="select"] svg{fill:#555 !important;color:#555 !important;}

/* ── 드롭다운 펼침 메뉴(팝오버) — 화면 전역 ── */
[data-baseweb="popover"],
[data-baseweb="popover"] *,
[data-baseweb="menu"],
[data-baseweb="menu"] *,
ul[role="listbox"],
ul[role="listbox"] li,
li[role="option"],
[data-baseweb="select"] [role="listbox"],
[data-testid="stSelectboxVirtualDropdown"],
[data-testid="stSelectboxVirtualDropdown"] *{
  background:#ffffff !important;color:#1a1a1a !important;
}
/* 드롭다운 항목 hover/선택 */
li[role="option"]:hover,
ul[role="listbox"] li:hover{
  background:#fbe9e7 !important;color:#8b1a1a !important;
}
li[role="option"][aria-selected="true"]{
  background:#fdecea !important;color:#8b1a1a !important;font-weight:600 !important;
}

/* ── 슬라이더(Slider) ── */
section[data-testid="stSidebar"] [data-baseweb="slider"]{background:transparent !important;}
section[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"]{
  background:#c0392b !important;border:2px solid #fff !important;
}
/* 슬라이더 값 라벨(말풍선) */
[data-baseweb="slider"] [data-testid="stTickBar"],
[data-baseweb="slider"] [data-testid="stTickBarMin"],
[data-baseweb="slider"] [data-testid="stTickBarMax"]{color:#555 !important;}
[data-baseweb="slider"] div[style*="background"]{color:#1a1a1a !important;}
.stSlider [data-baseweb="slider"] div{color:#1a1a1a !important;}
.stSlider label{color:#1a1a1a !important;}
/* 슬라이더 현재값 툴팁 */
[data-baseweb="tooltip"],
[data-baseweb="tooltip"] *{background:#c0392b !important;color:#fff !important;}

/* ── 라디오 버튼 ── */
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stRadio label p,
section[data-testid="stSidebar"] .stRadio div{color:#1a1a1a !important;}
.stRadio > div > label > div > p{color:#1a1a1a !important;font-size:.88rem !important;}

/* ── 체크박스 ── */
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stCheckbox label p,
section[data-testid="stSidebar"] .stCheckbox span{color:#1a1a1a !important;}

/* ── 숫자 입력 +/- 버튼 ── */
.stNumberInput button,
.stNumberInput [data-testid="stNumberInputStepDown"],
.stNumberInput [data-testid="stNumberInputStepUp"],
.stNumberInput [role="button"],
.stNumberInput div[class*="StepButton"],
.stNumberInput > div > div > button{
  background:#ffffff !important;color:#1a1a1a !important;border:1px solid #c8c8c8 !important;
}
.stNumberInput button:hover{background:#f0f0f0 !important;color:#c0392b !important;}
.stNumberInput button svg{fill:#555 !important;color:#555 !important;}
.stNumberInput input{
  background:#ffffff !important;color:#1a1a1a !important;
  border:1px solid #c8c8c8 !important;font-size:.9rem !important;
}

/* ── 알림 메시지 ── */
section[data-testid="stSidebar"] .stSuccess,
section[data-testid="stSidebar"] .stSuccess p{color:#1b5e20 !important;}
section[data-testid="stSidebar"] .stWarning,
section[data-testid="stSidebar"] .stWarning p{color:#e65100 !important;}
section[data-testid="stSidebar"] .stInfo,
section[data-testid="stSidebar"] .stInfo p{color:#0d47a1 !important;}
section[data-testid="stSidebar"] .stError,
section[data-testid="stSidebar"] .stError p{color:#b71c1c !important;}

/* ── expander ── */
section[data-testid="stSidebar"] .streamlit-expanderHeader,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary{
  color:#1a1a1a !important;font-weight:600 !important;background:#f5f0e3 !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary *{color:#1a1a1a !important;}
.streamlit-expanderContent,
section[data-testid="stSidebar"] [data-testid="stExpanderDetails"]{
  background:#ffffff !important;color:#1a1a1a !important;
}
.streamlit-expanderContent *,
section[data-testid="stSidebar"] [data-testid="stExpanderDetails"] *{color:#1a1a1a !important;}

/* ── 구분선 ── */
section[data-testid="stSidebar"] hr{border-color:#e0e0e0 !important;}

/* ════════════════════════════════════════════════
   본문 영역 공통 (드롭다운/슬라이더 전역 적용)
   ════════════════════════════════════════════════ */
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-baseweb="select"] div,
[data-baseweb="select"] span{background:#ffffff !important;color:#1a1a1a !important;}
[data-baseweb="select"] svg{fill:#555 !important;}
</style>
""", unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ████  CORE DATA TABLES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HEAVENLY_STEMS   = ["갑","을","병","정","무","기","경","신","임","계"]
EARTHLY_BRANCHES = ["자","축","인","묘","진","사","오","미","신","유","술","해"]
STEM_OHAENG   = {"갑":"목","을":"목","병":"화","정":"화","무":"토","기":"토","경":"금","신":"금","임":"수","계":"수"}
BRANCH_OHAENG = {"자":"수","축":"토","인":"목","묘":"목","진":"토","사":"화","오":"화","미":"토","신":"금","유":"금","술":"토","해":"수"}
STEM_YIN_YANG   = {"갑":"양","을":"음","병":"양","정":"음","무":"양","기":"음","경":"양","신":"음","임":"양","계":"음"}
BRANCH_YIN_YANG = {"자":"양","축":"음","인":"양","묘":"음","진":"양","사":"음","오":"양","미":"음","신":"양","유":"음","술":"양","해":"음"}
HIDDEN_STEMS = {"자":["계"],"축":["계","신","기"],"인":["무","병","갑"],"묘":["갑","을"],"진":["을","계","무"],"사":["무","경","병"],"오":["기","정"],"미":["정","을","기"],"신":["무","임","경"],"유":["경","신"],"술":["신","정","무"],"해":["무","갑","임"]}
BRANCH_MAIN_GI = {"자":"계","축":"기","인":"갑","묘":"을","진":"무","사":"병","오":"정","미":"기","신":"경","유":"신","술":"무","해":"임"}

NAEUM_NAMES = ["海中金","爐中火","大林木","路傍土","劍鋒金","山頭火","澗下水","城頭土","白蠟金","楊柳木","泉中水","屋上土","霹靂火","松柏木","長流水","沙中金","山下火","平地木","壁上土","金箔金","覆燈火","天河水","大驛土","釵釧金","桑柘木","大溪水","沙中土","天上火","石榴木","大海水"]
NAEUM_OH    = ["금","화","목","토","금","화","수","토","금","목","수","토","화","목","수","금","화","목","토","금","화","수","토","금","목","수","토","화","목","수"]

TWELVE_FORTUNE = ["절","태","양","장생","목욕","관대","건록","제왕","쇠","병","사","묘"]
FORTUNE_SCORE  = {"절":10,"태":20,"양":30,"장생":90,"목욕":60,"관대":80,"건록":100,"제왕":95,"쇠":50,"병":30,"사":20,"묘":15}
STEM_BIRTH_BRANCH = {"갑":"해","을":"오","병":"인","정":"유","무":"인","기":"유","경":"사","신":"자","임":"신","계":"묘"}

SIKSHIN_MAP = {
    ("목","목","양"):"비견",("목","목","음"):"겁재",("목","화","양"):"식신",("목","화","음"):"상관",
    ("목","토","양"):"편재",("목","토","음"):"정재",("목","금","양"):"편관",("목","금","음"):"정관",
    ("목","수","양"):"편인",("목","수","음"):"정인",
    ("화","화","양"):"비견",("화","화","음"):"겁재",("화","토","양"):"식신",("화","토","음"):"상관",
    ("화","금","양"):"편재",("화","금","음"):"정재",("화","수","양"):"편관",("화","수","음"):"정관",
    ("화","목","양"):"편인",("화","목","음"):"정인",
    ("토","토","양"):"비견",("토","토","음"):"겁재",("토","금","양"):"식신",("토","금","음"):"상관",
    ("토","수","양"):"편재",("토","수","음"):"정재",("토","목","양"):"편관",("토","목","음"):"정관",
    ("토","화","양"):"편인",("토","화","음"):"정인",
    ("금","금","양"):"비견",("금","금","음"):"겁재",("금","수","양"):"식신",("금","수","음"):"상관",
    ("금","목","양"):"편재",("금","목","음"):"정재",("금","화","양"):"편관",("금","화","음"):"정관",
    ("금","토","양"):"편인",("금","토","음"):"정인",
    ("수","수","양"):"비견",("수","수","음"):"겁재",("수","목","양"):"식신",("수","목","음"):"상관",
    ("수","화","양"):"편재",("수","화","음"):"정재",("수","토","양"):"편관",("수","토","음"):"정관",
    ("수","금","양"):"편인",("수","금","음"):"정인",
}

STEM_HAP = {frozenset(["갑","기"]):"토",frozenset(["을","경"]):"금",frozenset(["병","신"]):"수",frozenset(["정","임"]):"목",frozenset(["무","계"]):"화"}
BRANCH_HAP_6 = [("자","축"),("인","해"),("묘","술"),("진","유"),("사","신"),("오","미")]
BRANCH_SAMHAP= [({"신","자","진"},"수"),({"해","묘","미"},"목"),({"인","오","술"},"화"),({"사","유","축"},"금")]
BRANCH_BANGHAP=[({"인","묘","진"},"목"),({"사","오","미"},"화"),({"신","유","술"},"금"),({"해","자","축"},"수")]
BRANCH_CHUNG = [("자","오"),("축","미"),("인","신"),("묘","유"),("진","술"),("사","해")]
BRANCH_HYUNG_3A= frozenset(["인","사","신"])
BRANCH_HYUNG_3B= frozenset(["축","술","미"])
BRANCH_HYUNG_2 = frozenset(["자","묘"])
BRANCH_HYUNG_SELF = {"진","오","유","해"}
BRANCH_PA    = [("자","유"),("오","묘"),("인","해"),("사","신"),("축","진"),("술","미")]
BRANCH_HAE   = [("자","미"),("축","오"),("인","사"),("묘","진"),("신","해"),("유","술")]
BRANCH_WONJIN= [("자","미"),("축","오"),("인","유"),("묘","신"),("진","해"),("사","술")]
GONGMANG_TABLE = {0:["술","해"],1:["신","유"],2:["오","미"],3:["진","사"],4:["인","묘"],5:["자","축"]}

SISAL_12_START = {"신":"신","자":"신","진":"신","해":"해","묘":"해","미":"해","인":"인","오":"인","술":"인","사":"사","유":"사","축":"사"}
SISAL_12_NAMES = ["겁살","재살","천살","지살","년살","월살","망신","장성","반안","역마","육해","화개"]
SISAL_12_DESC  = ["재물·명예 손상","질병·재난 주의","하늘의 시련","이동·여행 신중","다툼 주의","소모적 소비","명예 실추 주의","리더십 안정","고생 후 안정","이동·변화·역마","육친 인연 변화","예술·종교·고독"]

# 특수 귀인 신살 (Module G)
TIANYIGUI_MAP = {"갑":["축","미"],"무":["축","미"],"을":["자","신"],"기":["자","신"],"병":["해","유"],"정":["해","유"],"경":["오","인"],"신":["오","인"],"임":["사","묘"],"계":["사","묘"]}
MUNCHANG_MAP  = {"갑":"사","을":"오","병":"신","정":"유","무":"신","기":"유","경":"해","신":"자","임":"인","계":"묘"}
HAKDANG_MAP   = {"갑":"해","을":"오","병":"인","정":"유","무":"인","기":"유","경":"사","신":"자","임":"신","계":"묘"}
AMROK_MAP     = {"갑":"해","을":"술","병":"신","정":"미","무":"신","기":"미","경":"사","신":"진","임":"인","계":"축"}
GEUNROK_MAP   = {"갑":"인","을":"묘","병":"사","정":"오","무":"사","기":"오","경":"신","신":"유","임":"해","계":"자"}
YANGYIN_MAP   = {"갑":"묘","을":"인","병":"오","정":"사","무":"오","기":"사","경":"유","신":"신","임":"자","계":"해"}

# 삼재 (三災) - 생년지지 기준
SAMJAE_MAP = {
    "신":["인","묘","진"],"자":["인","묘","진"],"진":["인","묘","진"],
    "해":["사","오","미"],"묘":["사","오","미"],"미":["사","오","미"],
    "인":["신","유","술"],"오":["신","유","술"],"술":["신","유","술"],
    "사":["해","자","축"],"유":["해","자","축"],"축":["해","자","축"],
}

# 육친 (六親) 십성 대응
YUKCHINS_MALE = {
    "비견":"형제(남)","겁재":"형제(경쟁)","식신":"장모·처남","상관":"조모",
    "편재":"부친·연인","정재":"처(妻)","편관":"자녀(아들)","정관":"자녀(딸)",
    "편인":"조모·계모","정인":"모친",
}
YUKCHINS_FEMALE = {
    "비견":"자매(여)","겁재":"자매(경쟁)","식신":"자녀(딸)","상관":"자녀(아들·외향)",
    "편재":"부친","정재":"재물","편관":"남편(비공식)","정관":"남편(공식)",
    "편인":"조모·이모","정인":"모친·스승",
}
PILLAR_YUKCHINS_LABEL = {"year":"조부모궁(년주)","month":"부모·형제궁(월주)","day":"배우자궁(일지)","hour":"자녀궁(시주)"}

# 수리 81수리
SUREE_81 = {
    1:("대길","만물의 시작, 강한 의지와 독립"),2:("흉","분리와 고독, 이별 주의"),
    3:("길","명예와 지혜, 번영"),4:("대흉","사망·고난, 큰 어려움"),
    5:("대길","오행 균형, 풍요와 성공"),6:("길","안태와 평화, 안정된 삶"),
    7:("길","독립적 강인함"),8:("길","발전과 번영, 노력으로 성공"),
    9:("흉","종극, 무성하나 쇠퇴"),10:("흉","공허함"),
    11:("길","재도약, 갱신의 기회"),12:("흉","의지박약, 장애물"),
    13:("길","지혜와 총명함"),14:("흉","이산과 고독"),
    15:("대길","통솔력, 훌륭한 리더십"),16:("길","덕망과 존경"),
    17:("길","용기있는 전진"),18:("길","점진적 발전과 성공"),
    19:("흉","재화는 모으나 고독"),20:("흉","허망과 헛수고"),
    21:("대길","두령, 최고의 리더십"),22:("흉","중도 좌절"),
    23:("대길","공명, 재능 발휘"),24:("대길","입신, 축재와 성공"),
    25:("길","안강, 건강과 평안"),26:("혼재","영웅, 기복이 심함"),
    27:("흉","중간에 실패"),28:("대흉","역경과 고난"),
    29:("대길","공명, 출세"),30:("혼재","길흉 반반, 부침이 심함"),
    31:("대길","융창, 크게 번창"),32:("길","요행, 뜻밖의 행운"),
    33:("대길","승천, 활기찬 발전"),34:("대흉","파산, 파멸"),
    35:("길","온화, 안정된 생활"),36:("흉","파란, 풍파가 많음"),
    37:("길","덕위, 명예와 지위"),38:("길","문예, 예술적 재능"),
    39:("길","안태, 귀하고 장수"),40:("흉","무상, 공허함"),
    41:("대길","최고의 번영"),42:("흉","고행, 고생이 많음"),
    43:("흉","산란, 정신적 혼란"),44:("대흉","마장, 큰 불운"),
    45:("대길","대지, 총명한 지혜"),46:("흉","불행, 어려움"),
    47:("길","출세, 성공"),48:("대길","덕망, 크게 존경받음"),
    49:("혼재","흥망 교차"),50:("혼재","반길반흉"),
    51:("혼재","흥망 반복"),52:("길","행운"),
    53:("흉","외화내빈"),54:("대흉","멸망"),
    55:("흉","불완전"),56:("흉","한탄"),
    57:("길","길운"),58:("길","대기만성"),
    59:("흉","쇠퇴"),60:("흉","암흑"),
    61:("대길","길상"),62:("흉","분산"),
    63:("길","순탄"),64:("흉","혼란"),
    65:("길","명예"),66:("흉","쇠운"),
    67:("길","행복"),68:("길","성취"),
    69:("흉","불행"),70:("흉","공허"),
    71:("길","길운"),72:("흉","배신"),
    73:("길","평안"),74:("흉","암울"),
    75:("길","평화"),76:("흉","이별"),
    77:("혼재","내우"),78:("길","복록"),
    79:("흉","불운"),80:("흉","공허"),
    81:("대길","환원, 1수와 동일한 대길수"),
}

# 풍수
MYEONGGUNG_MAP = {1:"감(坎)",2:"곤(坤)",3:"진(震)",4:"손(巽)",5:"중궁",6:"건(乾)",7:"태(兌)",8:"간(艮)",9:"이(離)"}
DONG_SAHTAEK = {1,3,4,9}; SEO_SAHTAEK = {2,6,7,8}
PALGAE_GILHUNG = {
    1:{"생기":"동남","천을":"남","연년":"동","복위":"북","절명":"서북","오귀":"서남","육살":"동북","화해":"서"},
    2:{"생기":"서북","천을":"서","연년":"동북","복위":"서남","절명":"동","오귀":"동남","육살":"남","화해":"동북"},
    3:{"생기":"남","천을":"북","연년":"동남","복위":"동","절명":"서","오귀":"동북","육살":"서북","화해":"서남"},
    4:{"생기":"북","천을":"동","연년":"남","복위":"동남","절명":"서남","오귀":"서","육살":"서북","화해":"동북"},
    6:{"생기":"서","천을":"동북","연년":"서남","복위":"서북","절명":"동","오귀":"남","육살":"동남","화해":"북"},
    7:{"생기":"동북","천을":"서북","연년":"서남","복위":"서","절명":"동남","오귀":"북","육살":"동","화해":"남"},
    8:{"생기":"서남","천을":"서","연년":"서북","복위":"동북","절명":"남","오귀":"동","육살":"동남","화해":"북"},
    9:{"생기":"동","천을":"동남","연년":"북","복위":"남","절명":"서남","오귀":"서","육살":"서북","화해":"동북"},
}
SAMSAL_MAP     = {"신":"동방(寅方)","자":"동방(寅方)","진":"동방(寅方)","해":"서방(申方)","묘":"서방(申方)","미":"서방(申方)","인":"북방(亥方)","오":"북방(亥方)","술":"북방(亥方)","사":"남방(巳方)","유":"남방(巳方)","축":"남방(巳方)"}
DAEJANGGUN_MAP = {"신":"동방","유":"동방","술":"동방","해":"남방","자":"남방","축":"남방","인":"서방","묘":"서방","진":"서방","사":"북방","오":"북방","미":"북방"}

# 조후
JOHU_MAP = {
    "자":{"계절":"겨울","need":["화","목"],"desc":"한랭·수기 과다. 丙·甲이 조후용신."},
    "축":{"계절":"겨울","need":["화","목"],"desc":"한냉·토기. 丙火와 甲木으로 온기 필요."},
    "인":{"계절":"봄","need":["화","수"],"desc":"목기 상승. 丙火와 癸水의 조화 필요."},
    "묘":{"계절":"봄","need":["금","수"],"desc":"목 무성. 庚金으로 억제, 癸水로 윤택."},
    "진":{"계절":"봄→여름","need":["수","금"],"desc":"건조 토기. 壬水로 윤택, 庚金으로 소토."},
    "사":{"계절":"여름","need":["수","금"],"desc":"화기 강렬. 壬·癸水가 최우선 조후용신."},
    "오":{"계절":"여름","need":["수"],"desc":"최강 화기. 壬癸 水가 절대 조후용신."},
    "미":{"계절":"여름→가을","need":["수","목"],"desc":"조열 토기. 癸水로 윤택, 甲木으로 소토."},
    "신":{"계절":"가을","need":["화","수"],"desc":"서늘 금기. 丁火로 제련, 壬水로 흘려보냄."},
    "유":{"계절":"가을","need":["화","토"],"desc":"금기 강성. 丁火 제련, 丙火 온기 필요."},
    "술":{"계절":"가을→겨울","need":["화","목"],"desc":"한기 도래. 丙火·甲木으로 온기 필요."},
    "해":{"계절":"겨울","need":["화","목"],"desc":"차가운 수기. 甲木·丙火가 조후용신."},
}

# 오행 생극
OH_克_BY = {"목":"금","화":"수","토":"목","금":"화","수":"토"}
OH_生_BY = {"목":"수","화":"목","토":"화","금":"토","수":"금"}
OH_克    = {"목":"토","화":"금","토":"수","금":"목","수":"화"}
OH_生    = {"목":"화","화":"토","토":"금","금":"수","수":"목"}

# 직업·건강·행운
OHAENG_DETAIL = {
    "목":{"직업":["교육·학문","의료·한의학","문화·예술","법조·판사","출판·언론","환경·생태","복지·상담"],"건강":["간장","담낭","눈·시력","근육·힘줄","신경계"],"색":["초록","청색"],"방위":"동방(東)","숫자":"3, 8"},
    "화":{"직업":["방송·연예","IT·전기전자","마케팅·광고","주식·금융","요식업","에너지","강사·코치"],"건강":["심장","소장","혀·언어","혈관·혈압","정신건강"],"색":["빨강","주황"],"방위":"남방(南)","숫자":"2, 7"},
    "토":{"직업":["부동산·건설","공무원·행정","농업·식품","중개업","종교·철학","무역","보험"],"건강":["위장","비장·췌장","피부","입술·구강","면역계"],"색":["황색","갈색"],"방위":"중앙·사방","숫자":"5, 10"},
    "금":{"직업":["금융·은행","제조·기계","군인·경찰","무역·수출","회계·세무","외과","스포츠"],"건강":["폐","대장","코·호흡기","뼈·치아","기관지"],"색":["흰색","은색","금색"],"방위":"서방(西)","숫자":"4, 9"},
    "수":{"직업":["유통·물류","여행·관광","철학·역학","종교·명상","연구·학자","수산업","IT(데이터)"],"건강":["신장","방광","귀·청력","생식기","호르몬"],"색":["검정","남색"],"방위":"북방(北)","숫자":"1, 6"},
}

# 서양 별자리 (Module K)
ZODIAC_TABLE = [
    (3,21,4,19,"양자리","Aries","불","화","강한 의지·선구자 기질. 화(火)의 즉흥성과 유사."),
    (4,20,5,20,"황소자리","Taurus","흙","토","안정·실용·물질적 감각. 토(土)의 뚝심과 유사."),
    (5,21,6,20,"쌍둥이자리","Gemini","공기","목","소통·다재다능·호기심. 목(木)의 확산성과 유사."),
    (6,21,7,22,"게자리","Cancer","물","수","감수성·가정적·직관. 수(水)의 수용성과 유사."),
    (7,23,8,22,"사자자리","Leo","불","화","자존심·창의·리더십. 화(火)의 빛남과 유사."),
    (8,23,9,22,"처녀자리","Virgo","흙","금","분석·완벽·섬세함. 금(金)의 정밀성과 유사."),
    (9,23,10,22,"천칭자리","Libra","공기","목","균형·조화·외교. 목(木)의 유연함과 유사."),
    (10,23,11,21,"전갈자리","Scorpio","물","수","깊이·집요·변혁. 수(水)의 심층과 유사."),
    (11,22,12,21,"사수자리","Sagittarius","불","화","자유·철학·낙천. 화(火)의 확장성과 유사."),
    (12,22,1,19,"염소자리","Capricorn","흙","토","목표·인내·전통. 토(土)의 묵직함과 유사."),
    (1,20,2,18,"물병자리","Aquarius","공기","목","독창·혁신·인류애. 목(木)의 새로움과 유사."),
    (2,19,3,20,"물고기자리","Pisces","물","수","감성·공감·신비. 수(水)의 흐름과 유사."),
]

# UI constants
OHAENG_COLOR = {"목":"#4caf50","화":"#ef5350","토":"#ffa726","금":"#bdbdbd","수":"#42a5f5"}
OHAENG_LABEL = {"목":"木 목","화":"火 화","토":"土 토","금":"金 금","수":"水 수"}
PILLAR_KEYS  = ["year","month","day","hour"]
PILLAR_LABEL = {"year":"年 연주","month":"月 월주","day":"日 일주","hour":"時 시주"}
COMPASS_CLASS= {"생기":"comp-생기","천을":"comp-천을","연년":"comp-연년","복위":"comp-복위","절명":"comp-절명","오귀":"comp-오귀","육살":"comp-육살","화해":"comp-화해"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE A  만세력
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def ganzi_pos(si: int, bi: int) -> int:
    for i in range(60):
        if i % 10 == si and i % 12 == bi:
            return i
    return 0

def get_naeum(stem: str, branch: str) -> tuple:
    pos = ganzi_pos(HEAVENLY_STEMS.index(stem), EARTHLY_BRANCHES.index(branch))
    p = pos // 2
    return NAEUM_NAMES[p], NAEUM_OH[p]

def get_gongmang(ds: str, db: str) -> list:
    pos = ganzi_pos(HEAVENLY_STEMS.index(ds), EARTHLY_BRANCHES.index(db))
    return GONGMANG_TABLE.get(pos // 10, [])

def solar_to_ganjee(year: int, month: int, day: int, hour: int) -> dict:
    ys = (year - 4) % 10;  yb = (year - 4) % 12
    yst = HEAVENLY_STEMS[ys]
    base = {"갑":2,"을":4,"병":6,"정":8,"무":10,"기":12,"경":14,"신":16,"임":18,"계":20}[yst]
    ms = (base + month - 1) % 10;  mb = (month + 1) % 12
    delta = (date(year, month, day) - date(1900,1,1)).days
    ds = (delta + 10) % 10;   db = (delta + 10) % 12
    hb = (hour // 2) % 12;    hs = (ds * 2 + hb) % 10
    return {
        "year":  {"stem":HEAVENLY_STEMS[ys],"branch":EARTHLY_BRANCHES[yb]},
        "month": {"stem":HEAVENLY_STEMS[ms],"branch":EARTHLY_BRANCHES[mb]},
        "day":   {"stem":HEAVENLY_STEMS[ds],"branch":EARTHLY_BRANCHES[db]},
        "hour":  {"stem":HEAVENLY_STEMS[hs],"branch":EARTHLY_BRANCHES[hb]},
    }

def get_year_ganzi(year: int) -> dict:
    s = (year-4)%10;  b = (year-4)%12
    return {"stem":HEAVENLY_STEMS[s],"branch":EARTHLY_BRANCHES[b],"year":year}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE B  명리 관계 연산
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_sikshin(ilgan: str, target: str) -> str:
    io = STEM_OHAENG[ilgan];  to = STEM_OHAENG[target]
    rel = "양" if STEM_YIN_YANG[ilgan] == STEM_YIN_YANG[target] else "음"
    return SIKSHIN_MAP.get((io, to, rel), "?")

def get_twelve_fortune(ilgan: str, branch: str) -> str:
    start = STEM_BIRTH_BRANCH.get(ilgan,"해")
    offset = (EARTHLY_BRANCHES.index(branch) - EARTHLY_BRANCHES.index(start)) % 12
    return TWELVE_FORTUNE[offset]

def calc_ohaeng_score(pillars: dict) -> dict:
    s = {"목":0,"화":0,"토":0,"금":0,"수":0}
    for p in PILLAR_KEYS:
        s[STEM_OHAENG[pillars[p]["stem"]]] += 3
        s[BRANCH_OHAENG[pillars[p]["branch"]]] += 2
        for h in HIDDEN_STEMS.get(pillars[p]["branch"],[]):
            s[STEM_OHAENG[h]] += 1
    return s

def calc_all_sikshin(pillars: dict, ilgan: str) -> dict:
    r = {}
    for p in PILLAR_KEYS:
        st = pillars[p]["stem"];  br = pillars[p]["branch"]
        r[f"{p}_stem"]   = get_sikshin(ilgan, st) if st != ilgan else "일간"
        r[f"{p}_branch"] = get_sikshin(ilgan, BRANCH_MAIN_GI[br])
    return r

def calc_all_fortune(pillars: dict, ilgan: str) -> dict:
    return {p: get_twelve_fortune(ilgan, pillars[p]["branch"]) for p in PILLAR_KEYS}

def detect_stem_hap(pillars: dict) -> list:
    stems = [pillars[p]["stem"] for p in PILLAR_KEYS]
    result = []
    for i in range(len(stems)):
        for j in range(i+1, len(stems)):
            key = frozenset([stems[i], stems[j]])
            if key in STEM_HAP:
                result.append({"pair":f"{stems[i]}·{stems[j]}", "result":STEM_HAP[key]})
    return result

def detect_branch_relations(pillars: dict) -> dict:
    brs = [pillars[p]["branch"] for p in PILLAR_KEYS];  bs = set(brs)
    hap6,samhap,banghap,chung,hyung,pa,hae,wonjin = [],[],[],[],[],[],[],[]
    for i in range(len(brs)):
        for j in range(i+1, len(brs)):
            a,b = brs[i],brs[j]; ps = f"{a}-{b}"
            if (a,b) in BRANCH_HAP_6 or (b,a) in BRANCH_HAP_6: hap6.append(ps)
            if (a,b) in BRANCH_CHUNG or (b,a) in BRANCH_CHUNG: chung.append(ps)
            if (a,b) in BRANCH_PA    or (b,a) in BRANCH_PA:    pa.append(ps)
            if (a,b) in BRANCH_HAE   or (b,a) in BRANCH_HAE:   hae.append(ps)
            if (a,b) in BRANCH_WONJIN or (b,a) in BRANCH_WONJIN: wonjin.append(ps)
    if bs & BRANCH_HYUNG_3A == BRANCH_HYUNG_3A: hyung.append("인-사-신(지세지형)")
    elif len(bs & BRANCH_HYUNG_3A) == 2: hyung.append("·".join(bs & BRANCH_HYUNG_3A)+" 형")
    if bs & BRANCH_HYUNG_3B == BRANCH_HYUNG_3B: hyung.append("축-술-미(무은지형)")
    elif len(bs & BRANCH_HYUNG_3B) == 2: hyung.append("·".join(bs & BRANCH_HYUNG_3B)+" 형")
    if len(bs & BRANCH_HYUNG_2) == 2: hyung.append("자-묘(무례지형)")
    for b in brs:
        if b in BRANCH_HYUNG_SELF: hyung.append(f"{b} 자형")
    for (grp,oh) in BRANCH_SAMHAP:
        inter = grp & bs
        if len(inter) >= 2: samhap.append(f"{'·'.join(sorted(inter,key=EARTHLY_BRANCHES.index))} 삼합({oh})")
    for (grp,oh) in BRANCH_BANGHAP:
        if len(grp & bs) >= 3: banghap.append(f"{'·'.join(sorted(grp&bs,key=EARTHLY_BRANCHES.index))} 방합({oh})")
    return {"6합":hap6,"삼합":samhap,"방합":banghap,"충":chung,"형":hyung,"파":pa,"해":hae,"원진":wonjin}

def calc_12sisal(year_branch: str, pillars: dict) -> list:
    start = SISAL_12_START.get(year_branch,"자")
    si    = EARTHLY_BRANCHES.index(start)
    sb    = [EARTHLY_BRANCHES[(si+i)%12] for i in range(12)]
    all_b = [pillars[p]["branch"] for p in PILLAR_KEYS]
    return [{"name":n,"branch":sb[i],"active":sb[i] in all_b,"count":all_b.count(sb[i]),"desc":SISAL_12_DESC[i]} for i,n in enumerate(SISAL_12_NAMES)]

def calc_yukguk(ilgan: str, month_branch: str) -> str:
    sik = get_sikshin(ilgan, BRANCH_MAIN_GI[month_branch])
    return {"비견":"건록격(建祿格)","겁재":"양인격(羊刃格)","식신":"식신격(食神格)","상관":"상관격(傷官格)","편재":"편재격(偏財格)","정재":"정재격(正財格)","편관":"편관격(偏官格)","정관":"정관격(正官格)","편인":"편인격(偏印格)","정인":"정인격(正印格)"}.get(sik,"잡격")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE C  동적 변수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_daeun(pillars: dict, gender: str, birth_year: int) -> list:
    ms = HEAVENLY_STEMS.index(pillars["month"]["stem"])
    mb = EARTHLY_BRANCHES.index(pillars["month"]["branch"])
    ys = HEAVENLY_STEMS.index(pillars["year"]["stem"])
    fwd = ((ys%2==0) and gender=="남성") or ((ys%2!=0) and gender=="여성")
    result = []
    for i in range(10):
        d = 1 if fwd else -1
        si = (ms + d*(i+1)) % 10;  bi = (mb + d*(i+1)) % 12
        st = HEAVENLY_STEMS[si];   br = EARTHLY_BRANCHES[bi]
        result.append({"stem":st,"branch":br,"age":3+i*10,
                        "stem_oh":STEM_OHAENG[st],"branch_oh":BRANCH_OHAENG[br],
                        "naeum":get_naeum(st,br)[0],"fortune":get_twelve_fortune(pillars["day"]["stem"],br)})
    return result

def calc_weolun(year: int) -> list:
    yst = HEAVENLY_STEMS[(year-4)%10]
    base = {"갑":2,"을":4,"병":6,"정":8,"무":10,"기":12,"경":14,"신":16,"임":18,"계":20}[yst]
    result = []
    for m in range(1,13):
        st = HEAVENLY_STEMS[(base+m-1)%10];  br = EARTHLY_BRANCHES[(m+1)%12]
        result.append({"month":m,"stem":st,"branch":br,"stem_oh":STEM_OHAENG[st],"branch_oh":BRANCH_OHAENG[br]})
    return result

def calc_seun_interaction(pillars: dict, seun: dict) -> dict:
    ss,sb = seun["stem"],seun["branch"]
    all_s = [pillars[p]["stem"]   for p in PILLAR_KEYS]
    all_b = [pillars[p]["branch"] for p in PILLAR_KEYS]
    conflicts,supports = [],[]
    for b in all_b:
        if (sb,b) in BRANCH_CHUNG or (b,sb) in BRANCH_CHUNG: conflicts.append(f"세운 {sb} ↔ 원국 {b} 충(沖)")
        if (sb,b) in BRANCH_HAP_6 or (b,sb) in BRANCH_HAP_6: supports.append(f"세운 {sb} ↔ 원국 {b} 합(合)")
    for st in all_s:
        key = frozenset([ss,st])
        if key in STEM_HAP: supports.append(f"세운 {ss} ↔ 원국 {st} 천간합→{STEM_HAP[key]}")
    return {"충":conflicts,"합":supports}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE D  성명학 + 풍수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_suri81(strokes: list) -> dict:
    if len(strokes) == 3:
        s,n1,n2 = strokes
        nums = {"원격":n1%81 or 81,"형격":(s+n1)%81 or 81,"이격":(n1+n2)%81 or 81,"정격":(s+n1+n2)%81 or 81}
    elif len(strokes) == 2:
        s,n1 = strokes
        nums = {"원격":n1%81 or 81,"형격":(s+n1)%81 or 81,"이격":n1%81 or 81,"정격":(s+n1)%81 or 81}
    else:
        return {}
    result = {}
    for guk,num in nums.items():
        gh,desc = SUREE_81.get(num, ("?","?"))
        result[guk] = {"수":num,"길흉":gh,"의미":desc}
    return result

def calc_myeonggung(birth_year: int, gender: str) -> int:
    yy = birth_year % 100 or 100
    val = (100-yy)%9 if gender=="남성" else (yy+5)%9
    return val or 9

def get_fengshui(myeonggung: int) -> dict:
    idx = myeonggung if myeonggung != 5 else 2
    return {"본명궁":myeonggung,"괘명":MYEONGGUNG_MAP.get(myeonggung,"?"),"사택":"동사택" if myeonggung in DONG_SAHTAEK else "서사택","8방위":PALGAE_GILHUNG.get(idx,{})}

def get_samsal_daejang(current_year: int) -> dict:
    yb = EARTHLY_BRANCHES[(current_year-4)%12]
    return {"년지":yb,"삼살방":SAMSAL_MAP.get(yb,"?"),"대장군방":DAEJANGGUN_MAP.get(yb,"?"),"이사주의":f"삼살방({SAMSAL_MAP.get(yb,'?')})과 대장군방({DAEJANGGUN_MAP.get(yb,'?')}) 방향은 이사·수리 주의"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE E  조후·용신
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_johu(month_branch: str, ohaeng_score: dict) -> dict:
    info  = JOHU_MAP.get(month_branch, {})
    need  = info.get("need", [])
    total = sum(ohaeng_score.values()) or 1
    return {**info, "fulfilled":[oh for oh in need if ohaeng_score.get(oh,0)/total >= 0.15], "lacking":[oh for oh in need if ohaeng_score.get(oh,0)/total < 0.15]}

def calc_yongshin(ilgan_oh: str, self_ratio: float) -> dict:
    if self_ratio >= 0.38:
        yong,hee,ki,han,gu = OH_克_BY[ilgan_oh],OH_克[ilgan_oh],OH_生_BY[ilgan_oh],ilgan_oh,OH_生[ilgan_oh]; strength="신강(身强)"
    elif self_ratio <= 0.22:
        yong,hee,ki,han,gu = OH_生_BY[ilgan_oh],ilgan_oh,OH_克_BY[ilgan_oh],OH_克[ilgan_oh],OH_生[ilgan_oh]; strength="신약(身弱)"
    else:
        yong,hee,ki,han,gu = OH_克_BY[ilgan_oh],OH_生_BY[ilgan_oh],None,None,None; strength="중화(中和)"
    return {"용신":yong,"희신":hee,"기신":ki,"한신":han,"구신":gu,"강약":strength}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE F  직업·건강
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_career_health(ilgan_oh: str, yongshin: dict, ohaeng_score: dict) -> dict:
    yong = yongshin.get("용신", ilgan_oh)
    hee  = yongshin.get("희신", ilgan_oh)
    sorted_oh = sorted(ohaeng_score, key=ohaeng_score.get, reverse=True)
    weak = sorted_oh[-1];  strong = sorted_oh[0]
    career = list(dict.fromkeys(OHAENG_DETAIL[yong]["직업"][:4] + OHAENG_DETAIL[hee]["직업"][:3]))
    return {"추천직업":career,"건강주의":OHAENG_DETAIL[weak]["건강"],"건강강점":OHAENG_DETAIL[strong]["건강"],"행운색상":list(dict.fromkeys(OHAENG_DETAIL[yong]["색"]+OHAENG_DETAIL[hee]["색"]))[:3],"행운방위":OHAENG_DETAIL[yong]["방위"],"행운숫자":OHAENG_DETAIL[yong]["숫자"],"약한오행":weak,"강한오행":strong}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE G  귀인 & 특수신살 & 삼재
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_special_sisal(ilgan: str, pillars: dict) -> dict:
    all_br = [pillars[p]["branch"] for p in PILLAR_KEYS]
    bs = set(all_br)
    def check_br(target): return target in bs
    def check_br_list(targets): return [b for b in targets if b in bs]

    tianyigui = check_br_list(TIANYIGUI_MAP.get(ilgan,[]))
    munchang  = check_br(MUNCHANG_MAP.get(ilgan,""))
    hakdang   = check_br(HAKDANG_MAP.get(ilgan,""))
    amrok     = check_br(AMROK_MAP.get(ilgan,""))
    geunrok   = check_br(GEUNROK_MAP.get(ilgan,""))
    yangyin   = check_br(YANGYIN_MAP.get(ilgan,""))

    return {
        "천을귀인": {"active": len(tianyigui)>0, "branches": tianyigui, "desc":"하늘의 도움, 귀인 만남. 어려울 때 도움 받는 복."},
        "문창귀인": {"active": munchang, "branch": MUNCHANG_MAP.get(ilgan,""), "desc":"총명함·학문·문예 재능. 수험·창작에 유리."},
        "학당귀인": {"active": hakdang, "branch": HAKDANG_MAP.get(ilgan,""), "desc":"학업·명예 복. 교육·연구 분야 적합."},
        "암록":     {"active": amrok,   "branch": AMROK_MAP.get(ilgan,""),   "desc":"숨어있는 록(祿), 꼭 필요할 때 나타나는 복."},
        "건록":     {"active": geunrok, "branch": GEUNROK_MAP.get(ilgan,""), "desc":"직업·재물이 안정적. 강한 자립심."},
        "양인":     {"active": yangyin, "branch": YANGYIN_MAP.get(ilgan,""), "desc":"강한 의지와 투쟁심. 전문직·기술직에 유리하나 칠살과 충하면 주의."},
    }

def check_samjae(birth_year: int, current_year: int) -> dict:
    year_b = EARTHLY_BRANCHES[(birth_year-4)%12]
    cur_b  = EARTHLY_BRANCHES[(current_year-4)%12]
    sj_brs = SAMJAE_MAP.get(year_b, [])
    if cur_b in sj_brs:
        idx = sj_brs.index(cur_b)
        return {"in_samjae":True,"phase":["입삼재(入三災)","중삼재(中三災)","출삼재(出三災)"][idx],"year_branch":cur_b,"desc":"삼재 기간에는 큰 변화, 이동, 투자를 피하고 몸가짐을 조심하세요."}
    next_y = current_year + 1;  next_b = EARTHLY_BRANCHES[(next_y-4)%12]
    if next_b in sj_brs:
        return {"in_samjae":False,"upcoming":True,"desc":f"내년({next_y}년)부터 입삼재가 시작됩니다. 미리 대비하세요."}
    return {"in_samjae":False,"upcoming":False}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE H  육친 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_yukchins(pillars: dict, ilgan: str, gender: str, relations: dict) -> dict:
    yk_map = YUKCHINS_MALE if gender == "남성" else YUKCHINS_FEMALE
    result = {}
    all_chung = set()
    for c in relations.get("충", []):
        parts = c.split("-")
        all_chung.update(parts)

    for p in PILLAR_KEYS:
        st = pillars[p]["stem"];  br = pillars[p]["branch"]
        sik_s  = get_sikshin(ilgan, st) if st != ilgan else "일간"
        sik_b  = get_sikshin(ilgan, BRANCH_MAIN_GI[br])
        chung_warn = br in all_chung

        if p == "day":
            yukchins_str = ("처(妻)" if gender=="남성" else "남편(夫)") + f" 궁 / 십성: {sik_b}"
        else:
            ukc_s = yk_map.get(sik_s, "")
            ukc_b = yk_map.get(sik_b, "")
            yukchins_str = f"천간({sik_s}:{ukc_s}) / 지지({sik_b}:{ukc_b})"

        result[p] = {
            "label": PILLAR_YUKCHINS_LABEL[p],
            "stem_sikshin": sik_s, "branch_sikshin": sik_b,
            "yukchins": yukchins_str,
            "chung_warn": chung_warn,
            "fortune": get_twelve_fortune(ilgan, br),
        }
    return result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE I  궁합 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_goonghap(r1: dict, r2: dict) -> dict:
    """심층 궁합 분석 - 8개 영역 종합 평가"""
    name1 = r1["meta"]["name"]; name2 = r2["meta"]["name"]
    oh1 = r1["ohaeng_score"];  oh2 = r2["ohaeng_score"]
    t1  = sum(oh1.values()) or 1;  t2 = sum(oh2.values()) or 1
    score = 50
    complementary, conflict_ohs = [], []
    detail_oh = []  # 오행별 상세 분석
    for oh in ["목","화","토","금","수"]:
        rt1 = oh1[oh]/t1;  rt2 = oh2[oh]/t2
        if rt1 < 0.15 and rt2 > 0.28:
            complementary.append(f"{oh}({name2}이 보완)")
            detail_oh.append(f"✦ {oh}: {name1} 부족({rt1*100:.0f}%), {name2}({rt2*100:.0f}%)이 채워줌")
            score += 5
        elif rt2 < 0.15 and rt1 > 0.28:
            complementary.append(f"{oh}({name1}이 보완)")
            detail_oh.append(f"✦ {oh}: {name2} 부족({rt2*100:.0f}%), {name1}({rt1*100:.0f}%)이 채워줌")
            score += 5
        elif rt1 > 0.35 and rt2 > 0.35:
            conflict_ohs.append(f"{oh}(양쪽 과다)")
            detail_oh.append(f"⚠ {oh}: 양쪽 모두 강함({rt1*100:.0f}%, {rt2*100:.0f}%) — 같은 영역서 충돌 가능")
            score -= 3
        elif rt1 < 0.10 and rt2 < 0.10:
            detail_oh.append(f"△ {oh}: 양쪽 모두 약함 — 이 분야 보완 필요")
            score -= 2

    # 일지 관계
    db1 = r1["pillars"]["day"]["branch"];  db2 = r2["pillars"]["day"]["branch"]
    db1_oh = BRANCH_OHAENG[db1]; db2_oh = BRANCH_OHAENG[db2]
    day_rel = "중립"
    day_rel_desc = "특별한 합·충 관계 없이 평범. 서로 무난히 적응 가능"
    if (db1,db2) in BRANCH_HAP_6 or (db2,db1) in BRANCH_HAP_6:
        day_rel = "6합(合) ✦ 천생연분"
        day_rel_desc = "두 배우자궁이 결합. 자연스러운 끌림, 부부 금실 좋고 장수 인연. 부드러운 사랑"
        score += 20
    elif (db1,db2) in BRANCH_CHUNG or (db2,db1) in BRANCH_CHUNG:
        day_rel = "충(沖) ⚠ 갈등"
        day_rel_desc = "정면 충돌. 서로 강하게 끌리지만 자주 부딪힘. 만남이 짧거나 굴곡이 큼. 서로 다른 영역에서 활동하면 완화"
        score -= 15
    elif (db1,db2) in BRANCH_WONJIN or (db2,db1) in BRANCH_WONJIN:
        day_rel = "원진(怨嗔) ⚠ 서로 불편"
        day_rel_desc = "겉으로는 잘 지내지만 속으로 미묘한 거부감. 사소한 일에 짜증·오해 자주 발생"
        score -= 8
    elif (db1,db2) in BRANCH_HAE or (db2,db1) in BRANCH_HAE:
        day_rel = "해(害) ⚠ 상해"
        day_rel_desc = "서로의 약점을 건드림. 한쪽이 다른 쪽에게 상처주기 쉬움"
        score -= 6
    elif (db1,db2) in BRANCH_PA or (db2,db1) in BRANCH_PA:
        day_rel = "파(破) ⚠ 깨짐"
        day_rel_desc = "약속·계획이 자주 어긋남. 함께한 일이 흐지부지되기 쉬움"
        score -= 5
    else:
        for (grp,oh) in BRANCH_SAMHAP:
            if db1 in grp and db2 in grp:
                day_rel = f"삼합({oh}국) ✦ 깊은 인연"
                day_rel_desc = f"두 일지가 {oh} 기운을 강하게 만듦. 공동 목표 달성에 시너지. 사업·동업 적합"
                score += 12
                break
        else:
            for (grp,oh) in BRANCH_BANGHAP:
                if db1 in grp and db2 in grp:
                    day_rel = f"방합({oh}국) ✦ 계절 동지"
                    day_rel_desc = f"같은 계절({oh}) 기운. 가치관·생활리듬 비슷"
                    score += 8
                    break

    # 일간 관계 (십성 기준)
    ilgan1 = r1["ilgan"]["stem"];  ilgan2 = r2["ilgan"]["stem"]
    sik_12 = get_sikshin(ilgan1, ilgan2)
    sik_21 = get_sikshin(ilgan2, ilgan1)
    stem_key = frozenset([ilgan1, ilgan2])
    stem_hap_res = STEM_HAP.get(stem_key)
    stem_hap_desc = ""
    if stem_hap_res:
        stem_hap_desc = f"두 일간이 합쳐 {stem_hap_res} 기운 생성 — 강한 끌림과 결속"
        score += 15

    # 십성 관계 해석
    sikshin_desc = {
        "비견": "친구·동료 같은 관계. 자존심 부딪힘 주의",
        "겁재": "경쟁자 관계. 재물 다툼 가능",
        "식신": "편안하고 다정한 관계. 잘 표현해줌",
        "상관": "재능 자극하지만 자유로워 불안정",
        "편재": "활기차고 사업 파트너 적합",
        "정재": "안정적·신뢰. 결혼에 가장 좋음",
        "편관": "엄격·도전 자극. 강한 영향력",
        "정관": "존경·도덕적 관계. 모범적 부부",
        "편인": "독특한 매력·정신적 유대",
        "정인": "따뜻한 보살핌. 어머니 같은 사랑",
        "일간": "같은 일간 — 매우 닮은 영혼",
    }
    sik_12_desc = sikshin_desc.get(sik_12, "")
    sik_21_desc = sikshin_desc.get(sik_21, "")

    # 용신 상호작용
    yong1 = r1["yongshin"]["용신"];  yong2 = r2["yongshin"]["용신"]
    il1_oh = STEM_OHAENG[ilgan1];   il2_oh = STEM_OHAENG[ilgan2]
    yong_desc = []
    if il2_oh == yong1:
        score += 10
        yong_desc.append(f"✦ {name2}({il2_oh})이 {name1}의 용신({yong1})과 일치 — 큰 도움")
    if il1_oh == yong2:
        score += 10
        yong_desc.append(f"✦ {name1}({il1_oh})이 {name2}의 용신({yong2})과 일치 — 큰 도움")
    if not yong_desc:
        yong_desc.append("용신 직접 일치는 없음 — 일상적 보완 위주")

    # 격국 결합 분석
    yukguk1 = r1["yukguk"]; yukguk2 = r2["yukguk"]
    yukguk_desc = f"{name1}: {yukguk1} / {name2}: {yukguk2}"

    # 종합 점수 및 등급
    score = max(0, min(100, score))
    if score >= 85:
        grade = "천생연분(天生緣分) ♥♥♥"
        grade_color = "#2e7d32"
        overall = f"하늘이 맺어준 인연. 깊이 사랑하고 오래갈 관계. 서로의 빈 부분을 채우는 완벽한 조합."
    elif score >= 70:
        grade = "좋은 인연 ✦✦"
        grade_color = "#558b2f"
        overall = "서로 잘 맞는 좋은 관계. 작은 갈등은 있어도 노력하면 평생 동반자가 될 수 있는 인연."
    elif score >= 55:
        grade = "무난한 관계 ◯"
        grade_color = "#b8860b"
        overall = "특별한 끌림은 적지만 큰 충돌도 없는 무난한 관계. 서로 노력하면 좋은 동반자."
    elif score >= 40:
        grade = "주의가 필요한 인연 △"
        grade_color = "#e65100"
        overall = "맞지 않는 부분이 많아 자주 부딪힐 수 있음. 서로의 차이를 인정하고 배려가 필수."
    else:
        grade = "신중히 고려 ⚠"
        grade_color = "#c62828"
        overall = "근본적으로 다른 두 사람. 만나도 자주 갈등. 결혼·동업은 매우 신중히."

    # 강점·약점 정리
    strengths = []
    weaknesses = []
    if "천생연분" in day_rel or "삼합" in day_rel:
        strengths.append(f"💎 배우자궁 합 — {day_rel}")
    if stem_hap_res:
        strengths.append(f"💎 일간 천간합 → {stem_hap_res} 기운 생성")
    if complementary:
        strengths.append(f"💎 오행 보완: {', '.join(complementary)}")
    if yong_desc and "✦" in yong_desc[0]:
        strengths.append(f"💎 {yong_desc[0].replace('✦ ', '')}")

    if "충" in day_rel or "원진" in day_rel:
        weaknesses.append(f"⚠ {day_rel} — {day_rel_desc}")
    if conflict_ohs:
        weaknesses.append(f"⚠ 오행 과다 충돌: {', '.join(conflict_ohs)}")

    # 권장사항 (점수·관계별 맞춤 조언)
    advice = []
    if score >= 70:
        advice.append("✓ 적극적으로 관계 발전 추천")
        advice.append("✓ 함께 새로운 일 시도해도 좋은 시기")
    elif score >= 55:
        advice.append("✓ 자주 대화하고 서로의 가치관 이해 노력")
        advice.append("✓ 공통의 취미·활동으로 거리 좁히기")
    else:
        advice.append("⚠ 결혼·동업 등 큰 결정은 천천히")
        advice.append("⚠ 서로의 영역 존중하고 거리 두기")

    # 충 있을 때 완화법
    if "충" in day_rel:
        advice.append("💡 충 완화법: 서로 다른 일·취미·시간대 활동하면 갈등 ↓")
    if "원진" in day_rel:
        advice.append("💡 원진 완화법: 솔직한 대화, 묵은 감정 빠르게 풀기")

    # 가족 관계 조언
    family_advice = ""
    if score >= 70:
        family_advice = "함께 사는 데 무리 없음. 좋은 영향 주고받음."
    elif score >= 55:
        family_advice = "공간·시간 분리하면 평화로움. 서로 간섭 줄이기."
    else:
        family_advice = "같은 공간에서 자주 부딪힘. 각자 영역 확보 필수."

    return {
        "score": score, "grade": grade, "grade_color": grade_color,
        "overall": overall,
        "오행보완": complementary, "오행충돌": conflict_ohs,
        "오행상세": detail_oh,
        "일지관계": day_rel, "일지해설": day_rel_desc,
        "1이2보는십성": sik_12, "1이2보는십성해설": sik_12_desc,
        "2가1보는십성": sik_21, "2가1보는십성해설": sik_21_desc,
        "천간합": f"→{stem_hap_res}" if stem_hap_res else "없음",
        "천간합해설": stem_hap_desc,
        "용신1": yong1, "용신2": yong2, "용신상호작용": yong_desc,
        "격국비교": yukguk_desc,
        "강점": strengths, "약점": weaknesses,
        "권장사항": advice,
        "가족조언": family_advice,
        "name1": name1, "name2": name2,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE J  택일 (일진 계산)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_monthly_ilgin(year: int, month: int) -> list:
    days_in_month = calendar.monthrange(year, month)[1]
    epoch = date(1900,1,1)
    result = []
    weekdays = ["월","화","수","목","금","토","일"]
    for d in range(1, days_in_month+1):
        delta = (date(year,month,d) - epoch).days
        ds = (delta+10)%10;  db = (delta+10)%12
        wd = date(year,month,d).weekday()
        result.append({"day":d,"stem":HEAVENLY_STEMS[ds],"branch":EARTHLY_BRANCHES[db],"stem_oh":STEM_OHAENG[HEAVENLY_STEMS[ds]],"branch_oh":BRANCH_OHAENG[EARTHLY_BRANCHES[db]],"weekday":weekdays[wd],"weekday_idx":wd})
    return result

def rate_ilgin_day(ilgan: str, day_branch: str, purpose: str = "일반") -> str:
    day_b = day_branch
    ilgan_b = STEM_BIRTH_BRANCH.get(ilgan,"해")
    # 건록일 = 매우 좋음
    if day_b == GEUNROK_MAP.get(ilgan,""): return "대길"
    # 합일 = 좋음
    for (a,b) in BRANCH_HAP_6:
        if (ilgan_b == a and day_b == b) or (ilgan_b == b and day_b == a): return "길"
    # 충일 = 나쁨
    for (a,b) in BRANCH_CHUNG:
        if (ilgan_b == a and day_b == b) or (ilgan_b == b and day_b == a): return "흉"
    # 양인일 = 조심
    if day_b == YANGYIN_MAP.get(ilgan,""): return "흉"
    # 삼합 = 좋음
    for (grp,oh) in BRANCH_SAMHAP:
        if ilgan_b in grp and day_b in grp: return "길"
    return "보통"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE K  서양 별자리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_zodiac(month: int, day: int) -> dict:
    for sm,sd,em,ed,name,en,elem,oh,desc in ZODIAC_TABLE:
        if sm < em:
            if (month == sm and day >= sd) or (month == em and day <= ed): return {"name":name,"en":en,"element":elem,"ohaeng":oh,"desc":desc}
        else:
            if (month == sm and day >= sd) or (month == em and day <= ed): return {"name":name,"en":en,"element":elem,"ohaeng":oh,"desc":desc}
    return {"name":"?","en":"?","element":"?","ohaeng":"?","desc":""}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE L  사주 종합 점수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def calc_saju_score(result: dict) -> dict:
    score = 50.0
    # 십이운성 평균
    fort_scores = [FORTUNE_SCORE.get(result["all_fortune"][p],50) for p in PILLAR_KEYS]
    fort_avg    = sum(fort_scores)/4
    score += (fort_avg - 60) * 0.15

    # 합충 점수
    rel = result["relations"]
    score += len(rel.get("6합",[])) * 4
    score += len(rel.get("삼합",[])) * 6
    score += len(result.get("stem_hap",[])) * 3
    score -= len(rel.get("충",[])) * 5
    score -= len(rel.get("형",[])) * 4
    score -= len(rel.get("파",[])) * 2

    # 용신 오행 강도
    yong_oh = result["yongshin"].get("용신","")
    if yong_oh:
        total  = sum(result["ohaeng_score"].values()) or 1
        yr     = result["ohaeng_score"].get(yong_oh,0)/total
        score += (yr - 0.2) * 30

    # 귀인 활성
    ssisal = result.get("special_sisal",{})
    for k,v in ssisal.items():
        if v.get("active"): score += 3

    # 격국 길흉 보정
    yukguk = result.get("yukguk","")
    if "정관격" in yukguk or "정재격" in yukguk or "식신격" in yukguk: score += 8
    elif "편관격" in yukguk or "양인격" in yukguk: score += 2

    score = max(5, min(98, score))
    if score >= 85: grade="상상(上上) ✦ 매우 빼어난 사주"
    elif score >= 70: grade="상중(上中) ✦ 훌륭한 사주"
    elif score >= 55: grade="중상(中上) — 좋은 편"
    elif score >= 40: grade="중하(中下) — 노력이 필요"
    else: grade="하하(下下) — 큰 노력 필요"

    return {"score":round(score,1),"grade":grade,"fort_avg":round(fort_avg),"합수":len(rel.get("6합",[]))+len(rel.get("삼합",[])), "충형수":len(rel.get("충",[]))+len(rel.get("형",[]))}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# INTEGRATED JSON BUILDER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_saju_result(year: int, month: int, day: int, hour: int, gender: str, name: str, hanja_name: str = "") -> dict:
    pillars   = solar_to_ganjee(year,month,day,hour)
    ilgan_s   = pillars["day"]["stem"];   ilgan_b = pillars["day"]["branch"]
    ilgan_oh  = STEM_OHAENG[ilgan_s];    month_b = pillars["month"]["branch"]
    ohaeng    = calc_ohaeng_score(pillars)
    total_oh  = sum(ohaeng.values()) or 1;  self_ratio = ohaeng[ilgan_oh]/total_oh
    gongmang  = get_gongmang(ilgan_s, ilgan_b)
    all_sik   = calc_all_sikshin(pillars, ilgan_s)
    all_fort  = calc_all_fortune(pillars, ilgan_s)
    all_naeum = {p:get_naeum(pillars[p]["stem"],pillars[p]["branch"]) for p in PILLAR_KEYS}
    stem_hap  = detect_stem_hap(pillars)
    relations = detect_branch_relations(pillars)
    sisal_12  = calc_12sisal(pillars["year"]["branch"], pillars)
    yukguk    = calc_yukguk(ilgan_s, month_b)
    daeun     = calc_daeun(pillars, gender, year)
    seun_now  = get_year_ganzi(datetime.now().year)
    weolun    = calc_weolun(datetime.now().year)
    seun_inter= calc_seun_interaction(pillars, seun_now)
    johu      = calc_johu(month_b, ohaeng)
    yongshin  = calc_yongshin(ilgan_oh, self_ratio)
    myeonggung= calc_myeonggung(year, gender)
    fengshui  = get_fengshui(myeonggung)
    samsal    = get_samsal_daejang(datetime.now().year)
    career    = get_career_health(ilgan_oh, yongshin, ohaeng)
    ssisal    = calc_special_sisal(ilgan_s, pillars)
    samjae    = check_samjae(year, datetime.now().year)
    yukchins  = calc_yukchins(pillars, ilgan_s, gender, relations)
    zodiac    = get_zodiac(month, day)

    r = {
        "meta":        {"name":name,"gender":gender,"birth":f"{year}-{month:02d}-{day:02d} {hour:02d}:00"},
        "pillars":     pillars,
        "ilgan":       {"stem":ilgan_s,"branch":ilgan_b,"ohaeng":ilgan_oh,"naeum":get_naeum(ilgan_s,ilgan_b)[0],"twelve_fortune":get_twelve_fortune(ilgan_s,ilgan_b)},
        "gongmang":    gongmang,
        "ohaeng_score":ohaeng,
        "self_ratio_pct": round(self_ratio*100,1),
        "yukguk":      yukguk,
        "all_sikshin": all_sik,
        "all_fortune": all_fort,
        "all_naeum":   {p:{"name":v[0],"oh":v[1]} for p,v in all_naeum.items()},
        "stem_hap":    stem_hap,
        "relations":   relations,
        "sisal_12":    sisal_12,
        "daeun":       daeun,
        "seun_now":    seun_now,
        "seun_interaction": seun_inter,
        "weolun":      weolun,
        "johu":        johu,
        "yongshin":    yongshin,
        "fengshui":    fengshui,
        "samsal":      samsal,
        "career_health":career,
        "special_sisal":ssisal,
        "samjae":      samjae,
        "yukchins":    yukchins,
        "zodiac":      zodiac,
    }
    r["saju_score"] = calc_saju_score(r)

    # Module N: 이름 오행 분석
    balam  = calc_balam_ohaeng(name)
    jawon  = calc_jawon_ohaeng(hanja_name) if hanja_name else []
    r["name_analysis"] = {
        "korean_name":  name,
        "hanja_name":   hanja_name,
        "balam_ohaeng": balam,
        "jawon_ohaeng": jawon,
        "harmony": calc_name_saju_harmony(balam, jawon, yongshin, ohaeng) if (balam or jawon) else {},
    }
    return r



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE N  이름 오행 분석 (발음오행 + 자원오행)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 초성(받침 제외) → 발음오행
CHOSONG_OHAENG = {
    "ㄱ":"목","ㅋ":"목",
    "ㄴ":"화","ㄷ":"화","ㄹ":"화","ㅌ":"화",
    "ㅇ":"토","ㅎ":"토",
    "ㅅ":"금","ㅆ":"금","ㅈ":"금","ㅉ":"금","ㅊ":"금",
    "ㅁ":"수","ㅂ":"수","ㅃ":"수","ㅍ":"수",
    "ㄲ":"목","ㄸ":"화","ㅀ":"화",
}
CHOSONG_LIST = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"]

# 주요 한자 자원오행 사전 (성명에 자주 쓰이는 한자 500자 핵심)
HANJA_OHAENG = {
    # 목(木) 계열
    "木":"목","林":"목","森":"목","松":"목","柳":"목","桂":"목","楠":"목","栗":"목",
    "樹":"목","植":"목","根":"목","枝":"목","葉":"목","花":"목","草":"목","蘭":"목",
    "東":"목","春":"목","仁":"목","甲":"목","寅":"목","卯":"목","甫":"목","模":"목",
    "泰":"목","大":"목","太":"목","元":"목","基":"목","起":"목","昇":"목","成":"목",
    "聖":"목","勝":"목","相":"목","碩":"목","善":"목","宣":"목","先":"목","建":"목",
    "健":"목","彦":"목","賢":"목","現":"목","炫":"목","玄":"목","翰":"목","翼":"목",
    # 화(火) 계열
    "火":"화","炎":"화","炳":"화","燦":"화","烈":"화","熙":"화","赫":"화","焄":"화",
    "南":"화","夏":"화","丙":"화","午":"화","巳":"화","丁":"화","禮":"화","文":"화",
    "光":"화","明":"화","映":"화","星":"화","晶":"화","昊":"화","日":"화","曜":"화",
    "旭":"화","炫":"화","煥":"화","燁":"화","熙":"화","赫":"화","顯":"화","彰":"화",
    "彦":"화","英":"화","榮":"화","永":"화","寧":"화","美":"화","俊":"화","峻":"화",
    # 토(土) 계열
    "土":"토","地":"토","坤":"토","山":"토","岳":"토","堅":"토","基":"토","培":"토",
    "中":"토","央":"토","戊":"토","己":"토","辰":"토","戌":"토","丑":"토","未":"토",
    "信":"토","誠":"토","實":"토","重":"토","廣":"토","博":"토","厚":"토","德":"토",
    "道":"토","義":"토","泰":"토","安":"토","定":"토","靜":"토","穩":"토","豊":"토",
    "鎬":"토","昌":"토","昱":"토","旼":"토","暎":"토","景":"토","晟":"토","晉":"토",
    # 금(金) 계열
    "金":"금","鐵":"금","鋼":"금","銀":"금","銅":"금","錫":"금","珠":"금","玉":"금",
    "西":"금","秋":"금","庚":"금","辛":"금","申":"금","酉":"금","義":"금","智":"금",
    "剛":"금","毅":"금","勇":"금","武":"금","强":"금","珍":"금","寶":"금","玹":"금",
    "鉉":"금","鎭":"금","錦":"금","鐘":"금","鍾":"금","銀":"금","鎬":"금","哲":"금",
    "吉":"금","洛":"금","樂":"금","嶺":"금","嵐":"금","峰":"금","峯":"금","鳳":"금",
    # 수(水) 계열
    "水":"수","海":"수","江":"수","河":"수","洋":"수","湖":"수","淸":"수","潤":"수",
    "北":"수","冬":"수","壬":"수","癸":"수","亥":"수","子":"수","知":"수","智":"수",
    "深":"수","源":"수","泉":"수","沿":"수","波":"수","瀚":"수","洪":"수","濟":"수",
    "浩":"수","澤":"수","淡":"수","淵":"수","淑":"수","泰":"수","汎":"수","汝":"수",
    "允":"수","允":"수","潤":"수","澔":"수","浚":"수","洋":"수","涵":"수","湧":"수",
}

def get_chosong(char: str) -> str:
    """한글 음절에서 초성 추출"""
    code = ord(char)
    if 0xAC00 <= code <= 0xD7A3:
        idx = (code - 0xAC00) // 28 // 21
        return CHOSONG_LIST[idx]
    return ""

def calc_balam_ohaeng(korean_name: str) -> list:
    """한글 이름 각 글자의 발음오행 반환"""
    result = []
    for ch in korean_name:
        cho = get_chosong(ch)
        if cho:
            oh = CHOSONG_OHAENG.get(cho, "")
            result.append({"char": ch, "chosong": cho, "ohaeng": oh})
    return result

def calc_jawon_ohaeng(hanja_name: str) -> list:
    """한자 이름 각 글자의 자원오행 반환"""
    result = []
    for ch in hanja_name:
        if ch.strip():
            oh = HANJA_OHAENG.get(ch, "")
            result.append({"char": ch, "ohaeng": oh or "?", "known": ch in HANJA_OHAENG})
    return result



# 한글 음절 → 가장 많이 쓰이는 한자 성씨/이름자 자동변환 매핑
# (한자 필드에 실수로 한글을 입력했을 때 도움 제공용)
HANGUL_TO_HANJA_COMMON = {
    "김":"金","이":"李","박":"朴","최":"崔","정":"鄭","강":"姜","조":"趙",
    "윤":"尹","장":"張","임":"林","한":"韓","오":"吳","서":"徐","신":"申",
    "권":"權","황":"黃","안":"安","송":"宋","류":"柳","유":"柳","홍":"洪",
    "고":"高","문":"文","양":"梁","성":"成","차":"車","허":"許","남":"南",
    "심":"沈","노":"盧","하":"河","전":"全","민":"旻","준":"俊","현":"玄",
    "진":"珍","수":"秀","영":"榮","철":"哲","길":"吉","동":"東","서":"書",
    "호":"浩","원":"元","경":"敬","태":"泰","명":"明","형":"炯","찬":"燦",
    "혁":"赫","선":"善","기":"基","승":"昇","우":"佑","건":"健","재":"在",
    "석":"碩","성":"聖","열":"烈","환":"煥","빈":"彬","혜":"惠","미":"美",
    "지":"智","희":"熙","은":"恩","연":"延","수":"修","린":"麟","봉":"鳳",
}

def normalize_hanja_input(raw: str) -> tuple:
    """한글→한자 자동변환. 반환: (정제문자열, 경고목록, 변환목록)"""
    import unicodedata as _ud
    result, warnings, converted = [], [], []
    for ch in raw.strip():
        if not ch.strip():
            continue
        # NFC 정규화 (입력 방식 차이 흡수)
        ch = _ud.normalize('NFC', ch)
        code = ord(ch)
        # 완성형 한글 음절 범위 (가-힣)
        if 0xAC00 <= code <= 0xD7A3:
            if ch in HANGUL_TO_HANJA_COMMON:
                hj = HANGUL_TO_HANJA_COMMON[ch]
                converted.append((ch, hj))
                warnings.append(f"'{ch}' → '{hj}'(으)로 자동 변환됨")
                result.append(hj)
            else:
                warnings.append(f"'{ch}'는 한글입니다. 해당 한자를 직접 입력하세요.")
                result.append(ch)
        else:
            result.append(ch)
    return "".join(result), warnings, converted

# 원획법(原劃法) 한자 획수 데이터베이스 — 한국 성명에 자주 쓰이는 800자
HANJA_STROKES = {
    # ── 성씨 ──
    "金":8,"李":7,"朴":6,"崔":11,"鄭":15,"姜":9,"趙":14,"尹":4,"張":11,"林":8,
    "韓":17,"吳":7,"徐":10,"申":5,"權":22,"黃":12,"安":6,"宋":7,"柳":9,"洪":9,
    "高":10,"梁":11,"成":7,"車":7,"許":11,"南":9,"沈":7,"盧":16,"丁":2,"河":8,
    "陳":16,"具":8,"文":4,"辛":7,"薛":17,"廉":13,"呂":7,"魚":11,"殷":10,"片":4,
    "秋":9,"嚴":20,"蔡":17,"元":4,"千":3,"方":4,"孔":4,"裵":14,"白":5,"明":8,
    "池":6,"武":8,"卞":4,"康":11,"曺":11,"玄":5,"馬":10,"孫":10,"周":8,"任":6,
    "鞠":17,"閔":12,"全":6,"羅":19,"諸":16,"劉":15,"陸":11,"邊":19,"楊":13,"皮":5,
    "甘":5,"咸":9,"強":12,"葛":12,"邦":7,"班":10,"歐":15,"龍":16,"甲":5,"乙":1,
    # ── 이름 — 목(木) 계열 ──
    "木":4,"林":8,"森":12,"松":8,"柳":9,"桂":10,"楠":13,"栗":10,"樹":16,"植":12,
    "根":10,"枝":8,"葉":12,"花":7,"草":9,"蘭":19,"東":8,"春":9,"仁":4,"基":11,
    "起":10,"昇":8,"成":7,"聖":13,"勝":12,"相":9,"碩":14,"善":12,"宣":9,"先":6,
    "建":9,"健":11,"彦":9,"賢":16,"現":11,"炫":9,"玄":5,"翰":16,"翼":17,"準":13,
    "俊":9,"竣":12,"埈":10,"晙":10,"模":14,"謨":16,"謀":16,"茂":8,"武":8,"懋":17,
    "旻":8,"旼":8,"旭":6,"旺":8,"昊":8,"昱":9,"昌":8,"晶":12,"晟":11,"晉":10,
    # ── 이름 — 화(火) 계열 ──
    "火":4,"炎":8,"炳":9,"燦":17,"烈":10,"熙":13,"赫":14,"南":9,"夏":10,"光":6,
    "明":8,"映":9,"星":9,"日":4,"曜":18,"炫":9,"煥":13,"燁":16,"顯":23,"彰":14,
    "彦":9,"英":8,"榮":14,"永":5,"寧":14,"美":9,"禮":18,"文":4,"炅":9,"炯":9,
    "熙":13,"禧":17,"曦":23,"曙":17,"曉":16,"朗":11,"朝":12,"晨":11,"曼":11,
    "昞":9,"昺":9,"炜":8,"炬":9,"熔":14,"燮":17,"燦":17,"烋":9,"煌":13,"燿":18,
    # ── 이름 — 토(土) 계열 ──
    "土":3,"地":6,"坤":8,"山":3,"岳":8,"堅":12,"培":11,"中":4,"央":5,"信":9,
    "誠":14,"實":14,"重":9,"廣":15,"博":12,"厚":9,"德":15,"道":13,"義":13,"安":6,
    "定":8,"靜":16,"穩":16,"豊":18,"昌":8,"昱":9,"旼":8,"暎":13,"景":12,"泰":10,
    "均":7,"坤":8,"垠":9,"坰":8,"垢":9,"城":10,"域":11,"在":6,"存":6,"地":6,
    "坦":8,"埈":10,"堯":12,"壽":14,"壯":7,"壁":16,"壇":17,"壙":19,"増":15,"堂":11,
    # ── 이름 — 금(金) 계열 ──
    "鐵":21,"鋼":16,"銀":14,"銅":14,"錫":16,"珠":10,"玉":5,"西":6,"秋":9,"義":13,
    "智":12,"剛":10,"毅":15,"勇":9,"武":8,"强":12,"珍":9,"寶":20,"玹":9,"鉉":11,
    "鎭":18,"錦":16,"鐘":20,"鍾":17,"哲":10,"吉":6,"洛":9,"樂":15,"嶺":17,"峰":10,
    "峯":10,"鳳":14,"秀":7,"秉":8,"秀":7,"稔":13,"穎":16,"禎":14,"祥":10,"祐":10,
    "祿":13,"禧":17,"祺":11,"禹":9,"祿":13,"福":13,"禎":14,"禹":9,"祚":10,"祿":13,
    "兌":7,"銓":14,"鑄":22,"鎔":18,"鎬":18,"鉦":13,"鈺":13,"鎌":17,"鏞":21,"鑫":24,
    # ── 이름 — 수(水) 계열 ──
    "水":4,"海":10,"江":6,"河":8,"洋":9,"湖":12,"淸":11,"潤":15,"知":8,"智":12,
    "深":11,"源":13,"泉":9,"波":8,"瀚":20,"濟":17,"浩":10,"澤":16,"淑":11,"允":4,
    "潤":15,"澔":16,"浚":10,"涵":11,"湧":12,"洙":9,"汎":6,"泳":8,"洵":9,"浣":10,
    "洪":9,"洞":9,"洛":9,"洵":9,"泰":10,"浩":10,"淵":11,"淡":11,"湜":13,"湛":12,
    "滿":14,"漢":14,"澈":16,"瀅":19,"潔":15,"澄":15,"清":11,"淨":11,"漪":14,"漸":14,
    # ── 기타 자주 쓰이는 이름자 ──
    "龍":16,"鳳":14,"麟":23,"龜":16,"鶴":21,"雄":12,"傑":12,"豪":14,"英":8,"雅":12,
    "正":5,"大":3,"太":4,"小":3,"長":8,"幸":8,"福":13,"善":12,"吉":6,"利":7,
    "才":3,"能":10,"能":10,"學":16,"文":4,"武":8,"詩":13,"書":10,"禮":18,"樂":15,
    "孝":7,"悌":10,"忠":8,"信":9,"義":13,"廉":13,"恥":10,"謙":17,"遜":13,"讓":24,
    "希":7,"望":11,"志":7,"夢":13,"想":13,"心":4,"思":9,"念":8,"恩":10,"愛":13,
    "情":11,"愉":12,"悅":10,"喜":12,"歡":22,"樂":15,"悠":11,"安":6,"寬":15,"泰":10,
    "亨":7,"利":7,"貞":9,"元":4,"亮":9,"俊":9,"傑":12,"才":3,"賢":16,"良":7,
    "佑":7,"佳":8,"佑":7,"侃":8,"倫":10,"偉":11,"倬":10,"傑":12,"僖":14,"儁":15,
    "光":6,"克":7,"冠":9,"凱":12,"凰":11,"勉":9,"勤":13,"勳":16,"匡":6,"卿":12,
    "厚":9,"吉":6,"同":6,"和":8,"哲":10,"嘉":14,"圓":13,"國":11,"圭":6,"在":6,
    "培":11,"基":11,"坤":8,"城":10,"堯":12,"庭":10,"廷":7,"弘":5,"強":12,"彬":10,
    "後":9,"德":15,"志":7,"愿":14,"慶":15,"憲":16,"懷":19,"承":8,"效":10,"敏":11,
    "敬":13,"數":15,"時":10,"曾":12,"朔":10,"朝":12,"格":10,"桓":10,"榮":14,"橋":16,
    "民":5,"氏":4,"求":7,"泰":10,"洙":9,"海":10,"淳":11,"煜":13,"璟":17,"瑞":13,
    "瑜":13,"瑾":14,"璃":15,"寶":20,"璇":16,"瑤":14,"珉":9,"珀":9,"珮":10,"珏":9,
    "相":9,"石":5,"磊":15,"磨":16,"祉":9,"種":14,"稀":12,"立":5,"竟":11,"章":11,
    "端":14,"精":14,"紀":9,"素":10,"綠":14,"維":14,"緯":15,"繁":17,"義":13,"翼":17,
    "聰":17,"肯":8,"能":10,"自":6,"至":6,"舜":13,"艾":6,"芳":7,"若":8,"茹":9,
    "萬":12,"葵":12,"蒼":13,"蓮":13,"藍":17,"虎":8,"蓉":13,"藏":18,"行":6,"衡":16,
    "補":12,"裕":12,"親":16,"觀":25,"規":11,"覺":20,"言":7,"誠":14,"謹":18,"豊":18,
    "賢":16,"賚":15,"贊":19,"起":10,"越":12,"逸":12,"遠":14,"道":13,"邦":7,"鄉":17,
    "鎬":18,"長":8,"開":12,"閏":10,"陶":16,"隆":12,"靖":13,"頌":13,"顯":23,"飛":9,
    "馨":20,"駿":17,"麗":19,"黎":15,"默":16,"齊":14,
}

def auto_strokes_from_hanja(hanja_name: str) -> dict:
    """한자 이름에서 원획법 획수 자동 계산."""
    import unicodedata as _ud
    # NFC 정규화로 입력 방식 차이 흡수
    chars   = [_ud.normalize('NFC', c) for c in hanja_name.strip() if c.strip()]
    missing = [c for c in chars if c not in HANJA_STROKES]
    strokes = [HANJA_STROKES.get(c, 0) for c in chars]
    return {"strokes": strokes, "chars": chars, "missing": missing, "auto": True}

def strokes_to_suri(strokes: list) -> dict:
    """획수 리스트 → 4격 81수리 (기존 calc_suri81 대체 가능)"""
    if len(strokes) == 3:
        s, n1, n2 = strokes
        nums = {"원격": n1%81 or 81, "형격": (s+n1)%81 or 81,
                "이격": (n1+n2)%81 or 81, "정격": (s+n1+n2)%81 or 81}
    elif len(strokes) == 2:
        s, n1 = strokes
        nums = {"원격": n1%81 or 81, "형격": (s+n1)%81 or 81,
                "이격": n1%81 or 81,  "정격": (s+n1)%81 or 81}
    elif len(strokes) >= 4:   # 4글자 이름 처리
        s, n1, n2, n3 = strokes[0], strokes[1], strokes[2], strokes[3]
        nums = {"원격": n1%81 or 81, "형격": (s+n1)%81 or 81,
                "이격": (n1+n2)%81 or 81, "정격": (s+n1+n2+n3)%81 or 81}
    else:
        return {}
    result = {}
    for guk, num in nums.items():
        gh, desc = SUREE_81.get(num, ("?","?"))
        result[guk] = {"수": num, "길흉": gh, "의미": desc}
    return result

def calc_name_saju_harmony(balam: list, jawon: list, yongshin: dict, ohaeng_score: dict) -> dict:
    """이름 오행과 사주의 보완·충돌 분석"""
    yong = yongshin.get("용신","")
    hee  = yongshin.get("희신","")
    ki   = yongshin.get("기신","")
    total = sum(ohaeng_score.values()) or 1
    weak_ohs = [oh for oh, s in ohaeng_score.items() if s/total < 0.15]

    name_ohs = [b["ohaeng"] for b in balam if b["ohaeng"]]
    name_ohs += [j["ohaeng"] for j in jawon if j["ohaeng"] not in ("","?")]

    supports, conflicts, neutrals = [], [], []
    for oh in name_ohs:
        if oh in (yong, hee):
            supports.append(oh)
        elif oh == ki:
            conflicts.append(oh)
        else:
            neutrals.append(oh)

    # 점수: 보완 +10, 충돌 -8, 부족오행 보완 +5
    score = 70
    score += len(supports) * 10
    score -= len(conflicts) * 8
    for oh in weak_ohs:
        if oh in name_ohs:
            score += 5
    score = max(0, min(100, score))

    if score >= 85:   grade = "✦ 매우 좋은 이름 — 사주를 강하게 보완"
    elif score >= 70: grade = "○ 좋은 이름 — 사주와 잘 어울림"
    elif score >= 55: grade = "△ 보통 — 큰 영향 없음"
    else:             grade = "⚠ 주의 — 사주 기신 오행이 이름에 많음"

    return {
        "score": score, "grade": grade,
        "supports": supports, "conflicts": conflicts,
        "weak_補完": [oh for oh in weak_ohs if oh in name_ohs],
    }



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LLM  slim 요약 + generate_llm_report
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def slim_saju_for_api(r: dict) -> str:
    """핵심 정보만 압축 텍스트로 변환 (토큰 절약)"""
    birth_year = int(r["meta"]["birth"][:4])
    cur_age    = datetime.now().year - birth_year
    cd = next((d for d in r["daeun"] if d["age"] <= cur_age < d["age"] + 10), r["daeun"][0])
    seun = r["seun_now"]
    ys   = r["yongshin"]
    ch   = r["career_health"]
    sj   = r.get("samjae", {})
    rel  = r["relations"]

    lines = [
        f"[기본] {r['meta']['name']} ({r['meta']['gender']}) · {r['meta']['birth']}",
        f"[일주] {r['ilgan']['stem']}{r['pillars']['day']['branch']} "
        f"({r['ilgan']['ohaeng']}·{r['ilgan']['twelve_fortune']}·납음 {r['ilgan']['naeum']})",
        f"[사주원국] 년={r['pillars']['year']['stem']}{r['pillars']['year']['branch']} "
        f"월={r['pillars']['month']['stem']}{r['pillars']['month']['branch']} "
        f"일={r['pillars']['day']['stem']}{r['pillars']['day']['branch']} "
        f"시={r['pillars']['hour']['stem']}{r['pillars']['hour']['branch']}",
        f"[오행점수] " + " ".join(f"{k}{v}" for k, v in r["ohaeng_score"].items()),
        f"[격국] {r['yukguk']} / {ys['강약']} (자력 {r['self_ratio_pct']}%)",
        f"[용신] 용={ys['용신']} 희={ys['희신']} 기={ys.get('기신','-')} 한={ys.get('한신','-')}",
        f"[공망] {' '.join(r['gongmang']) or '없음'}",
        f"[주요관계] 충={rel['충']} 합={rel['6합']} 삼합={rel['삼합']} 형={rel['형']}",
        f"[활성신살] {[s['name'] for s in r['sisal_12'] if s['active']]}",
        f"[귀인] {[k for k,v in r.get('special_sisal',{}).items() if v.get('active')]}",
        f"[삼재] {'현재 '+sj.get('phase','') if sj.get('in_samjae') else '없음'}",
        f"[현재대운] {cd['stem']}{cd['branch']} ({cd['age']}~세) · {cd['fortune']}",
        f"[세운] {seun['year']}년 {seun['stem']}{seun['branch']} "
        f"충={r['seun_interaction']['충']} 합={r['seun_interaction']['합']}",
        f"[직업적성] {ch['추천직업'][:4]}",
        f"[건강주의] {ch['건강주의'][:3]}",
        f"[종합점수] {r['saju_score']['score']}점 / {r['saju_score']['grade']}",
    ]
    na = r.get("name_analysis", {})
    if na.get("balam_ohaeng"):
        lines.append(f"[이름발음오행] " +
                     " ".join(f"{b['char']}({b['ohaeng']})" for b in na["balam_ohaeng"]))
    return "\n".join(lines)


def generate_llm_report(saju_json: dict, extra: str = ""):
    """심층 사주 분석 리포트 — 12개 영역 입체 해석"""
    import os
    api_key = (st.session_state.get("gemini_api_key_input", "") or
               os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key:
        raise ValueError("사이드바에 Gemini API 키를 입력해 주세요.")
    model_name = st.session_state.get("gemini_model", "gemini-2.5-flash-lite")
    genai.configure(api_key=api_key)

    # ── 데이터 추출 ──
    r = saju_json
    cur_year = datetime.now().year
    cur_month = datetime.now().month
    cur_age   = cur_year - int(r["meta"]["birth"][:4])

    # 현재 + 다음 대운
    cd = next((d for d in r["daeun"] if d["age"] <= cur_age < d["age"]+10), r["daeun"][0])
    next_d_idx = r["daeun"].index(cd) + 1 if cd in r["daeun"] else 0
    nd = r["daeun"][next_d_idx] if next_d_idx < len(r["daeun"]) else None

    # 3개년 세운
    seun_3y_list = []
    for o in range(0, 3):
        yg = get_year_ganzi(cur_year + o)
        # 일간 기준 십성
        sik = get_sikshin(r["ilgan"]["stem"], yg["stem"])
        seun_3y_list.append(f"{cur_year+o}년 {yg['stem']}{yg['branch']}({sik})")

    # 올해 월별 운(현재월부터 12개월)
    weolun_full = []
    for w in r["weolun"]:
        m = w["month"]
        if m >= cur_month:
            sik_s = get_sikshin(r["ilgan"]["stem"], w["stem"])
            weolun_full.append(f"{m}월 {w['stem']}{w['branch']}({sik_s})")
    weol_str = " / ".join(weolun_full[:8])  # 앞 8개월

    # 관계
    act_rel = {k:v for k,v in r["relations"].items() if v}
    rel_str = "; ".join(f"{k}:{','.join(v) if isinstance(v,list) else v}" for k,v in act_rel.items())

    # 귀인/신살
    act_guiin = [k for k,v in r.get("special_sisal",{}).items() if v.get("active")]
    act_sisal = [s["name"] for s in r.get("sisal_12",[]) if s.get("active")]

    # 삼재
    sj = r.get("samjae",{})
    samjae_str = ("진행중-" + sj.get("phase","")) if sj.get("in_samjae") else "해당없음"

    # 육친
    ykch = r.get("yukchins", {})
    spouse_warn = ykch.get("day", {}).get("chung_warn", False)

    # 통합 데이터 패키지
    core = f"""[기본 정보]
- 이름: {r["meta"]["name"]}, 성별: {r["meta"]["gender"]}, 생년월일: {r["meta"]["birth"]}
- 현재 나이: 만 {cur_age}세

[사주 원국]
- 년주: {r["pillars"]["year"]["stem"]}{r["pillars"]["year"]["branch"]}
- 월주: {r["pillars"]["month"]["stem"]}{r["pillars"]["month"]["branch"]}
- 일주: {r["pillars"]["day"]["stem"]}{r["pillars"]["day"]["branch"]} (★ 본인)
- 시주: {r["pillars"]["hour"]["stem"]}{r["pillars"]["hour"]["branch"]}
- 일간 오행: {r["ilgan"]["ohaeng"]}, 납음: {r["ilgan"]["naeum"]}, 십이운성: {r["ilgan"]["twelve_fortune"]}

[오행 균형]
- 점수: {json.dumps(r["ohaeng_score"], ensure_ascii=False)}
- 일간 자력 비율: {r["self_ratio_pct"]}%
- 강약: {r["yongshin"]["강약"]}

[격국과 용신]
- 격국: {r["yukguk"]}
- 용신(가장 필요한 기운): {r["yongshin"].get("용신","")}
- 희신(보조 기운): {r["yongshin"].get("희신","")}
- 기신(주의할 기운): {r["yongshin"].get("기신","")}

[조후(계절 균형)]
- 태어난 계절: {r["johu"].get("계절","")}
- 부족한 기운: {r["johu"].get("lacking",[])}
- 충족된 기운: {r["johu"].get("fulfilled",[])}

[관계성 — 합·충·형·해]
{rel_str if rel_str else "특별한 관계 없음"}

[현재 대운 ({cd['age']}~{cd['age']+9}세)]
- 간지: {cd["stem"]}{cd["branch"]}, 납음: {cd["naeum"]}, 십이운성: {cd["fortune"]}
{f"- 다음 대운 ({nd['age']}~{nd['age']+9}세): {nd['stem']}{nd['branch']}" if nd else ""}

[향후 3년 세운]
{" → ".join(seun_3y_list)}

[올해 월별 흐름 (현재 {cur_month}월 ~ 향후 8개월)]
{weol_str}

[귀인·신살]
- 활성 귀인: {", ".join(act_guiin) if act_guiin else "없음"}
- 활성 12신살: {", ".join(act_sisal) if act_sisal else "없음"}
- 삼재: {samjae_str}

[육친]
- 배우자궁 충(沖) 여부: {"있음 (관계 부침 주의)" if spouse_warn else "없음"}

[직업·건강 베이스라인]
- 추천 직업군: {", ".join(r["career_health"]["추천직업"][:5])}
- 약한 오행 (건강 주의): {r["career_health"]["약한오행"]} → {", ".join(r["career_health"]["건강주의"][:4])}
- 행운 색상: {", ".join(r["career_health"]["행운색상"])}
- 행운 방위: {r["career_health"]["행운방위"]}

[종합 점수]
- {r["saju_score"]["score"]}점 / {r["saju_score"]["grade"]}
"""

    if extra:
        core += f"\n[추가 정보]\n{extra}"

    # 선택 영역(MBTI는 선택, 자미두수는 자동 적용) — 종합 조언 '앞'에 배치
    mbti = r["meta"].get("mbti", "")
    jami = True  # 자미두수는 항상 자동 포함
    extra_sections = ""
    next_num = 12  # 11번 다음, 종합은 맨 뒤로 밀림

    if mbti:
        core += f"\n[MBTI]\n- {mbti}"
        extra_sections += f"""

## 🧬 {next_num}. 사주 × MBTI 교차 분석 ({mbti})
이 사람의 사주(타고난 기운)와 MBTI({mbti}, 현재 성격 유형)를 교차 분석하세요. 사주가 보여주는 본질과 {mbti} 성향이 일치하는 부분(시너지)과 충돌하는 부분(긴장)을 구체적으로 짚어주세요. 일간 오행과 {mbti}의 에너지 방향, 사주 십성 구조와 {mbti}의 사고·판단 방식이 어떻게 어울리는지. 타고난 운을 {mbti} 성격으로 잘 살리는 실용 조언으로 마무리. (350자 이상)"""
        next_num += 1

    if jami:
        birth = r["meta"]["birth"]
        gender = r["meta"]["gender"]
        extra_sections += f"""

## 🟣 {next_num}. 자미두수(紫微斗數)로 본 인생 지도
이 사람의 생년월일시({birth}, {gender})를 자미두수 관점에서 분석하되, **반드시 일반인이 쉽게 이해할 수 있는 일상 언어로** 풀어주세요.

[작성 방법 — 매우 중요]
- 자미두수는 인생을 여러 '방(궁)'으로 나눠 보는 동양 별점이라고 쉽게 소개하세요.
- 별 이름(자미·천부·태양 등)을 쓸 때는 반드시 그 뜻을 일상어로 풀어주세요. 예: "리더십의 별인 자미성(紫微星) — 쉽게 말해 '대장 기질'이 있다는 뜻이에요"
- 어려운 한자 용어(명궁·재백궁 등)는 "타고난 성격 방", "돈이 들어오는 방", "직업·성공의 방", "배우자·결혼의 방"처럼 쉬운 말로 바꿔 설명하세요.
- 다음 4가지를 일상어로: ① 타고난 핵심 성격 ② 재물 운(돈) ③ 직업·성공 운 ④ 배우자·결혼 운
- 앞서 본 사주 분석과 비슷하게 나온 점, 혹은 다르게 나온 점을 한 줄로 짚어 재미를 더하세요.
- 전문가에게 설명하듯 말고, 친구에게 쉽게 이야기하듯 따뜻하게. (400자 이상)
※ 자미두수는 유파별로 해석이 조금씩 달라 참고용임을 부드럽게 한 번 언급."""
        next_num += 1

    final_num = next_num  # 종합 조언 번호 (선택 영역 다음)
    total_areas = final_num
    if extra_sections:
        final_instr = f"【필수】 1번부터 {final_num}번 종합 조언까지 {total_areas}개 영역을 모두 빠짐없이 순서대로 쓰고 완성하세요. 특히 {12}~{final_num}번을 절대 빠뜨리지 마세요. 각 영역 약 300자."
    else:
        final_instr = "【필수】 12개 영역을 모두 빠짐없이 쓰고 12번 종합까지 완성하세요. 각 영역 약 300자로 풍부하게, 단 도중에 끊기지 않도록 균형있게 작성."

    prompt = f"""당신은 50년 경력의 따뜻하고 통찰력 있는 명리학 상담가입니다.
아래 사주 데이터로 12개 영역을 모두 분석하는 풍부한 종합 리포트를 작성하세요.

{core}

【작성 규칙】
- 12개 영역을 빠짐없이 모두 작성하고 마지막까지 완성하세요 (이게 가장 중요)
- 각 영역은 5~6문장, 약 300자 분량으로 충실하고 풍부하게 작성
- 명리 용어는 괄호로 쉽게 풀이 (예: 식신(食神, 표현·재능의 기운))
- 사주 글자에 근거해 구체적으로, 영역 간 내용 반복 금지
- 따뜻한 존댓말, 때때로 위트있게

## 📜 1. 타고난 본질
일간({r["ilgan"]["stem"]}, {r["ilgan"]["ohaeng"]})을 자연물에 비유한 성격, 강점·약점, 일지({r["pillars"]["day"]["branch"]})가 보여주는 속마음과 겉모습의 차이.

## ⚖️ 2. 오행의 균형
과한 기운과 부족한 기운, 그것이 성격·건강·인간관계에 미치는 영향, 부족한 기운을 채우는 실천법.

## 🏛️ 3. 격국
{r["yukguk"]}의 의미와 이 사람이 가장 빛나는 무대, 세상과 관계 맺는 방식.

## 🔑 4. 용신
용신({r["yongshin"].get("용신","")})이 필요한 이유와 강화하는 직업·환경·습관, 기신({r["yongshin"].get("기신","")}) 주의점.

## 💰 5. 재물운
재성 구조로 본 재물 그릇과 흐름, 사업형/직장형, 큰돈 들어오는 시기와 분야, 돈 관리 조언.

## 💼 6. 직업운
잘 맞는 직군, 조직생활/창업 적합도, 30·40·50대 커리어 흐름과 승진 시기.

## ❤️ 7. 사랑·결혼운
배우자궁({r["pillars"]["day"]["branch"]})으로 본 인연의 모습, 연애 스타일, 결혼 시기. {"배우자궁 충(沖)이 있어 관계 부침 주의. " if spouse_warn else ""}좋은 인연 지키는 법.

## 🏥 8. 건강운
약한 오행({r["career_health"]["약한오행"]})으로 주의할 신체 부위와 질환, 현재 대운의 건강 포인트, 음식·운동 조언.

## 🌊 9. 현재 대운
대운 {cd["stem"]}{cd["branch"]}({cd['age']}~{cd['age']+9}세)의 기운과 분위기, 핵심 키워드 3개, 할 일과 조심할 것.

## 📅 10. {cur_year}년 올해 운세
올해 전체 흐름, 가장 좋은 달과 조심할 달, 재물·일·연애·건강 분야별 포인트.

## 🔮 11. 다가올 3년
{cur_year+1}~{cur_year+2}년의 큰 흐름과 기회·변화, 지금부터 준비할 것, 터닝포인트.
{extra_sections}

## ⭐ {final_num}. 종합 조언
가장 빛나는 강점, 좌우명 같은 조언, 행운의 색({", ".join(r["career_health"]["행운색상"][:2])})·방위({r["career_health"]["행운방위"]})·숫자({r["career_health"]["행운숫자"]}) 활용법, 따뜻한 마무리.

{final_instr}"""
    model = genai.GenerativeModel(model_name)
    gen_config = {"max_output_tokens": 13000, "temperature": 0.8}
    try:
        response = model.generate_content(prompt, generation_config=gen_config)
        text = ""
        try:
            text = response.text
        except Exception:
            if response.candidates:
                parts = response.candidates[0].content.parts
                text = "".join(getattr(p, "text", "") for p in parts)
        try:
            fr = str(response.candidates[0].finish_reason)
            if fr in ("2", "FinishReason.MAX_TOKENS", "MAX_TOKENS"):
                text += "\n\n_(분량이 길어 일부 생략됨 — 다시 생성하거나 flash-lite 모델 권장)_"
        except Exception:
            pass
        if not text:
            text = "리포트 생성에 실패했습니다. 다시 시도해 주세요."
        yield text
    except Exception as e:
        yield f"\n\n[리포트 생성 오류] {str(e)[:200]}\n\n잠시 후 다시 시도하거나 모델을 변경해 주세요."


def chat_with_saju(saju_json: dict, history: list, user_msg: str):
    """사주 기반 질의응답 — 역술원 상담 느낌"""
    import os
    api_key = (st.session_state.get("gemini_api_key_input", "") or
               os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key:
        return "사이드바에 Gemini API 키를 입력해 주세요."
    model_name = st.session_state.get("gemini_model", "gemini-2.5-flash-lite")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    r = saju_json
    cur_year = datetime.now().year
    cur_age  = cur_year - int(r["meta"]["birth"][:4])
    cd = next((d for d in r["daeun"] if d["age"] <= cur_age < d["age"]+10), r["daeun"][0])

    sysinfo = (
        f"[상담 대상 사주]\n"
        f"이름:{r['meta']['name']} 성별:{r['meta']['gender']} 생년:{r['meta']['birth']} (만 {cur_age}세)\n"
        f"일주:{r['ilgan']['stem']}{r['pillars']['day']['branch']}({r['ilgan']['ohaeng']}) "
        f"격국:{r['yukguk']} 강약:{r['yongshin']['강약']}\n"
        f"용신:{r['yongshin'].get('용신','')} 희신:{r['yongshin'].get('희신','')} "
        f"기신:{r['yongshin'].get('기신','')}\n"
        f"오행:{json.dumps(r['ohaeng_score'],ensure_ascii=False)}\n"
        f"현재대운:{cd['stem']}{cd['branch']}({cd['age']}~{cd['age']+9}세)\n"
        f"사주원국: 년{r['pillars']['year']['stem']}{r['pillars']['year']['branch']} "
        f"월{r['pillars']['month']['stem']}{r['pillars']['month']['branch']} "
        f"일{r['pillars']['day']['stem']}{r['pillars']['day']['branch']} "
        f"시{r['pillars']['hour']['stem']}{r['pillars']['hour']['branch']}"
    )

    # 대화 히스토리 구성
    convo = ""
    for turn in history:
        role = "상담자" if turn["role"] == "user" else "역술가"
        convo += f"\n{role}: {turn['content']}"

    prompt = (
        "당신은 따뜻하고 지혜로운 50년 경력 역술 상담가입니다.\n"
        "아래 사주 정보를 바탕으로, 상담자의 질문에 친근하고 구체적으로 답하세요.\n"
        "명리 용어는 괄호로 쉽게 풀이하고, 300자 내외로 핵심을 짚어 따뜻하게 답하세요. 답변은 반드시 완결된 문장으로 끝내세요.\n"
        "사주 근거를 들어 설명하고, 단정적 불운 예언 대신 조언과 가능성으로 답하세요.\n\n"
        f"{sysinfo}\n"
        f"\n[지금까지의 대화]{convo if convo else ' (없음)'}\n"
        f"\n상담자: {user_msg}\n역술가:"
    )

    try:
        resp = model.generate_content(
            prompt, generation_config={"max_output_tokens": 6000, "temperature": 0.9})
        try:
            return resp.text
        except Exception:
            if resp.candidates:
                parts = resp.candidates[0].content.parts
                return "".join(getattr(p, "text", "") for p in parts) or "답변 생성 실패"
            return "답변을 생성하지 못했습니다."
    except Exception as e:
        return f"오류: {str(e)[:150]}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SLOT FACTORY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_slot_id = [0]

def make_slot() -> dict:
    _slot_id[0] += 1
    return {
        "id": f"p{_slot_id[0]}",
        "name": "", "hanja_name": "", "gender": "남성",
        "cal_type": "양력",
        "year": 1990, "month": 6, "day": 15,
        "hour": 12, "minute": 0,
    }

def read_slot(slot: dict) -> dict:
    sid = slot["id"]
    return {
        "name":       st.session_state.get(f"name_{sid}",     slot["name"]),
        "hanja_name": st.session_state.get(f"hanja_{sid}",    slot.get("hanja_name", "")),
        "gender":     st.session_state.get(f"gender_{sid}",   slot["gender"]),
        "cal_type":   st.session_state.get(f"cal_{sid}",      slot.get("cal_type", "양력")),
        "year":       int(st.session_state.get(f"year_{sid}",  slot["year"])),
        "month":      int(st.session_state.get(f"month_{sid}", slot["month"])),
        "day":        int(st.session_state.get(f"day_{sid}",   slot["day"])),
        "hour":       int(st.session_state.get(f"hour_{sid}",  slot["hour"])),
        "minute":     int(st.session_state.get(f"minute_{sid}",slot.get("minute", 0))),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UI 헬퍼 — 사주 결과 렌더링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ohaeng_radar_svg(ohaeng: dict) -> str:
    total  = sum(ohaeng.values()) or 1
    order  = ["목","화","토","금","수"]
    angles = [i * 72 - 90 for i in range(5)]
    cx, cy, r = 110, 110, 80

    def pt(a, ratio):
        rad = math.radians(a)
        return cx + r * ratio * math.cos(rad), cy + r * ratio * math.sin(rad)

    grid = ""
    for lv in [0.25, 0.5, 0.75, 1.0]:
        pts = " ".join(f"{pt(a,lv)[0]:.1f},{pt(a,lv)[1]:.1f}" for a in angles)
        grid += f'<polygon points="{pts}" fill="none" stroke="#e0e0e0" stroke-width="0.5"/>'
    axes = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{pt(a,1)[0]:.1f}" y2="{pt(a,1)[1]:.1f}" stroke="#e0e0e0" stroke-width="0.5"/>'
        for a in angles)
    data_pts = [pt(angles[i], min(ohaeng[oh] / total * 5, 1.0)) for i, oh in enumerate(order)]
    data_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in data_pts)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{OHAENG_COLOR[order[i]]}" stroke="white" stroke-width="1.5"/>'
        for i, (x, y) in enumerate(data_pts))
    labels = ""
    for i, oh in enumerate(order):
        lx, ly = pt(angles[i], 1.32)
        c   = OHAENG_COLOR[oh]
        pct = round(ohaeng[oh] / total * 100)
        labels += (f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle"'
                   f' fill="{c}" font-size="11" font-weight="700" font-family="Noto Serif KR">{oh}</text>')
        labels += (f'<text x="{lx:.1f}" y="{ly+14:.1f}" text-anchor="middle"'
                   f' fill="#666" font-size="9">{pct}%</text>')
    return (f'<svg viewBox="0 0 220 220" width="220" height="220">'
            f'{grid}{axes}'
            f'<polygon points="{data_str}" fill="rgba(192,57,43,0.18)" '
            f'stroke="#c0392b" stroke-width="2" stroke-linejoin="round"/>'
            f'{dots}{labels}</svg>')


def render_pillar_cards(r: dict):
    pillars, gm = r["pillars"], r["gongmang"]
    all_sik, all_fort, all_naeum = r["all_sikshin"], r["all_fortune"], r["all_naeum"]
    html = '<div class="pillar-grid">'
    for p in PILLAR_KEYS:
        s  = pillars[p]["stem"];  b  = pillars[p]["branch"]
        so = STEM_OHAENG[s];      bo = BRANCH_OHAENG[b]
        sc = OHAENG_COLOR[so];    bc = OHAENG_COLOR[bo]
        is_day = "day-col" if p == "day" else ""
        gm_html = '<div class="p-gm">⊘ 공망</div>' if b in gm else ""
        html += (f'<div class="pillar-card {is_day}">'
                 f'<div class="p-label">{PILLAR_LABEL[p]}</div>'
                 f'<div class="p-stem" style="color:{sc}">{s}</div>'
                 f'<div class="p-branch" style="color:{bc}">{b}</div>'
                 f'<div class="p-sub">{all_sik[p+"_stem"]} / {all_sik[p+"_branch"]}</div>'
                 f'<div class="p-fort">{all_fort[p]}</div>'
                 f'<div class="p-naeum">{all_naeum[p]["name"]}</div>'
                 f'{gm_html}</div>')
    st.markdown(html + '</div>', unsafe_allow_html=True)


def render_ohaeng_bars(ohaeng: dict):
    total = sum(ohaeng.values()) or 1
    for oh, score in ohaeng.items():
        pct = round(score / total * 100)
        c   = OHAENG_COLOR[oh]
        st.markdown(
            f'<div class="oh-bar-wrap">'
            f'<div class="oh-bar-row"><span style="color:{c};font-weight:600">{OHAENG_LABEL[oh]}</span>'
            f'<span style="color:#555">{score}점 ({pct}%)</span></div>'
            f'<div class="oh-bar-bg"><div class="oh-bar-fill" style="width:{pct}%;background:{c}"></div></div>'
            f'</div>',
            unsafe_allow_html=True)


def render_yongshin(ys: dict):
    html = ""
    for k, cls in [("용신","ys-용신"),("희신","ys-희신"),("기신","ys-기신"),("한신","ys-한신"),("구신","ys-구신")]:
        v = ys.get(k)
        if v:
            c = OHAENG_COLOR.get(v, "#666")
            html += f'<span class="ys-badge {cls}">{k}: <b style="color:{c}">{v}</b></span>'
    st.markdown(html, unsafe_allow_html=True)


def render_relations(rel: dict, stem_hap: list):
    html = ""
    for h in stem_hap:
        html += f'<span class="rel-badge rel-stem">천간합 {h["pair"]}→{h["result"]}</span>'
    cls_map = {"6합":"rel-합","삼합":"rel-삼합","방합":"rel-방합","충":"rel-충",
               "형":"rel-형","파":"rel-파","해":"rel-해","원진":"rel-원진"}
    for rt, pairs in rel.items():
        for p in pairs:
            html += f'<span class="rel-badge {cls_map.get(rt,"")}">{rt} {p}</span>'
    st.markdown(html or '<span style="color:#999">특이 관계 없음</span>', unsafe_allow_html=True)


def render_12sisal(sisal_12: list):
    html = '<div class="sisal-grid">'
    for s in sisal_12:
        cls = "sisal-on" if s["active"] else "sisal-off"
        cnt = f"×{s['count']}" if s["count"] > 1 else ""
        html += (f'<div class="sisal-cell {cls}" title="{s["desc"]}">'
                 f'<span class="sisal-name">{s["name"]}{cnt}</span>'
                 f'<span class="sisal-branch">{s["branch"]}</span></div>')
    st.markdown(html + '</div>', unsafe_allow_html=True)
    for s in sisal_12:
        if s["active"]:
            st.caption(f"◉ **{s['name']}** ({s['branch']}) — {s['desc']}")


def render_daeun(daeun: list, birth_year: int):
    cur_age = datetime.now().year - birth_year
    html    = '<div class="daeun-grid">'
    for d in daeun:
        cls = "daeun-cell cur" if d["age"] <= cur_age < d["age"] + 10 else "daeun-cell"
        sc  = OHAENG_COLOR[d["stem_oh"]]; bc = OHAENG_COLOR[d["branch_oh"]]
        html += (f'<div class="{cls}">'
                 f'<div class="daeun-char" style="color:{sc}">{d["stem"]}</div>'
                 f'<div class="daeun-char" style="color:{bc}">{d["branch"]}</div>'
                 f'<div class="daeun-age">{d["age"]}~</div></div>')
    st.markdown(html + '</div>', unsafe_allow_html=True)
    st.caption("✦ 빨간 테두리 = 현재 대운")


def render_weolun(weolun: list):
    cur_m = datetime.now().month
    html  = '<div class="weol-grid">'
    for w in weolun:
        cls = "weol-cell cur-m" if w["month"] == cur_m else "weol-cell"
        sc  = OHAENG_COLOR[w["stem_oh"]]; bc = OHAENG_COLOR[w["branch_oh"]]
        html += (f'<div class="{cls}">'
                 f'<div class="weol-mo">{w["month"]}월</div>'
                 f'<div class="daeun-char" style="color:{sc}">{w["stem"]}</div>'
                 f'<div class="daeun-char" style="color:{bc}">{w["branch"]}</div></div>')
    st.markdown(html + '</div>', unsafe_allow_html=True)


def render_suri(suri: dict):
    if not suri:
        st.info("사이드바에 한자 이름을 입력하면 획수가 자동 계산됩니다.")
        return
    guk_lbl = {"원격":"초년운","형격":"청년운","이격":"중년운","정격":"말년운"}
    html = '<table class="suri-table"><tr><th>格</th><th>기간</th><th>수리</th><th>길흉</th><th>의미</th></tr>'
    for guk, val in suri.items():
        gl = "suri-good" if "길" in val["길흉"] else "suri-bad"
        html += (f'<tr><td><b>{guk}</b></td><td>{guk_lbl.get(guk,"")}</td>'
                 f'<td style="text-align:center"><b>{val["수"]}</b></td>'
                 f'<td class="{gl}">{val["길흉"]}</td><td>{val["의미"]}</td></tr>')
    st.markdown(html + "</table>", unsafe_allow_html=True)


def render_compass(dirmap: dict, feng: dict):
    dir_to_guk = {v: k for k, v in dirmap.items()}
    pos_map = {
        (0,0):"서북",(0,1):"북",(0,2):"동북",
        (1,0):"서",  (1,1):"center",(1,2):"동",
        (2,0):"서남",(2,1):"남",(2,2):"동남",
    }
    html = '<div class="compass-wrap">'
    for row in range(3):
        for col in range(3):
            dn = pos_map[(row, col)]
            if dn == "center":
                html += f'<div class="compass-cell compass-center">{feng["괘명"]}<br><small>{feng["사택"]}</small></div>'
            else:
                guk  = dir_to_guk.get(dn, "")
                cls  = COMPASS_CLASS.get(guk, "")
                icon = "✦" if guk in ["생기","천을","연년","복위"] else "✕"
                html += f'<div class="compass-cell {cls}"><small>{dn}</small><br><b>{icon} {guk}</b></div>'
    st.markdown(html + '</div>', unsafe_allow_html=True)


def render_special_sisal(ssisal: dict):
    html = ""
    for name, info in ssisal.items():
        active = info.get("active", False)
        cls    = "guiin-on" if active else "guiin-off"
        icon   = "◉" if active else "○"
        html  += f'<span class="guiin-badge {cls}">{icon} {name}</span>'
    st.markdown(html, unsafe_allow_html=True)
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    for name, info in ssisal.items():
        if info.get("active"):
            br_info = f'({info.get("branches", info.get("branch",""))})'
            st.success(f"✦ **{name}** {br_info} — {info['desc']}")


def render_yukchins(yukchins: dict):
    html = ('<table class="yukchins-table">'
            '<tr><th>宮</th><th>천간십성</th><th>지지십성</th><th>육친</th><th>운성</th><th>충</th></tr>')
    for p, info in yukchins.items():
        warn = "⚠" if info["chung_warn"] else ""
        html += (f'<tr><td><b>{info["label"]}</b></td>'
                 f'<td>{info["stem_sikshin"]}</td><td>{info["branch_sikshin"]}</td>'
                 f'<td>{info["yukchins"]}</td><td>{info["fortune"]}</td>'
                 f'<td style="color:#e53935">{warn}</td></tr>')
    st.markdown(html + "</table>", unsafe_allow_html=True)


def render_goonghap_score(gh: dict):
    sc    = gh["score"]
    color = "#2e7d32" if sc >= 70 else ("#b8860b" if sc >= 50 else "#c62828")
    st.markdown(
        f'<div class="goonghap-score">'
        f'<div class="goonghap-num" style="color:{color}">{sc}</div>'
        f'<div style="font-size:.9rem;font-weight:600;margin:.3rem 0">{gh["grade"]}</div>'
        f'<div style="background:#f0e8d8;border-radius:4px;height:12px;margin:.4rem 0">'
        f'<div style="height:100%;width:{sc}%;background:{color};border-radius:4px"></div></div>'
        f'</div>',
        unsafe_allow_html=True)


def render_택일_calendar(ilgin_list: list, ilgan: str, year: int, month: int):
    first_wd = date(year, month, 1).weekday()
    html = '<div style="margin:.5rem 0"><div class="cal-grid">'
    for wd in ["월","화","수","목","금","토","일"]:
        html += f'<div style="text-align:center;font-size:.72rem;color:#888;padding:.2rem">{wd}</div>'
    for _ in range(first_wd):
        html += '<div class="cal-cell cal-empty"></div>'
    for d in ilgin_list:
        rate = rate_ilgin_day(ilgan, d["branch"])
        cls  = {"대길":"cal-길","길":"cal-길","흉":"cal-흉","보통":"cal-보통"}.get(rate, "cal-보통")
        sc_  = OHAENG_COLOR[d["stem_oh"]]; bc_ = OHAENG_COLOR[d["branch_oh"]]
        icon = {"대길":"★","길":"○","흉":"✕","보통":"·"}.get(rate,"·")
        html += (f'<div class="cal-cell {cls}">'
                 f'<div class="day-num">{d["day"]}({d["weekday"]})</div>'
                 f'<div class="gan" style="color:{sc_}">{d["stem"]}</div>'
                 f'<div class="gan" style="color:{bc_}">{d["branch"]}</div>'
                 f'<div style="font-size:.65rem">{icon}</div></div>')
    st.markdown(html + '</div></div>', unsafe_allow_html=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: 개인 15탭
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _copy_iframe(text: str, label: str, height: int = 50):
    """클립보드 복사 버튼 (iframe 격리)"""
    import json as _j
    import streamlit.components.v1 as _c
    safe = _j.dumps(text)
    html = ('<html><head><meta charset="utf-8"></head><body style="margin:0;padding:0">'
            '<button id="cpb" style="width:100%;padding:.7rem;background:#1565c0;'
            'color:#fff;border:none;border-radius:8px;font-size:1.0rem;font-weight:700;'
            'cursor:pointer;font-family:sans-serif;height:' + str(height-8) + 'px">'
            + label + '</button><script>'
            'var T=__TEXT__;var b=document.getElementById("cpb");'
            'b.addEventListener("click",function(){'
            'function ok(){b.innerText="\u2713 \ubcf5\uc0ac \uc644\ub8cc!";'
            'b.style.background="#2e7d32";setTimeout(function(){b.innerText=L;'
            'b.style.background="#1565c0";},2000);}'
            'function fb(){var t=document.createElement("textarea");t.value=T;'
            'document.body.appendChild(t);t.select();'
            'try{document.execCommand("copy");ok();}catch(e){b.innerText="\ubcf5\uc0ac \uc2e4\ud328";}'
            'document.body.removeChild(t);}'
            'if(navigator.clipboard&&navigator.clipboard.writeText){'
            'navigator.clipboard.writeText(T).then(ok).catch(fb);}else{fb();}'
            '});var L=b.innerText;</script></body></html>').replace("__TEXT__", safe)
    _c.html(html, height=height)


def render_ai_report_section(r: dict, extra_text: str = ""):
    """AI 명리 리포트 + 역술 상담 채팅 — 독립 섹션"""
    st.markdown(
        f'<div class="ai-header-block">'
        f'<div class="ai-header-title">🔮 AI 명리 종합 해석 리포트</div>'
        f'<div class="ai-header-sub">{r["meta"]["name"]}님의 사주를 AI가 {13 + (1 if r["meta"].get("mbti") else 0)}개 영역으로 입체 분석합니다</div>'
        f'</div>',
        unsafe_allow_html=True)

    api_ok    = bool(st.session_state.get("gemini_api_key_input","").strip())
    cache_key = f"ai_report_{r['meta']['name']}_{r['meta']['birth']}"

    if not api_ok:
        st.warning("🔒 사이드바 하단에 Gemini API 키를 입력하면 활성화됩니다.\n\n"
                   "키 발급: https://aistudio.google.com → Get API Key (무료)")
        return

    # 활성 귀인/삼재 자동 첨부
    extra = extra_text
    if r["samjae"].get("in_samjae"):
        extra += f"\n[삼재] {r['samjae'].get('phase','')} 중"
    active_g = [k for k,v in r["special_sisal"].items() if v.get("active")]
    if active_g:
        extra += f"\n[귀인] {', '.join(active_g)} 활성"

    has_cache = cache_key in st.session_state

    # ════════════ 리포트 없을 때: 생성 버튼 ════════════
    if not has_cache:
        if st.button("✦  AI 종합 리포트 생성하기", key=f"gen_{cache_key}",
                     use_container_width=True, type="primary"):
            try:
                with st.spinner("🔮 AI가 12개 영역을 심층 분석 중입니다... (20~40초)"):
                    parts = []
                    for chunk in generate_llm_report(r, extra):
                        parts.append(chunk)
                    result_text = "".join(parts)
                if result_text and len(result_text) > 50:
                    st.session_state[cache_key] = result_text
                    st.rerun()
                else:
                    st.error("리포트가 너무 짧게 생성됐습니다. 다시 시도해 주세요.")
            except Exception as ex:
                err = str(ex)
                if "429" in err:
                    st.error("⚠️ API 한도 초과 (429) — 1~2분 후 재시도하거나 "
                             "gemini-2.5-flash-lite 로 변경하세요.")
                else:
                    st.error(f"오류: {err[:200]}")
        return

    # ════════════ 리포트 있을 때 ════════════
    report_text = st.session_state[cache_key]

    # 상단: 다시생성 / 삭제 / 복사
    col_L, col_R = st.columns([1.6, 1])
    with col_L:
        if st.button("🔄  새로 다시 생성하기", key=f"regen_{cache_key}",
                     use_container_width=True, type="primary"):
            st.session_state.pop(cache_key, None)
            st.rerun()
    with col_R:
        with st.container(key=f"del_report_{abs(hash(cache_key))%10000}"):
            if st.button("🗑  리포트 삭제하기", key=f"clr_{cache_key}",
                         use_container_width=True):
                st.session_state.pop(cache_key, None)
                st.rerun()
        _copy_iframe(report_text, "📋 리포트 전체 복사", height=46)

    # 본문
    # 리포트 본문 (마크다운 정상 렌더링 — ## 제목, ** 강조 자동 변환)
    st.markdown('<div class="llm-report-box">', unsafe_allow_html=True)
    st.markdown(report_text)
    st.markdown('</div>', unsafe_allow_html=True)

    # ════════════ 💬 역술 상담실 (본문과 전체복사 사이) ════════════
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown(
        '<div class="chat-header">💬 AI 역술 상담실</div>'
        '<div class="chat-sub">사주에 대해 궁금한 점을 자유롭게 물어보세요 '
        '(예: 올해 이직해도 될까요? / 저랑 잘 맞는 배우자는? / 건강 조심할 점은?)</div>',
        unsafe_allow_html=True)

    chat_key = f"chat_{r['meta']['name']}_{r['meta']['birth']}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    # 대화 내역 (카톡 스타일)
    chat_html = '<div class="chat-box">'
    if not st.session_state[chat_key]:
        chat_html += ('<div class="chat-empty">아직 대화가 없습니다.<br>'
                      '아래 입력창에 질문을 적어보세요 🔮</div>')
    for turn in st.session_state[chat_key]:
        safe_c = turn["content"].replace("<","&lt;").replace(">","&gt;")
        if turn["role"] == "user":
            chat_html += (f'<div class="chat-row right">'
                          f'<div class="bubble user">{safe_c}</div></div>')
        else:
            chat_html += (f'<div class="chat-row left">'
                          f'<div class="bubble ai">{safe_c}</div></div>')
    chat_html += '</div>'
    st.markdown(chat_html, unsafe_allow_html=True)

    # 입력창 (text_input + 전송 버튼 — 어디서든 안정 작동)
    ci1, ci2 = st.columns([5, 1])
    with ci1:
        user_q = st.text_input("질문 입력", key=f"input_{chat_key}",
                               placeholder="궁금한 점을 입력하고 전송을 누르세요...",
                               label_visibility="collapsed")
    with ci2:
        send = st.button("전송", key=f"send_{chat_key}",
                         use_container_width=True, type="primary")

    if send and user_q.strip():
        st.session_state[chat_key].append({"role":"user","content":user_q.strip()})
        with st.spinner("🔮 역술가가 답변 중..."):
            answer = chat_with_saju(r, st.session_state[chat_key][:-1], user_q.strip())
        st.session_state[chat_key].append({"role":"assistant","content":answer})
        st.rerun()

    # 대화 지우기
    if st.session_state[chat_key]:
        with st.container(key=f"clrchat_{abs(hash(chat_key))%10000}"):
            if st.button("🗑  대화 내용 지우기", key=f"clrc_{chat_key}",
                         use_container_width=True):
                st.session_state[chat_key] = []
                st.rerun()

    # ════════════ 하단: 전체 복사 (리포트 + 대화) ════════════
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    full_copy = report_text
    if st.session_state[chat_key]:
        full_copy += "\n\n━━━ 💬 상담 대화 ━━━\n"
        for turn in st.session_state[chat_key]:
            who = "❓ 질문" if turn["role"]=="user" else "🔮 답변"
            full_copy += f"\n[{who}] {turn['content']}\n"
        _copy_iframe(full_copy, "📋 리포트 + 대화 전체 복사", height=52)
    else:
        _copy_iframe(report_text, "📋 리포트 전체 복사", height=52)

    st.caption("✦ 캐시된 리포트 · 🗑 버튼으로 삭제 후 재생성 가능")


def render_15tabs(r: dict, suri: dict, birth_year: int,
                  partner_result: dict = None, partner_gh: dict = None):
    tabs = st.tabs([
        "🀄 사주원국","⚖️ 오행·용신","🔗 관계분석","🎯 십성·격국",
        "🕰 대운·세운·월운","⚡ 신살","🌟 귀인·삼재","👨‍👩‍👧 육친",
        "💑 궁합","📅 택일","📿 성명학","🧭 풍수",
        "💼 직업·건강","🌐 별자리",
    ])

    with tabs[0]:  # 사주원국
        sc = r["saju_score"]
        col_sc, col_ti = st.columns([1, 3])
        with col_sc:
            sc_c = "#2e7d32" if sc["score"] >= 70 else ("#b8860b" if sc["score"] >= 50 else "#c62828")
            st.markdown(
                f'<div style="text-align:center;background:white;border-radius:8px;'
                f'padding:.8rem;border:1px solid #e0e0e0">'
                f'<div style="font-size:.7rem;color:#888">종합 점수</div>'
                f'<div style="font-size:2rem;font-weight:700;color:{sc_c}">{sc["score"]}</div>'
                f'<div style="font-size:.72rem;color:{sc_c}">{sc["grade"]}</div></div>',
                unsafe_allow_html=True)
        with col_ti:
            il = r["ilgan"]
            st.markdown(f'<div class="stitle">🀄 {r["meta"]["name"]} · {r["meta"]["birth"]}</div>',
                        unsafe_allow_html=True)
            st.caption(f'일간: {il["stem"]}({il["ohaeng"]}) | 납음: {il["naeum"]} '
                       f'| 운성: {il["twelve_fortune"]} | 격국: {r["yukguk"]} '
                       f'| 공망: {"·".join(r["gongmang"]) or "없음"}')
        render_pillar_cards(r)
        st.caption("천간(천간십성) / 지지(지지십성) / 십이운성 / 납음 / ⊘공망")

    with tabs[1]:  # 오행·용신
        col_r, col_b = st.columns([1, 2])
        with col_r:
            st.markdown('<div class="stitle">오행 레이더</div>', unsafe_allow_html=True)
            st.markdown(ohaeng_radar_svg(r["ohaeng_score"]), unsafe_allow_html=True)
        with col_b:
            st.markdown('<div class="stitle">오행 점수</div>', unsafe_allow_html=True)
            render_ohaeng_bars(r["ohaeng_score"])
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        ys = r["yongshin"]
        with c1:
            st.markdown('<div class="stitle">억부·강약</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="icard"><div class="icard-t">강약</div>'
                        f'<div class="icard-v">{ys["강약"]}</div></div>'
                        f'<div class="icard"><div class="icard-t">자력 비율</div>'
                        f'<div class="icard-v">{r["self_ratio_pct"]}%</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="stitle">용신</div>', unsafe_allow_html=True)
            render_yongshin(ys)
        with c3:
            st.markdown('<div class="stitle">조후</div>', unsafe_allow_html=True)
            johu = r["johu"]
            st.markdown(f'<div class="icard"><div class="icard-t">계절</div>'
                        f'<div class="icard-v">{johu.get("계절","?")}</div></div>',
                        unsafe_allow_html=True)
            st.caption(johu.get("desc", ""))
            for oh in johu.get("lacking", []):   st.error(f"⚠ {oh} 오행 부족")
            for oh in johu.get("fulfilled", []): st.success(f"✓ {oh} 오행 충족")

    with tabs[2]:  # 관계분석
        with st.expander("📖 합·충·형·파·해·원진이란?", expanded=False):
            st.markdown("""
사주 여덟 글자 사이의 **상호작용**입니다.

**🟢 합(合) — 결합**
- **천간합**: 두 천간이 짝을 이뤄 새 오행으로 변함 (예: 갑+기 → 토)
- **6합·삼합·방합**: 지지끼리 결합 — 화합·기운 강화

**🔴 충(沖) — 정면 충돌**
180도 반대 지지가 부딪힘. 변화·이동·갈등을 일으키지만 변혁의 기회이기도 합니다.

**🟠 형(刑)** — 가시 박힘. 사고·법적 문제·건강 주의.

**🟡 파(破)·해(害)·원진(怨嗔)** — 미묘하게 어긋남. 깨짐·손해·서로 미워하는 감정.

> 합이 많으면 인덕이 좋고, 충이 많으면 변화가 많은 삶을 살게 됩니다.
""")
        st.markdown('<div class="stitle">🔗 합·충·형·파·해·원진 전체</div>', unsafe_allow_html=True)
        render_relations(r["relations"], r["stem_hap"])
        rel = r["relations"]
        c1, c2 = st.columns(2)
        with c1:
            for item in rel["충"]:  st.error(f"⚡ 충 {item}")
            for item in rel["형"]:  st.warning(f"⚠ 형 {item}")
            for item in rel["원진"]: st.warning(f"💢 원진 {item}")
        with c2:
            for item in rel["6합"]:  st.success(f"✦ 6합 {item}")
            for item in rel["삼합"]: st.success(f"✦ 삼합 {item}")
            for item in rel["방합"]: st.info(f"◉ 방합 {item}")
            for item in rel["파"]:   st.warning(f"◦ 파 {item}")
            for item in rel["해"]:   st.warning(f"◦ 해 {item}")

    with tabs[3]:  # 십성·격국
        with st.expander("📖 십성과 격국이란?", expanded=False):
            st.markdown("""
**십성(十星)** 은 일간(본인)에 대한 다른 글자들의 관계를 10가지로 분류한 것입니다.

| 분류 | 의미 |
|---|---|
| **비견·겁재** | 형제·친구·경쟁자. 독립심·자존심 |
| **식신·상관** | 자식(여)·표현력·창의·재능 |
| **정재·편재** | 재물·아내(남). 정재=안정, 편재=사업·투기 |
| **정관·편관** | 직장·명예·자식(남). 정관=공직, 편관=무관·도전 |
| **정인·편인** | 어머니·학문·문서. 정인=학자, 편인=종교·예술 |

**격국(格局)** 은 사주의 '주된 무대'를 결정짓는 구조입니다.
""")
        st.markdown('<div class="stitle">🎯 사주 8자 십성</div>', unsafe_allow_html=True)
        pillars = r["pillars"]
        html = ('<table class="suri-table"><tr>'
                '<th>구분</th><th>천간</th><th>천간십성</th><th>십이운성</th><th>지지</th><th>지지십성</th></tr>')
        for p in PILLAR_KEYS:
            s  = pillars[p]["stem"]; b = pillars[p]["branch"]
            sc_ = OHAENG_COLOR[STEM_OHAENG[s]]; bc_ = OHAENG_COLOR[BRANCH_OHAENG[b]]
            ft  = r["all_fortune"][p]; fts = FORTUNE_SCORE.get(ft, 0)
            fc  = "#2e7d32" if fts >= 80 else ("#e65100" if fts >= 50 else "#c62828")
            html += (f'<tr><td><b>{PILLAR_LABEL[p]}</b></td>'
                     f'<td style="color:{sc_};font-weight:700">{s}</td>'
                     f'<td>{r["all_sikshin"][p+"_stem"]}</td>'
                     f'<td style="color:{fc}">{ft}({fts})</td>'
                     f'<td style="color:{bc_};font-weight:700">{b}</td>'
                     f'<td>{r["all_sikshin"][p+"_branch"]}</td></tr>')
        st.markdown(html + "</table>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="stitle">격국: {r["yukguk"]}</div>', unsafe_allow_html=True)
            desc_map = {
                "건록격(建祿格)":"강한 자립심·리더십.","양인격(羊刃格)":"강렬한 에너지·전문직.",
                "식신격(食神格)":"풍요·창의·표현.","상관격(傷官格)":"재능·자유로운 영혼.",
                "편재격(偏財格)":"사업·투기·대범함.","정재격(正財格)":"성실한 재물 축적.",
                "편관격(偏官格)":"강인·도전·경쟁.","정관격(正官格)":"명예·원칙·공직.",
                "편인격(偏印格)":"학문·종교·예술.","정인격(正印格)":"학문·명예·교육.",
            }
            st.info(desc_map.get(r["yukguk"], "복잡한 격국, 다양한 분야 활약 가능."))
        with c2:
            sc = r["saju_score"]
            st.markdown('<div class="stitle">종합 점수</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="icard"><div class="icard-t">점수</div>'
                        f'<div class="icard-v">{sc["score"]}점 · {sc["grade"]}</div></div>',
                        unsafe_allow_html=True)

    with tabs[4]:  # 대운·세운·월운
        with st.expander("📖 대운·세운·월운이란?", expanded=False):
            st.markdown("""
타고난 사주(원국)에 시간이라는 변수가 더해지면 운(運)이 됩니다.

**🕰️ 대운(大運)** — 10년 단위 큰 흐름
- 인생을 10년씩 나눠 각 시기의 큰 기운을 봅니다
- 어떤 대운이 오느냐가 인생 전반의 색깔을 결정합니다

**☀️ 세운(歲運)** — 매년의 운세
- 그 해의 천간지지가 사주에 어떤 영향을 미치는지 분석

**🌙 월운(月運)** — 매달의 흐름
- 중요한 결정·계약은 길월(吉月)에 잡으면 좋습니다

> 같은 사주라도 대운 흐름에 따라 인생이 정반대로 펼쳐질 수 있습니다.
""")
        st.markdown('<div class="stitle">🕰 대운</div>', unsafe_allow_html=True)
        render_daeun(r["daeun"], birth_year)
        cur_age = datetime.now().year - birth_year
        cd = next((d for d in r["daeun"] if d["age"] <= cur_age < d["age"]+10), r["daeun"][0])
        st.markdown(f'<div class="icard"><div class="icard-t">현재 대운 ({cd["age"]}~{cd["age"]+9}세)</div>'
                    f'<div class="icard-v">{cd["stem"]}{cd["branch"]} · {cd["naeum"]} · {cd["fortune"]}</div></div>',
                    unsafe_allow_html=True)
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        seun = r["seun_now"]
        st.markdown(f'<div class="stitle">🌞 {seun["year"]}년 세운</div>', unsafe_allow_html=True)
        sc_ = OHAENG_COLOR[STEM_OHAENG[seun["stem"]]]; bc_ = OHAENG_COLOR[BRANCH_OHAENG[seun["branch"]]]
        st.markdown(f'<div class="icard"><div class="icard-t">세운 간지</div>'
                    f'<div class="icard-v"><span style="color:{sc_}">{seun["stem"]}</span> '
                    f'<span style="color:{bc_}">{seun["branch"]}</span></div></div>',
                    unsafe_allow_html=True)
        for c in r["seun_interaction"].get("충",[]): st.error(f"⚠ {c}")
        for h in r["seun_interaction"].get("합",[]): st.success(f"✦ {h}")
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown(f'<div class="stitle">🌙 월운</div>', unsafe_allow_html=True)
        render_weolun(r["weolun"])

    with tabs[5]:  # 신살
        with st.expander("📖 12신살이란?", expanded=False):
            st.markdown("""
**12신살(神煞)** 은 사주에 깃든 특별한 기운으로, 일종의 '인생 양념' 같은 존재입니다.

| 신살 | 의미 |
|---|---|
| **겁살·재살** | 손재·재난 주의 |
| **천살·지살** | 하늘이 주는 시련, 이동 운 |
| **년살·월살** | 소모·다툼 주의 |
| **망신살** | 명예 손상 주의 |
| **장성살** | 리더십·권위 |
| **반안살** | 고생 후 안정 |
| **역마살** | 이동·여행·변화가 많음 |
| **육해살** | 인간관계 변화 |
| **화개살** | 예술·종교·고독한 영혼 |

신살은 절대적 길흉이 아니라, **활용하기 나름**인 에너지입니다.
""")
        st.markdown(f'<div class="stitle">⚡ 12신살 (년지: {r["pillars"]["year"]["branch"]})</div>',
                    unsafe_allow_html=True)
        render_12sisal(r["sisal_12"])

    with tabs[6]:  # 귀인·삼재
        with st.expander("📖 귀인·삼재란?", expanded=False):
            st.markdown("""
**🌟 특수 귀인(貴人)** — 사주에 깃든 행운의 별
- **천을귀인**: 위기에서 구원받는 최고의 길성
- **문창귀인**: 학문·시험·창작에 유리
- **학당귀인**: 교육·연구·명예 운
- **암록**: 숨어있는 복, 위기 때 나타나는 도움
- **건록**: 자립·직업운 안정
- **양인**: 강한 의지·전문직 유리(과하면 위험)

**🔥 삼재(三災)** — 9년에 한 번씩 3년간 오는 액운 기간
- **입삼재**: 변화의 시작
- **중삼재**: 가장 조심해야 할 해
- **출삼재**: 액운이 빠져나가는 해

> 삼재 기간엔 큰 결정(이사·창업·결혼)을 신중히 하라는 옛 지혜입니다.
""")
        st.markdown('<div class="stitle">🌟 귀인 신살</div>', unsafe_allow_html=True)
        render_special_sisal(r["special_sisal"])
        st.markdown('<div class="stitle">🔥 삼재</div>', unsafe_allow_html=True)
        sj = r["samjae"]
        if sj.get("in_samjae"):
            st.error(f"⚠ 현재 **{sj['phase']}** 중"); st.warning(sj["desc"])
        elif sj.get("upcoming"):
            st.warning(f"📢 {sj['desc']}")
        else:
            st.success("✦ 현재 삼재 기간이 아닙니다.")

    with tabs[7]:  # 육친
        with st.expander("📖 육친이란?", expanded=False):
            st.markdown("""
**육친(六親)** 은 사주에서 본 가족·인간관계입니다.

각 기둥은 인생의 인간관계 무대를 나타냅니다:
- **연주(年柱)**: 조부모·뿌리
- **월주(月柱)**: 부모·형제
- **일지(日支)**: ★ **배우자궁** — 결혼 상대의 모습이 담김
- **시주(時柱)**: 자녀·말년

**남성** 기준
- 정재 = 정식 부인, 편재 = 연인·아버지
- 정관 = 딸, 편관 = 아들

**여성** 기준
- 정관 = 정식 남편, 편관 = 비공식 남자
- 식신 = 딸, 상관 = 아들
- 정인 = 어머니

배우자궁(일지)이 충(沖)이면 결혼생활에 부침이 있을 수 있다는 옛 해석입니다.
""")
        st.markdown('<div class="stitle">👨‍👩‍👧 육친 분석</div>', unsafe_allow_html=True)
        render_yukchins(r["yukchins"])

    with tabs[8]:  # 궁합
        with st.expander("📖 사주 궁합이란?", expanded=False):
            st.markdown("""
**궁합(宮合)** 은 두 사람의 사주를 비교해 인연의 깊이를 봅니다.

주요 분석 요소:
1. **일지(日支) 관계** — 가장 중요. 합이면 천생연분, 충이면 갈등
2. **오행 보완** — 한쪽이 부족한 오행을 상대가 채워주는지
3. **천간합** — 두 일간이 합을 이루면 천생배필
4. **용신 상호작용** — 내 용신이 상대 사주에 있으면 큰 도움

> 점수가 낮다고 절대 안 되는 게 아니라, **어떤 부분에서 노력이 필요한지** 보여주는 지표입니다.
""")
        st.markdown('<div class="stitle">💑 궁합 종합 분석</div>', unsafe_allow_html=True)
        if partner_result and partner_gh:
            gh = partner_gh
            n1 = gh.get("name1",""); n2 = gh.get("name2","")

            # 점수 & 총평 배너
            sc = gh["score"]
            color = gh.get("grade_color", "#888")
            st.markdown(
                f'<div style="background:white;border:2px solid {color};border-radius:12px;'
                f'padding:1.3rem;text-align:center;margin-bottom:1rem;'
                f'box-shadow:0 3px 10px rgba(0,0,0,.06)">'
                f'<div style="font-size:.8rem;color:#888">{n1} ↔ {n2}</div>'
                f'<div style="font-family:Noto Serif KR,serif;font-size:3.2rem;'
                f'font-weight:700;color:{color};line-height:1.2">{sc}점</div>'
                f'<div style="font-size:1.1rem;font-weight:600;color:{color};margin-top:.3rem">{gh["grade"]}</div>'
                f'<div style="font-size:.9rem;color:#444;margin-top:.6rem;line-height:1.6;'
                f'background:#f8f5ec;padding:.7rem;border-radius:6px">{gh["overall"]}</div>'
                f'</div>', unsafe_allow_html=True)

            # 강점·약점 카드
            st.markdown('<div class="stitle">💎 강점 & 약점</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**💎 강점**")
                if gh["강점"]:
                    for s in gh["강점"]: st.success(s)
                else:
                    st.caption("특별한 강점 요소 없음")
            with c2:
                st.markdown("**⚠ 약점**")
                if gh["약점"]:
                    for w in gh["약점"]: st.warning(w)
                else:
                    st.caption("큰 약점 요소 없음")

            # 일지 관계 상세
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">🌟 배우자궁(일지) 관계</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="icard"><div class="icard-t">관계 유형</div>'
                f'<div class="icard-v">{gh["일지관계"]}</div>'
                f'<div style="font-size:.88rem;color:#555;margin-top:.5rem;line-height:1.6">{gh["일지해설"]}</div></div>',
                unsafe_allow_html=True)

            # 일간 천간합
            if gh["천간합해설"]:
                st.markdown(
                    f'<div class="icard"><div class="icard-t">일간 천간합</div>'
                    f'<div class="icard-v">{gh["천간합"]}</div>'
                    f'<div style="font-size:.88rem;color:#555;margin-top:.4rem">{gh["천간합해설"]}</div></div>',
                    unsafe_allow_html=True)

            # 십성 상호 시각
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">👁 서로를 바라보는 십성</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    f'<div class="icard"><div class="icard-t">{n1}이 본 {n2}</div>'
                    f'<div class="icard-v">{gh["1이2보는십성"]}</div>'
                    f'<div style="font-size:.85rem;color:#555;margin-top:.4rem">{gh["1이2보는십성해설"]}</div></div>',
                    unsafe_allow_html=True)
            with c2:
                st.markdown(
                    f'<div class="icard"><div class="icard-t">{n2}가 본 {n1}</div>'
                    f'<div class="icard-v">{gh["2가1보는십성"]}</div>'
                    f'<div style="font-size:.85rem;color:#555;margin-top:.4rem">{gh["2가1보는십성해설"]}</div></div>',
                    unsafe_allow_html=True)

            # 오행 상세
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">🌈 오행 상호작용 분석</div>', unsafe_allow_html=True)
            if gh.get("오행상세"):
                for line in gh["오행상세"]:
                    if line.startswith("✦"):
                        st.success(line)
                    elif line.startswith("⚠"):
                        st.warning(line)
                    else:
                        st.info(line)
            else:
                st.caption("오행 측면에서 특별한 보완·충돌 없음")

            # 용신 상호작용
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">🔑 용신 상호작용</div>', unsafe_allow_html=True)
            st.caption(f"{n1} 용신: **{gh['용신1']}**  |  {n2} 용신: **{gh['용신2']}**")
            for line in gh["용신상호작용"]:
                if line.startswith("✦"): st.success(line)
                else: st.caption(line)

            # 격국 비교
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">🏛 격국 비교</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="icard"><div class="icard-v" style="font-size:.92rem">{gh["격국비교"]}</div></div>',
                unsafe_allow_html=True)

            # 권장사항
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            st.markdown('<div class="stitle">💡 관계 운영 가이드</div>', unsafe_allow_html=True)
            for a in gh["권장사항"]:
                if a.startswith("✓"): st.success(a)
                elif a.startswith("⚠"): st.warning(a)
                else: st.info(a)

            # 가족 조언
            st.markdown(
                f'<div class="icard" style="border-left:4px solid #8b1a1a;margin-top:.8rem">'
                f'<div class="icard-t">가족·동거 조언</div>'
                f'<div style="font-size:.92rem;line-height:1.6;color:#333;margin-top:.3rem">{gh["가족조언"]}</div></div>',
                unsafe_allow_html=True)
        else:
            st.info("👥 2명 이상 등록 후 [상호 궁합·관계성 보기]를 활성화하세요.\n\n3명 이상이면 모든 쌍의 매트릭스가 상단에 표시됩니다.")

    with tabs[9]:  # 택일
        with st.expander("📖 택일이란?", expanded=False):
            st.markdown("""
**택일(擇日)** 은 중요한 일을 시작하기 좋은 날을 고르는 것입니다.

본인의 일간을 기준으로 매일의 일진을 비교합니다:
- ★ **대길일**: 건록일(직업운 강함)
- ✦ **길일**: 본인 일지와 합·삼합을 이루는 날
- ✕ **흉일**: 본인 일지와 충(沖)을 이루는 날·양인일

**활용**: 계약·이사·결혼·중요 회의·면접 등은 길일을 택하는 게 전통적 지혜입니다.

> 흉일이 절대적 불운은 아니지만, 중요한 결정은 가급적 피하는 게 좋다는 옛 사람들의 통계적 지혜입니다.
""")
        now = datetime.now(); cy = now.year; cm = now.month
        st.caption(f"{cy}년 {cm}월 · 일간 {r['ilgan']['stem']} 기준")
        ilgin = get_monthly_ilgin(cy, cm)
        render_택일_calendar(ilgin, r["ilgan"]["stem"], cy, cm)

    with tabs[10]:  # 성명학
        with st.expander("📖 성명학이란?", expanded=False):
            st.markdown("""
**성명학(姓名學)** 은 이름이 인생에 미치는 영향을 분석합니다. 세 가지 측면을 봅니다:

**1. 발음오행** — 한글 초성의 오행
- ㄱ·ㅋ = 목 / ㄴ·ㄷ·ㄹ·ㅌ = 화 / ㅇ·ㅎ = 토 / ㅅ·ㅈ·ㅊ = 금 / ㅁ·ㅂ·ㅍ = 수

**2. 자원오행** — 한자 자체가 가진 오행
- 木 자가 들어가면 목 기운, 火 자는 화 기운…

**3. 수리성명학 (81수리)** — 한자 획수로 4격 계산
- **원격(元格)**: 초년운
- **형격(亨格)**: 청년운
- **이격(利格)**: 중년운
- **정격(貞格)**: 말년운 (전체 총평)

> 사주에 부족한 오행이 이름에 있으면 보완 효과가 있다고 봅니다.
""")
        na = r.get("name_analysis", {})
        balam = na.get("balam_ohaeng", [])
        jawon = na.get("jawon_ohaeng", [])
        st.markdown('<div class="stitle">🔊 발음오행</div>', unsafe_allow_html=True)
        if balam:
            html = ""
            for b in balam:
                c = OHAENG_COLOR.get(b["ohaeng"], "#888")
                html += (f'<div style="display:inline-block;text-align:center;'
                         f'background:white;border:1.5px solid {c};border-radius:6px;'
                         f'padding:.6rem .9rem;margin:.3rem;min-width:70px">'
                         f'<div style="font-size:1.4rem;font-weight:700">{b["char"]}</div>'
                         f'<div style="font-size:.72rem;color:#888">{b["chosong"]}</div>'
                         f'<div style="font-size:.85rem;font-weight:600;color:{c}">{b["ohaeng"]}</div></div>')
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.info("사이드바에 한글 이름을 입력하면 발음오행이 분석됩니다.")

        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="stitle">📿 수리성명학</div>', unsafe_allow_html=True)
        render_suri(suri)

    with tabs[11]:  # 풍수
        with st.expander("📖 풍수란?", expanded=False):
            st.markdown("""
**풍수지리(風水地理)** 는 환경과 사람의 기운의 조화를 봅니다.

**본명궁(本命宮)** — 태어난 해와 성별로 정해지는 자신의 괘
- **동사택**: 감(北)·진(東)·손(東南)·이(南) 계열
- **서사택**: 건(西北)·태(西)·간(東北)·곤(西南) 계열

**8방위 길흉**
- 🟢 길방: 생기·천을·연년·복위 — 침실·공부방·사무실 좋음
- 🔴 흉방: 절명·오귀·육살·화해 — 화장실·창고 배치 권장

**삼살방·대장군방** — 해마다 바뀌는 흉방
- 이사·증축·수리 시 피하는 게 전통입니다

> 본인 체질(동사택·서사택)에 맞는 집·방향을 고르면 일이 잘 풀린다는 가르침입니다.
""")
        feng = r["fengshui"]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="icard"><div class="icard-t">본명궁</div>'
                        f'<div class="icard-v">{feng["본명궁"]}궁 · {feng["괘명"]}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            cls_c = "#2e7d32" if feng["사택"] == "동사택" else "#1565c0"
            st.markdown(f'<div class="icard"><div class="icard-t">사택</div>'
                        f'<div class="icard-v" style="color:{cls_c}">{feng["사택"]}</div></div>',
                        unsafe_allow_html=True)
        with c3:
            dirmap = feng.get("8방위", {})
            st.markdown(f'<div class="icard"><div class="icard-t">생기방(최길)</div>'
                        f'<div class="icard-v">✦ {dirmap.get("생기","?")}</div></div>',
                        unsafe_allow_html=True)
        if dirmap:
            render_compass(dirmap, feng)
        samsal = r["samsal"]
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="icard"><div class="icard-t">삼살방</div>'
                        f'<div class="icard-v" style="color:#c62828">⚠ {samsal["삼살방"]}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="icard"><div class="icard-t">대장군방</div>'
                        f'<div class="icard-v" style="color:#e65100">⚠ {samsal["대장군방"]}</div></div>',
                        unsafe_allow_html=True)
        st.warning(samsal["이사주의"])

    with tabs[12]:  # 직업·건강
        with st.expander("📖 사주로 보는 직업·건강", expanded=False):
            st.markdown("""
**직업 적성** — 사주의 용신(用神)·희신(喜神) 오행을 직업과 연결합니다.

| 오행 | 적합 분야 |
|---|---|
| 🌳 목 | 교육·의료·문화예술·법조·환경 |
| 🔥 화 | 방송·IT·마케팅·금융·요식·강사 |
| ⛰️ 토 | 부동산·건설·공무원·농업·종교 |
| ⚙️ 금 | 금융·제조·군경·의료·회계·스포츠 |
| 💧 수 | 유통·여행·연구·역학·IT(데이터) |

**건강** — 약한 오행이 약점 신체 부위
- 목 약 → 간·눈·근육
- 화 약 → 심장·혈관·정신
- 토 약 → 위장·소화기
- 금 약 → 폐·호흡기·뼈
- 수 약 → 신장·생식기·청력

> 평생 약한 오행에 해당하는 부위를 관리하면 큰 병을 피할 수 있다는 지혜입니다.
""")
        ch = r["career_health"]
        st.markdown('<div class="stitle">💼 직업 적성</div>', unsafe_allow_html=True)
        st.markdown("".join(f'<span class="tag">🏢 {j}</span>' for j in ch["추천직업"]),
                    unsafe_allow_html=True)
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'**⚠ 주의 부위** (약한: {ch["약한오행"]})')
            for h in ch["건강주의"]: st.warning(f"• {h}")
        with c2:
            st.markdown(f'**✓ 강건 부위** (강한: {ch["강한오행"]})')
            for h in ch["건강강점"]: st.success(f"• {h}")
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="icard"><div class="icard-t">행운 색상</div>'
                        f'<div class="icard-v">{"·".join(ch["행운색상"])}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="icard"><div class="icard-t">행운 방위</div>'
                        f'<div class="icard-v">{ch["행운방위"]}</div></div>',
                        unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="icard"><div class="icard-t">행운 숫자</div>'
                        f'<div class="icard-v">{ch["행운숫자"]}</div></div>',
                        unsafe_allow_html=True)

    with tabs[13]:  # 별자리
        with st.expander("📖 서양 별자리와 동양 오행의 연계", expanded=False):
            st.markdown("""
서양 점성술의 **12별자리**는 4원소(불·흙·공기·물)로 분류되며, 동양의 5행과 흥미롭게 대응됩니다.

| 서양 원소 | 동양 오행 | 별자리 |
|---|---|---|
| 🔥 불 | 화 | 양자리·사자자리·사수자리 |
| ⛰️ 흙 | 토·금 | 황소자리·처녀자리·염소자리 |
| 💨 공기 | 목 | 쌍둥이자리·천칭자리·물병자리 |
| 💧 물 | 수 | 게자리·전갈자리·물고기자리 |

**일간 오행 = 별자리 오행** 이면 → 에너지가 강하게 집중
**다르면** → 두 가지 면모를 모두 가진 다면적 성격

> 동서양 점성술이 의외로 닿는 지점이 많다는 게 흥미롭습니다.
""")
        zodiac = r["zodiac"]
        elem_c = {"불":"#e53935","흙":"#e65100","공기":"#2e7d32","물":"#1565c0"}.get(zodiac.get("element",""),"#888")
        oh_c   = OHAENG_COLOR.get(zodiac.get("ohaeng",""),"#888")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="zodiac-card">'
                f'<div style="font-size:.7rem;color:#888">서양 별자리</div>'
                f'<div style="font-size:1.5rem;font-weight:700;color:{elem_c}">'
                f'{zodiac.get("name","?")} ({zodiac.get("en","")})</div>'
                f'<div style="margin:.4rem 0">'
                f'<span class="tag" style="color:{elem_c}">원소: {zodiac.get("element","?")}</span>'
                f'<span class="tag" style="color:{oh_c}">오행: {zodiac.get("ohaeng","?")}</span></div>'
                f'<div style="font-size:.85rem;color:#555">{zodiac.get("desc","")}</div></div>',
                unsafe_allow_html=True)
        with c2:
            il_oh = r["ilgan"]["ohaeng"]; z_oh = zodiac.get("ohaeng","")
            if il_oh == z_oh:
                st.success(f"✦ 동양({il_oh})과 서양({z_oh}) 오행 일치 — 에너지가 강하게 집중됩니다.")
            else:
                st.info(f"◉ 동양 일간: {il_oh} / 서양 별자리: {z_oh}")



# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: 궁합 매트릭스
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def render_compat_matrix(results: list, pairs: dict):
    """다인원(2~N명) 상호 관계 매트릭스 — 가족·그룹 분석"""
    n     = len(results)
    names = [r["meta"]["name"] or f"인원{i+1}" for i, r in enumerate(results)]
    pair_list = [(i, j, pairs[(i,j)]) for i in range(n) for j in range(i+1, n)]

    # ── 상단 그룹 종합 패널 ──
    avg_score = sum(gh["score"] for _, _, gh in pair_list) / len(pair_list) if pair_list else 0
    best_pair = max(pair_list, key=lambda x: x[2]["score"]) if pair_list else None
    worst_pair = min(pair_list, key=lambda x: x[2]["score"]) if pair_list else None

    avg_color = "#2e7d32" if avg_score >= 70 else ("#b8860b" if avg_score >= 55 else "#c62828")

    if n >= 3:
        group_label = "👨‍👩‍👧‍👦 가족·그룹 종합 분석" if n >= 3 else "💑 두 사람 관계"
    else:
        group_label = "💑 두 사람 관계 분석"

    st.markdown(f'<div class="stitle" style="font-size:1.15rem">{group_label}</div>',
                unsafe_allow_html=True)

    # 종합 카드
    if n >= 3 and best_pair and worst_pair:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#fff5f5 0%,#fef8ec 100%);'
            f'border:2px solid {avg_color};border-radius:12px;padding:1.2rem;'
            f'margin-bottom:1rem;box-shadow:0 3px 10px rgba(0,0,0,.06)">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap">'
            f'<div><div style="font-size:.78rem;color:#666">{n}명 가족·그룹의 평균 궁합</div>'
            f'<div style="font-family:Noto Serif KR,serif;font-size:2.6rem;'
            f'font-weight:700;color:{avg_color};line-height:1">{avg_score:.1f}점</div></div>'
            f'<div style="text-align:right;font-size:.85rem">'
            f'<div style="color:#2e7d32">💎 최고: {names[best_pair[0]]}↔{names[best_pair[1]]} ({best_pair[2]["score"]}점)</div>'
            f'<div style="color:#c62828;margin-top:.2rem">⚠ 주의: {names[worst_pair[0]]}↔{names[worst_pair[1]]} ({worst_pair[2]["score"]}점)</div>'
            f'<div style="color:#666;margin-top:.2rem">총 {len(pair_list)}쌍 비교</div></div></div></div>',
            unsafe_allow_html=True)

    # ── 매트릭스 표 (N×N 격자) ──
    if n >= 3:
        st.markdown('<div class="stitle">📊 전체 관계 매트릭스</div>', unsafe_allow_html=True)
        html = '<table style="width:100%;border-collapse:collapse;margin:.7rem 0;font-size:.82rem">'
        # 헤더
        html += '<tr><th style="background:#fdf8f0;padding:.55rem;border:1px solid #d4c4a8;width:90px"></th>'
        for nm in names:
            html += f'<th style="background:#fdf8f0;padding:.55rem;border:1px solid #d4c4a8;color:#8b1a1a">{nm}</th>'
        html += '</tr>'
        # 행
        for i in range(n):
            html += f'<tr><th style="background:#fdf8f0;padding:.55rem;border:1px solid #d4c4a8;color:#8b1a1a">{names[i]}</th>'
            for j in range(n):
                if i == j:
                    html += '<td style="background:#e8e0c8;padding:.55rem;border:1px solid #d4c4a8;text-align:center;color:#888">—</td>'
                else:
                    key = (min(i,j), max(i,j))
                    gh  = pairs[key]
                    sc  = gh["score"]
                    bg  = "#e8f5e9" if sc>=70 else ("#fff8e1" if sc>=55 else ("#ffebee" if sc<40 else "#fff3e0"))
                    fg  = "#1b5e20" if sc>=70 else ("#bf360c" if sc>=55 else ("#b71c1c" if sc<40 else "#e65100"))
                    html += (
                        f'<td style="background:{bg};padding:.55rem;border:1px solid #d4c4a8;'
                        f'text-align:center;color:{fg};font-weight:600">{sc}</td>'
                    )
            html += '</tr>'
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)
        st.caption("🟢 70+ 좋음  🟡 55-69 보통  🟠 40-54 주의  🔴 ~39 신중")

    # ── 쌍별 요약 카드 ──
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="stitle">💑 쌍별 궁합 요약</div>', unsafe_allow_html=True)
    ncols = min(2, len(pair_list))
    cols  = st.columns(ncols)
    for idx, (i, j, gh) in enumerate(pair_list):
        sc   = gh["score"]
        color = gh.get("grade_color", "#888")
        oh1  = results[i]["ilgan"]["ohaeng"]; oh2 = results[j]["ilgan"]["ohaeng"]
        c1_  = OHAENG_COLOR[oh1]; c2_ = OHAENG_COLOR[oh2]
        with cols[idx % ncols]:
            st.markdown(
                f'<div style="background:white;border:1.5px solid {color};border-radius:10px;'
                f'padding:1rem;margin-bottom:.7rem;box-shadow:0 2px 8px rgba(0,0,0,.06)">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">'
                f'<span style="font-weight:700;font-size:.95rem">'
                f'<span style="color:{c1_}">{names[i]}</span>'
                f'<span style="color:#888"> ↔ </span>'
                f'<span style="color:{c2_}">{names[j]}</span></span>'
                f'<span style="font-family:Noto Serif KR,serif;font-size:1.8rem;'
                f'font-weight:700;color:{color}">{sc}</span></div>'
                f'<div style="background:#f0e8d8;border-radius:3px;height:8px;margin-bottom:.4rem">'
                f'<div style="height:100%;width:{sc}%;background:{color};border-radius:3px"></div></div>'
                f'<div style="font-size:.85rem;color:{color};font-weight:600;margin-bottom:.3rem">{gh["grade"]}</div>'
                f'<div style="font-size:.78rem;color:#444;line-height:1.5;'
                f'background:#fafaf5;padding:.4rem .6rem;border-radius:4px">{gh["overall"]}</div>'
                f'<div style="font-size:.72rem;color:#666;margin-top:.4rem">📌 일지: {gh["일지관계"]}</div></div>',
                unsafe_allow_html=True)

    # ── 쌍별 풍부한 상세 (확장 가능) ──
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown('<div class="stitle">🔍 쌍별 심층 분석</div>', unsafe_allow_html=True)
    for i, j, gh in pair_list:
        with st.expander(f"💞 {names[i]} ↔ {names[j]}  |  {gh['score']}점 · {gh['grade']}"):
            # 사주 비교
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**{names[i]}** 사주")
                render_pillar_cards(results[i])
            with c2:
                st.markdown(f"**{names[j]}** 사주")
                render_pillar_cards(results[j])

            st.markdown('<hr class="divider">', unsafe_allow_html=True)

            # 총평
            st.markdown(
                f'<div style="background:#f8f5ec;border-left:4px solid {gh.get("grade_color","#888")};'
                f'padding:.8rem 1rem;border-radius:4px;margin-bottom:.7rem">'
                f'<div style="font-size:.92rem;color:#222;line-height:1.6">{gh["overall"]}</div></div>',
                unsafe_allow_html=True)

            # 강점·약점
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**💎 강점**")
                if gh["강점"]:
                    for s in gh["강점"]: st.success(s)
                else: st.caption("특별한 강점 요소 없음")
            with c2:
                st.markdown("**⚠ 약점**")
                if gh["약점"]:
                    for w in gh["약점"]: st.warning(w)
                else: st.caption("큰 약점 요소 없음")

            # 일지·천간·십성
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(
                    f'<div class="icard"><div class="icard-t">배우자궁(일지) 관계</div>'
                    f'<div class="icard-v">{gh["일지관계"]}</div>'
                    f'<div style="font-size:.83rem;color:#555;margin-top:.4rem;line-height:1.5">{gh["일지해설"]}</div></div>',
                    unsafe_allow_html=True)
                if gh["천간합해설"]:
                    st.markdown(
                        f'<div class="icard"><div class="icard-t">일간 천간합</div>'
                        f'<div class="icard-v">{gh["천간합"]}</div>'
                        f'<div style="font-size:.82rem;color:#555;margin-top:.3rem">{gh["천간합해설"]}</div></div>',
                        unsafe_allow_html=True)
            with c2:
                st.markdown(
                    f'<div class="icard"><div class="icard-t">{names[i]}이 본 {names[j]}</div>'
                    f'<div class="icard-v">{gh["1이2보는십성"]}</div>'
                    f'<div style="font-size:.82rem;color:#555;margin-top:.3rem">{gh["1이2보는십성해설"]}</div></div>',
                    unsafe_allow_html=True)
                st.markdown(
                    f'<div class="icard"><div class="icard-t">{names[j]}가 본 {names[i]}</div>'
                    f'<div class="icard-v">{gh["2가1보는십성"]}</div>'
                    f'<div style="font-size:.82rem;color:#555;margin-top:.3rem">{gh["2가1보는십성해설"]}</div></div>',
                    unsafe_allow_html=True)

            # 오행 상세
            st.markdown("**🌈 오행 상호작용**")
            if gh.get("오행상세"):
                for line in gh["오행상세"]:
                    if line.startswith("✦"): st.success(line)
                    elif line.startswith("⚠"): st.warning(line)
                    else: st.info(line)
            else:
                st.caption("특별한 오행 상호작용 없음")

            # 용신
            st.markdown("**🔑 용신 상호작용**")
            st.caption(f"{names[i]} 용신: **{gh['용신1']}**  |  {names[j]} 용신: **{gh['용신2']}**")
            for line in gh["용신상호작용"]:
                if line.startswith("✦"): st.success(line)
                else: st.caption(line)

            # 권장사항
            st.markdown("**💡 관계 운영 가이드**")
            for a in gh["권장사항"]:
                if a.startswith("✓"): st.success(a)
                elif a.startswith("⚠"): st.warning(a)
                else: st.info(a)

            # 가족 조언
            st.markdown(
                f'<div class="icard" style="border-left:4px solid #8b1a1a;margin-top:.6rem">'
                f'<div class="icard-t">동거·가족 조언</div>'
                f'<div style="font-size:.9rem;line-height:1.6;color:#333;margin-top:.3rem">{gh["가족조언"]}</div></div>',
                unsafe_allow_html=True)

    # ── 그룹 전체 조언 (3명+) ──
    if n >= 3:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown('<div class="stitle">👨‍👩‍👧‍👦 그룹 전체 운영 조언</div>', unsafe_allow_html=True)

        # 오행 분포 그룹 분석
        group_oh = {"목":0, "화":0, "토":0, "금":0, "수":0}
        for r in results:
            for oh, sc in r["ohaeng_score"].items():
                group_oh[oh] += sc
        total = sum(group_oh.values()) or 1
        max_oh = max(group_oh, key=group_oh.get)
        min_oh = min(group_oh, key=group_oh.get)
        max_pct = group_oh[max_oh]/total*100
        min_pct = group_oh[min_oh]/total*100

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f'<div class="icard"><div class="icard-t">그룹 우세 기운</div>'
                f'<div class="icard-v" style="color:{OHAENG_COLOR[max_oh]}">{max_oh}({max_pct:.0f}%)</div>'
                f'<div style="font-size:.83rem;color:#555;margin-top:.3rem">이 그룹은 {max_oh} 성향이 강함. 같이 있을 때 이런 분위기가 자주 형성됨</div></div>',
                unsafe_allow_html=True)
        with c2:
            st.markdown(
                f'<div class="icard"><div class="icard-t">그룹 부족 기운</div>'
                f'<div class="icard-v" style="color:{OHAENG_COLOR[min_oh]}">{min_oh}({min_pct:.0f}%)</div>'
                f'<div style="font-size:.83rem;color:#555;margin-top:.3rem">{min_oh} 기운이 부족 — 의식적으로 보완하면 전체 균형이 좋아짐</div></div>',
                unsafe_allow_html=True)

        # 종합 조언
        if avg_score >= 75:
            st.success(f"💚 평균 {avg_score:.0f}점 — 매우 화목한 그룹입니다. 큰 갈등 없이 함께 잘 어울리는 인연이에요.")
        elif avg_score >= 60:
            st.info(f"💛 평균 {avg_score:.0f}점 — 무난한 그룹. 작은 노력으로 더 좋아질 수 있는 관계입니다.")
        elif avg_score >= 45:
            st.warning(f"💡 평균 {avg_score:.0f}점 — 서로의 차이가 큰 그룹. 각자의 개성을 인정하는 배려가 필요해요.")
        else:
            st.error(f"⚠ 평균 {avg_score:.0f}점 — 어울리기 어려운 조합. 거리 조절과 각자 영역 확보가 중요합니다.")

        # 그룹 조언 리스트
        group_advice = [
            f"💎 **가장 좋은 쌍**: {names[best_pair[0]]} ↔ {names[best_pair[1]]} — 이 둘이 다른 멤버를 잇는 다리 역할을 맡으면 좋아요",
            f"⚠ **주의 쌍**: {names[worst_pair[0]]} ↔ {names[worst_pair[1]]} — 직접 부딪히기보다 다른 가족을 통해 소통하면 부드러워집니다",
            f"🌟 모임이나 식사 자리는 {names[best_pair[0]]}이/가 주도하면 분위기가 좋아집니다",
            f"🏠 같은 공간에 있을 때는 {min_oh} 기운이 도는 색상/소품(예: {OHAENG_DETAIL[min_oh]['색'][0]}색)을 활용해 보세요",
        ]
        for a in group_advice:
            st.markdown(f"- {a}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RENDER: 다인원 개별 분석
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def render_individual_multi(results: list, suri_list: list, birth_years: list, pairs: dict):
    n     = len(results)
    names = [r["meta"]["name"] or f"인원{i+1}" for i, r in enumerate(results)]
    st.markdown('<div class="stitle">👤 개별 사주 정밀 분석</div>', unsafe_allow_html=True)
    person_tabs = st.tabs([f"{'👤' if i==0 else '👥'} {nm}" for i, nm in enumerate(names)])
    for i, ptab in enumerate(person_tabs):
        with ptab:
            partner_result, partner_gh = None, None
            if n == 2:
                j   = 1 - i
                key = (min(i,j), max(i,j))
                if key in pairs:
                    partner_result = results[j]
                    partner_gh     = pairs[key]
            suri = suri_list[i] if i < len(suri_list) else {}
            # ★ 각 인원의 AI 리포트도 상단에 별도 표시
            render_ai_report_section(results[i])
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
            render_15tabs(results[i], suri, birth_years[i],
                          partner_result=partner_result, partner_gh=partner_gh)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN APP  ─  상태 관리 완전 재작성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_api_key_from_file() -> str:
    """앱 시작 시 저장된 API 키 로드"""
    import pathlib, base64, json as _json
    cfg = pathlib.Path.home() / ".saju_hobbang_config.json"
    try:
        if cfg.exists():
            data = _json.loads(cfg.read_text(encoding="utf-8"))
            raw  = data.get("gemini_api_key", "")
            return base64.b64decode(raw.encode()).decode() if raw else ""
    except Exception:
        pass
    return ""

def _save_api_key_to_file(key: str):
    import pathlib, base64, json as _json
    cfg = pathlib.Path.home() / ".saju_hobbang_config.json"
    try:
        encoded = base64.b64encode(key.encode()).decode()
        cfg.write_text(_json.dumps({"gemini_api_key": encoded}), encoding="utf-8")
    except Exception:
        pass


def main():
    st.markdown(
        '<div class="saju-header"><h1>&#9775; 천명도 天命圖</h1>'
        '<div class="sub">HS사주방 v3.1 · Dynamic Multi-Slot · On-Demand AI</div>'
        '</div>', unsafe_allow_html=True)

    # ── SESSION STATE 초기화 ──────────────────────────────
    if "slot_ids" not in st.session_state:
        st.session_state.slot_ids  = [1]
        st.session_state.next_sid  = 2
    if "api_key_loaded" not in st.session_state:
        # 1순위: URL 쿼리 파라미터 (브라우저가 기억) → 2순위: 로컬 파일
        loaded = ""
        try:
            qp = st.query_params.get("k", "")
            if qp:
                import base64 as _b64
                loaded = _b64.b64decode(qp.encode()).decode()
        except Exception:
            loaded = ""
        if not loaded:
            loaded = load_api_key()
        if loaded:
            st.session_state["gemini_api_key_input"] = loaded
        st.session_state.api_key_loaded = True

    # ── SIDEBAR ──────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            '<div style="text-align:center;padding:.5rem .4rem .7rem;'
            'border-bottom:2px solid #c0392b;margin-bottom:.8rem">'
            '<div style="font-family:Noto Serif KR,serif;font-size:1.15rem;'
            'font-weight:700;color:#c0392b">🔮 HS사주방</div>'
            '<div style="font-size:.7rem;color:#888;margin-top:.2rem">v3.1 Ultimate</div>'
            '</div>', unsafe_allow_html=True)

        slot_ids = st.session_state.slot_ids
        n_slots  = len(slot_ids)
        st.markdown("### 👥 분석 대상 (" + str(n_slots) + "명)")

        delete_sid = None
        for i, sid in enumerate(slot_ids):
            label = st.session_state.get("name_" + str(sid), "") or ("인원 " + str(i+1))
            icon  = "👤" if i == 0 else "👥"
            with st.expander(icon + " " + label, expanded=(n_slots == 1)):
                if n_slots > 1:
                    if st.button("✕ 삭제", key="del_" + str(sid), use_container_width=True):
                        delete_sid = sid

                st.text_input("이름 (한글)",       key="name_"   + str(sid), placeholder="홍길동",
                              help="표시용. 사주 계산은 생년월일시만 사용합니다.")
                st.text_input("한자 이름 (선택)",   key="hanja_"  + str(sid), placeholder="洪吉東",
                              help="입력 시 자원오행·수리성명학 자동 계산")
                st.selectbox("성별", ["남성","여성"], key="gender_" + str(sid))
                st.radio("달력 종류", ["양력","음력"], horizontal=True, key="cal_" + str(sid))
                st.number_input("년도",      1900, 2025, 1990, key="year_"  + str(sid))
                st.number_input("월",        1,   12,    6,   key="month_" + str(sid))
                st.number_input("일",        1,   31,   15,   key="day_"   + str(sid))
                st.number_input("시 (0~23)", 0,   23,   12,   key="hour_"  + str(sid),
                                help="24시간제")
                st.number_input("분 (0~59)", 0,   59,    0,   key="min_"   + str(sid))
                st.selectbox("MBTI (선택)",
                             ["모름", "INTJ","INTP","ENTJ","ENTP",
                              "INFJ","INFP","ENFJ","ENFP",
                              "ISTJ","ISFJ","ESTJ","ESFJ",
                              "ISTP","ISFP","ESTP","ESFP"],
                             key="mbti_" + str(sid),
                             help="입력 시 사주×MBTI 교차 분석이 리포트에 추가됩니다")

        if delete_sid is not None:
            st.session_state.slot_ids.remove(delete_sid)
            for k in ["results","pairs","birth_years","suri_list"]:
                st.session_state.pop(k, None)
            st.rerun()

        if st.button("＋ 인원 추가", use_container_width=True):
            st.session_state.slot_ids.append(st.session_state.next_sid)
            st.session_state.next_sid += 1
            st.rerun()

        st.markdown("---")

        # 수리성명학 (각 슬롯의 한자 이름 입력 시 자동 계산됨)
        st.markdown("### 📿 수리성명학")
        st.info("💡 각 인원의 **한자 이름**을 입력하면 획수가 자동 계산되어 인원별로 적용됩니다.")
        with st.expander("한자 이름 없을 경우 수동 입력 (첫 번째 인원만)", expanded=False):
            st.caption("한자 이름이 없는 경우에만 사용하세요.")
            nc = st.radio("이름 구성", ["2글자","3글자"], index=1,
                          horizontal=True, key="n_chars_r")
            if nc == "2글자":
                strokes = [int(st.number_input("성씨", 1,81,8, key="s1")),
                           int(st.number_input("이름", 1,81,12,key="n1"))]
            else:
                strokes = [int(st.number_input("성씨",  1,81,8, key="s1")),
                           int(st.number_input("이름1", 1,81,12,key="n1")),
                           int(st.number_input("이름2", 1,81,10,key="n2"))]

        if n_slots >= 2:
            st.markdown("---")
            st.markdown("### ⚙️ 분석 모드")
            opt_indiv  = st.checkbox("개별 사주 정밀 분석", value=True,  key="opt_indiv")
            opt_matrix = st.checkbox("상호 궁합·관계성",    value=True,  key="opt_matrix")
        else:
            opt_indiv  = True
            opt_matrix = False

        st.markdown("---")
        analyze_btn = st.button("✦  사주 분석 시작", use_container_width=True)

        # Gemini API 키 (하단)
        st.markdown("---")
        st.markdown("### 🔑 Gemini API 키")
        st.text_input("API 키", type="password", placeholder="AIza...",
                      key="gemini_api_key_input",
                      help="https://aistudio.google.com → Get API Key (무료)")
        # API 키 변수 (모델 조회 버튼에서 사용)
        api_key_val = st.session_state.get("gemini_api_key_input","").strip()

        # 모델 리스트 강제 초기화 (캐시 버전 키 v3로 갱신)
        if st.session_state.get("models_cache_ver") != "v3":
            st.session_state["available_models"] = [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-3-flash",
                "gemini-flash-latest",
            ]
            st.session_state["models_cache_ver"] = "v3"

        # 안전한 인덱스 계산
        current_model = st.session_state.get("gemini_model", "")
        try:
            current_idx = st.session_state["available_models"].index(current_model)
        except ValueError:
            current_idx = 0

        st.selectbox("모델 선택",
                     st.session_state["available_models"],
                     index=current_idx, key="gemini_model",
                     help="리포트가 자꾸 잘리면 gemini-2.5-flash-lite 로 바꿔보세요")

        # ── 사용 가능 모델 자동 조회 ──
        col_q, col_r = st.columns([3, 1])
        with col_q:
            query_btn = st.button("🔍 내 API 키로 모델 조회",
                                  use_container_width=True,
                                  disabled=not api_key_val,
                                  key="query_models_btn")
        with col_r:
            reset_btn = st.button("↺", use_container_width=True,
                                  help="모델 리스트 초기화",
                                  key="reset_models_btn")

        if reset_btn:
            st.session_state.pop("available_models", None)
            st.session_state.pop("models_cache_ver", None)
            st.session_state.pop("gemini_model", None)
            st.rerun()

        if query_btn:
            try:
                genai.configure(api_key=api_key_val)
                # 모든 모델 받기
                all_models = list(genai.list_models())
                st.caption(f"📡 전체 응답: {len(all_models)}개 모델")

                EXCLUDE = ["robotics","vision","embedding","imagen","tts",
                           "aqa","learnlm","veo","audio","image-generation",
                           "thinking-exp"]
                text_models = []
                excluded   = []
                for m in all_models:
                    if "generateContent" not in m.supported_generation_methods:
                        continue
                    name = m.name.replace("models/", "")
                    nl   = name.lower()
                    if "gemini" not in nl:
                        continue
                    if any(kw in nl for kw in EXCLUDE):
                        excluded.append(name)
                        continue
                    text_models.append(name)

                # 정렬: flash > pro > 기타
                def sk(n):
                    nl = n.lower()
                    if "flash-latest" in nl: return (1, n)
                    if "flash" in nl and "8b" in nl: return (2, n)
                    if "flash" in nl: return (3, n)
                    if "pro" in nl: return (4, n)
                    return (5, n)
                text_models = sorted(set(text_models), key=sk)

                if text_models:
                    st.session_state["available_models"] = text_models
                    st.success(f"✓ 텍스트 모델 {len(text_models)}개:")
                    for tm in text_models[:6]:
                        st.caption(f"  • {tm}")
                    if excluded:
                        with st.expander(f"제외된 모델 {len(excluded)}개"):
                            for em in excluded[:15]:
                                st.caption(f"  ✕ {em}")
                    st.info("⚙ 페이지가 자동 갱신됩니다.")
                    import time; time.sleep(2)
                    st.rerun()
                else:
                    st.warning(f"⚠ 텍스트 모델 0개. 전체 {len(all_models)}개 중 generateContent 가능한 일반 모델이 없습니다.")
                    if excluded:
                        st.caption("제외된 모델 (특수 목적):")
                        for em in excluded[:10]:
                            st.caption(f"  ✕ {em}")
            except Exception as e:
                st.error(f"조회 실패: {type(e).__name__}: {str(e)[:200]}")
        c_sv, c_dl = st.columns(2)
        with c_sv:
            if st.button("💾 저장", use_container_width=True, disabled=not api_key_val):
                save_api_key(api_key_val)
                # URL 파라미터에도 저장 (브라우저가 기억 → 재접속 시 자동 로드)
                try:
                    import base64 as _b64
                    st.query_params["k"] = _b64.b64encode(api_key_val.encode()).decode()
                except Exception:
                    pass
                st.success("저장됨! 이 페이지를 즐겨찾기하면 다음에도 키가 유지됩니다.")
        with c_dl:
            if st.button("🗑 삭제", use_container_width=True, disabled=not api_key_val):
                save_api_key("")
                st.session_state["gemini_api_key_input"] = ""
                try:
                    st.query_params.clear()
                except Exception:
                    pass
                st.rerun()
        if api_key_val:
            st.success("✓ API 키 입력됨", icon="🔓")
        else:
            st.caption("🔒 미입력 시 AI 리포트만 비활성화")

    # ── 분석 실행 (버튼 클릭 시에만) ─────────────────────
    if analyze_btn:
        valid_slots = [sid for sid in st.session_state.slot_ids
                       if st.session_state.get("name_" + str(sid), "").strip()]
        if not valid_slots:
            st.warning("최소 1명의 이름을 입력해 주세요.")
            st.stop()
        with st.spinner(str(len(valid_slots)) + "명 사주 분석 중…"):
            results, birth_years, suri_list = [], [], []
            for sid in valid_slots:
                name   = st.session_state.get("name_"   + str(sid), "")
                hanja  = st.session_state.get("hanja_"  + str(sid), "")
                gender = st.session_state.get("gender_" + str(sid), "남성")
                cal    = st.session_state.get("cal_"    + str(sid), "양력")
                y  = int(st.session_state.get("year_"   + str(sid), 1990))
                m  = int(st.session_state.get("month_"  + str(sid), 6))
                d  = int(st.session_state.get("day_"    + str(sid), 15))
                h  = int(st.session_state.get("hour_"   + str(sid), 12))
                mn = int(st.session_state.get("min_"    + str(sid), 0))
                if cal == "음력":
                    y, m, d = lunar_to_solar(y, m, d)
                actual_hour = (h * 60 + mn) // 60
                r = build_saju_result(y, m, d, actual_hour, gender, name,
                                      hanja_name=hanja)
                mbti = st.session_state.get("mbti_" + str(sid), "모름")
                r["meta"]["mbti"] = mbti if mbti != "모름" else ""
                results.append(r)
                birth_years.append(y)

                # ★ 인원별 수리성명학 자동 계산 (한자 이름 입력 시)
                if hanja.strip():
                    normalized, _, _ = normalize_hanja_input(hanja)
                    auto = auto_strokes_from_hanja(normalized)
                    if auto["strokes"] and all(s > 0 for s in auto["strokes"]):
                        suri_list.append(strokes_to_suri(auto["strokes"]))
                    else:
                        suri_list.append({})
                else:
                    # 첫 번째 인원이고 사이드바 수동 입력값이 있으면 사용
                    if sid == valid_slots[0] and strokes:
                        suri_list.append(strokes_to_suri(strokes))
                    else:
                        suri_list.append({})

            pairs = {}
            if len(results) >= 2:
                for ii in range(len(results)):
                    for jj in range(ii+1, len(results)):
                        pairs[(ii,jj)] = calc_goonghap(results[ii], results[jj])
        st.session_state["results"]     = results
        st.session_state["suri_list"]   = suri_list
        st.session_state["pairs"]       = pairs
        st.session_state["birth_years"] = birth_years

    # ── 결과 렌더링 (파이썬 연산만 — API 자동 호출 없음) ──
    results     = st.session_state.get("results",     [])
    suri_list   = st.session_state.get("suri_list",   [])
    pairs       = st.session_state.get("pairs",       {})
    birth_years = st.session_state.get("birth_years", [])

    if not results:
        st.info("👈 사이드바에 생년월일시를 입력하고 [사주 분석 시작]을 눌러 주세요.")
        return

    n = len(results)
    if n == 1:
        # ★ AI 리포트를 최상단에 별도 섹션으로 표시
        render_ai_report_section(results[0])
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        render_15tabs(results[0], suri_list[0], birth_years[0])
        return

    opt_indiv  = st.session_state.get("opt_indiv",  True)
    opt_matrix = st.session_state.get("opt_matrix", True)
    if not opt_indiv and not opt_matrix:
        st.warning("사이드바에서 분석 모드를 최소 1개 선택해 주세요.")
        return

    st.markdown(
        "".join(
            '<span class="tag" style="color:' + OHAENG_COLOR[r["ilgan"]["ohaeng"]] + ';font-weight:600">' +
            r["meta"]["name"] + '(' + r["ilgan"]["ohaeng"] + ')</span>'
            for r in results),
        unsafe_allow_html=True)

    # ── 다인원 전체 복사 (궁합 + 모든 개인 리포트) ──
    def _build_full_group_text():
        lines = []
        lines.append("═══════════════════════════════")
        lines.append(f"  {n}명 종합 분석 리포트")
        lines.append("═══════════════════════════════\n")
        # 궁합 요약
        if pairs:
            lines.append("━━━ 💑 궁합 분석 ━━━\n")
            names = [r["meta"]["name"] or f"인원{i+1}" for i, r in enumerate(results)]
            for (i, j), gh in pairs.items():
                lines.append(f"[{names[i]} ↔ {names[j]}] {gh['score']}점 · {gh['grade']}")
                lines.append(f"  {gh.get('overall','')}")
                if gh.get("일지관계"):
                    lines.append(f"  · 일지관계: {gh['일지관계']}")
                if gh.get("강점"):
                    lines.append("  · 강점: " + " / ".join(s.replace("💎 ","") for s in gh["강점"]))
                if gh.get("약점"):
                    lines.append("  · 주의: " + " / ".join(w.replace("⚠ ","") for w in gh["약점"]))
                lines.append("")
        # 각 개인 AI 리포트 (생성된 것만)
        lines.append("━━━ 📜 개인별 AI 리포트 ━━━\n")
        any_report = False
        for r in results:
            ck = f"ai_report_{r['meta']['name']}_{r['meta']['birth']}"
            if ck in st.session_state:
                any_report = True
                lines.append(f"\n【 {r['meta']['name']}님 】")
                lines.append(st.session_state[ck])
                # 채팅 대화도 포함
                chk = f"chat_{r['meta']['name']}_{r['meta']['birth']}"
                if st.session_state.get(chk):
                    lines.append("\n  --- 상담 대화 ---")
                    for t in st.session_state[chk]:
                        who = "❓질문" if t["role"]=="user" else "🔮답변"
                        lines.append(f"  [{who}] {t['content']}")
                lines.append("\n" + "─"*30)
        if not any_report:
            lines.append("(아직 생성된 개인 리포트가 없습니다. 각 인원 탭에서 'AI 리포트 생성'을 먼저 눌러 주세요.)")
        return "\n".join(lines)

    full_group_text = _build_full_group_text()
    _copy_iframe(full_group_text, "📋 전체 복사 (궁합 + 모든 개인 리포트)", height=52)
    st.caption("※ 각 인원의 AI 리포트를 먼저 생성하면 복사 내용에 포함됩니다.")

    if opt_matrix:
        render_compat_matrix(results, pairs)
    if opt_indiv:
        if opt_matrix:
            st.markdown('<hr class="divider">', unsafe_allow_html=True)
        render_individual_multi(results, suri_list, birth_years, pairs)


if __name__ == "__main__":
    main()
