#!/usr/bin/env python3
"""Render every SVG in ``assets/`` from one source of truth.

The README leans on hand-tuned SVG rather than screenshots, and every graphic
ships in a dark and a light variant so it reads correctly in both GitHub
themes. Keeping the two variants in sync by hand is a losing game, so they are
generated: one geometry description, two palettes.

Usage::

    python tools/assets/render_assets.py            # write assets/*.svg
    python tools/assets/render_assets.py --check    # fail if any file is stale

``--check`` is what CI runs, so a hand-edit to assets/ that was never mirrored
into this file gets caught at review time instead of drifting silently.

Zero third-party dependencies on purpose: this has to run on a clean checkout
with nothing but a Python interpreter.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "assets"


# --------------------------------------------------------------------------
# Palettes
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Palette:
    """Colour roles, defined once per theme.

    Role names describe *function* (``accent``, ``danger``, ``panel``) rather
    than colour, so the light palette can reassign hues without every call site
    having to care which theme it is drawing.
    """

    name: str
    bg0: str
    bg1: str
    bg2: str
    panel: str
    panel_opacity: str
    stroke: str
    text: str
    muted: str
    dim: str
    cyan: str
    cyan_bright: str
    blue: str
    green: str
    amber: str
    danger: str
    grid: str
    grid_opacity: str
    edge_opacity: str


DARK = Palette(
    name="dark",
    bg0="#050B16",
    bg1="#0A1526",
    bg2="#0F1F35",
    panel="#0B1526",
    panel_opacity="0.72",
    stroke="#1E293B",
    text="#E2E8F0",
    muted="#94A3B8",
    dim="#64748B",
    cyan="#22D3EE",
    cyan_bright="#67E8F9",
    blue="#3B82F6",
    green="#34D399",
    amber="#FBBF24",
    danger="#F87171",
    grid="#3B82F6",
    grid_opacity="0.075",
    edge_opacity="0.85",
)

LIGHT = Palette(
    name="light",
    bg0="#FFFFFF",
    bg1="#F1F5F9",
    bg2="#E2E8F0",
    panel="#FFFFFF",
    panel_opacity="0.88",
    stroke="#CBD5E1",
    text="#0F172A",
    muted="#475569",
    dim="#64748B",
    cyan="#0891B2",
    cyan_bright="#06B6D4",
    blue="#2563EB",
    green="#059669",
    amber="#B45309",
    danger="#DC2626",
    grid="#2563EB",
    grid_opacity="0.07",
    edge_opacity="0.55",
)

MONO = "'SF Mono', 'JetBrains Mono', Consolas, 'Courier New', monospace"
SANS = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def esc(text: str) -> str:
    """XML-escape a string bound for a text node or attribute."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def chip_width(label: str) -> float:
    """Pill width for a 13px/600 sans label.

    The constants are lifted from the profile README's hero so chips in this
    repo line up visually with the ones over there.
    """
    return round(30.05 + 7.15 * len(label), 1)


def mono_width(text: str, size: float) -> float:
    """Advance width of a monospace run. 0.6em per glyph is close enough for
    layout maths and never wrong in a way a reader would notice."""
    return len(text) * size * 0.6


def chip(x: float, y: float, label: str, dot: str, p: Palette, delay: float) -> str:
    """One rounded capability pill with a coloured status dot."""
    w = chip_width(label)
    return f"""      <g class="fade" style="animation-delay:{delay}s">
        <rect x="{x}" y="{y}" width="{w}" height="30" rx="15" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.stroke}" stroke-width="1"/>
        <circle cx="{x + 15}" cy="{y + 15}" r="3" fill="{dot}"/>
        <text x="{x + 26}" y="{y + 20}" font-family="{SANS}" font-size="13" font-weight="600" fill="{p.text}">{esc(label)}</text>
      </g>"""


def chip_row(x0: float, y: float, labels: list[tuple[str, str]], p: Palette, delay0: float) -> str:
    """Lay chips left to right with a fixed 8px gutter, staggering the fades."""
    out: list[str] = []
    x = x0
    for i, (label, dot) in enumerate(labels):
        out.append(chip(x, y, label, dot, p, round(delay0 + i * 0.09, 2)))
        x += chip_width(label) + 8
    return "\n".join(out)


# --------------------------------------------------------------------------
# Shared SVG fragments
# --------------------------------------------------------------------------


