#!/usr/bin/env python3
"""Generate a paper-ready HealChain system architecture figure.

The output is a high-resolution SVG that avoids text overlap by separating
component details from edge explanations. Flow details are shown as numbered
markers plus a legend, which works better when the figure is converted to PNG,
PDF, Word, or LaTeX formats for an IEEE paper.
"""

from __future__ import annotations

import argparse
import datetime as dt
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape


CANVAS_WIDTH = 3600
CANVAS_HEIGHT = 2600


PALETTE = {
    "ink": "#172033",
    "muted": "#536170",
    "paper": "#ffffff",
    "grid": "#eef2f7",
    "client_fill": "#f4f8ff",
    "client_stroke": "#2f6fed",
    "coord_fill": "#f6fbf8",
    "coord_stroke": "#23875f",
    "agg_fill": "#fff7ee",
    "agg_stroke": "#d97706",
    "chain_fill": "#f7f5ff",
    "chain_stroke": "#7357d5",
    "store_fill": "#eff9fb",
    "store_stroke": "#138496",
    "edge": "#344256",
    "edge_soft": "#667386",
}


@dataclass(frozen=True)
class Box:
    key: str
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


class Svg:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.parts: list[str] = []

    def add(self, raw: str) -> None:
        self.parts.append(raw)

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str,
        stroke: str = "none",
        sw: float = 1.0,
        rx: float = 0.0,
        opacity: float | None = None,
        dash: str | None = None,
        css_class: str | None = None,
    ) -> None:
        attrs = [
            f'x="{x:.1f}"',
            f'y="{y:.1f}"',
            f'width="{w:.1f}"',
            f'height="{h:.1f}"',
            f'fill="{fill}"',
            f'stroke="{stroke}"',
            f'stroke-width="{sw:.1f}"',
        ]
        if rx:
            attrs.extend([f'rx="{rx:.1f}"', f'ry="{rx:.1f}"'])
        if opacity is not None:
            attrs.append(f'opacity="{opacity:.3f}"')
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if css_class:
            attrs.append(f'class="{css_class}"')
        self.add(f"<rect {' '.join(attrs)} />")

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke: str = PALETTE["edge"],
        sw: float = 2.0,
        dash: str | None = None,
        marker: bool = False,
        opacity: float = 1.0,
    ) -> None:
        attrs = [
            f'x1="{x1:.1f}"',
            f'y1="{y1:.1f}"',
            f'x2="{x2:.1f}"',
            f'y2="{y2:.1f}"',
            f'stroke="{stroke}"',
            f'stroke-width="{sw:.1f}"',
            'fill="none"',
            'stroke-linecap="round"',
            f'opacity="{opacity:.3f}"',
        ]
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if marker:
            attrs.append('marker-end="url(#arrow)"')
        self.add(f"<line {' '.join(attrs)} />")

    def polyline(
        self,
        points: Sequence[tuple[float, float]],
        *,
        stroke: str = PALETTE["edge"],
        sw: float = 2.0,
        dash: str | None = None,
        marker: bool = True,
        opacity: float = 1.0,
    ) -> None:
        point_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        attrs = [
            f'points="{point_str}"',
            f'stroke="{stroke}"',
            f'stroke-width="{sw:.1f}"',
            'fill="none"',
            'stroke-linejoin="round"',
            'stroke-linecap="round"',
            f'opacity="{opacity:.3f}"',
        ]
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
        if marker:
            attrs.append('marker-end="url(#arrow)"')
        self.add(f"<polyline {' '.join(attrs)} />")

    def circle(
        self,
        x: float,
        y: float,
        r: float,
        *,
        fill: str,
        stroke: str = "none",
        sw: float = 1.0,
    ) -> None:
        self.add(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.1f}" />'
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: int = 16,
        weight: int | str = 400,
        fill: str = PALETTE["ink"],
        anchor: str = "start",
        family: str = "Arial, Helvetica, sans-serif",
        opacity: float = 1.0,
    ) -> None:
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}" opacity="{opacity:.3f}">{escape(value)}</text>'
        )

    def text_block(
        self,
        x: float,
        y: float,
        width: float,
        lines: Iterable[str],
        *,
        size: int = 18,
        fill: str = PALETTE["muted"],
        weight: int | str = 400,
        line_height: float = 1.28,
        bullet: bool = False,
        max_lines: int | None = None,
    ) -> int:
        rendered = 0
        max_chars = max(22, int(width / (size * 0.54)))
        for original in lines:
            prefix = "- " if bullet else ""
            wrapped = textwrap.wrap(
                original,
                width=max_chars,
                initial_indent=prefix,
                subsequent_indent="  " if bullet else "",
                break_long_words=False,
                break_on_hyphens=False,
            ) or [prefix.rstrip()]
            for line in wrapped:
                if max_lines is not None and rendered >= max_lines:
                    return rendered
                self.text(x, y + rendered * size * line_height, line, size=size, fill=fill, weight=weight)
                rendered += 1
        return rendered

    def finish(self) -> str:
        header = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">
