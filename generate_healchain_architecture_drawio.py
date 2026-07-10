#!/usr/bin/env python3
"""Generate a fully editable Draw.io architecture diagram for HealChain.

Unlike the SVG wrapper, this script emits native Draw.io XML cells: every layer,
component card, badge, label, connector, marker, and legend item is separately
editable in diagrams.net/draw.io.
"""

from __future__ import annotations

import datetime as dt
import html
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


CANVAS_WIDTH = 3600
CANVAS_HEIGHT = 2600


PALETTE = {
    "ink": "#172033",
    "muted": "#536170",
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


class Drawio:
    def __init__(self, width: int, height: int) -> None:
        modified = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
        self.mxfile = ET.Element(
            "mxfile",
            {
                "host": "app.diagrams.net",
                "modified": modified,
                "agent": "Codex",
                "version": "24.7.17",
                "type": "device",
            },
        )
        self.diagram = ET.SubElement(
            self.mxfile,
            "diagram",
            {"id": "healchain-system-architecture-editable", "name": "HealChain System Architecture"},
        )
        self.model = ET.SubElement(
            self.diagram,
            "mxGraphModel",
            {
                "dx": str(width),
                "dy": str(height),
                "grid": "1",
                "gridSize": "10",
                "guides": "1",
                "tooltips": "1",
                "connect": "1",
                "arrows": "1",
                "fold": "1",
                "page": "1",
                "pageScale": "1",
                "pageWidth": str(width),
                "pageHeight": str(height),
                "math": "0",
                "shadow": "0",
            },
        )
        self.root = ET.SubElement(self.model, "root")
        ET.SubElement(self.root, "mxCell", {"id": "0"})
        ET.SubElement(self.root, "mxCell", {"id": "1", "parent": "0"})

    def vertex(self, cell_id: str, value: str, style: str, x: float, y: float, w: float, h: float) -> None:
        cell = ET.SubElement(
            self.root,
            "mxCell",
            {"id": cell_id, "value": value, "style": style, "vertex": "1", "parent": "1"},
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {"x": f"{x:.1f}", "y": f"{y:.1f}", "width": f"{w:.1f}", "height": f"{h:.1f}", "as": "geometry"},
        )

    def edge(
        self,
        cell_id: str,
        points: Sequence[tuple[float, float]],
        *,
        color: str,
        dashed: bool = False,
        width: float = 3.0,
    ) -> None:
        dash = "dashed=1;dashPattern=10 8;" if dashed else ""
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            f"html=1;endArrow=block;endFill=1;strokeColor={color};strokeWidth={width:.1f};{dash}"
        )
        cell = ET.SubElement(
            self.root,
            "mxCell",
            {"id": cell_id, "value": "", "style": style, "edge": "1", "parent": "1"},
        )
        geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        sx, sy = points[0]
        tx, ty = points[-1]
        ET.SubElement(geom, "mxPoint", {"x": f"{sx:.1f}", "y": f"{sy:.1f}", "as": "sourcePoint"})
        ET.SubElement(geom, "mxPoint", {"x": f"{tx:.1f}", "y": f"{ty:.1f}", "as": "targetPoint"})
        if len(points) > 2:
            arr = ET.SubElement(geom, "Array", {"as": "points"})
            for x, y in points[1:-1]:
                ET.SubElement(arr, "mxPoint", {"x": f"{x:.1f}", "y": f"{y:.1f}"})

    def xml(self) -> str:
        ET.indent(self.mxfile, space="  ")
        xml = ET.tostring(self.mxfile, encoding="unicode", short_empty_elements=True)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml + "\n"


def text_style(size: int, color: str, *, bold: bool = False, align: str = "left") -> str:
    return (
        "text;html=1;strokeColor=none;fillColor=none;whiteSpace=wrap;rounded=0;"
        f"align={align};verticalAlign=top;fontSize={size};fontColor={color};"
        f"fontStyle={1 if bold else 0};spacing=0;"
    )


def rect_style(fill: str, stroke: str, *, rounded: bool = True, opacity: int | None = None, shadow: bool = False) -> str:
    style = (
        f"rounded={1 if rounded else 0};whiteSpace=wrap;html=1;arcSize=6;"
        f"fillColor={fill};strokeColor={stroke};strokeWidth=2;"
    )
    if opacity is not None:
        style += f"opacity={opacity};"
    if shadow:
        style += "shadow=1;"
    return style