def backdrop_defs(p: Palette, prefix: str) -> str:
    """Gradients, patterns and filters shared by the card-style graphics."""
    return f"""    <linearGradient id="{prefix}Bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="{p.bg0}"/><stop offset="52%" stop-color="{p.bg1}"/><stop offset="100%" stop-color="{p.bg2}"/></linearGradient>
    <linearGradient id="{prefix}Title" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="{p.cyan_bright}"/><stop offset="48%" stop-color="{p.blue}"/><stop offset="100%" stop-color="{p.green}"/><animate attributeName="x1" values="-40%;60%;-40%" dur="9s" repeatCount="indefinite"/><animate attributeName="x2" values="60%;160%;60%" dur="9s" repeatCount="indefinite"/></linearGradient>
    <linearGradient id="{prefix}Edge" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="{p.cyan}" stop-opacity="{p.edge_opacity}"/><stop offset="50%" stop-color="{p.blue}" stop-opacity="0.45"/><stop offset="100%" stop-color="{p.green}" stop-opacity="0.8"/></linearGradient>
    <linearGradient id="{prefix}Rule" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="{p.cyan}"/><stop offset="100%" stop-color="{p.green}" stop-opacity="0"/></linearGradient>
    <linearGradient id="{prefix}Scan" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="{p.cyan_bright}" stop-opacity="0"/><stop offset="50%" stop-color="{p.cyan_bright}" stop-opacity="0.40"/><stop offset="100%" stop-color="{p.cyan_bright}" stop-opacity="0"/></linearGradient>
    <radialGradient id="{prefix}OrbC" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="{p.cyan}" stop-opacity="0.50"/><stop offset="100%" stop-color="{p.cyan}" stop-opacity="0"/></radialGradient>
    <radialGradient id="{prefix}OrbG" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="{p.green}" stop-opacity="0.50"/><stop offset="100%" stop-color="{p.green}" stop-opacity="0"/></radialGradient>
    <radialGradient id="{prefix}OrbB" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="{p.blue}" stop-opacity="0.50"/><stop offset="100%" stop-color="{p.blue}" stop-opacity="0"/></radialGradient>
    <pattern id="{prefix}Grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0v40" fill="none" stroke="{p.grid}" stroke-opacity="{p.grid_opacity}" stroke-width="1"/></pattern>
    <filter id="{prefix}Glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    <filter id="{prefix}Blur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="26"/></filter>"""


ANIMATION_CSS = """    .fade{animation:fadeIn .7s ease-out backwards}
    .type{animation:type 1.45s steps(28,end) .35s backwards}
    .wipe{animation:wipe .95s cubic-bezier(.16,.9,.24,1) 1.9s backwards}
    .wipe2{animation:wipe .95s cubic-bezier(.16,.9,.24,1) 2.15s backwards}
    .grow{transform-box:fill-box;transform-origin:left center;animation:grow .8s cubic-bezier(.16,.9,.24,1) 2.7s backwards}
    .drift-a{animation:driftA 13s ease-in-out infinite}
    .drift-b{animation:driftB 17s ease-in-out infinite}
    .drift-c{animation:driftC 11s ease-in-out infinite}
    .grid-pan{animation:gridPan 22s linear infinite}
    .scan{animation:scan 7.5s cubic-bezier(.5,0,.5,1) infinite}
    .caret{animation:blink 1.06s steps(1,end) 1.8s infinite}
    .role{animation:role 17.6s linear infinite}
    .beat{animation:beat 2.6s ease-in-out infinite}
    .live{animation:live 2.2s ease-in-out infinite}
    .wave{animation:wave 5.5s linear infinite}
    .climb{animation:climb 4.4s cubic-bezier(.5,0,.5,1) infinite}
    .reject{animation:reject 4.4s ease-in-out infinite}
    @keyframes fadeIn{from{opacity:0}}
    @keyframes type{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
    @keyframes wipe{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
    @keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
    @keyframes driftA{0%,100%{transform:translate(0,0)}50%{transform:translate(26px,-20px)}}
    @keyframes driftB{0%,100%{transform:translate(0,0)}50%{transform:translate(-30px,18px)}}
    @keyframes driftC{0%,100%{transform:translate(0,0)}50%{transform:translate(16px,24px)}}
    @keyframes gridPan{to{transform:translate(-40px,-40px)}}
    @keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
    @keyframes role{0%,1%{opacity:0}3%,22%{opacity:1}25%,100%{opacity:0}}
    @keyframes beat{0%,100%{opacity:.35}50%{opacity:.9}}
    @keyframes live{0%,100%{opacity:.35}50%{opacity:1}}
    @keyframes wave{to{transform:translateX(-216px)}}"""

REDUCED_MOTION = """    @media (prefers-reduced-motion: reduce){
      .fade,.type,.wipe,.wipe2,.grow,.drift-a,.drift-b,.drift-c,.grid-pan,.scan,.caret,.role,.beat,.live,.wave,.climb,.reject,.flow,.pulse,.tick{animation:none}
    }"""


