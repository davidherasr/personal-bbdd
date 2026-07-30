from __future__ import annotations

import html
import math
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from .config import FORMATION_TEMPLATES, ROLE_PROFILES


def safe(value: object) -> str:
    return html.escape(str(value or ""))


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ink:#152033; --muted:#667085; --line:#e4e7ec; --surface:#ffffff;
          --soft:#f7f8fb; --brand:#183a72; --accent:#d9a72e; --good:#157f58;
          --warn:#a85d00; --danger:#a93333;
        }
        .stApp {background:linear-gradient(145deg,#f4f6f9 0%,#fff 44%,#fbf7ed 100%);}
        .block-container {max-width:1440px; padding-top:1.5rem; padding-bottom:4rem;}
        [data-testid="stSidebar"] {background:#eef1f5; border-right:1px solid #dfe3e8;}
        h1,h2,h3 {color:var(--ink); letter-spacing:-.025em;}
        .hero {border:1px solid var(--line); border-radius:26px; padding:28px 30px;
          background:radial-gradient(circle at 88% 5%,rgba(242,202,98,.20),transparent 30%),#fff;
          box-shadow:0 14px 35px rgba(21,32,51,.06); margin-bottom:1.1rem;}
        .hero h1 {font-size:2.45rem; margin:.6rem 0 .6rem;}
        .hero p {font-size:1.05rem; color:var(--muted); max-width:900px; margin:0; line-height:1.65;}
        .pill {display:inline-flex; border:1px solid #d6dce5; background:#f4f6fa; border-radius:999px;
          padding:6px 13px; margin-right:8px; color:#27456f; font-size:.82rem; font-weight:700;}
        .pill.gold {background:#fff7dc; color:#775b00; border-color:#eedc9e;}
        .kpi-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:1rem 0;}
        .kpi {background:#fff;border:1px solid var(--line);border-radius:18px;padding:18px 19px;min-height:112px;
          box-shadow:0 8px 24px rgba(21,32,51,.035);}
        .kpi.good {background:#edf9f3;border-color:#ccebdc}.kpi.warn {background:#fff7ed;border-color:#f1dbc0}
        .kpi .label {color:var(--muted);font-size:.86rem}.kpi .value {color:var(--ink);font-size:2rem;font-weight:800;margin-top:10px}
        .panel {background:#fff;border:1px solid var(--line);border-radius:22px;padding:22px;margin:1rem 0;
          box-shadow:0 8px 26px rgba(21,32,51,.04);}
        .mini-grid {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;}
        .mini-card {border:1px solid var(--line);border-radius:16px;padding:16px;background:#fff;}
        .mini-card .title {font-weight:800;color:var(--ink);margin-bottom:7px}.mini-card .sub {color:var(--muted);line-height:1.5}
        .score-row {display:grid;grid-template-columns:150px 1fr 42px;align-items:center;gap:10px;margin:10px 0;}
        .score-track {height:9px;background:#e9edf3;border-radius:999px;overflow:hidden}.score-fill {height:100%;border-radius:999px;background:linear-gradient(90deg,#1d3e7a,#2f8f69)}
        .signal {display:inline-flex;border:1px solid #dfe4eb;border-radius:999px;padding:6px 10px;margin:4px 4px 0 0;background:#fff;font-size:.84rem}
        .signal.good {border-color:#b9e1cf;background:#f0fbf5;color:#126444}.signal.bad {border-color:#efc4c4;background:#fff4f4;color:#8b2f2f}
        .priority {display:inline-flex;width:45px;height:45px;align-items:center;justify-content:center;border-radius:13px;font-weight:900;font-size:1.1rem;border:1px solid #ddcf8b;background:#fff8dc;color:#6b5100}
        .empty-state {border:1px dashed #cfd6df;border-radius:20px;padding:26px;background:#fbfcfe;color:var(--muted)}
        @media(max-width:900px){.kpi-grid{grid-template-columns:repeat(2,1fr)}.mini-grid{grid-template-columns:1fr}.hero h1{font-size:2rem}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, tag1: str = "Scouting", tag2: str = "Decisión") -> None:
    st.markdown(
        f'<div class="hero"><span class="pill">{safe(tag1)}</span><span class="pill gold">{safe(tag2)}</span>'
        f'<h1>{safe(title)}</h1><p>{safe(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def kpi_grid(items: Sequence[Tuple[str, object, str]]) -> None:
    cards = []
    for label, value, tone in items:
        cards.append(f'<div class="kpi {safe(tone)}"><div class="label">{safe(label)}</div><div class="value">{safe(value)}</div></div>')
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def score_rows(items: Sequence[Tuple[str, int, str]]) -> None:
    rows = []
    for label, value, hint in items:
        rows.append(
            f'<div class="score-row"><div title="{safe(hint)}">{safe(label)}</div>'
            f'<div class="score-track"><div class="score-fill" style="width:{max(0,min(100,int(value)))}%"></div></div>'
            f'<strong>{int(value)}</strong></div>'
        )
    st.markdown(f'<div class="panel">{"".join(rows)}</div>', unsafe_allow_html=True)


def signals(positive: Iterable[str], alerts: Iterable[str]) -> None:
    positive_html = "".join(f'<span class="signal good">✓ {safe(x)}</span>' for x in positive)
    alerts_html = "".join(f'<span class="signal bad">! {safe(x)}</span>' for x in alerts)
    if not positive_html and not alerts_html:
        st.caption("Todavía no hay señales calculables.")
        return
    st.markdown(f'<div class="panel">{positive_html}{alerts_html}</div>', unsafe_allow_html=True)


def priority_block(label: str, score: object, action: str) -> None:
    st.markdown(
        f'<div class="panel" style="display:flex;gap:16px;align-items:center"><span class="priority">{safe(label)}</span>'
        f'<div><div style="color:#667085">Prioridad de decisión</div><div style="font-size:1.65rem;font-weight:900">{safe(score)}/100</div>'
        f'<div style="color:#475467;margin-top:3px">{safe(action)}</div></div></div>',
        unsafe_allow_html=True,
    )


def progress_list(title: str, rows: Sequence[Tuple[str, int]]) -> None:
    if not rows:
        return
    max_value = max(v for _, v in rows) or 1
    parts = [f'<h3>{safe(title)}</h3>']
    for label, value in rows:
        pct = max(2, round(value / max_value * 100))
        parts.append(
            f'<div style="display:flex;justify-content:space-between;margin-top:13px"><strong>{safe(label)}</strong><span>{value}</span></div>'
            f'<div class="score-track"><div class="score-fill" style="width:{pct}%"></div></div>'
        )
    st.markdown(f'<div class="panel">{"".join(parts)}</div>', unsafe_allow_html=True)


def radar_svg(criteria: Sequence[Tuple[str, float]], comparison: Sequence[Tuple[str, float]] | None = None, height: int = 470) -> None:
    if len(criteria) < 3:
        st.info("El radar necesita al menos tres métricas con datos.")
        return
    width = 720
    cx, cy, radius = 360, 225, 165
    n = len(criteria)

    def point(index: int, value: float, r: float = radius) -> Tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * index / n
        scale = max(0.0, min(100.0, value)) / 100.0
        return cx + math.cos(angle) * r * scale, cy + math.sin(angle) * r * scale

    grid = []
    for level in [20, 40, 60, 80, 100]:
        pts = [point(i, level) for i in range(n)]
        grid.append('<polygon points="{}" fill="none" stroke="#d9dfe8" stroke-width="1"/>'.format(" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)))
    axes = []
    labels = []
    for i, (label, _value) in enumerate(criteria):
        end_x, end_y = point(i, 100)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{end_x:.1f}" y2="{end_y:.1f}" stroke="#d9dfe8"/>')
        angle = -math.pi / 2 + 2 * math.pi * i / n
        lx = cx + math.cos(angle) * (radius + 32)
        ly = cy + math.sin(angle) * (radius + 32)
        anchor = "middle"
        if lx < cx - 20:
            anchor = "end"
        elif lx > cx + 20:
            anchor = "start"
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" font-size="12" fill="#344054">{safe(label)}</text>')
    primary_pts = [point(i, value) for i, (_, value) in enumerate(criteria)]
    shapes = ['<polygon points="{}" fill="rgba(24,58,114,.24)" stroke="#183a72" stroke-width="3"/>'.format(" ".join(f"{x:.1f},{y:.1f}" for x, y in primary_pts))]
    legend = '<rect x="20" y="18" width="14" height="4" fill="#183a72"/><text x="42" y="24" font-size="12" fill="#344054">Referencia</text>'
    if comparison:
        comp_map = dict(comparison)
        comp_pts = [point(i, comp_map.get(key, 0.0)) for i, (key, _value) in enumerate(criteria)]
        shapes.append('<polygon points="{}" fill="rgba(217,167,46,.15)" stroke="#d9a72e" stroke-width="3"/>'.format(" ".join(f"{x:.1f},{y:.1f}" for x, y in comp_pts)))
        legend += '<rect x="125" y="18" width="14" height="4" fill="#d9a72e"/><text x="147" y="24" font-size="12" fill="#344054">Comparación</text>'
    svg = f'''<div style="background:#fff;border:1px solid #e4e7ec;border-radius:20px;padding:8px">
    <svg viewBox="0 0 {width} 450" width="100%" height="{height}" role="img" aria-label="Radar comparativo">
      {legend}{''.join(grid)}{''.join(axes)}{''.join(shapes)}{''.join(labels)}
    </svg></div>'''
    components.html(svg, height=height + 20, scrolling=False)


def percentile_bars(items: Sequence[Tuple[str, float, int]]) -> None:
    parts = []
    for label, value, pct in items:
        parts.append(
            f'<div style="margin:14px 0"><div style="display:flex;justify-content:space-between"><strong>{safe(label)}</strong>'
            f'<span>{value:.1f} · P{pct}</span></div><div class="score-track"><div class="score-fill" style="width:{pct}%"></div></div></div>'
        )
    st.markdown(f'<div class="panel">{"".join(parts)}</div>', unsafe_allow_html=True)


def render_lineup(formation: str, slots: Mapping[str, Mapping[str, object]], height: int = 620) -> None:
    template = FORMATION_TEMPLATES.get(formation, [])
    cards = []
    for slot_key, slot_label, x, y in template:
        data = slots.get(slot_key, {})
        player = safe(data.get("player", slot_label))
        role = safe(data.get("role", ""))
        score = safe(data.get("score", ""))
        cards.append(
            f'<div class="player" style="left:{x}%;top:{100-y}%"><strong>{player}</strong>'
            f'<span>{role}</span><small>{score}</small></div>'
        )
    html_block = f'''
    <style>
      .pitch{{position:relative;height:{height-30}px;background:linear-gradient(90deg,#176a35,#1d743d);border:4px solid #d7eadc;border-radius:18px;overflow:hidden}}
      .pitch:before{{content:"";position:absolute;left:50%;top:0;bottom:0;border-left:2px solid #d7eadc}}
      .circle{{position:absolute;left:50%;top:50%;width:120px;height:120px;border:2px solid #d7eadc;border-radius:50%;transform:translate(-50%,-50%)}}
      .box{{position:absolute;top:22%;width:16%;height:56%;border:2px solid #d7eadc}}.box.left{{left:0}}.box.right{{right:0}}
      .player{{position:absolute;transform:translate(-50%,-50%);width:112px;min-height:60px;padding:8px 6px;border-radius:12px;background:#17243a;color:#fff;text-align:center;box-shadow:0 5px 12px rgba(0,0,0,.25);border:2px solid rgba(255,255,255,.35)}}
      .player strong{{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.player span{{display:block;color:#d8e4f2;font-size:10px;margin-top:3px}}.player small{{display:block;color:#f2ca62;font-size:10px;margin-top:3px}}
    </style>
    <div class="pitch"><div class="circle"></div><div class="box left"></div><div class="box right"></div>{''.join(cards)}</div>
    '''
    components.html(html_block, height=height, scrolling=False)


def empty_state(title: str, message: str) -> None:
    st.markdown(f'<div class="empty-state"><strong>{safe(title)}</strong><div style="margin-top:8px">{safe(message)}</div></div>', unsafe_allow_html=True)


def strip_plot(rows: Sequence[Tuple[str, float, str]], title: str, height: int = 390) -> None:
    if not rows:
        st.info("No hay datos para la distribución.")
        return
    width = 900
    top = 70
    bottom = height - 55
    axis_y = (top + bottom) / 2
    circles = []
    labels = []
    sorted_rows = sorted(rows, key=lambda item: item[1], reverse=True)
    for index, (name, value, group) in enumerate(sorted_rows):
        x = 55 + max(0.0, min(100.0, float(value))) / 100.0 * (width - 110)
        jitter = ((index % 7) - 3) * 13
        y = axis_y + jitter
        tone = "#183a72" if group in {"A", "B+", "B"} else "#d9a72e" if group == "C" else "#8b95a7"
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{tone}" opacity=".82"><title>{safe(name)} · {value:.1f}</title></circle>')
    for tick in range(0, 101, 20):
        x = 55 + tick / 100 * (width - 110)
        labels.append(f'<line x1="{x:.1f}" y1="{top-5}" x2="{x:.1f}" y2="{bottom+5}" stroke="#e2e6ec"/><text x="{x:.1f}" y="{bottom+28}" text-anchor="middle" font-size="12" fill="#667085">{tick}</text>')
    svg = f'''<div style="background:#fff;border:1px solid #e4e7ec;border-radius:20px;padding:10px">
      <svg viewBox="0 0 {width} {height}" width="100%" height="{height}">
        <text x="28" y="30" font-size="18" font-weight="700" fill="#152033">{safe(title)}</text>
        {''.join(labels)}<line x1="55" y1="{axis_y}" x2="{width-55}" y2="{axis_y}" stroke="#c7ced8" stroke-width="2"/>{''.join(circles)}
      </svg></div>'''
    components.html(svg, height=height + 20, scrolling=False)