def html_lines(lines: Iterable[str]) -> str:
    return "<br>".join(html.escape(line) for line in lines)


def draw_text(g: Drawio, cell_id: str, text: str, x: float, y: float, w: float, h: float, *, size: int, color: str, bold: bool = False, align: str = "left") -> None:
    g.vertex(cell_id, html.escape(text), text_style(size, color, bold=bold, align=align), x, y, w, h)


def draw_layer(g: Drawio, box: Box, title: str, fill: str, stroke: str) -> None:
    g.vertex(f"{box.key}_layer", "", rect_style(fill, stroke, opacity=88), box.x, box.y, box.w, box.h)
    draw_text(g, f"{box.key}_title", title.upper(), box.x + 34, box.y + 24, box.w - 68, 40, size=22, color=stroke, bold=True)


def draw_card(g: Drawio, box: Box, title: str, body: Sequence[str], *, fill: str, stroke: str, label: str) -> None:
    g.vertex(f"{box.key}_card", "", rect_style(fill, stroke, shadow=True), box.x, box.y, box.w, box.h)
    g.vertex(
        f"{box.key}_bar",
        "",
        f"rounded=1;whiteSpace=wrap;html=1;arcSize=6;fillColor={stroke};strokeColor={stroke};strokeWidth=1;",
        box.x,
        box.y,
        box.w,
        12,
    )
    badge_w = max(74, 22 + len(label) * 13)
    g.vertex(
        f"{box.key}_badge",
        html.escape(label),
        (
            f"rounded=1;whiteSpace=wrap;html=1;arcSize=20;fillColor={stroke};strokeColor={stroke};"
            "fontColor=#ffffff;fontStyle=1;fontSize=20;align=center;verticalAlign=middle;"
        ),
        box.x + 28,
        box.y + 30,
        badge_w,
        42,
    )
    title_x = box.x + 52 + badge_w
    g.vertex(
        f"{box.key}_heading",
        html.escape(title),
        text_style(30, PALETTE["ink"], bold=True),
        title_x,
        box.y + 32,
        box.w - (title_x - box.x) - 28,
        74,
    )
    bullet_text = html_lines(f"- {line}" for line in body)
    g.vertex(
        f"{box.key}_body",
        bullet_text,
        text_style(21, PALETTE["muted"]),
        box.x + 28,
        box.y + 110,
        box.w - 56,
        box.h - 120,
    )


def flow_marker(g: Drawio, cell_id: str, x: float, y: float, number: int, color: str) -> None:
    g.vertex(
        f"{cell_id}_outer",
        "",
        f"ellipse;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={color};strokeWidth=3;",
        x - 24,
        y - 24,
        48,
        48,
    )
    g.vertex(
        cell_id,
        str(number),
        (
            f"ellipse;whiteSpace=wrap;html=1;fillColor={color};strokeColor={color};strokeWidth=1;"
            "fontColor=#ffffff;fontStyle=1;fontSize=19;align=center;verticalAlign=middle;"
        ),
        x - 18,
        y - 18,
        36,
        36,
    )


def module_flow(g: Drawio) -> None:
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
    for idx, (num, title, subtitle) in enumerate(modules):
        x = x0 + idx * (w + gap)
        g.vertex(f"module_{num}_box", "", rect_style("#ffffff", "#b6c4da"), x, y, w, h)
        g.vertex(
            f"module_{num}_badge",
            html.escape(num),
            "rounded=1;whiteSpace=wrap;html=1;arcSize=6;fillColor=#172033;strokeColor=#172033;fontColor=#ffffff;fontStyle=1;fontSize=28;align=center;verticalAlign=middle;",
            x,
            y,
            78,
            h,
        )
        draw_text(g, f"module_{num}_title", title, x + 98, y + 24, w - 115, 34, size=23, color=PALETTE["ink"], bold=True)
        draw_text(g, f"module_{num}_subtitle", subtitle, x + 98, y + 62, w - 115, 30, size=18, color=PALETTE["muted"])
        if idx < len(modules) - 1:
            g.edge(f"module_{num}_arrow", [(x + w + 4, y + h / 2), (x + w + gap - 7, y + h / 2)], color=PALETTE["edge"], width=3.0)


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


