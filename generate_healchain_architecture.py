#!/usr/bin/env python3
"""Generate a paper-ready HealChain system architecture figure.

The script writes a deterministic SVG without external dependencies. The
resulting vector file can be imported into Inkscape, Illustrator, Word, or
LaTeX workflows and exported to PDF/PNG for an IEEE paper.
"""

from __future__ import annotations

import argparse
import datetime as dt
import textwrap
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape


CANVAS_WIDTH = 1800
CANVAS_HEIGHT = 1320


PALETTE = {
    "ink": "#172033",
    "muted": "#536170",
    "paper": "#ffffff",
    "grid": "#edf1f7",
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
    "monitor_fill": "#fff4f6",
    "monitor_stroke": "#c9345b",
    "edge": "#39485a",
    "edge_soft": "#637083",
}


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
            attrs.append(f'rx="{rx:.1f}"')
            attrs.append(f'ry="{rx:.1f}"')
        if opacity is not None:
            attrs.append(f'opacity="{opacity:.3f}"')
        if dash:
            attrs.append(f'stroke-dasharray="{dash}"')
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
        family: str = "Inter, Arial, Helvetica, sans-serif",
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
        size: int = 15,
        fill: str = PALETTE["muted"],
        weight: int | str = 400,
        line_height: float = 1.25,
        bullet: bool = False,
        max_lines: int | None = None,
    ) -> int:
        rendered = 0
        max_chars = max(18, int(width / (size * 0.52)))
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
  <marker id="arrow" markerWidth="11" markerHeight="11" refX="9" refY="5.5" orient="auto" markerUnits="strokeWidth">
    <path d="M 0 0 L 10 5.5 L 0 11 z" fill="{PALETTE["edge"]}" />
  </marker>
  <filter id="softShadow" x="-10%" y="-10%" width="120%" height="130%">
    <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#0f172a" flood-opacity="0.10"/>
  </filter>
  <style>
    .card {{ filter: url(#softShadow); }}
    .smallcaps {{ font-variant: small-caps; letter-spacing: 1px; }}
  </style>
</defs>
'''
        return header + "\n".join(self.parts) + "\n</svg>\n"


def draw_background(svg: Svg) -> None:
    svg.rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT, fill="#fbfcfe")
    for x in range(60, CANVAS_WIDTH, 120):
        svg.line(x, 0, x, CANVAS_HEIGHT, stroke=PALETTE["grid"], sw=1, opacity=0.55)
    for y in range(80, CANVAS_HEIGHT, 120):
        svg.line(0, y, CANVAS_WIDTH, y, stroke=PALETTE["grid"], sw=1, opacity=0.55)


def draw_layer(svg: Svg, x: int, y: int, w: int, h: int, title: str, fill: str, stroke: str) -> None:
    svg.rect(x, y, w, h, fill=fill, stroke=stroke, sw=1.4, rx=10, opacity=0.86)
    svg.text(x + 22, y + 27, title.upper(), size=15, weight=700, fill=stroke)


def draw_card(
    svg: Svg,
    key: str,
    x: int,
    y: int,
    w: int,
    h: int,
    title: str,
    body: Sequence[str],
    *,
    fill: str,
    stroke: str,
    label: str | None = None,
    max_body_lines: int | None = None,
) -> dict[str, float]:
    svg.add(f'<g id="{escape(key)}" class="card">')
    svg.rect(x, y, w, h, fill=fill, stroke=stroke, sw=2.0, rx=8)
    svg.rect(x, y, w, 8, fill=stroke, stroke="none", rx=8)
    if label:
        svg.rect(x + 14, y + 20, 48, 27, fill=stroke, stroke="none", rx=6)
        svg.text(x + 38, y + 39, label, size=14, weight=800, fill="#ffffff", anchor="middle")
        title_x = x + 74
        title_width = w - 92
    else:
        title_x = x + 18
        title_width = w - 36
    title_lines = textwrap.wrap(title, width=max(18, int(title_width / 10)), break_long_words=False)
    for i, line in enumerate(title_lines[:2]):
        svg.text(title_x, y + 34 + i * 18, line, size=18, weight=800, fill=PALETTE["ink"])
    body_y = y + 65 if len(title_lines[:2]) == 1 else y + 80
    svg.text_block(
        x + 18,
        body_y,
        w - 36,
        body,
        size=14,
        fill=PALETTE["muted"],
        bullet=True,
        max_lines=max_body_lines,
    )
    svg.add("</g>")
    return {
        "x": float(x),
        "y": float(y),
        "w": float(w),
        "h": float(h),
        "cx": float(x + w / 2),
        "cy": float(y + h / 2),
        "top": float(y),
        "bottom": float(y + h),
        "left": float(x),
        "right": float(x + w),
    }


def label_box(svg: Svg, x: float, y: float, label: str, *, width: int = 180) -> None:
    lines = textwrap.wrap(label, width=max(18, int(width / 8)), break_long_words=False)
    height = 20 + 16 * len(lines)
    svg.rect(x - width / 2, y - height / 2, width, height, fill="#ffffff", stroke="#c7d0dd", sw=1.0, rx=6, opacity=0.96)
    for i, line in enumerate(lines):
        svg.text(x, y - 5 + i * 16, line, size=12, weight=700, fill=PALETTE["edge"], anchor="middle")


def edge(
    svg: Svg,
    points: Sequence[tuple[float, float]],
    label: str | None = None,
    *,
    label_at: tuple[float, float] | None = None,
    color: str = PALETTE["edge"],
    dash: str | None = None,
    width: float = 2.3,
    opacity: float = 0.92,
) -> None:
    svg.polyline(points, stroke=color, sw=width, dash=dash, marker=True, opacity=opacity)
    if label:
        lx, ly = label_at or points[len(points) // 2]
        label_box(svg, lx, ly, label)


def draw_module_flow(svg: Svg) -> None:
    modules = [
        ("M1", "Task publishing", "escrow lock + accuracy commit"),
        ("M2", "Registration", "miner proof, PoS, key delivery"),
        ("M3", "Local training", "DGC + score commit + NDD-FE"),
        ("M4", "Aggregation", "decrypt, BSGS, update, evaluate"),
        ("M5", "Verification", "candidate hash + signed votes"),
        ("M6", "Publication", "verified model metadata on-chain"),
        ("M7", "Rewards", "accuracy/score reveal + payout"),
    ]
    x0 = 60
    y = 90
    gap = 12
    w = int((CANVAS_WIDTH - 120 - gap * (len(modules) - 1)) / len(modules))
    h = 62
    for i, (num, title, subtitle) in enumerate(modules):
        x = x0 + i * (w + gap)
        svg.rect(x, y, w, h, fill="#ffffff", stroke="#b7c3d7", sw=1.4, rx=8)
        svg.rect(x, y, 47, h, fill=PALETTE["ink"], stroke="none", rx=8)
        svg.text(x + 23.5, y + 38, num, size=17, weight=850, fill="#ffffff", anchor="middle")
        svg.text(x + 60, y + 25, title, size=15, weight=800, fill=PALETTE["ink"])
        svg.text(x + 60, y + 47, subtitle, size=12, weight=500, fill=PALETTE["muted"])
        if i < len(modules) - 1:
            svg.line(x + w + 2, y + h / 2, x + w + gap - 4, y + h / 2, stroke=PALETTE["edge"], sw=2.2, marker=True)


def draw_architecture(svg: Svg) -> None:
    draw_background(svg)

    svg.text(60, 43, "HealChain System Architecture", size=30, weight=850, fill=PALETTE["ink"])
    svg.text(
        60,
        69,
        "Privacy-preserving federated learning with blockchain escrow, secure aggregation, consensus, and reward distribution",
        size=17,
        weight=500,
        fill=PALETTE["muted"],
    )
    draw_module_flow(svg)

    draw_layer(svg, 60, 178, 1680, 225, "Application and participant layer", "#f7faff", PALETTE["client_stroke"])
    draw_layer(svg, 60, 438, 1680, 265, "Off-chain coordination and storage layer", "#f7fcf9", PALETTE["coord_stroke"])
    draw_layer(svg, 60, 738, 1680, 290, "Secure aggregation and consensus layer", "#fff9f2", PALETTE["agg_stroke"])
    draw_layer(svg, 60, 1063, 1680, 210, "Blockchain settlement layer", "#faf8ff", PALETTE["chain_stroke"])

    boxes: dict[str, dict[str, float]] = {}

    boxes["publisher"] = draw_card(
        svg,
        "publisher",
        100,
        224,
        300,
        140,
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
    boxes["frontend"] = draw_card(
        svg,
        "frontend",
        445,
        224,
        335,
        140,
        "Frontend UI (Next.js)",
        [
            "Wallet-based task publishing, miner registration, training trigger",
            "Verification, reveal, and reward screens",
            "Reads backend state and sends contract transactions",
        ],
        fill=PALETTE["client_fill"],
        stroke=PALETTE["client_stroke"],
        label="UI",
    )
    boxes["miners"] = draw_card(
        svg,
        "miners",
        830,
        224,
        405,
        140,
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
    boxes["operator"] = draw_card(
        svg,
        "aggregator_operator",
        1285,
        224,
        355,
        140,
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

    boxes["backend"] = draw_card(
        svg,
        "backend",
        100,
        488,
        425,
        170,
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
    boxes["db"] = draw_card(
        svg,
        "postgres",
        585,
        488,
        330,
        170,
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
    boxes["artifacts"] = draw_card(
        svg,
        "artifacts",
        970,
        488,
        330,
        170,
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
    boxes["monitor"] = draw_card(
        svg,
        "monitoring",
        1355,
        488,
        285,
        170,
        "Experiment Monitor and Paper Outputs",
        [
            "Run-scoped JSONL service metrics",
            "experiment_summary.json",
            "round_metrics.csv and client_metrics.csv",
        ],
        fill=PALETTE["monitor_fill"],
        stroke=PALETTE["monitor_stroke"],
        label="IEEE",
    )

    boxes["aggregator"] = draw_card(
        svg,
        "aggregator",
        100,
        795,
        425,
        180,
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
    boxes["crypto"] = draw_card(
        svg,
        "secure_aggregation_core",
        585,
        795,
        365,
        180,
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
    boxes["model"] = draw_card(
        svg,
        "model_update",
        1010,
        795,
        330,
        180,
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
    boxes["consensus"] = draw_card(
        svg,
        "consensus",
        1400,
        795,
        240,
        180,
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

    boxes["evm"] = draw_card(
        svg,
        "evm",
        100,
        1114,
        335,
        125,
        "EVM Network (Ganache / Testnet)",
        [
            "JSON-RPC provider and wallet-signed transactions",
            "Immutable event log for task and reward state",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="RPC",
    )
    boxes["escrow"] = draw_card(
        svg,
        "escrow",
        495,
        1114,
        270,
        125,
        "HealChainEscrow",
        [
            "M1 reward lock and accuracy commit",
            "Task status and refund safety path",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M1",
    )
    boxes["stake"] = draw_card(
        svg,
        "stake_registry",
        810,
        1114,
        225,
        125,
        "StakeRegistry",
        [
            "Stake-aware miner support",
            "Selection context for participation",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M2",
    )
    boxes["block"] = draw_card(
        svg,
        "block_publisher",
        1080,
        1114,
        260,
        125,
        "BlockPublisher",
        [
            "M6 model hash, accuracy, score commits",
            "On-chain training result metadata",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M6",
    )
    boxes["reward"] = draw_card(
        svg,
        "reward_distribution",
        1385,
        1114,
        255,
        125,
        "RewardDistribution",
        [
            "M7 accuracy and score reveal",
            "Proportional payout to miners",
        ],
        fill=PALETTE["chain_fill"],
        stroke=PALETTE["chain_stroke"],
        label="M7",
    )

    # Main workflow edges.
    edge(
        svg,
        [(boxes["publisher"]["right"], boxes["publisher"]["cy"]), (boxes["frontend"]["left"], boxes["frontend"]["cy"])],
        "wallet inputs and task intent",
        label_at=(423, 276),
        width=2.4,
    )
    edge(
        svg,
        [
            (boxes["frontend"]["cx"], boxes["frontend"]["bottom"]),
            (boxes["frontend"]["cx"], 424),
            (boxes["backend"]["cx"], 424),
            (boxes["backend"]["cx"], boxes["backend"]["top"]),
        ],
        "REST task, miner, train, reveal APIs",
        label_at=(540, 423),
        width=2.4,
    )
    edge(
        svg,
        [
            (boxes["miners"]["cx"], boxes["miners"]["bottom"]),
            (boxes["miners"]["cx"], 428),
            (boxes["backend"]["right"] - 55, 428),
            (boxes["backend"]["right"] - 55, boxes["backend"]["top"]),
        ],
        "signed sparse ciphertext + score commit",
        label_at=(760, 423),
        width=2.4,
    )
    edge(
        svg,
        [
            (boxes["backend"]["right"], boxes["backend"]["cy"]),
            (boxes["db"]["left"], boxes["db"]["cy"]),
        ],
        "persist protocol state",
        label_at=(555, 575),
        color=PALETTE["coord_stroke"],
    )
    edge(
        svg,
        [
            (boxes["backend"]["right"], boxes["backend"]["cy"] + 38),
            (boxes["artifacts"]["left"], boxes["artifacts"]["cy"] + 38),
        ],
        "store and resolve model/proof links",
        label_at=(748, 632),
        color=PALETTE["store_stroke"],
    )
    edge(
        svg,
        [
            (boxes["operator"]["cx"], boxes["operator"]["bottom"]),
            (boxes["operator"]["cx"], 744),
            (boxes["aggregator"]["right"] - 35, 744),
            (boxes["aggregator"]["right"] - 35, boxes["aggregator"]["top"]),
        ],
        "selected aggregator job",
        label_at=(896, 744),
        width=2.2,
    )
    edge(
        svg,
        [
            (boxes["backend"]["cx"], boxes["backend"]["bottom"]),
            (boxes["backend"]["cx"], 742),
            (boxes["aggregator"]["cx"], 742),
            (boxes["aggregator"]["cx"], boxes["aggregator"]["top"]),
        ],
        "task metadata, keys, submissions",
        label_at=(315, 735),
        color=PALETTE["agg_stroke"],
        width=2.4,
    )
    edge(
        svg,
        [
            (boxes["aggregator"]["right"], boxes["aggregator"]["cy"]),
            (boxes["crypto"]["left"], boxes["crypto"]["cy"]),
        ],
        "validated payloads",
        label_at=(555, 885),
        color=PALETTE["agg_stroke"],
    )
    edge(
        svg,
        [
            (boxes["crypto"]["right"], boxes["crypto"]["cy"]),
            (boxes["model"]["left"], boxes["model"]["cy"]),
        ],
        "aggregate update vector",
        label_at=(981, 885),
        color=PALETTE["agg_stroke"],
    )
    edge(
        svg,
        [
            (boxes["model"]["right"], boxes["model"]["cy"]),
            (boxes["consensus"]["left"], boxes["consensus"]["cy"]),
        ],
        "candidate block hash",
        label_at=(1368, 885),
        color=PALETTE["agg_stroke"],
    )
    edge(
        svg,
        [
            (boxes["consensus"]["cx"], boxes["consensus"]["bottom"]),
            (boxes["consensus"]["cx"], 1047),
            (boxes["backend"]["right"] + 40, 1047),
            (boxes["backend"]["right"] + 40, boxes["backend"]["bottom"]),
        ],
        "majority-valid candidate",
        label_at=(1035, 1047),
        color=PALETTE["agg_stroke"],
        width=2.4,
    )
    edge(
        svg,
        [
            (boxes["model"]["cx"], boxes["model"]["top"]),
            (boxes["model"]["cx"], 716),
            (boxes["artifacts"]["cx"], 716),
            (boxes["artifacts"]["cx"], boxes["artifacts"]["bottom"]),
        ],
        "read validation data; write modelLink/W_new",
        label_at=(1086, 716),
        color=PALETTE["store_stroke"],
        dash="8 6",
    )
    edge(
        svg,
        [
            (boxes["miners"]["right"], boxes["miners"]["cy"] + 12),
            (boxes["consensus"]["right"] + 35, boxes["miners"]["cy"] + 12),
            (boxes["consensus"]["right"] + 35, boxes["consensus"]["cy"]),
            (boxes["consensus"]["right"], boxes["consensus"]["cy"]),
        ],
        "M5 signed verification votes",
        label_at=(1546, 648),
        color=PALETTE["agg_stroke"],
        dash="8 6",
        width=2.2,
    )

    # Blockchain interactions.
    edge(
        svg,
        [
            (boxes["frontend"]["left"] + 38, boxes["frontend"]["bottom"]),
            (boxes["frontend"]["left"] + 38, 1087),
            (boxes["evm"]["cx"], 1087),
            (boxes["evm"]["cx"], boxes["evm"]["top"]),
        ],
        "publisher/miner wallet transactions",
        label_at=(270, 1087),
        color=PALETTE["chain_stroke"],
        width=2.2,
    )
    edge(
        svg,
        [
            (boxes["backend"]["left"] + 55, boxes["backend"]["bottom"]),
            (boxes["backend"]["left"] + 55, 1048),
            (boxes["block"]["cx"], 1048),
            (boxes["block"]["cx"], boxes["block"]["top"]),
        ],
        "M6 backend chain bridge",
        label_at=(687, 1048),
        color=PALETTE["chain_stroke"],
        width=2.4,
    )
    edge(
        svg,
        [(boxes["evm"]["right"], boxes["evm"]["cy"]), (boxes["escrow"]["left"], boxes["escrow"]["cy"])],
        None,
        color=PALETTE["chain_stroke"],
        width=2.0,
    )
    edge(
        svg,
        [(boxes["escrow"]["right"], boxes["escrow"]["cy"]), (boxes["stake"]["left"], boxes["stake"]["cy"])],
        None,
        color=PALETTE["chain_stroke"],
        width=2.0,
    )
    edge(
        svg,
        [(boxes["stake"]["right"], boxes["stake"]["cy"]), (boxes["block"]["left"], boxes["block"]["cy"])],
        None,
        color=PALETTE["chain_stroke"],
        width=2.0,
    )
    edge(
        svg,
        [(boxes["block"]["right"], boxes["block"]["cy"]), (boxes["reward"]["left"], boxes["reward"]["cy"])],
        "published block enables reveal",
        label_at=(1360, 1177),
        color=PALETTE["chain_stroke"],
        width=2.0,
    )
    edge(
        svg,
        [
            (boxes["reward"]["cx"], boxes["reward"]["top"]),
            (boxes["reward"]["cx"], 1070),
            (boxes["miners"]["cx"], 1070),
            (boxes["miners"]["cx"], boxes["miners"]["bottom"]),
        ],
        "M7 proportional rewards",
        label_at=(1215, 1070),
        color=PALETTE["chain_stroke"],
        dash="8 6",
        width=2.0,
    )

    # Observability edges.
    edge(
        svg,
        [
            (boxes["backend"]["right"], boxes["backend"]["top"] + 28),
            (boxes["monitor"]["left"], boxes["monitor"]["top"] + 28),
        ],
        "API and DB metrics",
        label_at=(948, 516),
        color=PALETTE["monitor_stroke"],
        dash="5 5",
        width=1.9,
        opacity=0.82,
    )
    edge(
        svg,
        [
            (boxes["aggregator"]["right"], boxes["aggregator"]["bottom"] - 18),
            (boxes["monitor"]["cx"], boxes["aggregator"]["bottom"] - 18),
            (boxes["monitor"]["cx"], boxes["monitor"]["bottom"]),
        ],
        "aggregation logs and round metrics",
        label_at=(1032, 958),
        color=PALETTE["monitor_stroke"],
        dash="5 5",
        width=1.9,
        opacity=0.82,
    )

    # Legend and reproducibility note.
    legend_y = 1293
    svg.line(72, legend_y, 142, legend_y, stroke=PALETTE["edge"], sw=2.4, marker=True)
    svg.text(155, legend_y + 5, "solid: API call or blockchain transaction", size=13, weight=650, fill=PALETTE["muted"])
    svg.line(430, legend_y, 500, legend_y, stroke=PALETTE["monitor_stroke"], sw=2.0, dash="6 5", marker=True)
    svg.text(512, legend_y + 5, "dashed: artifact, metrics, or verification side flow", size=13, weight=650, fill=PALETTE["muted"])
    svg.text(
        1738,
        legend_y + 5,
        "Generated from repository architecture docs",
        size=13,
        weight=650,
        fill=PALETTE["muted"],
        anchor="end",
    )


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
        "stored as local/IPFS links, and run-scoped logs feed the experiment "
        "analysis outputs used for reporting."
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