def terminal_bar(x: float, y: float, width: float, host: str, command: str, p: Palette) -> str:
    """macOS-style window chrome with a typed command. Sets the tone before the
    reader has read a single word: this is a thing you run."""
    return f"""      <g transform="translate({x},{y})" font-family="{MONO}">
        <rect x="-14" y="-24" width="{width}" height="34" rx="9" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.stroke}" stroke-width="1"/>
        <circle cx="2" cy="-7" r="4.1" fill="#FF5F57"/>
        <circle cx="17" cy="-7" r="4.1" fill="#FEBC2E"/>
        <circle cx="32" cy="-7" r="4.1" fill="#28C840"/>
        <text x="52" y="-3" font-size="12.5" fill="{p.muted}">{esc(host)}</text>
        <text x="0" y="34" font-size="14.5" fill="{p.green}">$</text>
        <g class="type">
          <text x="14" y="34" font-size="14.5" fill="{p.text}">{esc(command)}</text>
        </g>
        <rect class="caret" x="{round(18 + mono_width(command, 14.5), 1)}" y="21" width="8.5" height="17" fill="{p.cyan}" opacity="0"/>
      </g>"""


def can_wave(x: float, y: float, p: Palette, label: str = "CAN-FD 2 Mbps") -> str:
    """A scrolling square wave. Reads as bus traffic without pretending to be a
    real capture of anything."""
    tooth = (
        "M0 22 h12 V8 h16 V22 h10 V8 h8 V22 h20 V8 h12 V22 h14 V8 h18 V22 h10 "
        "V8 h14 V22 h16 V8 h10 V22 h16 V8 h12 V22 h8"
    )
    return f"""        <g transform="translate({x},{y})">
          <g clip-path="url(#hWaveClip)">
            <g class="wave">
              <path d="{tooth}" fill="none" stroke="{p.cyan}" stroke-opacity="0.85" stroke-width="1.6"/>
              <g transform="translate(216,0)"><path d="{tooth}" fill="none" stroke="{p.cyan}" stroke-opacity="0.85" stroke-width="1.6"/></g>
            </g>
          </g>
          <text x="216" y="2" text-anchor="end" font-family="{MONO}" font-size="9" letter-spacing="2" fill="{p.dim}">{esc(label)}</text>
        </g>"""


def trust_chain(cx: float, top: float, p: Palette) -> str:
    """The chain-of-trust column: fuses at the bottom, then ROM, SBL and APP,
    each verifying the one above it.

    The rejected downgrade is the point of the graphic. A boot chain that only
    ever succeeds is a diagram; a boot chain refusing a correctly signed image
    because its security version sits behind the monotonic counter is the demo.
    """
    w = 214.0
    x = cx - w / 2
    pitch, plate = 70, 54
    stages = [
        ("APP", "app.bin  ·  SVN 4", p.green, 0.0),
        ("SBL", "sbl.bin  ·  SVN 3", p.cyan, 1.1),
        ("BootROM", "immutable  ·  root of trust", p.blue, 2.2),
    ]
    parts: list[str] = [
        '      <g class="fade" style="animation-delay:2.9s">',
        f'        <text x="{cx}" y="{top - 56}" text-anchor="middle" font-family="{MONO}" font-size="10.5" letter-spacing="3.2" fill="{p.dim}">CHAIN OF TRUST</text>',
    ]
    for i, (name, sub, colour, delay) in enumerate(stages):
        y = top + i * pitch
        parts.append(
            f"""        <g>
          <rect x="{x}" y="{y}" width="{w}" height="{plate}" rx="12" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{colour}" stroke-opacity="0.42" stroke-width="1.2"/>
          <rect x="{x}" y="{y}" width="4" height="{plate}" rx="2" fill="{colour}"/>
          <text x="{x + 18}" y="{y + 23}" font-family="{SANS}" font-size="14.5" font-weight="700" fill="{p.text}">{esc(name)}</text>
          <text x="{x + 18}" y="{y + 41}" font-family="{MONO}" font-size="10.5" fill="{p.muted}">{esc(sub)}</text>
          <circle class="beat" cx="{x + w - 20}" cy="{y + 27}" r="4.2" fill="{colour}" style="animation-delay:{delay}s"/>
        </g>"""
        )
        if i < len(stages) - 1:
            arrow_y = y + plate
            parts.append(
                f"""        <g>
          <path d="M{cx} {arrow_y + 14} V{arrow_y + 3}" stroke="{p.cyan}" stroke-opacity="0.5" stroke-width="1.6"/>
          <path d="M{cx - 4.5} {arrow_y + 8} L{cx} {arrow_y + 2} L{cx + 4.5} {arrow_y + 8}" fill="none" stroke="{p.cyan}" stroke-opacity="0.75" stroke-width="1.6" stroke-linecap="round"/>
          <text x="{cx + 12}" y="{arrow_y + 13}" font-family="{MONO}" font-size="9.5" letter-spacing="1.4" fill="{p.dim}">verify</text>
        </g>"""
            )
    fuse_y = top + 3 * pitch + 6
    parts.append(
        f"""        <g>
          <rect x="{x}" y="{fuse_y}" width="{w}" height="30" rx="8" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.stroke}" stroke-width="1"/>
          <text x="{x + 14}" y="{fuse_y + 19}" font-family="{MONO}" font-size="10" letter-spacing="1.2" fill="{p.dim}">OTP</text>
          <g>
            <rect x="{x + 48}" y="{fuse_y + 10}" width="9" height="10" rx="2" fill="{p.amber}" opacity="0.9"/>
            <rect x="{x + 61}" y="{fuse_y + 10}" width="9" height="10" rx="2" fill="{p.amber}" opacity="0.9"/>
            <rect x="{x + 74}" y="{fuse_y + 10}" width="9" height="10" rx="2" fill="{p.amber}" opacity="0.9"/>
            <rect x="{x + 87}" y="{fuse_y + 10}" width="9" height="10" rx="2" fill="{p.amber}" opacity="0.35"/>
            <rect x="{x + 100}" y="{fuse_y + 10}" width="9" height="10" rx="2" fill="{p.amber}" opacity="0.35"/>
          </g>
          <text x="{x + w - 14}" y="{fuse_y + 19}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{p.muted}">counter = 3</text>
        </g>"""
    )
    parts.append(
        f"""        <g class="reject">
          <rect x="{x + 4}" y="{top - 42}" width="{w - 8}" height="26" rx="8" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.danger}" stroke-opacity="0.6" stroke-width="1.2"/>
          <circle cx="{x + 22}" cy="{top - 29}" r="3.6" fill="{p.danger}"/>
          <text x="{x + 34}" y="{top - 24.5}" font-family="{MONO}" font-size="10" letter-spacing="0.6" fill="{p.danger}">REJECT · SVN_ROLLBACK</text>
        </g>"""
    )
    parts.append("      </g>")
    return "\n".join(parts)