def draw_edges(g: Drawio, b: dict[str, Box]) -> None:
    edge_specs = [
        ("flow_01", [(b["publisher"].right, b["publisher"].cy), (b["frontend"].left, b["frontend"].cy)], 1, ((b["publisher"].right + b["frontend"].left) / 2, b["publisher"].cy), PALETTE["edge"], False),
        ("flow_02", [(b["frontend"].cx, b["frontend"].bottom), (b["frontend"].cx, 670), (b["backend"].cx, 670), (b["backend"].cx, b["backend"].top)], 2, (b["frontend"].cx, 670), PALETTE["edge"], False),
        ("flow_03", [(b["miners"].cx, b["miners"].bottom), (b["miners"].cx, 670), (b["backend"].right - 110, 670), (b["backend"].right - 110, b["backend"].top)], 3, (b["miners"].cx, 670), PALETTE["edge"], False),
        ("flow_04", [(b["operator"].cx, b["operator"].bottom), (b["operator"].cx, 1155), (b["aggregator"].right - 120, 1155), (b["aggregator"].right - 120, b["aggregator"].top)], 4, (b["operator"].cx, 1155), PALETTE["agg_stroke"], False),
        ("flow_05", [(b["backend"].right, b["backend"].cy - 55), (b["db"].left, b["db"].cy - 55)], 5, (1110, b["backend"].cy - 55), PALETTE["coord_stroke"], False),
        ("flow_06", [(b["backend"].right, b["backend"].cy + 55), (b["artifacts"].left, b["artifacts"].cy + 55)], 6, (2030, b["backend"].cy + 55), PALETTE["store_stroke"], False),
        ("flow_07", [(b["backend"].cx, b["backend"].bottom), (b["backend"].cx, 1155), (b["aggregator"].cx, 1155), (b["aggregator"].cx, b["aggregator"].top)], 7, (b["backend"].cx, 1155), PALETTE["agg_stroke"], False),
        ("flow_08", [(b["aggregator"].right, b["aggregator"].cy), (b["crypto"].left, b["crypto"].cy)], 8, (1010, b["aggregator"].cy), PALETTE["agg_stroke"], False),
        ("flow_09", [(b["crypto"].right, b["crypto"].cy), (b["model"].left, b["model"].cy)], 9, (1820, b["crypto"].cy), PALETTE["agg_stroke"], False),
        ("flow_10", [(b["model"].right, b["model"].cy), (b["consensus"].left, b["consensus"].cy)], 10, (2640, b["model"].cy), PALETTE["agg_stroke"], False),
        ("flow_11", [(b["artifacts"].cx, b["artifacts"].bottom), (b["artifacts"].cx, 1155), (b["model"].cx, 1155), (b["model"].cx, b["model"].top)], 11, (b["model"].cx, 1155), PALETTE["store_stroke"], True),
        ("flow_12", [(b["miners"].right, b["miners"].cy + 55), (3540, b["miners"].cy + 55), (3540, b["consensus"].cy), (b["consensus"].right, b["consensus"].cy)], 12, (3540, 990), PALETTE["agg_stroke"], True),
        ("flow_13", [(b["frontend"].left + 60, b["frontend"].bottom), (100, b["frontend"].bottom), (100, b["evm"].cy), (b["evm"].left, b["evm"].cy)], 13, (100, 1535), PALETTE["chain_stroke"], False),
        ("flow_14", [(b["backend"].left + 70, b["backend"].bottom), (b["backend"].left + 70, 1590), (b["block"].cx, 1590), (b["block"].cx, b["block"].top)], 14, (b["block"].cx, 1590), PALETTE["chain_stroke"], False),
        ("flow_15", [(b["block"].right, b["block"].cy), (b["reward"].left, b["reward"].cy)], 15, (2670, b["block"].cy), PALETTE["chain_stroke"], False),
        ("flow_16", [(b["reward"].cx, b["reward"].top), (b["reward"].cx, 1590), (b["miners"].cx, 1590), (b["miners"].cx, b["miners"].bottom)], 16, (b["reward"].cx, 1590), PALETTE["chain_stroke"], True),
    ]
    for cell_id, points, num, marker_at, color, dashed in edge_specs:
        g.edge(cell_id, points, color=color, dashed=dashed, width=3.2)
        flow_marker(g, f"{cell_id}_marker", marker_at[0], marker_at[1], num, color)

    for idx, (start, end) in enumerate(
        [
            ((b["evm"].right, b["evm"].cy), (b["escrow"].left, b["escrow"].cy)),
            ((b["escrow"].right, b["escrow"].cy), (b["stake"].left, b["stake"].cy)),
            ((b["stake"].right, b["stake"].cy), (b["block"].left, b["block"].cy)),
        ],
        start=1,
    ):
        g.edge(f"chain_contract_link_{idx}", [start, end], color=PALETTE["chain_stroke"], width=2.7)


