"""
Eco Command Center visual system for DrainGuard AI.

Palette: warm ivory canvas, white surfaces, forest-green sidebar, emerald accents,
sage secondary surfaces. Red is reserved for critical alerts and error states.
High-priority findings use amber. All user text is escaped before HTML rendering.
"""

import html

import streamlit as st

# Palette
BG = "#F5F7F2"
SURFACE = "#FFFFFF"
FOREST = "#244C3A"
EMERALD = "#16845B"
SAGE = "#E6EEE4"
TEXT = "#202923"
MUTED = "#68766C"
BORDER = "#DCE4D8"
AMBER = "#B7791F"
RED = "#C24141"
SUCCESS = "#237547"
GRID = "#E3EAE0"

# Priority tiers mapped onto the palette.
PRIORITY_TONE = {"High": "high", "Medium": "medium", "Low": "low"}
PRIORITY_COLORS = {"High": AMBER, "Medium": "#8A9A8E", "Low": SUCCESS}
ACCENT = EMERALD

ICONS = {
    "drop": '<path d="M12 3s6 6.2 6 10.2A6 6 0 0 1 6 13.2C6 9.2 12 3 12 3z"/>',
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4h6v3H9z"/><path d="M9 13l2 2 4-4"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    "alert": '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17v.5"/>',
}

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {{
  --dg-bg: {BG}; --dg-surface: {SURFACE}; --dg-forest: {FOREST}; --dg-emerald: {EMERALD};
  --dg-sage: {SAGE}; --dg-text: {TEXT}; --dg-muted: {MUTED}; --dg-border: {BORDER};
}}

html, body, [class*="css"], .stApp {{
  font-family: 'Inter', -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: var(--dg-text);
}}
.stApp {{ background: var(--dg-bg); }}
header[data-testid="stHeader"] {{ background: var(--dg-bg); }}
.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1360px; }}
h1 {{ font-size: 1.7rem !important; font-weight: 650 !important; color: var(--dg-text); letter-spacing: -0.01em; }}
h2, h3 {{ color: var(--dg-text); font-weight: 600 !important; }}
#MainMenu, footer {{ visibility: hidden; }}