# --------------------------------------------------------------------------
# hero.svg
# --------------------------------------------------------------------------

HERO_ROLES = [
    "Secure boot  ·  chain of trust, rollback protection, measured boot",
    "AUTOSAR SecOC  ·  CMAC, freshness, replay that actually replays",
    "ISO/SAE 21434  ·  TARA with traceability you can query",
    "Key lifecycle  ·  generation to destruction, audited end to end",
]

HERO_CHIPS = [
    ("Secure Boot", "cyan"),
    ("SecOC", "green"),
    ("Key Lifecycle", "blue"),
    ("TARA / 21434", "cyan"),
    ("IVN Gateway", "green"),
    ("Firmware Validation", "blue"),
]


def render_hero(p: Palette) -> str:
    dot = {"cyan": p.cyan, "green": p.green, "blue": p.blue}
    roles = "\n".join(
        f"""        <text class="role" x="0" y="0" opacity="{1 if i == 0 else 0}" style="animation-delay:{round(3.2 + i * 4.4, 1)}s"><tspan fill="{p.cyan}">&gt;</tspan> {esc(r)}</text>"""
        for i, r in enumerate(HERO_ROLES)
    )
    chips = chip_row(56, 336, [(label, dot[k]) for label, k in HERO_CHIPS], p, 3.5)
    aria = (
        "Automotive ECU Cybersecurity Lab — six buildable projects covering secure boot, "
        "AUTOSAR SecOC, ECU key lifecycle, ISO/SAE 21434 TARA, in-vehicle network defence, "
        "and firmware security validation."
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="440" viewBox="0 0 1280 440" role="img" aria-label="{esc(aria)}">
  <title>Automotive ECU Cybersecurity Lab</title>
  <defs>
{backdrop_defs(p, "h")}
    <clipPath id="hCard"><rect width="1280" height="440" rx="24"/></clipPath>
    <clipPath id="hWaveClip"><rect x="0" y="0" width="216" height="30"/></clipPath>
  </defs>
  <style>
{ANIMATION_CSS}
    @keyframes scan{{0%{{transform:translateY(-90px);opacity:1}}100%{{transform:translateY(530px);opacity:1}}}}
    @keyframes climb{{0%{{opacity:0;transform:translateY(0)}}12%{{opacity:1}}88%{{opacity:1}}100%{{opacity:0;transform:translateY(-148px)}}}}
    @keyframes reject{{0%,58%{{opacity:0}}66%,92%{{opacity:1}}100%{{opacity:0}}}}
{REDUCED_MOTION}
  </style>
  <g clip-path="url(#hCard)">
    <rect width="1280" height="440" fill="url(#hBg)"/>
    <g class="grid-pan"><rect x="-40" y="-40" width="1360" height="520" fill="url(#hGrid)"/></g>
    <g filter="url(#hBlur)">
      <circle class="drift-a" cx="150" cy="120" r="150" fill="url(#hOrbC)"/>
      <circle class="drift-b" cx="1080" cy="330" r="170" fill="url(#hOrbG)"/>
      <circle class="drift-c" cx="640" cy="60" r="140" fill="url(#hOrbB)"/>
    </g>
    <rect class="scan" x="0" y="0" width="1280" height="90" fill="url(#hScan)" opacity="0"/>

{terminal_bar(56, 52, 392, "micheal@ecu-lab — zsh", "make demo PROJECT=secure-boot", p)}

    <g class="wipe" transform="translate(56,144)">
      <text x="0" y="0" font-family="{SANS}" font-size="52" font-weight="800" letter-spacing="-0.5" fill="url(#hTitle)" filter="url(#hGlow)">AUTOMOTIVE ECU</text>
    </g>
    <g class="wipe2" transform="translate(56,196)">
      <text x="0" y="0" font-family="{SANS}" font-size="52" font-weight="800" letter-spacing="-0.5" fill="url(#hTitle)" filter="url(#hGlow)">CYBERSECURITY LAB</text>
    </g>
    <rect class="grow" x="56" y="214" width="320" height="4" rx="2" fill="url(#hRule)"/>

    <g transform="translate(58,248)" font-family="{MONO}" font-size="15" fill="{p.muted}">
{roles}
    </g>

    <g class="fade" style="animation-delay:3.0s">
      <rect x="56" y="268" width="800" height="42" rx="11" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.cyan}" stroke-opacity="0.28" stroke-width="1"/>
      <text x="76" y="295" font-family="{SANS}" font-size="15" fill="{p.text}">Six buildable projects across the automotive product-security lifecycle — spec, plan, and definition of done for each.</text>
    </g>