def draw_cards(g: Drawio, b: dict[str, Box]) -> None:
    cards = [
        ("publisher", "Task Publisher / Researcher", ["Defines dataset, initial model, reward, deadline, target accuracy", "Commits H(accuracy || nonceTP)", "Reveals accuracy after publication"], PALETTE["client_fill"], PALETTE["client_stroke"], "USER"),
        ("frontend", "Frontend UI (Next.js)", ["Wallet-based publishing, miner registration, training trigger", "Verification, reveal, and reward screens", "Reads backend state and sends contract transactions"], PALETTE["client_fill"], PALETTE["client_stroke"], "UI"),
        ("miners", "Miner FL Clients (N participants)", ["Raw medical data remains local", "Train model, compute gradients, apply DGC compression", "Create score commit, NDD-FE sparse ciphertext, ECDSA signature"], PALETTE["client_fill"], PALETTE["client_stroke"], "M3"),
        ("operator", "Selected Aggregator Endpoint", ["Chosen through task/miner state and stake-aware orchestration", "Runs Python API service for aggregation jobs", "Uses task-scoped keys and backend metadata"], PALETTE["client_fill"], PALETTE["client_stroke"], "M2"),
        ("backend", "Backend Coordination API (Express + Prisma)", ["Task lifecycle, wallet signature checks, proof verification", "Miner registration, PoS selection, key derivation and delivery", "Opaque relay for submissions, verification votes, publish/reward APIs"], PALETTE["coord_fill"], PALETTE["coord_stroke"], "API"),
        ("db", "PostgreSQL State Store", ["Task, Miner, Gradient, Block, Verification, Reward tables", "Round status and current model links", "Audit trail for protocol progress"], PALETTE["coord_fill"], PALETTE["coord_stroke"], "DB"),
        ("artifacts", "Artifact / IPFS Storage", ["Initial models and validation datasets", "Miner proofs and model artifact links", "Updated W_new artifacts for iterative rounds"], PALETTE["store_fill"], PALETTE["store_stroke"], "IPFS"),
        ("aggregator", "Aggregator Orchestrator (Python M4-M6)", ["Polls backend for task metadata, selected miners, keys, submissions", "Validates sparse schema, signatures, hashes, and participant limits", "Builds candidate block and submits final payload"], PALETTE["agg_fill"], PALETTE["agg_stroke"], "M4"),
        ("crypto", "Secure Aggregation Core", ["NDD-FE designated decryption over sparse ciphertext", "BSGS recovery of quantized gradient coordinates", "Dense reconstruction only after strict sparse recovery"], PALETTE["agg_fill"], PALETTE["agg_stroke"], "SEC"),
        ("model", "Model Update and Evaluation", ["Apply W(t+1) = W(t) + eta * aggregate update", "Evaluate accuracy on validation data", "Publish modelLink or carry-forward W_new for next round"], PALETTE["agg_fill"], PALETTE["agg_stroke"], "EVAL"),
        ("consensus", "Miner Verification Consensus", ["Candidate hash broadcast", "Signed VALID / INVALID votes", "Majority decision before publication"], PALETTE["agg_fill"], PALETTE["agg_stroke"], "M5"),
        ("evm", "EVM Network (Ganache / Testnet)", ["JSON-RPC provider and wallet-signed transactions", "Immutable event log for task and reward state"], PALETTE["chain_fill"], PALETTE["chain_stroke"], "RPC"),
        ("escrow", "HealChainEscrow", ["M1 reward lock and accuracy commit", "Task status and refund safety path"], PALETTE["chain_fill"], PALETTE["chain_stroke"], "M1"),
        ("stake", "StakeRegistry", ["Stake-aware miner support", "Selection context for participation"], PALETTE["chain_fill"], PALETTE["chain_stroke"], "M2"),
        ("block", "BlockPublisher", ["M6 model hash, accuracy, score commits", "On-chain training result metadata"], PALETTE["chain_fill"], PALETTE["chain_stroke"], "M6"),
        ("reward", "RewardDistribution", ["M7 accuracy and score reveal", "Proportional payout to miners"], PALETTE["chain_fill"], PALETTE["chain_stroke"], "M7"),
    ]
    for key, title, body, fill, stroke, label in cards:
        draw_card(g, b[key], title, body, fill=fill, stroke=stroke, label=label)