/* Sidebar: forest green with white navigation */
section[data-testid="stSidebar"] {{ background: {FOREST}; border-right: none; }}
section[data-testid="stSidebar"] * {{ color: #FFFFFF; }}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,.15); }}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ color: rgba(255,255,255,.72) !important; font-size: .78rem; }}
.dg-brand {{ display: flex; align-items: center; gap: .6rem; padding: .25rem 0 1.1rem 0; }}
.dg-brand-name {{ font-weight: 700; font-size: 1.02rem; color: #FFFFFF; line-height: 1.2; }}
.dg-brand-sub {{ font-size: .7rem; color: rgba(255,255,255,.72); text-transform: uppercase; letter-spacing: .08em; margin-top: 2px; }}
section[data-testid="stSidebar"] [role="radiogroup"] > label {{
  padding: .55rem .75rem; border-radius: 8px; margin: 2px 0; cursor: pointer;
  border-left: 3px solid transparent; transition: background .15s ease;
}}
section[data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background: rgba(255,255,255,.07); }}
section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {{
  background: rgba(255,255,255,.14); border-left: 3px solid #5BD3A0;
}}
section[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p {{ font-weight: 600; }}

/* Page header */
.dg-page-sub {{ color: var(--dg-muted); font-size: .92rem; margin: -.5rem 0 1.4rem 0; }}
.dg-section {{ font-size: .76rem; color: var(--dg-muted); text-transform: uppercase; letter-spacing: .08em; margin: 1.5rem 0 .7rem 0; font-weight: 600; }}
.dg-chart-title {{ font-size: .86rem; color: var(--dg-text); font-weight: 600; margin-bottom: .4rem; }}

/* Cards */
.dg-card {{
  background: var(--dg-surface); border: 1px solid var(--dg-border); border-radius: 12px;
  padding: 1.05rem 1.15rem; height: 100%; box-shadow: 0 1px 2px rgba(32,41,35,.05);
}}
.dg-card-head {{ display: flex; justify-content: space-between; align-items: flex-start; }}
.dg-icon {{ width: 36px; height: 36px; border-radius: 10px; background: var(--dg-sage); display: flex; align-items: center; justify-content: center; }}
.dg-metric-label {{ color: var(--dg-muted); font-size: .76rem; text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }}
.dg-metric-value {{ color: var(--dg-text); font-size: 1.9rem; font-weight: 650; line-height: 1.15; margin-top: .45rem; }}
.dg-metric-hint {{ color: var(--dg-muted); font-size: .78rem; margin-top: .3rem; }}
.dg-feed-card {{ padding: .35rem 1.15rem; }}
.dg-feed-item {{ display: flex; justify-content: space-between; gap: 1rem; align-items: center; padding: .8rem 0; border-bottom: 1px solid var(--dg-border); }}
.dg-feed-item:last-child {{ border-bottom: none; }}
.dg-feed-title {{ color: var(--dg-text); font-weight: 600; font-size: .92rem; }}
.dg-feed-meta {{ color: var(--dg-muted); font-size: .78rem; margin-top: 2px; }}

/* Badges */
.dg-badge {{ display: inline-block; padding: .14rem .6rem; border-radius: 999px; font-size: .72rem; font-weight: 600; border: 1px solid; white-space: nowrap; }}
.dg-badge-high {{ color: #8A5A12; border-color: rgba(183,121,31,.5); background: rgba(183,121,31,.12); }}
.dg-badge-medium {{ color: #4F5F54; border-color: #C9D5C9; background: {SAGE}; }}
.dg-badge-low {{ color: {SUCCESS}; border-color: rgba(35,117,71,.4); background: rgba(35,117,71,.09); }}
.dg-badge-critical {{ color: #A83232; border-color: rgba(194,65,65,.45); background: rgba(194,65,65,.09); }}
.dg-badge-neutral {{ color: var(--dg-muted); border-color: var(--dg-border); background: {SURFACE}; }}
.dg-badge-accent {{ color: {EMERALD}; border-color: rgba(22,132,91,.4); background: rgba(22,132,91,.09); }}

/* Empty states and banners */
.dg-empty {{ background: {SURFACE}; border: 1px dashed #C6D3C4; border-radius: 12px; padding: 1.7rem; text-align: center; color: var(--dg-muted); }}
.dg-empty-title {{ color: var(--dg-text); font-weight: 600; margin-bottom: .3rem; }}
.dg-banner {{ border: 1px solid #C6D8C9; background: {SAGE}; color: {FOREST}; border-radius: 10px; padding: .65rem .95rem; font-size: .86rem; margin-bottom: 1rem; }}
.dg-warn {{ border: 1px solid rgba(183,121,31,.35); background: rgba(183,121,31,.08); color: #6B4610; }}

/* Buttons and inputs */
.stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{ border-radius: 8px; border: 1px solid var(--dg-border); }}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
  background: {EMERALD}; color: #FFFFFF; border: none; font-weight: 600;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{ background: {FOREST}; color: #FFFFFF; }}
[data-testid="stFileUploader"] section {{ background: {SURFACE}; border: 1px dashed #C6D3C4; border-radius: 12px; }}
div[data-testid="stForm"] {{ background: {SURFACE}; border: 1px solid var(--dg-border); border-radius: 12px; padding: 1.2rem 1.3rem; }}
div[data-testid="stDataFrame"] {{ border: 1px solid var(--dg-border); border-radius: 10px; overflow: hidden; background: {SURFACE}; }}
div[data-testid="stExpander"] {{ background: {SURFACE}; border: 1px solid var(--dg-border); border-radius: 12px; }}
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def _svg(name: str, size: int = 18, color: str = EMERALD) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f'{ICONS[name]}</svg>'
    )


def inject_css() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def sidebar_brand() -> None:
    st.sidebar.markdown(
        '<div class="dg-brand">'
        f'{_svg("drop", 30, "#5BD3A0")}'
        '<div><div class="dg-brand-name">DrainGuard AI</div>'
        '<div class="dg-brand-sub">by PrimeOps · Prototype</div></div></div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f'<div class="dg-page-sub">{esc(subtitle)}</div>', unsafe_allow_html=True)


def section(label: str) -> None:
    st.markdown(f'<div class="dg-section">{esc(label)}</div>', unsafe_allow_html=True)


def badge(text: str, tone: str = "neutral") -> str:
    return f'<span class="dg-badge dg-badge-{esc(tone)}">{esc(text)}</span>'


def priority_badge(priority: str) -> str:
    return badge(priority, PRIORITY_TONE.get(priority, "neutral"))


def metric_card(label: str, value, hint: str = "", icon: str | None = None) -> None:
    icon_html = f'<div class="dg-icon">{_svg(icon)}</div>' if icon else ""
    st.markdown(
        f'<div class="dg-card"><div class="dg-card-head"><div>'
        f'<div class="dg-metric-label">{esc(label)}</div>'
        f'<div class="dg-metric-value">{esc(value)}</div></div>{icon_html}</div>'
        f'<div class="dg-metric-hint">{esc(hint)}</div></div>',
        unsafe_allow_html=True,
    )


def feed_item(title: str, meta: str, badge_html: str) -> str:
    return (
        '<div class="dg-feed-item"><div>'
        f'<div class="dg-feed-title">{esc(title)}</div>'
        f'<div class="dg-feed-meta">{esc(meta)}</div></div>'
        f'<div>{badge_html}</div></div>'
    )


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="dg-empty"><div class="dg-empty-title">{esc(title)}</div>{esc(body)}</div>',
        unsafe_allow_html=True,
    )


def banner(text: str, warn: bool = False) -> None:
    cls = "dg-banner dg-warn" if warn else "dg-banner"
    st.markdown(f'<div class="{cls}">{esc(text)}</div>', unsafe_allow_html=True)


def style_figure(fig, height: int = 320):
    """Light, transparent chart style using the Eco Command Center palette."""
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT),
        height=height,
        margin=dict(t=10, r=10, b=10, l=10),
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=BORDER)
    return fig