{chips}

{trust_chain(1078, 118, p)}

    <g class="fade" style="animation-delay:3.7s">
      <rect x="40" y="382" width="1200" height="44" rx="13" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.stroke}" stroke-width="1"/>
      <circle class="live" cx="66" cy="404" r="4.2" fill="{p.green}"/>
      <text x="80" y="409" font-family="{MONO}" font-size="12" letter-spacing="1.6" fill="{p.green}">6 PROJECTS</text>
      <line x1="186" y1="393" x2="186" y2="415" stroke="{p.stroke}" stroke-width="1"/>
      <text x="204" y="409" font-family="{MONO}" font-size="12" fill="{p.muted}">56 build phases</text>
      <line x1="336" y1="393" x2="336" y2="415" stroke="{p.stroke}" stroke-width="1"/>
      <text x="354" y="409" font-family="{MONO}" font-size="12" fill="{p.muted}">114 acceptance criteria</text>
      <line x1="576" y1="393" x2="576" y2="415" stroke="{p.stroke}" stroke-width="1"/>
      <text x="594" y="409" font-family="{MONO}" font-size="12" fill="{p.amber}">simulation-based — stated up front, every time</text>
{can_wave(1004, 393, p)}
    </g>
  </g>
  <rect x="1" y="1" width="1278" height="438" rx="23" fill="none" stroke="url(#hEdge)" stroke-width="1.6"/>