def draw_legend(g: Drawio) -> None:
    legend = Box("legend", 110, 2010, 3380, 430)
    g.vertex("legend_box", "", rect_style("#ffffff", "#c7d0dd"), legend.x, legend.y, legend.w, legend.h)
    draw_text(g, "legend_title", "Numbered Data Flow Legend", legend.x + 34, legend.y + 28, 470, 44, size=31, color=PALETTE["ink"], bold=True)
    draw_text(
        g,
        "legend_subtitle",
        "Numbers replace long arrow labels to keep the architecture figure readable after export.",
        legend.x + 560,
        legend.y + 31,
        1700,
        38,
        size=23,
        color=PALETTE["muted"],
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
        flow_marker(g, f"legend_marker_{num}", x + 24, y - 9, int(num), PALETTE["edge"])
        g.vertex(f"legend_text_{num}", html.escape(text), text_style(20, PALETTE["muted"]), x + 62, y - 24, col_w - 74, 58)

    g.edge("legend_solid_arrow", [(140, 2515), (235, 2515)], color=PALETTE["edge"], width=3.7)
    draw_text(g, "legend_solid_text", "solid: API call, pipeline handoff, or blockchain transaction", 260, 2495, 710, 34, size=20, color=PALETTE["muted"], bold=True)
    g.edge("legend_dashed_arrow", [(1010, 2515), (1105, 2515)], color=PALETTE["edge_soft"], dashed=True, width=3.1)
    draw_text(g, "legend_dashed_text", "dashed: artifact, verification, or reward side flow", 1130, 2495, 620, 34, size=20, color=PALETTE["muted"], bold=True)
    draw_text(g, "legend_source", "Generated from repository architecture docs", 2830, 2495, 640, 34, size=20, color=PALETTE["muted"], bold=True, align="right")


def build_drawio() -> str:
    g = Drawio(CANVAS_WIDTH, CANVAS_HEIGHT)
    g.vertex("background", "", rect_style("#fbfcfe", "none", rounded=False), 0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
    draw_text(g, "page_title", "HealChain System Architecture", 110, 38, 1200, 70, size=56, color=PALETTE["ink"], bold=True)
    draw_text(
        g,
        "page_subtitle",
        "Privacy-preserving federated learning with blockchain escrow, secure aggregation, consensus, and reward distribution",
        110,
        92,
        2200,
        42,
        size=29,
        color=PALETTE["muted"],
    )
    module_flow(g)

    for layer, title, fill, stroke in [
        (Box("app_layer", 110, 280, 3380, 360), "Application and participant layer", "#f7faff", PALETTE["client_stroke"]),
        (Box("coord_layer", 110, 700, 3380, 365), "Off-chain coordination and storage layer", "#f7fcf9", PALETTE["coord_stroke"]),
        (Box("agg_layer", 110, 1125, 3380, 390), "Secure aggregation and consensus layer", "#fff9f2", PALETTE["agg_stroke"]),
        (Box("chain_layer", 110, 1580, 3380, 380), "Blockchain settlement layer", "#faf8ff", PALETTE["chain_stroke"]),
    ]:
        draw_layer(g, layer, title, fill, stroke)

    boxes = architecture_boxes()
    draw_edges(g, boxes)
    draw_cards(g, boxes)
    draw_legend(g)
    return g.xml()


def main() -> None:
    out_dir = Path("artifacts/architecture")
    out_dir.mkdir(parents=True, exist_ok=True)
    xml_text = build_drawio()
    drawio_path = out_dir / "healchain_system_architecture.drawio"
    xml_path = out_dir / "healchain_system_architecture_editable.drawio.xml"
    drawio_path.write_text(xml_text, encoding="utf-8")
    xml_path.write_text(xml_text, encoding="utf-8")
    print(f"Wrote editable Draw.io file: {drawio_path}")
    print(f"Wrote editable Draw.io XML: {xml_path}")
    print(f"Page size: {CANVAS_WIDTH} x {CANVAS_HEIGHT}")


if __name__ == "__main__":
    main()