<defs>
  <marker id="arrow" markerWidth="13" markerHeight="13" refX="10.5" refY="6.5" orient="auto" markerUnits="strokeWidth">
    <path d="M 0 0 L 12 6.5 L 0 13 z" fill="{PALETTE["edge"]}" />
  </marker>
  <filter id="softShadow" x="-12%" y="-12%" width="124%" height="134%">
    <feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="#0f172a" flood-opacity="0.10"/>
  </filter>
  <style>
    .card {{ filter: url(#softShadow); }}
  </style>
</defs>
'''
        return header + "\n".join(self.parts) + "\n</svg>\n"


def draw_background(svg: Svg) -> None:
    svg.rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#fbfcfe")
    for x in range(80, CANVAS_WIDTH, 160):
        svg.line(x, 0, x, CANVAS_HEIGHT, stroke=PALETTE["grid"], sw=1, opacity=0.45)
    for y in range(90, CANVAS_HEIGHT, 160):
        svg.line(0, y, CANVAS_WIDTH, y, stroke=PALETTE["grid"], sw=1, opacity=0.45)


def draw_layer(svg: Svg, box: Box, title: str, fill: str, stroke: str) -> None:
    svg.rect(box.x, box.y, box.w, box.h, fill=fill, stroke=stroke, sw=1.9, rx=12, opacity=0.88)
    svg.text(box.x + 34, box.y + 44, title.upper(), size=22, weight=800, fill=stroke)


def draw_card(
    svg: Svg,
    box: Box,
    title: str,
    body: Sequence[str],
    *,
    fill: str,
    stroke: str,
    label: str | None = None,
    max_body_lines: int | None = None,
) -> None:
    svg.add(f'<g id="{escape(box.key)}" class="card">')
    svg.rect(box.x, box.y, box.w, box.h, fill=fill, stroke=stroke, sw=2.3, rx=9)
    svg.rect(box.x, box.y, box.w, 10, fill=stroke, stroke="none", rx=9)

    title_x = box.x + 26
    title_width = box.w - 52
    if label:
        badge_w = max(74, 22 + len(label) * 13)
        svg.rect(box.x + 28, box.y + 30, badge_w, 42, fill=stroke, stroke="none", rx=8)
        svg.text(box.x + 28 + badge_w / 2, box.y + 58, label, size=20, weight=850, fill="#ffffff", anchor="middle")
        title_x = box.x + 52 + badge_w
        title_width = box.w - (title_x - box.x) - 26

    title_lines = textwrap.wrap(title, width=max(18, int(title_width / 12)), break_long_words=False)
    for i, line in enumerate(title_lines[:2]):
        svg.text(title_x, box.y + 55 + i * 28, line, size=30, weight=850, fill=PALETTE["ink"])

    body_y = box.y + 105 if len(title_lines[:2]) == 1 else box.y + 134
    svg.text_block(
        box.x + 28,
        body_y,
        box.w - 56,
        body,
        size=21,
        fill=PALETTE["muted"],
        bullet=True,
        max_lines=max_body_lines,
    )
    svg.add("</g>")


def flow_marker(svg: Svg, x: float, y: float, number: int, color: str) -> None:
    svg.circle(x, y, 24, fill="#ffffff", stroke=color, sw=3.4)
    svg.circle(x, y, 18, fill=color, stroke="none")
    svg.text(x, y + 7, str(number), size=19, weight=850, fill="#ffffff", anchor="middle")


def edge(
    svg: Svg,
    points: Sequence[tuple[float, float]],
    *,
    number: int | None = None,
    marker_at: tuple[float, float] | None = None,
    color: str = PALETTE["edge"],
    dash: str | None = None,
    width: float = 3.2,
    opacity: float = 0.88,
) -> None:
    svg.polyline(points, stroke=color, sw=width, dash=dash, marker=True, opacity=opacity)
    if number is not None:
        mx, my = marker_at or points[len(points) // 2]
        flow_marker(svg, mx, my, number, color)


def draw_module_flow(svg: Svg) -> None:
    modules = [
        ("M1", "Task publishing", "Escrow + accuracy commit"),
        ("M2", "Registration", "Miner proof, PoS, key delivery"),
        ("M3", "Local training", "DGC + score commit + encryption"),
        ("M4", "Aggregation", "Decrypt, BSGS, update, evaluate"),
        ("M5", "Verification", "Signed votes + majority"),
        ("M6", "Publication", "Verified metadata on-chain"),
        ("M7", "Rewards", "Reveal + proportional payout"),
    ]
    x0 = 110
    y = 140
    gap = 24
    w = int((CANVAS_WIDTH - 220 - gap * (len(modules) - 1)) / len(modules))
    h = 105
    for i, (num, title, subtitle) in enumerate(modules):
        x = x0 + i * (w + gap)
        svg.rect(x, y, w, h, fill="#ffffff", stroke="#b6c4da", sw=1.7, rx=9)
        svg.rect(x, y, 78, h, fill=PALETTE["ink"], stroke="none", rx=9)
        svg.text(x + 39, y + 65, num, size=28, weight=850, fill="#ffffff", anchor="middle")
        svg.text(x + 98, y + 43, title, size=23, weight=850, fill=PALETTE["ink"])
        svg.text(x + 98, y + 76, subtitle, size=18, weight=500, fill=PALETTE["muted"])
        if i < len(modules) - 1:
            svg.line(x + w + 4, y + h / 2, x + w + gap - 7, y + h / 2, stroke=PALETTE["edge"], sw=3.0, marker=True)


def architecture_boxes() -> dict[str, Box]:
    return {
        "publisher": Box("publisher", 160, 350, 740, 240),
        "frontend": Box("frontend", 980, 350, 740, 240),
        "miners": Box("miners", 1800, 350, 740, 240),
        "operator": Box("selected_aggregator", 2620, 350, 740, 240),
        "backend": Box("backend", 160, 775, 900, 265),
        "db": Box("postgres", 1160, 775, 820, 265),
        "artifacts": Box("artifacts", 2080, 775, 950, 265),
        "aggregator": Box("aggregator", 160, 1225, 820, 290),
        "crypto": Box("secure_aggregation_core", 1040, 1225, 750, 290),
        "model": Box("model_update", 1850, 1225, 760, 290),
        "consensus": Box("consensus", 2670, 1225, 690, 290),
        "evm": Box("evm", 160, 1680, 600, 230),
        "escrow": Box("escrow", 840, 1680, 560, 230),
        "stake": Box("stake_registry", 1480, 1680, 470, 230),
        "block": Box("block_publisher", 2030, 1680, 600, 230),
        "reward": Box("reward_distribution", 2710, 1680, 650, 230),
    }


def draw_edges(svg: Svg, b: dict[str, Box]) -> None:
    # Top-to-middle orchestration. Routes stay in gutters between cards/layers.
    edge(
        svg,
        [(b["publisher"].right, b["publisher"].cy), (b["frontend"].left, b["frontend"].cy)],
        number=1,
        marker_at=((b["publisher"].right + b["frontend"].left) / 2, b["publisher"].cy),
    )
    edge(
        svg,
        [
            (b["frontend"].cx, b["frontend"].bottom),
            (b["frontend"].cx, 670),
            (b["backend"].cx, 670),
            (b["backend"].cx, b["backend"].top),
        ],
        number=2,
        marker_at=(b["frontend"].cx, 670),
    )
    edge(
        svg,
        [
            (b["miners"].cx, b["miners"].bottom),
            (b["miners"].cx, 670),
            (b["backend"].right - 110, 670),
            (b["backend"].right - 110, b["backend"].top),
        ],
        number=3,
        marker_at=(b["miners"].cx, 670),
    )
    edge(
        svg,
        [
            (b["operator"].cx, b["operator"].bottom),
            (b["operator"].cx, 1155),
            (b["aggregator"].right - 120, 1155),
            (b["aggregator"].right - 120, b["aggregator"].top),
        ],
        number=4,
        marker_at=(b["operator"].cx, 1155),
        color=PALETTE["agg_stroke"],
    )

    # Coordination layer.
    edge(svg, [(b["backend"].right, b["backend"].cy - 55), (b["db"].left, b["db"].cy - 55)], number=5, marker_at=(1110, b["backend"].cy - 55), color=PALETTE["coord_stroke"])
    edge(svg, [(b["backend"].right, b["backend"].cy + 55), (b["artifacts"].left, b["artifacts"].cy + 55)], number=6, marker_at=(2030, b["backend"].cy + 55), color=PALETTE["store_stroke"])

    # Aggregation pipeline.
    edge(
        svg,
        [
            (b["backend"].cx, b["backend"].bottom),
            (b["backend"].cx, 1155),
            (b["aggregator"].cx, 1155),
            (b["aggregator"].cx, b["aggregator"].top),
        ],
        number=7,
        marker_at=(b["backend"].cx, 1155),
        color=PALETTE["agg_stroke"],
    )
    edge(svg, [(b["aggregator"].right, b["aggregator"].cy), (b["crypto"].left, b["crypto"].cy)], number=8, marker_at=(1010, b["aggregator"].cy), color=PALETTE["agg_stroke"])
    edge(svg, [(b["crypto"].right, b["crypto"].cy), (b["model"].left, b["model"].cy)], number=9, marker_at=(1820, b["crypto"].cy), color=PALETTE["agg_stroke"])
    edge(svg, [(b["model"].right, b["model"].cy), (b["consensus"].left, b["consensus"].cy)], number=10, marker_at=(2640, b["model"].cy), color=PALETTE["agg_stroke"])
    edge(
        svg,
        [
            (b["artifacts"].cx, b["artifacts"].bottom),
            (b["artifacts"].cx, 1155),
            (b["model"].cx, 1155),
            (b["model"].cx, b["model"].top),
        ],
        number=11,
        marker_at=(b["model"].cx, 1155),
        color=PALETTE["store_stroke"],
        dash="10 8",
    )
    edge(
        svg,
        [
            (b["miners"].right, b["miners"].cy + 55),
            (3540, b["miners"].cy + 55),
            (3540, b["consensus"].cy),
            (b["consensus"].right, b["consensus"].cy),
        ],
        number=12,
        marker_at=(3540, 990),
        color=PALETTE["agg_stroke"],
        dash="10 8",
    )

    # Blockchain settlement. Long routes use side gutters so no line crosses text.
    edge(
        svg,
        [
            (b["frontend"].left + 60, b["frontend"].bottom),
            (100, b["frontend"].bottom),
            (100, b["evm"].cy),
            (b["evm"].left, b["evm"].cy),
        ],
        number=13,
        marker_at=(100, 1535),
        color=PALETTE["chain_stroke"],
    )
    edge(
        svg,
        [
            (b["backend"].left + 70, b["backend"].bottom),
            (b["backend"].left + 70, 1590),
            (b["block"].cx, 1590),
            (b["block"].cx, b["block"].top),
        ],
        number=14,
        marker_at=(b["block"].cx, 1590),
        color=PALETTE["chain_stroke"],
    )
    edge(svg, [(b["evm"].right, b["evm"].cy), (b["escrow"].left, b["escrow"].cy)], color=PALETTE["chain_stroke"], width=2.7)
    edge(svg, [(b["escrow"].right, b["escrow"].cy), (b["stake"].left, b["stake"].cy)], color=PALETTE["chain_stroke"], width=2.7)
    edge(svg, [(b["stake"].right, b["stake"].cy), (b["block"].left, b["block"].cy)], color=PALETTE["chain_stroke"], width=2.7)
    edge(svg, [(b["block"].right, b["block"].cy), (b["reward"].left, b["reward"].cy)], number=15, marker_at=(2670, b["block"].cy), color=PALETTE["chain_stroke"], width=2.7)
    edge(
        svg,
        [
            (b["reward"].cx, b["reward"].top),
            (b["reward"].cx, 1590),
            (b["miners"].cx, 1590),
            (b["miners"].cx, b["miners"].bottom),
        ],
        number=16,
        marker_at=(b["reward"].cx, 1590),
        color=PALETTE["chain_stroke"],
        dash="10 8",
        width=2.7,
    )


def draw_architecture_cards(svg: Svg, b: dict[str, Box]) -> None:
    draw_card(
        svg,
        b["publisher"],
        "Task Publisher / Researcher",
        [
            "Defines dataset, initial model, reward, deadline, target accuracy",
            "Commits H(accuracy || nonceTP)",
            "Reveals accuracy after publication",
        ],
        fill=PALETTE["client_fill"],
        stroke=PALETTE["client_stroke"],
        label="USER",
    )
    draw_card(
        svg,
        b["frontend"],
        "Frontend UI (Next.js)",
        [
            "Wallet-based publishing, miner registration, training trigger",
            "Verification, reveal, and reward screens",
            "Reads backend state and sends contract transactions",
        ],
        fill=PALETTE["client_fill"],
        stroke=PALETTE["client_stroke"],
        label="UI",
    )
    draw_card(
        svg,
        b["miners"],
        "Miner FL Clients (N participants)",
        [
            "Raw medical data remains local",
            "Train model, compute gradients, apply DGC compression",
            "Create score commit, NDD-FE sparse ciphertext, ECDSA signature",
        ],
        fill=PALETTE["client_fill"],
        stroke=PALETTE["client_stroke"],
        label="M3",
    )
    draw_card(
        svg,
        b["operator"],
        "Selected Aggregator Endpoint",
        [
            "Chosen through task/miner state and stake-aware orchestration",
            "Runs Python API service for aggregation jobs",
            "Uses task-scoped keys and backend metadata",
        ],
        fill=PALETTE["client_fill"],
        stroke=PALETTE["client_stroke"],
        label="M2",
    )
    draw_card(
        svg,
        b["backend"],
        "Backend Coordination API (Express + Prisma)",
        [
            "Task lifecycle, wallet signature checks, proof verification",
            "Miner registration, PoS selection, key derivation and delivery",
            "Opaque relay for submissions, verification votes, publish/reward APIs",
        ],
        fill=PALETTE["coord_fill"],
        stroke=PALETTE["coord_stroke"],
        label="API",
    )
    draw_card(
        svg,
        b["db"],
        "PostgreSQL State Store",
        [
            "Task, Miner, Gradient, Block, Verification, Reward tables",
            "Round status and current model links",
            "Audit trail for protocol progress",
        ],
        fill=PALETTE["coord_fill"],
        stroke=PALETTE["coord_stroke"],
        label="DB",
    )
    draw_card(
        svg,
        b["artifacts"],
        "Artifact / IPFS Storage",
        [
            "Initial models and validation datasets",
            "Miner proofs and model artifact links",
            "Updated W_new artifacts for iterative rounds",
        ],
        fill=PALETTE["store_fill"],
        stroke=PALETTE["store_stroke"],
        label="IPFS",
    )
    draw_card(
        svg,
        b["aggregator"],
        "Aggregator Orchestrator (Python M4-M6)",
        [
            "Polls backend for task metadata, selected miners, keys, submissions",
            "Validates sparse schema, signatures, hashes, and participant limits",
            "Builds candidate block and submits final payload",
        ],
        fill=PALETTE["agg_fill"],
        stroke=PALETTE["agg_stroke"],
        label="M4",
    )
    draw_card(
        svg,
        b["crypto"],
        "Secure Aggregation Core",
        [
            "NDD-FE designated decryption over sparse ciphertext",
            "BSGS recovery of quantized gradient coordinates",
            "Dense reconstruction only after strict sparse recovery",
        ],
        fill=PALETTE["agg_fill"],
        stroke=PALETTE["agg_stroke"],
        label="SEC",
    )
    draw_card(
        svg,
        b["model"],
        "Model Update and Evaluation",
        [
            "Apply W(t+1) = W(t) + eta * aggregate update",
            "Evaluate accuracy on validation data",
            "Publish modelLink or carry-forward W_new for next round",
        ],
        fill=PALETTE["agg_fill"],
        stroke=PALETTE["agg_stroke"],
        label="EVAL",
    )
    draw_card(
        svg,
        b["consensus"],
        "Miner Verification Consensus",
        [
            "Candidate hash broadcast",
            "Signed VALID / INVALID votes",
            "Majority decision before publication",
        ],
        fill=PALETTE["agg_fill"],
        stroke=PALETTE["agg_stroke"],
        label="M5",
    )
    draw_card(
        svg,
        b["evm"],
        "EVM Network (Ganache / Testnet)",
        [
            "JSON-RPC provider and wallet-signed transactions",
            "Immutable event log for task and reward state",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="RPC",
    )
    draw_card(
        svg,
        b["escrow"],
        "HealChainEscrow",
        [
            "M1 reward lock and accuracy commit",
            "Task status and refund safety path",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M1",
    )
    draw_card(
        svg,
        b["stake"],
        "StakeRegistry",
        [
            "Stake-aware miner support",
            "Selection context for participation",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M2",
    )
    draw_card(
        svg,
        b["block"],
        "BlockPublisher",
        [
            "M6 model hash, accuracy, score commits",
            "On-chain training result metadata",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M6",
    )
    draw_card(
        svg,
        b["reward"],
        "RewardDistribution",
        [
            "M7 accuracy and score reveal",
            "Proportional payout to miners",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M7",
    )


def draw_flow_legend(svg: Svg) -> None:
    legend = Box("legend", 110, 2010, 3380, 430)
    svg.rect(legend.x, legend.y, legend.w, legend.h, fill="#ffffff", stroke="#c7d0dd", sw=1.8, rx=12)
    svg.text(legend.x + 34, legend.y + 54, "Numbered Data Flow Legend", size=31, weight=850, fill=PALETTE["ink"])
    svg.text(
        legend.x + 560,
        legend.y + 54,
        "Numbers replace long arrow labels to keep the architecture figure readable after export.",
        size=23,
        weight=500,
        fill=PALETTE["muted"],
    )

    entries = [
        ("1", "Publisher inputs task/reward/accuracy commitment through the UI."),
        ("2", "Frontend calls backend REST APIs for task, miner, training, reveal, and reward actions."),
        ("3", "Miner clients submit signed sparse ciphertext, score commit, and encrypted hash."),
        ("4", "Selected aggregator endpoint starts a task-scoped aggregation job."),
        ("5", "Backend persists task, miner, gradient, block, verification, and reward state."),
        ("6", "Backend resolves model, proof, validation, and updated-model artifact links."),
        ("7", "Aggregator fetches task metadata, keys, selected miners, and submissions."),
        ("8", "Validated payloads enter NDD-FE decryption and BSGS recovery."),
        ("9", "Recovered aggregate update is applied to the global model and evaluated."),
        ("10", "Candidate block hash is sent for miner verification consensus."),
        ("11", "Model/validation artifacts are read and W_new/modelLink is written for later rounds."),
        ("12", "Miners return signed VALID/INVALID verification votes."),
        ("13", "Publisher/miner wallets submit contract transactions to the EVM network."),
        ("14", "Backend chain bridge publishes verified block metadata on-chain."),
        ("15", "Published block enables commit-reveal and reward settlement."),
        ("16", "Reward contract distributes proportional payouts after reveals."),
    ]

    col_w = 800
    row_h = 68
    start_x = [legend.x + 35, legend.x + 865, legend.x + 1695, legend.x + 2525]
    start_y = legend.y + 112
    for idx, (num, text) in enumerate(entries):
        col = idx // 4
        row = idx % 4
        x = start_x[col]
        y = start_y + row * row_h
        flow_marker(svg, x + 24, y - 9, int(num), PALETTE["edge"])
        svg.text_block(x + 62, y, col_w - 74, [text], size=20, line_height=1.18, fill=PALETTE["muted"])

    footer_y = 2515
    svg.line(140, footer_y, 235, footer_y, stroke=PALETTE["edge"], sw=3.7, marker=True)
    svg.text(260, footer_y + 8, "solid: API call, pipeline handoff, or blockchain transaction", size=20, weight=650, fill=PALETTE["muted"])
    svg.line(1010, footer_y, 1105, footer_y, stroke=PALETTE["edge_soft"], sw=3.1, dash="10 8", marker=True)
    svg.text(1130, footer_y + 8, "dashed: artifact, verification, or reward side flow", size=20, weight=650, fill=PALETTE["muted"])
    svg.text(3460, footer_y + 8, "Generated from repository architecture docs", size=20, weight=650, fill=PALETTE["muted"], anchor="end")


def draw_architecture(svg: Svg) -> None:
    draw_background(svg)
    svg.text(110, 72, "HealChain System Architecture", size=56, weight=850, fill=PALETTE["ink"])
    svg.text(
        110,
        116,
        "Privacy-preserving federated learning with blockchain escrow, secure aggregation, consensus, and reward distribution",
        size=29,
        weight=500,
        fill=PALETTE["muted"],
    )
    draw_module_flow(svg)

    layers = [
        (Box("app_layer", 110, 280, 3380, 360), "Application and participant layer", "#f7faff", PALETTE["client_stroke"]),
        (Box("coord_layer", 110, 700, 3380, 365), "Off-chain coordination and storage layer", "#f7fcf9", PALETTE["coord_stroke"]),
        (Box("agg_layer", 110, 1125, 3380, 390), "Secure aggregation and consensus layer", "#fff9f2", PALETTE["agg_stroke"]),
        (Box("chain_layer", 110, 1580, 3380, 380), "Blockchain settlement layer", "#faf8ff", PALETTE["chain_stroke"]),
    ]
    for layer_box, title, fill, stroke in layers:
        draw_layer(svg, layer_box, title, fill, stroke)

    boxes = architecture_boxes()
    draw_edges(svg, boxes)
    draw_architecture_cards(svg, boxes)
    draw_flow_legend(svg)


def caption_text() -> str:
    return (
        "Figure X. HealChain system architecture. The task publisher and miners "
        "operate through the Next.js frontend and miner-side FL clients, while "
        "raw medical data remains local to each miner. The Express/Prisma backend "
        "coordinates task state, wallet authentication, miner registration, "
        "stake-aware aggregator selection, key delivery, and opaque relay of "
        "signed encrypted submissions. Miner clients perform local training, "
        "DGC compression, score commitment, and NDD-FE sparse ciphertext "
        "submission. The selected Python aggregator validates submissions, "
        "performs NDD-FE decryption, BSGS recovery, global model update and "
        "evaluation, then forms a candidate block for miner verification "
        "consensus. Verified metadata is bridged to the EVM contracts for "
        "escrow, block publication, commit-reveal, and proportional reward "
        "distribution. Model, proof, validation, and updated-model artifacts are "
        "stored as local/IPFS links used by the backend, miner clients, and "
        "aggregator during task execution."
    )


def write_outputs(output: Path, caption_output: Path | None) -> None:
    svg = Svg(CANVAS_WIDTH, CANVAS_HEIGHT)
    draw_architecture(svg)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg.finish(), encoding="utf-8")

    if caption_output:
        caption_output.parent.mkdir(parents=True, exist_ok=True)
        generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        caption_output.write_text(
            caption_text()
            + "\n\n"
            + f"Generated UTC: {generated}\n"
            + "Source basis: README.md, TECHNICAL_IMPLEMENTATION_GUIDE.md, backend/README.md, "
            + "fl_client/README.md, aggregator/README.md, contracts/README.md.\n",
            encoding="utf-8",
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the HealChain system architecture SVG for paper figures."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/architecture/healchain_system_architecture.svg"),
        help="SVG output path.",
    )
    parser.add_argument(
        "--caption-output",
        type=Path,
        default=Path("artifacts/architecture/healchain_system_architecture_caption.txt"),
        help="Caption text output path. Use --no-caption to disable.",
    )
    parser.add_argument(
        "--no-caption",
        action="store_true",
        help="Only write the SVG and skip the caption text file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    caption_output = None if args.no_caption else args.caption_output
    write_outputs(args.output, caption_output)
    print(f"Wrote architecture SVG: {args.output}")
    if caption_output:
        print(f"Wrote caption text: {caption_output}")


if __name__ == "__main__":
    main()