</svg>
"""


# --------------------------------------------------------------------------
# hero-compact.svg — narrow viewports
# --------------------------------------------------------------------------


def render_hero_compact(p: Palette) -> str:
    dot = {"cyan": p.cyan, "green": p.green, "blue": p.blue}
    rows = [
        [("Secure Boot", "cyan"), ("SecOC", "green"), ("Key Lifecycle", "blue")],
        [("TARA / 21434", "cyan"), ("IVN Gateway", "green")],
        [("Firmware Validation", "blue")],
    ]
    chips = "\n".join(
        chip_row(32, 300 + i * 38, [(label, dot[k]) for label, k in row], p, 2.6 + i * 0.2)
        for i, row in enumerate(rows)
    )
    aria = "Automotive ECU Cybersecurity Lab — six buildable automotive product-security projects."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="760" height="470" viewBox="0 0 760 470" role="img" aria-label="{esc(aria)}">
  <title>Automotive ECU Cybersecurity Lab</title>
  <defs>
{backdrop_defs(p, "h")}
    <clipPath id="hCard"><rect width="760" height="470" rx="20"/></clipPath>
    <clipPath id="hWaveClip"><rect x="0" y="0" width="216" height="30"/></clipPath>
  </defs>
  <style>
{ANIMATION_CSS}
    @keyframes scan{{0%{{transform:translateY(-90px);opacity:1}}100%{{transform:translateY(560px);opacity:1}}}}
    @keyframes climb{{0%{{opacity:0}}100%{{opacity:0}}}}
    @keyframes reject{{0%,58%{{opacity:0}}66%,92%{{opacity:1}}100%{{opacity:0}}}}
{REDUCED_MOTION}
  </style>
  <g clip-path="url(#hCard)">
    <rect width="760" height="470" fill="url(#hBg)"/>
    <g class="grid-pan"><rect x="-40" y="-40" width="840" height="550" fill="url(#hGrid)"/></g>
    <g filter="url(#hBlur)">
      <circle class="drift-a" cx="90" cy="100" r="130" fill="url(#hOrbC)"/>
      <circle class="drift-b" cx="660" cy="380" r="140" fill="url(#hOrbG)"/>
    </g>
    <rect class="scan" x="0" y="0" width="760" height="80" fill="url(#hScan)" opacity="0"/>

{terminal_bar(32, 46, 360, "micheal@ecu-lab", "make demo", p)}

    <g class="wipe" transform="translate(32,132)">
      <text x="0" y="0" font-family="{SANS}" font-size="38" font-weight="800" letter-spacing="-0.4" fill="url(#hTitle)" filter="url(#hGlow)">AUTOMOTIVE ECU</text>
    </g>
    <g class="wipe2" transform="translate(32,176)">
      <text x="0" y="0" font-family="{SANS}" font-size="38" font-weight="800" letter-spacing="-0.4" fill="url(#hTitle)" filter="url(#hGlow)">CYBERSECURITY LAB</text>
    </g>
    <rect class="grow" x="32" y="192" width="240" height="4" rx="2" fill="url(#hRule)"/>

    <g class="fade" style="animation-delay:2.2s">
      <rect x="32" y="220" width="696" height="62" rx="11" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.cyan}" stroke-opacity="0.28" stroke-width="1"/>
      <text x="52" y="245" font-family="{SANS}" font-size="14.5" fill="{p.text}">Six buildable projects across the automotive</text>
      <text x="52" y="266" font-family="{SANS}" font-size="14.5" fill="{p.text}">product-security lifecycle.</text>
    </g>

{chips}

    <g class="fade" style="animation-delay:3.1s">
      <rect x="24" y="412" width="712" height="42" rx="12" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{p.stroke}" stroke-width="1"/>
      <circle class="live" cx="48" cy="433" r="4.2" fill="{p.green}"/>
      <text x="62" y="438" font-family="{MONO}" font-size="11.5" letter-spacing="1.4" fill="{p.green}">6 PROJECTS</text>
      <line x1="164" y1="422" x2="164" y2="444" stroke="{p.stroke}" stroke-width="1"/>
      <text x="180" y="438" font-family="{MONO}" font-size="11.5" fill="{p.muted}">56 phases</text>
      <line x1="286" y1="422" x2="286" y2="444" stroke="{p.stroke}" stroke-width="1"/>
      <text x="302" y="438" font-family="{MONO}" font-size="11.5" fill="{p.amber}">simulation-based</text>
{can_wave(496, 422, p, "CAN-FD")}
    </g>
  </g>
  <rect x="1" y="1" width="758" height="468" rx="19" fill="none" stroke="url(#hEdge)" stroke-width="1.6"/>
</svg>
"""


# --------------------------------------------------------------------------
# divider.svg
# --------------------------------------------------------------------------


def render_divider(p: Palette) -> str:
    ticks = "\n".join(
        f'  <rect class="tick" x="{90 * i}" y="10.0" width="1.4" height="8" fill="{p.cyan}" opacity="0.28" style="animation-delay:{round(0.28 * (i - 1), 2)}s"/>'
        for i in range(1, 10)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="28" viewBox="0 0 900 28" role="presentation" aria-hidden="true">
  <defs>
    <linearGradient id="dLine" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="{p.cyan}" stop-opacity="0"/><stop offset="18%" stop-color="{p.cyan}" stop-opacity="0.8"/><stop offset="50%" stop-color="{p.blue}" stop-opacity="0.8"/><stop offset="82%" stop-color="{p.green}" stop-opacity="0.8"/><stop offset="100%" stop-color="{p.green}" stop-opacity="0"/></linearGradient>
    <radialGradient id="dPulse" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="{p.cyan_bright}" stop-opacity="0.95"/><stop offset="100%" stop-color="{p.cyan_bright}" stop-opacity="0"/></radialGradient>
  </defs>
  <style>
    .pulse{{animation:travel 6s cubic-bezier(.55,0,.45,1) infinite}}
    .tick{{animation:twinkle 3.4s ease-in-out infinite}}
    @keyframes travel{{0%{{transform:translateX(40px);opacity:1}}100%{{transform:translateX(860px);opacity:1}}}}
    @keyframes twinkle{{0%,100%{{opacity:.25}}50%{{opacity:.8}}}}
    @media (prefers-reduced-motion: reduce){{.pulse,.tick{{animation:none}}}}
  </style>
  <line x1="0" y1="14.0" x2="900" y2="14.0" stroke="url(#dLine)" stroke-width="1.4"/>
{ticks}
  <g class="pulse" opacity="0"><circle cx="0" cy="14.0" r="11" fill="url(#dPulse)"/><circle cx="0" cy="14.0" r="2.6" fill="{p.cyan_bright}"/></g>
  <path d="M8 7.0 v14 M14 10.0 v8" stroke="{p.cyan}" stroke-opacity="0.75" stroke-width="1.4"/>
  <path d="M892 7.0 v14 M886 10.0 v8" stroke="{p.green}" stroke-opacity="0.75" stroke-width="1.4"/>
</svg>
"""


# --------------------------------------------------------------------------
# portfolio-map.svg — how the six projects compose
# --------------------------------------------------------------------------


def render_portfolio_map(p: Palette) -> str:
    """Four bands showing what each project owns and where they hand off.

    Band order is chosen so that every edge drawn is between *adjacent* bands,
    and every edge is a hand-off the build kits actually specify:

    * TARA emits requirement IDs the projects below trace their tests to.
    * The SecOC authenticator is reused as the gateway's enforcement point.
    * The key lifecycle manager provisions the MAC keys SecOC consumes
      (the export bridge in that project's optional final phase).

    No speculative arrows. A diagram that claims an integration the repo does
    not have is the same defect as a resume line that claims a tool you have
    not driven.
    """

    def band_label(x: float, y: float, text: str) -> str:
        return f'    <text x="{x}" y="{y}" font-family="{MONO}" font-size="10.5" letter-spacing="3" fill="{p.dim}">{esc(text)}</text>'

    def card(
        x: float, y: float, w: float, h: float, tag: str, title: str, lines: list[str], colour: str
    ) -> str:
        body = "\n".join(
            f'      <text x="{x + 18}" y="{y + 62 + i * 17}" font-family="{MONO}" font-size="11" fill="{p.muted}">{esc(line)}</text>'
            for i, line in enumerate(lines)
        )
        return f"""    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="13" fill="{p.panel}" fill-opacity="{p.panel_opacity}" stroke="{colour}" stroke-opacity="0.45" stroke-width="1.3"/>
      <rect x="{x}" y="{y}" width="{w}" height="4" rx="2" fill="{colour}"/>
      <text x="{x + 18}" y="{y + 26}" font-family="{MONO}" font-size="10" letter-spacing="1.8" fill="{colour}">{esc(tag)}</text>
      <text x="{x + 18}" y="{y + 46}" font-family="{SANS}" font-size="15" font-weight="700" fill="{p.text}">{esc(title)}</text>
{body}
    </g>"""

    def flow(x: float, y1: float, y2: float, label: str, colour: str, delay: float) -> str:
        """A dashed hand-off line with a travelling dot, drawn downward when
        y2 > y1 and upward otherwise."""
        up = y2 < y1
        head = (
            f'M{x - 5} {y2 + 7} L{x} {y2} L{x + 5} {y2 + 7}'
            if up
            else f'M{x - 5} {y2 - 7} L{x} {y2} L{x + 5} {y2 - 7}'
        )
        return f"""    <g>
      <path d="M{x} {y1} V{y2}" stroke="{colour}" stroke-opacity="0.45" stroke-width="1.4" stroke-dasharray="4 4"/>
      <path d="{head}" fill="none" stroke="{colour}" stroke-opacity="0.8" stroke-width="1.6" stroke-linecap="round"/>
      <circle class="flow" cx="0" cy="0" r="3" fill="{colour}" opacity="0" style="offset-path:path('M{x} {y1} V{y2}');offset-rotate:0deg;animation-delay:{delay}s"/>
      <text x="{x + 12}" y="{round((y1 + y2) / 2 + 4, 1)}" font-family="{MONO}" font-size="10" fill="{p.dim}">{esc(label)}</text>
    </g>"""

    def link(x1: float, x2: float, y: float, label: str, colour: str) -> str:
        """A horizontal reuse edge between two cards in the same band, drawn
        from x1 toward x2 with the head on the consuming end."""
        mid = (x1 + x2) / 2
        back = 7 if x2 > x1 else -7
        return f"""    <g>
      <path d="M{x1} {y} H{x2}" stroke="{colour}" stroke-opacity="0.45" stroke-width="1.4" stroke-dasharray="4 4"/>
      <path d="M{x2 - back} {y - 5} L{x2} {y} L{x2 - back} {y + 5}" fill="none" stroke="{colour}" stroke-opacity="0.8" stroke-width="1.6" stroke-linecap="round"/>
      <text x="{mid}" y="{y - 10}" text-anchor="middle" font-family="{MONO}" font-size="10" fill="{p.dim}">{esc(label)}</text>
    </g>"""

    aria = (
        "Portfolio map. Four bands: analysis, ECU, network, key material. The TARA workbench emits "
        "requirement identifiers the projects below trace their tests to; the SecOC authenticator is "
        "reused as the in-vehicle network gateway's enforcement point; the key lifecycle manager "
        "provisions the MAC keys SecOC consumes."
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="700" viewBox="0 0 1280 700" role="img" aria-label="{esc(aria)}">
  <title>How the six projects compose</title>
  <defs>
{backdrop_defs(p, "m")}
    <clipPath id="mCard"><rect width="1280" height="700" rx="22"/></clipPath>
  </defs>
  <style>
    .flow{{animation:flow 3.4s cubic-bezier(.5,0,.5,1) infinite}}
    .grid-pan{{animation:gridPan 26s linear infinite}}
    @keyframes flow{{0%{{opacity:0;offset-distance:0%}}12%{{opacity:.95}}88%{{opacity:.95}}100%{{opacity:0;offset-distance:100%}}}}
    @keyframes gridPan{{to{{transform:translate(-40px,-40px)}}}}
    @media (prefers-reduced-motion: reduce){{.flow,.grid-pan{{animation:none}}}}
  </style>
  <g clip-path="url(#mCard)">
    <rect width="1280" height="700" fill="url(#mBg)"/>
    <g class="grid-pan"><rect x="-40" y="-40" width="1360" height="780" fill="url(#mGrid)"/></g>
    <g filter="url(#mBlur)">
      <circle cx="200" cy="110" r="150" fill="url(#mOrbB)"/>
      <circle cx="1090" cy="600" r="170" fill="url(#mOrbG)"/>
    </g>

    <text x="40" y="46" font-family="{SANS}" font-size="21" font-weight="700" fill="{p.text}">How the six projects compose</text>
    <text x="40" y="72" font-family="{MONO}" font-size="11.5" fill="{p.muted}">Every arrow is a hand-off the build specs actually define — analysis down into requirements, key material up into the protocol that consumes it.</text>

{band_label(40, 112, "ANALYSIS")}
{card(40, 124, 1200, 86, "PROJECT 04", "ISO/SAE 21434 TARA Workbench", ["item definition → assets & damage scenarios → threat scenarios → attack feasibility → risk → cybersecurity goals & requirements"], p.amber)}

{flow(320, 210, 258, "REQ-*", p.amber, 0.0)}
{flow(960, 210, 258, "REQ-*", p.amber, 0.6)}

{band_label(40, 252, "ECU")}
{card(40, 264, 560, 132, "PROJECT 01", "Secure Boot Chain Simulator", ["BootROM → SBL → application, each verifying the next", "OTP root of trust · monotonic anti-rollback · measured boot", "valid signature, still refused: security version behind the counter"], p.blue)}
{card(680, 264, 560, 132, "PROJECT 06", "ECU Firmware Validation Pipeline", ["FreeRTOS + UDS/ISO-TP in C on an emulated Cortex-M", "8 planted CWEs vs static analysis, sanitizers, fuzzing, SBOM", "the tool-comparison matrix — including what nothing caught"], p.danger)}

{band_label(40, 442, "NETWORK")}
{card(40, 454, 560, 132, "PROJECT 05", "In-Vehicle Network Security Lab", ["LIN sub-bus · CAN-FD backbone · Automotive Ethernet", "zone firewall · routing · diagnostic filter · anomaly detector", "10 attacks, each run permissive vs hardened"], p.green)}
{card(680, 454, 560, 132, "PROJECT 02", "CAN Bus SecOC Demo", ["AES-128 CMAC · truncated MAC · truncated freshness value", "receiver-side freshness reconstruction + resynchronisation", "the same replay: accepted unprotected, rejected under SecOC"], p.cyan)}
{link(676, 604, 520, "reuse", p.cyan)}

{flow(960, 632, 590, "MAC keys", p.green, 1.2)}

{band_label(40, 624, "KEY MATERIAL")}
{card(40, 636, 1200, 52, "PROJECT 03", "ECU Key Lifecycle Manager", [], p.green)}
    <text x="404" y="682" font-family="{MONO}" font-size="11" fill="{p.muted}">generation · HKDF derivation · provisioning ceremony · rotation with overlap · signed revocation · hash-chained audit</text>
  </g>
  <rect x="1" y="1" width="1278" height="698" rx="21" fill="none" stroke="url(#mEdge)" stroke-width="1.6"/>
</svg>
"""


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

RENDERERS = {
    "hero": render_hero,
    "hero-compact": render_hero_compact,
    "divider": render_divider,
    "portfolio-map": render_portfolio_map,
}


def build() -> dict[Path, str]:
    """Return the full asset set as {path: contents}."""
    out: dict[Path, str] = {}
    for stem, fn in RENDERERS.items():
        out[ASSETS / f"{stem}.svg"] = fn(DARK)
        out[ASSETS / f"{stem}-light.svg"] = fn(LIGHT)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify assets/ matches this file instead of rewriting it",
    )
    args = parser.parse_args(argv)

    ASSETS.mkdir(parents=True, exist_ok=True)
    stale: list[Path] = []
    for path, content in build().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        if args.check:
            stale.append(path)
        else:
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(REPO_ROOT)}")

    if args.check:
        if stale:
            print("Assets are stale. Run: make assets", file=sys.stderr)
            for path in stale:
                print(f"  - {path.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        print(f"assets: {len(build())} files up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
