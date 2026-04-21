"""Min-Cut Algorithms — animated lecture.

A single-file Manim Community script that walks through the theory and
dry-runs of the main min-cut algorithms (Karger, Karger-Stein,
Stoer-Wagner, and max-flow/min-cut duality).

Render a specific scene, e.g.:
    manim -pqm min_cut_animation.py KargersFullDryRun
"""

from __future__ import annotations

import math
import random
from typing import Sequence

from manim import (
    DOWN,
    GOLD,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    Arrow,
    Circle,
    Create,
    FadeIn,
    FadeOut,
    Flash,
    Indicate,
    Line,
    MathTex,
    Mobject,
    ReplacementTransform,
    RoundedRectangle,
    Scene,
    SurroundingRectangle,
    Table,
    Text,
    Transform,
    VGroup,
    Write,
    config,
    smooth,
)

# ─── Theme ────────────────────────────────────────────────────────────────
config.background_color = "#0D1117"

NODE_COLOR = "#58A6FF"
EDGE_COLOR = "#30363D"
ACTIVE_COLOR = "#F2CC60"
ALERT_COLOR = "#FF7B72"
TEXT_COLOR = "#E6EDF3"
SUCCESS_COLOR = "#3FB950"
MERGE_COLOR = "#D2A8FF"  # purple for merged nodes
HIGHLIGHT_EDGE = "#FFA657"  # orange for highlighted edges
PSEUDO_BG = "#161B22"  # background for pseudocode boxes


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════
def styled_text(value: str, size: int = 28, color: str = TEXT_COLOR, **kwargs) -> Text:
    return Text(value, font_size=size, color=color, **kwargs)


def create_styled_box(
    title: str | None,
    content_lines: Sequence[str],
    width: float = 6.0,
    height: float | None = None,
    title_color: str = ACTIVE_COLOR,
    body_color: str = TEXT_COLOR,
    mono: bool = False,
    body_size: int = 22,
    title_size: int = 26,
) -> VGroup:
    """A RoundedRectangle + title + body used for pseudocode / info panels."""

    font = "Monospace" if mono else None
    body = VGroup(
        *[
            Text(
                line if line else " ",
                font_size=body_size,
                color=body_color,
                font=font,
            )
            for line in content_lines
        ]
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.18)

    if title:
        title_mob = Text(title, font_size=title_size, color=title_color, weight="BOLD")
        content = VGroup(title_mob, body).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
    else:
        content = body

    if height is None:
        height = content.height + 0.8

    box = RoundedRectangle(
        width=width,
        height=height,
        corner_radius=0.2,
        stroke_color=EDGE_COLOR,
        stroke_width=2,
        fill_color=PSEUDO_BG,
        fill_opacity=1.0,
    )
    content.move_to(box.get_center())
    if title:
        content.align_to(box, LEFT).shift(RIGHT * 0.3)
        content.align_to(box, UP).shift(DOWN * 0.3)
    return VGroup(box, content)


def create_step_counter(current: int, total: int) -> VGroup:
    label = Text(
        f"Step {current}/{total}", font_size=24, color=ACTIVE_COLOR, weight="BOLD"
    )
    box = RoundedRectangle(
        width=label.width + 0.5,
        height=label.height + 0.35,
        corner_radius=0.1,
        stroke_color=ACTIVE_COLOR,
        stroke_width=2,
        fill_color=PSEUDO_BG,
        fill_opacity=1.0,
    )
    label.move_to(box.get_center())
    return VGroup(box, label)


def highlight_edge_flash(
    scene: Scene, edge: Mobject, color: str = ACTIVE_COLOR, run_time: float = 0.5
) -> None:
    original_color = edge.get_color()
    scene.play(edge.animate.set_color(color).set_stroke(width=6), run_time=run_time)
    scene.play(edge.animate.set_color(original_color).set_stroke(width=3), run_time=run_time)


def make_node(label: str, position, radius: float = 0.25, color: str = NODE_COLOR) -> VGroup:
    circle = Circle(
        radius=radius,
        stroke_color=color,
        stroke_width=3,
        fill_color=color,
        fill_opacity=0.25,
    ).move_to(position)
    txt = Text(label, font_size=int(radius * 90), color=TEXT_COLOR, weight="BOLD")
    txt.move_to(circle.get_center())
    group = VGroup(circle, txt)
    group.circle = circle
    group.label = txt
    group.node_label = label
    return group


def make_edge(a: VGroup, b: VGroup, color: str = EDGE_COLOR, width: float = 3) -> Line:
    line = Line(
        a.circle.get_center(),
        b.circle.get_center(),
        color=color,
        stroke_width=width,
    )
    return line


def create_graph_with_labels(
    nodes: Sequence[str],
    edges: Sequence[tuple[str, str]],
    positions: dict,
    radius: float = 0.25,
    scale: float = 1.0,
    node_color: str = NODE_COLOR,
    edge_color: str = EDGE_COLOR,
) -> tuple[VGroup, dict, dict]:
    """Create a graph. Returns (group, node_dict, edge_dict).

    edge_dict is keyed by the unordered tuple (min(u,v), max(u,v)).
    """

    node_dict: dict[str, VGroup] = {
        n: make_node(n, positions[n], radius=radius, color=node_color) for n in nodes
    }
    edge_dict: dict[tuple[str, str], Line] = {}
    edge_group = VGroup()
    for u, v in edges:
        key = tuple(sorted((u, v)))
        if key in edge_dict:
            continue
        edge_dict[key] = make_edge(node_dict[u], node_dict[v], color=edge_color)
        edge_group.add(edge_dict[key])

    node_group = VGroup(*node_dict.values())
    full = VGroup(edge_group, node_group)
    full.scale(scale)
    return full, node_dict, edge_dict


def circle_positions(nodes: Sequence[str], radius: float = 2.6):
    n = len(nodes)
    return {
        node: radius
        * (
            math.cos(2 * math.pi * i / n - math.pi / 2) * RIGHT
            + math.sin(2 * math.pi * i / n - math.pi / 2) * UP
        )
        for i, node in enumerate(nodes)
    }


def indicated_title(text: str, color: str = ACTIVE_COLOR, size: int = 44) -> VGroup:
    title = Text(text, font_size=size, color=color, weight="BOLD")
    underline = Line(
        title.get_left() + DOWN * 0.35,
        title.get_right() + DOWN * 0.35,
        stroke_width=3,
        color=color,
    )
    return VGroup(title, underline)


# ═════════════════════════════════════════════════════════════════════════
# A.  intro_credits
# ═════════════════════════════════════════════════════════════════════════
class IntroCredits(Scene):
    def construct(self):
        title = Text(
            "Min-Cut Algorithms",
            font_size=72,
            color=ACTIVE_COLOR,
            weight="BOLD",
        )
        subtitle = Text(
            "Karger • Karger–Stein • Stoer–Wagner • Max-Flow",
            font_size=30,
            color=TEXT_COLOR,
        ).next_to(title, DOWN, buff=0.5)

        underline = Line(
            title.get_left(),
            title.get_left(),
            stroke_width=5,
            color=ACTIVE_COLOR,
        ).next_to(title, DOWN, buff=0.15)

        self.play(FadeIn(title, shift=UP * 0.4), run_time=1.5)
        self.play(
            underline.animate.put_start_and_end_on(
                title.get_left() + DOWN * 0.35, title.get_right() + DOWN * 0.35
            ),
            run_time=1.5,
            rate_func=smooth,
        )
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=1.5)
        self.wait(2)

        credits = VGroup(
            Text("Presented by", font_size=24, color=TEXT_COLOR),
            Text("Graph Algorithms Group", font_size=28, color=NODE_COLOR, weight="BOLD"),
        ).arrange(DOWN, buff=0.2)
        credits.to_edge(DOWN, buff=0.8)

        self.play(FadeIn(credits, shift=UP * 0.2), run_time=1.5)
        self.wait(1.5)
        self.play(
            FadeOut(VGroup(title, underline, subtitle, credits)),
            run_time=0.7,
        )


# ═════════════════════════════════════════════════════════════════════════
# B.  basics_chapter
# ═════════════════════════════════════════════════════════════════════════
class BasicsChapter(Scene):
    def construct(self):
        heading = indicated_title("Graph Basics").to_edge(UP, buff=0.8)
        self.play(Write(heading), run_time=1.5)

        bullets = [
            "• A graph G = (V, E) is a set of vertices V and edges E.",
            "• Edges connect pairs of vertices (possibly weighted).",
            "• Undirected graphs: edges have no direction.",
            "• Connected: every pair of vertices has a path between them.",
            "• A cut partitions V into two non-empty disjoint sets.",
            "• The size of a cut = number of edges crossing the partition.",
        ]
        bullet_group = VGroup(
            *[Text(b, font_size=28, color=TEXT_COLOR) for b in bullets]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        bullet_group.next_to(heading, DOWN, buff=0.7).align_to(heading, LEFT)

        for bullet in bullet_group:
            self.play(FadeIn(bullet, shift=RIGHT * 0.25), run_time=0.7)

        self.wait(1.5)
        self.play(FadeOut(VGroup(heading, bullet_group)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# C.  basics_graph_demo
# ═════════════════════════════════════════════════════════════════════════
class BasicsGraphDemo(Scene):
    def construct(self):
        heading = indicated_title("Anatomy of a Graph").to_edge(UP, buff=0.6)
        self.play(Write(heading), run_time=1.5)

        nodes = ["A", "B", "C", "D", "E", "F"]
        positions = circle_positions(nodes, radius=2.2)
        edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "E"),
            ("E", "F"),
            ("F", "A"),
            ("A", "C"),
            ("B", "E"),
        ]
        graph, node_dict, edge_dict = create_graph_with_labels(
            nodes, edges, positions, radius=0.25, scale=1.3
        )
        graph.shift(DOWN * 0.3)

        self.play(Create(graph), run_time=3)
        self.wait(0.8)

        # Arrows pointing to a vertex and an edge
        vertex_target = node_dict["A"]
        edge_target = edge_dict[("A", "B")]

        vertex_arrow = Arrow(
            start=vertex_target.get_center() + UP * 1.6 + LEFT * 1.6,
            end=vertex_target.get_center() + UP * 0.3 + LEFT * 0.2,
            color=ACTIVE_COLOR,
            buff=0.05,
            stroke_width=4,
        )
        vertex_label = Text("Vertex", font_size=24, color=ACTIVE_COLOR).next_to(
            vertex_arrow.get_start(), UP, buff=0.1
        )

        edge_mid = edge_target.get_center()
        edge_arrow = Arrow(
            start=edge_mid + DOWN * 1.4 + LEFT * 1.8,
            end=edge_mid + DOWN * 0.15 + LEFT * 0.15,
            color=HIGHLIGHT_EDGE,
            buff=0.05,
            stroke_width=4,
        )
        edge_label = Text("Edge", font_size=24, color=HIGHLIGHT_EDGE).next_to(
            edge_arrow.get_start(), DOWN, buff=0.1
        )

        self.play(Create(vertex_arrow), FadeIn(vertex_label), run_time=0.7)
        self.wait(1.2)
        self.play(Create(edge_arrow), FadeIn(edge_label), run_time=0.7)
        self.wait(1.5)

        self.play(
            FadeOut(VGroup(vertex_arrow, vertex_label, edge_arrow, edge_label)),
            run_time=0.7,
        )

        # Highlight degree of node A (neighbours: B, C, F ⇒ degree 3)
        degree_text = Text(
            "Degree of A = 3", font_size=30, color=ACTIVE_COLOR, weight="BOLD"
        ).to_edge(DOWN, buff=0.8)
        self.play(Write(degree_text), run_time=1.0)

        incident = [("A", "B"), ("A", "C"), ("A", "F")]
        anims = []
        for u, v in incident:
            key = tuple(sorted((u, v)))
            anims.append(edge_dict[key].animate.set_color(ACTIVE_COLOR).set_stroke(width=6))
        self.play(*anims, run_time=0.5)
        self.play(Indicate(node_dict["A"], color=ACTIVE_COLOR), run_time=0.8)
        self.wait(1.5)

        self.play(FadeOut(VGroup(heading, graph, degree_text)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# D.  problem_statement
# ═════════════════════════════════════════════════════════════════════════
class ProblemStatement(Scene):
    def construct(self):
        heading = indicated_title("Global vs. s-t Min-Cut").to_edge(UP, buff=0.6)
        self.play(Write(heading), run_time=1.5)

        desc_lines = [
            "• s-t min-cut: smallest set of edges separating source s from sink t.",
            "• Global min-cut: smallest cut over ALL possible (s, t) pairs.",
        ]
        descriptions = VGroup(
            *[Text(line, font_size=26, color=TEXT_COLOR) for line in desc_lines]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        descriptions.next_to(heading, DOWN, buff=0.5)
        for line in descriptions:
            self.play(FadeIn(line, shift=RIGHT * 0.25), run_time=0.7)
        self.wait(0.8)

        # Left: s-t cut. 4 nodes.
        left_positions = {
            "s": LEFT * 1.0 + UP * 0.6,
            "P": LEFT * 1.0 + DOWN * 0.6,
            "Q": RIGHT * 1.0 + UP * 0.6,
            "t": RIGHT * 1.0 + DOWN * 0.6,
        }
        left_edges = [("s", "P"), ("s", "Q"), ("P", "t"), ("Q", "t"), ("P", "Q")]
        left_graph, left_nodes, left_edge_dict = create_graph_with_labels(
            ["s", "P", "Q", "t"], left_edges, left_positions, radius=0.3, scale=1.0
        )
        left_graph.move_to(LEFT * 3.5 + DOWN * 1.2)

        # Highlight s and t
        left_nodes["s"].circle.set_stroke(color=SUCCESS_COLOR)
        left_nodes["s"].circle.set_fill(SUCCESS_COLOR, opacity=0.3)
        left_nodes["t"].circle.set_stroke(color=ALERT_COLOR)
        left_nodes["t"].circle.set_fill(ALERT_COLOR, opacity=0.3)

        # Cut edges on the left: {(s,Q), (P,t)} (example s-t cut of size 2)
        for cut_key in [tuple(sorted(("s", "Q"))), tuple(sorted(("P", "t")))]:
            left_edge_dict[cut_key].set_color(HIGHLIGHT_EDGE).set_stroke(width=5)

        left_caption = Text("s-t cut", font_size=26, color=TEXT_COLOR, weight="BOLD")
        left_caption.next_to(left_graph, DOWN, buff=0.3)

        # Right: global min-cut. 4 nodes.
        right_positions = {
            "1": LEFT * 1.0 + UP * 0.6,
            "2": LEFT * 1.0 + DOWN * 0.6,
            "3": RIGHT * 1.0 + UP * 0.6,
            "4": RIGHT * 1.0 + DOWN * 0.6,
        }
        right_edges = [("1", "2"), ("3", "4"), ("1", "3"), ("2", "4"), ("1", "4")]
        right_graph, right_nodes, right_edge_dict = create_graph_with_labels(
            ["1", "2", "3", "4"], right_edges, right_positions, radius=0.3, scale=1.0
        )
        right_graph.move_to(RIGHT * 3.5 + DOWN * 1.2)

        # Global min-cut on the right: remove one edge {(1,2)} for example
        for cut_key in [tuple(sorted(("1", "3"))), tuple(sorted(("2", "4")))]:
            right_edge_dict[cut_key].set_color(HIGHLIGHT_EDGE).set_stroke(width=5)

        right_caption = Text(
            "global min-cut", font_size=26, color=TEXT_COLOR, weight="BOLD"
        )
        right_caption.next_to(right_graph, DOWN, buff=0.3)

        self.play(
            Create(left_graph),
            Create(right_graph),
            run_time=3,
        )
        self.play(FadeIn(left_caption), FadeIn(right_caption), run_time=0.7)
        self.wait(3)
        self.play(
            FadeOut(
                VGroup(
                    heading,
                    descriptions,
                    left_graph,
                    right_graph,
                    left_caption,
                    right_caption,
                )
            ),
            run_time=0.7,
        )


# ═════════════════════════════════════════════════════════════════════════
# E.  kargers_pseudocode
# ═════════════════════════════════════════════════════════════════════════
class KargersPseudocode(Scene):
    def construct(self):
        heading = indicated_title("Karger's Algorithm").to_edge(UP, buff=0.6)
        self.play(Write(heading), run_time=1.5)

        lines = [
            "KARGER(G):",
            "  while |V| > 2:",
            "    pick random edge (u, v)",
            "    contract u and v",
            "    remove self-loops",
            "  return cut represented by final 2 nodes",
        ]
        box = create_styled_box(
            None,
            lines,
            width=8.5,
            mono=True,
            body_size=26,
        )
        box.move_to(LEFT * 2.5 + DOWN * 0.3)

        self.play(FadeIn(box[0]), run_time=1.0)
        inner = box[1]
        for line in inner:
            self.play(FadeIn(line, shift=RIGHT * 0.2), run_time=0.7)

        # Side notes
        notes = [
            "randomized — needs many runs",
            "contraction merges two vertices",
            "parallel edges are preserved",
            "loops vanish automatically",
            "O(V²) per iteration",
        ]
        note_mobs = VGroup(
            *[Text("• " + n, font_size=22, color=NODE_COLOR) for n in notes]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        note_mobs.to_edge(RIGHT, buff=0.8).shift(DOWN * 0.3)

        for note, code_line in zip(note_mobs, inner[1:]):
            self.play(
                code_line.animate.set_color(ACTIVE_COLOR),
                FadeIn(note, shift=LEFT * 0.2),
                run_time=0.7,
            )
            self.wait(0.6)
            self.play(code_line.animate.set_color(TEXT_COLOR), run_time=0.5)

        self.wait(2)
        self.play(FadeOut(VGroup(heading, box, note_mobs)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# F.  kargers_full_dry_run
# ═════════════════════════════════════════════════════════════════════════
class KargersFullDryRun(Scene):
    """Deterministic Karger dry-run on a 6-node graph that finds min-cut = 2."""

    def construct(self):
        heading = indicated_title("Karger — Full Dry Run", size=40).to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=1.5)

        # Initial positions — hex layout.
        nodes = ["A", "B", "C", "D", "E", "F"]
        positions = {
            "A": LEFT * 2.2 + UP * 1.4,
            "B": LEFT * 2.8,
            "C": LEFT * 2.2 + DOWN * 1.4,
            "D": RIGHT * 2.2 + DOWN * 1.4,
            "E": RIGHT * 2.8,
            "F": RIGHT * 2.2 + UP * 1.4,
        }
        base_edges = [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("D", "E"),
            ("E", "F"),
            ("F", "A"),
            ("A", "C"),
            ("B", "D"),
        ]

        node_mobs: dict[str, VGroup] = {
            n: make_node(n, positions[n], radius=0.35) for n in nodes
        }
        # multi-graph representation — list of edges as unordered pairs
        multi_edges: list[tuple[str, str]] = [tuple(sorted(e)) for e in base_edges]
        edge_mobs: list[tuple[tuple[str, str], Line]] = [
            (e, make_edge(node_mobs[e[0]], node_mobs[e[1]])) for e in multi_edges
        ]

        graph_group = VGroup(
            VGroup(*[m for _, m in edge_mobs]),
            VGroup(*node_mobs.values()),
        )

        self.play(Create(graph_group), run_time=4)
        self.wait(1.0)

        # UI: step counter (top-right), log box (bottom), edge count.
        total_steps = 4  # 6 → 2 nodes = 4 contractions
        step_counter = create_step_counter(0, total_steps).to_corner(
            RIGHT + UP, buff=0.5
        )
        self.play(FadeIn(step_counter), run_time=0.7)

        log_box = create_styled_box(
            "Contracting edge",
            ["— none —"],
            width=6.0,
            body_size=24,
            title_size=22,
        )
        log_box.to_edge(DOWN, buff=0.4)
        self.play(FadeIn(log_box), run_time=0.7)

        edge_count_label = Text(
            f"Edges: {len(multi_edges)}",
            font_size=24,
            color=NODE_COLOR,
            weight="BOLD",
        ).to_corner(LEFT + UP, buff=0.5)
        self.play(FadeIn(edge_count_label), run_time=0.5)

        # Deterministic contraction sequence that survives min-cut.
        # We avoid contracting the cut edges (A,C) and (B,D) between {A,B,C} and {D,E,F}.
        # Wait — our chosen cut must only cross two edges after contractions.
        # Actually the min-cut of THIS graph is 3 (not 2). Let's make it 2 by
        # removing (A,C) and (B,D) from base_edges — oh, but spec explicitly
        # lists these 8 edges. Recompute min-cut for these 8 edges:
        # {A,B,C} vs {D,E,F}: crossing edges (C,D) and (F,A) — that's 2. OK!
        # Internal to {A,B,C}: (A,B),(B,C),(A,C) — 3 edges (not crossing).
        # Internal to {D,E,F}: (D,E),(E,F),(B,D) — wait (B,D) crosses. So cut
        # edges are (C,D),(F,A),(B,D) = 3. Recompute:
        # Cross between {A,B,C} and {D,E,F}: (C,D), (F,A), (B,D) → 3 edges.
        # Try {A,B} vs rest: (B,C),(A,C),(A,F),(B,D) = 4. Try {A} vs rest:
        # (A,B),(A,C),(A,F) = 3.  {D} vs rest: (C,D),(D,E),(B,D) = 3.
        # {B} vs rest: (A,B),(B,C),(B,D) = 3. {C} vs rest: (B,C),(C,D),(A,C)=3.
        # {E} vs rest: (D,E),(E,F) = 2.  {F} vs rest: (E,F),(F,A) = 2.
        # So min-cut on this graph is 2 (isolating E or F). Contracting
        # everything except E gives a valid dry-run.

        # Contraction order: we want final two super-nodes to be "E" and the
        # rest. We contract all edges not incident on E first.
        # Steps chosen:
        #   1. contract (A,B)     → AB
        #   2. contract (AB,C)    → ABC
        #   3. contract (ABC,F)   → ABCF   (via (F,A))
        #   4. contract (ABCF,D)  → ABCFD  (via (C,D) or (B,D))
        # Remaining nodes: ABCFD and E. Edges between them: (D,E) and (E,F)
        # Final cut count = 2. Perfect.

        contractions: list[tuple[str, str, str, str]] = [
            # (edge u, edge v, merged label, human-readable edge desc)
            ("A", "B", "AB", "(A,B)"),
            ("AB", "C", "ABC", "(AB,C)"),
            ("ABC", "F", "ABCF", "(ABC,F)"),
            ("ABCF", "D", "ABCFD", "(ABCF,D)"),
        ]

        # We keep a mutable set of current super-nodes that map labels to
        # positions and circles.
        current_nodes: dict[str, VGroup] = dict(node_mobs)

        def find_edge_mob(u: str, v: str):
            for edge_key, line in edge_mobs:
                if tuple(sorted(edge_key)) == tuple(sorted((u, v))):
                    return edge_key, line
            return None, None

        for step, (u, v, merged_label, edge_desc) in enumerate(contractions, start=1):
            # Update step counter.
            new_counter = create_step_counter(step, total_steps).to_corner(
                RIGHT + UP, buff=0.5
            )
            self.play(Transform(step_counter, new_counter), run_time=0.5)

            # Highlight chosen edge.
            _, chosen_line = find_edge_mob(u, v)
            if chosen_line is None:
                continue
            self.play(
                chosen_line.animate.set_color(ACTIVE_COLOR).set_stroke(width=7),
                run_time=0.5,
            )

            # Update log box — rebuild with new contents.
            new_log = create_styled_box(
                "Contracting edge",
                [f"{edge_desc}  →  {merged_label}"],
                width=6.0,
                body_size=24,
                title_size=22,
            ).to_edge(DOWN, buff=0.4)
            self.play(Transform(log_box, new_log), run_time=0.7)

            # Animate node v moving to node u's position, fade out v's label,
            # then relabel u as merged_label.
            u_node = current_nodes[u]
            v_node = current_nodes[v]
            u_pos = u_node.circle.get_center()
            self.play(
                v_node.animate.move_to(u_pos),
                run_time=1.5,
            )

            # Replace u's label and circle color with MERGE_COLOR + merged label.
            radius = u_node.circle.radius
            new_node = make_node(merged_label, u_pos, radius=radius, color=MERGE_COLOR)
            self.play(
                ReplacementTransform(VGroup(u_node, v_node), new_node),
                run_time=0.7,
            )
            current_nodes[merged_label] = new_node
            # Remove old labels
            current_nodes.pop(u, None)
            current_nodes.pop(v, None)

            # Rewire edges: every edge incident to u or v becomes incident to merged_label.
            # Remove self-loops and update endpoints in multi_edges list.
            new_multi: list[tuple[str, str]] = []
            loop_lines: list[Line] = []
            keep_lines: list[tuple[tuple[str, str], Line]] = []
            for (ea, eb), line in edge_mobs:
                ea2 = merged_label if ea in (u, v) else ea
                eb2 = merged_label if eb in (u, v) else eb
                if ea2 == eb2:
                    loop_lines.append(line)
                    continue
                new_multi.append((ea2, eb2))
                keep_lines.append(((ea2, eb2), line))

            # Animate loop removal with a flash.
            if loop_lines:
                self.play(
                    *[Flash(line, color=ALERT_COLOR, flash_radius=0.3) for line in loop_lines],
                    *[FadeOut(line) for line in loop_lines],
                    run_time=0.7,
                )

            # Redraw remaining edges from current node positions.
            new_edge_mobs: list[tuple[tuple[str, str], Line]] = []
            rewire_anims = []
            for (ea, eb), line in keep_lines:
                target = Line(
                    current_nodes[ea].circle.get_center(),
                    current_nodes[eb].circle.get_center(),
                    color=EDGE_COLOR,
                    stroke_width=3,
                )
                rewire_anims.append(line.animate.become(target))
                new_edge_mobs.append(((ea, eb), line))
            if rewire_anims:
                self.play(*rewire_anims, run_time=0.7)

            edge_mobs = new_edge_mobs
            multi_edges = new_multi

            # Update edge count label.
            new_count_label = Text(
                f"Edges: {len(multi_edges)}",
                font_size=24,
                color=NODE_COLOR,
                weight="BOLD",
            ).to_corner(LEFT + UP, buff=0.5)
            self.play(Transform(edge_count_label, new_count_label), run_time=0.4)

            self.wait(1.5)

        # Final cut display.
        remaining = list(current_nodes.keys())
        # Count crossing edges.
        cross = [
            line
            for (ea, eb), line in edge_mobs
            if {ea, eb} == set(remaining)
        ]
        cut_size = len(cross)
        min_cut_size = 2
        color = SUCCESS_COLOR if cut_size == min_cut_size else ALERT_COLOR
        result = Text(
            f"Cut found: {cut_size} edges",
            font_size=36,
            color=color,
            weight="BOLD",
        )
        result_box = SurroundingRectangle(result, color=color, corner_radius=0.15, buff=0.25)
        result_group = VGroup(result, result_box).move_to(ORIGIN + UP * 0.3)

        self.play(*[line.animate.set_color(HIGHLIGHT_EDGE).set_stroke(width=6) for line in cross], run_time=0.5)
        self.play(Write(result), Create(result_box), run_time=1.5)
        self.play(Flash(result, color=color, flash_radius=1.2), run_time=1.0)
        self.wait(2)
        self.play(
            FadeOut(
                VGroup(
                    heading,
                    graph_group,
                    step_counter,
                    log_box,
                    edge_count_label,
                    result_group,
                    *[line for _, line in edge_mobs],
                    *list(current_nodes.values()),
                )
            ),
            run_time=0.7,
        )


# ═════════════════════════════════════════════════════════════════════════
# G.  dry_run_best_case  (dumbbell graph)
# ═════════════════════════════════════════════════════════════════════════
class DryRunBestCase(Scene):
    def construct(self):
        heading = indicated_title("Best Case — Dumbbell Graph").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        # Two 4-cliques connected by one bridge.
        left_center = LEFT * 3
        right_center = RIGHT * 3
        # Place 4 nodes of each clique in small squares.
        left_offsets = {
            "L1": UP * 0.7 + LEFT * 0.7,
            "L2": UP * 0.7 + RIGHT * 0.7,
            "L3": DOWN * 0.7 + LEFT * 0.7,
            "L4": DOWN * 0.7 + RIGHT * 0.7,
        }
        right_offsets = {
            "R1": UP * 0.7 + LEFT * 0.7,
            "R2": UP * 0.7 + RIGHT * 0.7,
            "R3": DOWN * 0.7 + LEFT * 0.7,
            "R4": DOWN * 0.7 + RIGHT * 0.7,
        }
        positions = {n: left_center + o for n, o in left_offsets.items()}
        positions.update({n: right_center + o for n, o in right_offsets.items()})

        # Clique edges (K4) and bridge.
        left_clique = [
            (a, b)
            for i, a in enumerate(left_offsets)
            for b in list(left_offsets)[i + 1 :]
        ]
        right_clique = [
            (a, b)
            for i, a in enumerate(right_offsets)
            for b in list(right_offsets)[i + 1 :]
        ]
        bridge = [("L2", "R1")]
        edges = left_clique + right_clique + bridge

        nodes = list(positions.keys())
        graph, node_dict, edge_dict = create_graph_with_labels(
            nodes, edges, positions, radius=0.2, scale=1.0
        )
        graph.shift(DOWN * 0.3)

        self.play(Create(graph), run_time=4)
        self.wait(0.5)

        # Dim internal edges, highlight the bridge in GOLD.
        bridge_key = tuple(sorted(("L2", "R1")))
        anims = []
        for key, line in edge_dict.items():
            if key == bridge_key:
                anims.append(line.animate.set_color(GOLD).set_stroke(width=5))
            else:
                anims.append(line.animate.set_color(EDGE_COLOR).set_stroke(width=2))
        self.play(*anims, run_time=0.5)

        total_edges = len(edges)
        prob_lines = [
            f"Total edges m = {total_edges}",
            "P(picking bridge) = 1 / m",
            f"            = 1 / {total_edges}",
            "bridge survives ⇒ algorithm succeeds",
        ]
        info = create_styled_box(
            "Probability",
            prob_lines,
            width=5.0,
            body_size=22,
            title_size=24,
        )
        info.to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)
        self.play(FadeIn(info), run_time=0.7)
        self.wait(2)

        # Simulate two quick contractions that stay inside left clique.
        for pair in [("L1", "L2"), ("L3", "L4")]:
            key = tuple(sorted(pair))
            if key not in edge_dict:
                continue
            self.play(
                edge_dict[key].animate.set_color(ACTIVE_COLOR).set_stroke(width=5),
                run_time=0.5,
            )
            u_node = node_dict[pair[0]]
            v_node = node_dict[pair[1]]
            target_pos = u_node.circle.get_center()
            self.play(v_node.animate.move_to(target_pos), run_time=1.5)
            self.play(FadeOut(v_node), FadeOut(edge_dict[key]), run_time=0.7)

        note = Text(
            "Bridge still there — we'd find min-cut!",
            font_size=26,
            color=SUCCESS_COLOR,
            weight="BOLD",
        ).to_edge(DOWN, buff=0.5)
        self.play(Write(note), run_time=1.0)
        self.wait(2)
        self.play(FadeOut(VGroup(heading, graph, info, note)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# H.  dry_run_worst_case  (cycle graph)
# ═════════════════════════════════════════════════════════════════════════
class DryRunWorstCase(Scene):
    def construct(self):
        heading = indicated_title("Worst Case — Cycle C8").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        nodes = [f"v{i}" for i in range(1, 9)]
        positions = circle_positions(nodes, radius=2.2)
        edges = [(nodes[i], nodes[(i + 1) % 8]) for i in range(8)]

        graph, node_dict, edge_dict = create_graph_with_labels(
            nodes, edges, positions, radius=0.25, scale=1.3
        )
        graph.shift(LEFT * 2 + DOWN * 0.3)
        self.play(Create(graph), run_time=4)

        # Highlight a representative min-cut = any two edges
        min_cut_edges = [tuple(sorted(("v1", "v2"))), tuple(sorted(("v5", "v6")))]
        self.play(
            *[
                edge_dict[k].animate.set_color(HIGHLIGHT_EDGE).set_stroke(width=6)
                for k in min_cut_edges
            ],
            run_time=0.5,
        )

        info_lines = [
            "every edge belongs to some min-cut",
            "min-cut size = 2",
            "P(success at step) = 2/n",
            "P(overall) ≥ 2/(n(n-1))",
            "         = 2/(8·7) = 1/28",
        ]
        info = create_styled_box(
            "Karger on Cn",
            info_lines,
            width=5.0,
            body_size=22,
            title_size=24,
        )
        info.to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)
        self.play(FadeIn(info), run_time=0.7)
        self.wait(2)

        formula = MathTex(
            r"P(\text{Karger finds min-cut}) \ge \frac{2}{n(n-1)}",
            color=ACTIVE_COLOR,
        )
        formula.scale(0.9).to_edge(DOWN, buff=0.6)
        self.play(Write(formula), run_time=1.5)
        self.wait(2.5)
        self.play(FadeOut(VGroup(heading, graph, info, formula)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# I.  dry_run_medium_case  (random graph, seed=42)
# ═════════════════════════════════════════════════════════════════════════
class DryRunMediumCase(Scene):
    def construct(self):
        heading = indicated_title("Medium Case — Random Graph").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        rnd = random.Random(42)
        nodes = [f"n{i}" for i in range(10)]
        positions = circle_positions(nodes, radius=2.2)
        edges = [
            (a, b)
            for i, a in enumerate(nodes)
            for b in nodes[i + 1 :]
            if rnd.random() < 0.3
        ]
        # Ensure graph is connected enough — add fallback edges if too sparse.
        if len(edges) < 10:
            edges += [(nodes[i], nodes[(i + 1) % 10]) for i in range(10)]

        graph, node_dict, edge_dict = create_graph_with_labels(
            nodes, edges, positions, radius=0.2, scale=1.2
        )
        graph.shift(LEFT * 2 + DOWN * 0.3)
        self.play(Create(graph), run_time=4)
        self.wait(0.5)

        # Run 3 quick contractions picking edges deterministically.
        picks = edges[:3]
        info_box = create_styled_box(
            "Status",
            ["Running 3 random contractions…"],
            width=5.0,
            body_size=22,
            title_size=24,
        )
        info_box.to_edge(RIGHT, buff=0.5).shift(DOWN * 0.3)
        self.play(FadeIn(info_box), run_time=0.7)

        for idx, (u, v) in enumerate(picks, start=1):
            key = tuple(sorted((u, v)))
            if key not in edge_dict:
                continue
            self.play(
                edge_dict[key].animate.set_color(ACTIVE_COLOR).set_stroke(width=5),
                run_time=0.5,
            )
            self.play(
                node_dict[v].animate.move_to(node_dict[u].circle.get_center()),
                run_time=1.5,
            )
            self.play(FadeOut(node_dict[v]), FadeOut(edge_dict[key]), run_time=0.7)

        conclusion = Text(
            "Success depends on graph structure",
            font_size=28,
            color=ACTIVE_COLOR,
            weight="BOLD",
        ).to_edge(DOWN, buff=0.6)
        self.play(Write(conclusion), run_time=1.5)
        self.wait(2)
        self.play(FadeOut(VGroup(heading, graph, info_box, conclusion)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# J.  karger_stein_pseudocode
# ═════════════════════════════════════════════════════════════════════════
class KargerSteinPseudocode(Scene):
    def construct(self):
        heading = indicated_title("Karger–Stein").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        lines = [
            "KARGER-STEIN(G):",
            "  if |V| ≤ 6:",
            "    return BRUTE_FORCE(G)",
            "  t = ceil(|V|/√2 + 1)",
            "  G1 = CONTRACT(G, t)",
            "  G2 = CONTRACT(G, t)",
            "  return min(",
            "      KARGER-STEIN(G1),",
            "      KARGER-STEIN(G2)",
            "  )",
        ]
        box = create_styled_box(None, lines, width=8.5, mono=True, body_size=24)
        box.move_to(LEFT * 2.5 + DOWN * 0.3)
        self.play(FadeIn(box[0]), run_time=0.8)
        for line in box[1]:
            self.play(FadeIn(line, shift=RIGHT * 0.25), run_time=0.7)
        self.wait(0.5)

        insight = create_styled_box(
            "Key insight",
            [
                "Contract to n/√2 vertices.",
                "Branch: two independent runs.",
                "Recurse in each branch.",
                "Dramatically better success",
                "probability than plain Karger.",
            ],
            width=4.8,
            body_size=22,
            title_size=24,
        )
        insight.to_edge(RIGHT, buff=0.5)
        self.play(FadeIn(insight), run_time=1.0)
        self.wait(3)
        self.play(FadeOut(VGroup(heading, box, insight)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# K.  karger_stein_recursion_tree
# ═════════════════════════════════════════════════════════════════════════
class KargerSteinRecursionTree(Scene):
    def construct(self):
        heading = indicated_title("Recursion Tree").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        def make_tree_node(label: str, pos, color=NODE_COLOR, radius=0.45) -> VGroup:
            circle = Circle(
                radius=radius,
                color=color,
                stroke_width=3,
                fill_color=color,
                fill_opacity=0.2,
            ).move_to(pos)
            txt = MathTex(label, color=TEXT_COLOR).scale(0.8)
            txt.move_to(circle.get_center())
            return VGroup(circle, txt)

        root = make_tree_node("n", UP * 2.2)
        level1 = [
            make_tree_node(r"n/\sqrt{2}", UP * 0.4 + LEFT * 2.5, color=NODE_COLOR),
            make_tree_node(r"n/\sqrt{2}", UP * 0.4 + RIGHT * 2.5, color=NODE_COLOR),
        ]
        level2 = [
            make_tree_node("n/2", DOWN * 1.3 + LEFT * 4.0, color=MERGE_COLOR, radius=0.4),
            make_tree_node("n/2", DOWN * 1.3 + LEFT * 1.3, color=MERGE_COLOR, radius=0.4),
            make_tree_node("n/2", DOWN * 1.3 + RIGHT * 1.3, color=MERGE_COLOR, radius=0.4),
            make_tree_node("n/2", DOWN * 1.3 + RIGHT * 4.0, color=MERGE_COLOR, radius=0.4),
        ]
        leaves = [
            make_tree_node(r"\le 6", DOWN * 2.8 + LEFT * 4.0, color=SUCCESS_COLOR, radius=0.35),
            make_tree_node(r"\le 6", DOWN * 2.8 + LEFT * 1.3, color=SUCCESS_COLOR, radius=0.35),
            make_tree_node(r"\le 6", DOWN * 2.8 + RIGHT * 1.3, color=SUCCESS_COLOR, radius=0.35),
            make_tree_node(r"\le 6", DOWN * 2.8 + RIGHT * 4.0, color=SUCCESS_COLOR, radius=0.35),
        ]

        self.play(FadeIn(root), run_time=1.0)
        edges_l1 = [
            Line(root[0].get_bottom(), child[0].get_top(), color=EDGE_COLOR)
            for child in level1
        ]
        self.play(*[Create(e) for e in edges_l1], *[FadeIn(c) for c in level1], run_time=1.5)

        edges_l2 = []
        for i, parent in enumerate(level1):
            for j in range(2):
                child = level2[i * 2 + j]
                edges_l2.append(Line(parent[0].get_bottom(), child[0].get_top(), color=EDGE_COLOR))
        self.play(*[Create(e) for e in edges_l2], *[FadeIn(c) for c in level2], run_time=1.5)

        edges_l3 = [
            Line(level2[i][0].get_bottom(), leaves[i][0].get_top(), color=EDGE_COLOR)
            for i in range(4)
        ]
        self.play(*[Create(e) for e in edges_l3], *[FadeIn(c) for c in leaves], run_time=1.5)

        leaf_note = Text(
            "leaves: brute force", font_size=22, color=SUCCESS_COLOR
        ).next_to(leaves[-1], RIGHT, buff=0.4)
        self.play(FadeIn(leaf_note), run_time=0.7)

        complexity = MathTex(
            r"\text{Total time: } \; O(n^2 \log^3 n)",
            color=ACTIVE_COLOR,
        ).scale(0.9).to_edge(DOWN, buff=0.5)
        self.play(Write(complexity), run_time=1.5)
        self.wait(3)
        self.play(
            FadeOut(
                VGroup(
                    heading,
                    root,
                    *level1,
                    *level2,
                    *leaves,
                    *edges_l1,
                    *edges_l2,
                    *edges_l3,
                    leaf_note,
                    complexity,
                )
            ),
            run_time=0.7,
        )


# ═════════════════════════════════════════════════════════════════════════
# L.  stoer_wagner_pseudocode
# ═════════════════════════════════════════════════════════════════════════
class StoerWagnerPseudocode(Scene):
    def construct(self):
        heading = indicated_title("Stoer–Wagner").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        lines = [
            "STOER-WAGNER(G):",
            "  min_cut = ∞",
            "  while |V| > 1:",
            "    (cut, s, t) = MIN-CUT-PHASE(G)",
            "    min_cut = min(min_cut, cut)",
            "    merge s and t",
            "  return min_cut",
        ]
        box = create_styled_box(None, lines, width=8.5, mono=True, body_size=26)
        box.move_to(LEFT * 2.5)
        self.play(FadeIn(box[0]), run_time=0.8)
        for line in box[1]:
            self.play(FadeIn(line, shift=RIGHT * 0.2), run_time=0.7)

        side = create_styled_box(
            "Properties",
            [
                "Deterministic",
                "Weighted graphs",
                "O(V·E + V² log V)",
                "No randomization!",
            ],
            width=4.5,
            body_size=22,
            title_size=24,
        )
        side.to_edge(RIGHT, buff=0.5)
        self.play(FadeIn(side), run_time=0.8)
        self.wait(3)
        self.play(FadeOut(VGroup(heading, box, side)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# M.  stoer_wagner_full_dry_run
# ═════════════════════════════════════════════════════════════════════════
class StoerWagnerFullDryRun(Scene):
    def construct(self):
        heading = indicated_title("Stoer–Wagner Dry Run", size=40).to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=1.5)

        # 5 nodes.
        nodes = ["1", "2", "3", "4", "5"]
        positions = {
            "1": LEFT * 3.0 + UP * 1.4,
            "2": LEFT * 1.2 + UP * 1.8,
            "3": LEFT * 0.0 + DOWN * 0.6,
            "4": LEFT * 1.2 + DOWN * 1.8,
            "5": LEFT * 3.0 + DOWN * 1.4,
        }
        edges_w = {
            ("1", "2"): 2,
            ("1", "3"): 3,
            ("2", "3"): 2,
            ("2", "4"): 3,
            ("3", "4"): 2,
            ("3", "5"): 2,
            ("4", "5"): 4,
        }
        edges = [tuple(sorted(e)) for e in edges_w]

        graph, node_dict, edge_dict = create_graph_with_labels(
            nodes, edges, positions, radius=0.3, scale=1.0
        )
        self.play(Create(graph), run_time=4)

        # Add weight labels to every edge.
        weight_labels: dict[tuple[str, str], Text] = {}
        for (u, v), w in edges_w.items():
            key = tuple(sorted((u, v)))
            mid = edge_dict[key].get_center()
            label = Text(str(w), font_size=20, color=ACTIVE_COLOR, weight="BOLD")
            label.move_to(mid + UP * 0.2 + RIGHT * 0.15)
            weight_labels[key] = label
            self.add(label)

        # Priority table on the right.
        table_title = Text("Weight Table", font_size=22, color=ACTIVE_COLOR, weight="BOLD")
        rows = VGroup(*[
            Text(f"{n}: 0", font_size=22, color=TEXT_COLOR) for n in nodes
        ]).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
        rows.next_to(table_title, DOWN, buff=0.3, aligned_edge=LEFT)
        table_box = SurroundingRectangle(
            VGroup(table_title, rows),
            corner_radius=0.15,
            color=EDGE_COLOR,
            buff=0.3,
        ).set_fill(PSEUDO_BG, opacity=1.0)
        table_box.set_z_index(-1)
        table_group = VGroup(table_box, table_title, rows).to_edge(RIGHT, buff=0.4)
        table_title.align_to(rows, LEFT)

        self.play(FadeIn(table_group), run_time=0.8)
        self.wait(0.5)

        # Run one phase starting from node "1".
        # Maximum adjacency ordering using edge weights.
        visited: list[str] = ["1"]
        weights: dict[str, int] = {n: 0 for n in nodes}
        weights["1"] = 0
        self.play(Indicate(node_dict["1"], color=ACTIVE_COLOR), run_time=0.7)

        def update_table():
            new_rows = VGroup(*[
                Text(
                    f"{n}: {weights[n]}"
                    + (" ✓" if n in visited else ""),
                    font_size=22,
                    color=SUCCESS_COLOR if n in visited else TEXT_COLOR,
                )
                for n in nodes
            ]).arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            new_rows.move_to(rows.get_center()).align_to(rows, LEFT)
            return new_rows

        # After visiting 1, update its neighbours' weights.
        def neighbours(u: str) -> list[tuple[str, int]]:
            result = []
            for (a, b), w in edges_w.items():
                if a == u:
                    result.append((b, w))
                elif b == u:
                    result.append((a, w))
            return result

        for nbr, w in neighbours("1"):
            weights[nbr] += w
        new_rows = update_table()
        self.play(Transform(rows, new_rows), run_time=0.7)
        self.wait(0.5)

        # Iteratively pick the most tightly connected unvisited node.
        phase_order = ["1"]
        while len(phase_order) < len(nodes):
            candidates = [(n, weights[n]) for n in nodes if n not in visited]
            candidates.sort(key=lambda x: -x[1])
            chosen, _ = candidates[0]
            visited.append(chosen)
            phase_order.append(chosen)

            self.play(
                node_dict[chosen].animate.set_color(ACTIVE_COLOR),
                run_time=0.5,
            )
            self.play(Indicate(node_dict[chosen], color=ACTIVE_COLOR), run_time=0.7)

            for nbr, w in neighbours(chosen):
                if nbr not in visited:
                    weights[nbr] += w
            new_rows = update_table()
            self.play(Transform(rows, new_rows), run_time=0.5)

        # cut-of-the-phase = weight of the last added vertex.
        last = phase_order[-1]
        second_last = phase_order[-2]
        cut_of_phase = weights[last]

        phase_text = Text(
            f"cut-of-phase = {cut_of_phase}   (isolating {last})",
            font_size=26,
            color=SUCCESS_COLOR,
            weight="BOLD",
        ).to_edge(DOWN, buff=1.4)
        self.play(Write(phase_text), run_time=1.5)
        self.wait(1.5)

        merge_text = Text(
            f"Merge {second_last} and {last}",
            font_size=24,
            color=MERGE_COLOR,
            weight="BOLD",
        ).next_to(phase_text, DOWN, buff=0.2)
        self.play(Write(merge_text), run_time=1.0)

        # Animate merge of last two.
        target_pos = node_dict[second_last].circle.get_center()
        self.play(node_dict[last].animate.move_to(target_pos), run_time=1.5)
        merged = make_node(
            f"{second_last}{last}", target_pos, radius=0.3, color=MERGE_COLOR
        )
        self.play(
            ReplacementTransform(
                VGroup(node_dict[second_last], node_dict[last]), merged
            ),
            run_time=0.7,
        )

        phase_done = Text(
            f"Phase 1 complete — cut = {cut_of_phase}",
            font_size=28,
            color=ACTIVE_COLOR,
            weight="BOLD",
        ).to_edge(DOWN, buff=0.5)
        self.play(Transform(phase_text, phase_done), FadeOut(merge_text), run_time=1.0)
        self.wait(1.5)

        # Phase 2 (abbreviated)
        abbr = Text(
            "Phase 2 (abbreviated): repeat on merged graph",
            font_size=24,
            color=TEXT_COLOR,
        ).to_edge(DOWN, buff=0.5)
        self.play(Transform(phase_text, abbr), run_time=1.0)
        self.wait(2)

        self.play(
            FadeOut(
                VGroup(
                    heading,
                    graph,
                    table_group,
                    phase_text,
                    merged,
                    *weight_labels.values(),
                )
            ),
            run_time=0.7,
        )


# ═════════════════════════════════════════════════════════════════════════
# N.  max_flow_theory
# ═════════════════════════════════════════════════════════════════════════
class MaxFlowTheory(Scene):
    def construct(self):
        heading = indicated_title("Max-Flow / Min-Cut Duality").to_edge(UP, buff=0.5)
        self.play(Write(heading), run_time=1.5)

        bullets = [
            "• A flow network has a source s and a sink t.",
            "• Each edge (u,v) has capacity c(u,v) ≥ 0.",
            "• A flow f respects capacities and conservation.",
            "• Max-flow = largest total flow out of s (= into t).",
            "• Ford–Fulkerson: repeatedly find augmenting paths.",
            "• Theorem:  max flow  =  min s-t cut capacity.",
        ]
        mobs = VGroup(
            *[Text(b, font_size=28, color=TEXT_COLOR) for b in bullets]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        mobs.next_to(heading, DOWN, buff=0.6)

        for line in mobs:
            self.play(FadeIn(line, shift=RIGHT * 0.25), run_time=0.7)

        formula = MathTex(
            r"\max_{f}\ |f| \;=\; \min_{(S,T)} c(S,T)",
            color=ACTIVE_COLOR,
        ).scale(1.1).to_edge(DOWN, buff=0.6)
        box = SurroundingRectangle(
            formula, color=ACTIVE_COLOR, corner_radius=0.15, buff=0.3
        )
        self.play(Write(formula), Create(box), run_time=1.5)
        self.wait(2.5)
        self.play(FadeOut(VGroup(heading, mobs, formula, box)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# O.  max_flow_dry_run
# ═════════════════════════════════════════════════════════════════════════
class MaxFlowDryRun(Scene):
    def construct(self):
        heading = indicated_title("Max-Flow Dry Run", size=40).to_edge(UP, buff=0.4)
        self.play(Write(heading), run_time=1.5)

        # 6 nodes: S, A, B, C, D, T
        positions = {
            "S": LEFT * 4.5,
            "A": LEFT * 1.5 + UP * 1.5,
            "B": RIGHT * 1.5 + UP * 1.5,
            "C": LEFT * 1.5 + DOWN * 1.5,
            "D": RIGHT * 1.5 + DOWN * 1.5,
            "T": RIGHT * 4.5,
        }
        # Edges with capacities.
        caps = {
            ("S", "A"): 10,
            ("S", "C"): 8,
            ("A", "B"): 5,
            ("A", "C"): 2,
            ("C", "D"): 9,
            ("B", "T"): 10,
            ("D", "T"): 7,
            ("B", "D"): 4,
        }

        node_mobs: dict[str, VGroup] = {
            n: make_node(n, positions[n], radius=0.3) for n in positions
        }
        # Directed arrows.
        arrow_mobs: dict[tuple[str, str], Arrow] = {}
        cap_labels: dict[tuple[str, str], Text] = {}
        for (u, v), c in caps.items():
            start = node_mobs[u].circle.get_center()
            end = node_mobs[v].circle.get_center()
            arrow = Arrow(
                start, end, color=EDGE_COLOR, buff=0.35, stroke_width=3, max_tip_length_to_length_ratio=0.08
            )
            arrow_mobs[(u, v)] = arrow
            mid = (start + end) / 2
            label = Text(f"{c}", font_size=20, color=ACTIVE_COLOR, weight="BOLD")
            perp = ((end - start) / max(1e-6, float(((end - start) ** 2).sum() ** 0.5))) * 0.3
            label.move_to(mid + UP * 0.3)
            cap_labels[(u, v)] = label

        self.play(
            *[FadeIn(n) for n in node_mobs.values()],
            *[Create(a) for a in arrow_mobs.values()],
            *[FadeIn(l) for l in cap_labels.values()],
            run_time=4,
        )

        # Highlight source (green) and sink (red).
        self.play(
            node_mobs["S"].circle.animate.set_stroke(color=SUCCESS_COLOR).set_fill(SUCCESS_COLOR, opacity=0.35),
            node_mobs["T"].circle.animate.set_stroke(color=ALERT_COLOR).set_fill(ALERT_COLOR, opacity=0.35),
            run_time=0.7,
        )

        flow_label = Text("Flow: 0", font_size=28, color=SUCCESS_COLOR, weight="BOLD")
        flow_label.to_corner(LEFT + DOWN, buff=0.6)
        self.play(FadeIn(flow_label), run_time=0.5)

        def augment(path: list[str], bottleneck: int, current_flow: int) -> int:
            keys = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            # Highlight path.
            self.play(
                *[arrow_mobs[k].animate.set_color(HIGHLIGHT_EDGE).set_stroke(width=6) for k in keys],
                run_time=0.7,
            )
            bottleneck_text = Text(
                f"Augmenting path: {' → '.join(path)}   bottleneck = {bottleneck}",
                font_size=22,
                color=ACTIVE_COLOR,
            ).to_edge(DOWN, buff=0.2)
            self.play(Write(bottleneck_text), run_time=0.7)
            self.wait(1.5)
            new_flow = current_flow + bottleneck
            new_flow_label = Text(
                f"Flow: {new_flow}", font_size=28, color=SUCCESS_COLOR, weight="BOLD"
            ).to_corner(LEFT + DOWN, buff=0.6)
            self.play(Transform(flow_label, new_flow_label), run_time=0.5)
            self.play(
                *[arrow_mobs[k].animate.set_color(SUCCESS_COLOR).set_stroke(width=4) for k in keys],
                FadeOut(bottleneck_text),
                run_time=0.7,
            )
            return new_flow

        cur = 0
        cur = augment(["S", "A", "B", "T"], 5, cur)  # bottleneck = min(10,5,10)=5
        cur = augment(["S", "C", "D", "T"], 7, cur)  # bottleneck = min(8,9,7)=7

        no_more = Text(
            "No more augmenting paths", font_size=28, color=ACTIVE_COLOR, weight="BOLD"
        ).to_edge(DOWN, buff=0.2)
        self.play(Write(no_more), run_time=1.0)
        self.wait(1.5)

        # Show min-cut: S-side {S, A} vs T-side {B, C, D, T}.
        s_side = {"S", "A"}
        for n, m in node_mobs.items():
            if n in s_side:
                self.play(
                    m.circle.animate.set_fill(SUCCESS_COLOR, opacity=0.4),
                    run_time=0.2,
                )
            elif n != "S":
                self.play(
                    m.circle.animate.set_fill(ALERT_COLOR, opacity=0.3),
                    run_time=0.15,
                )

        # Highlight cut edges = edges from s_side to t_side.
        cut_edges = [k for k in caps if k[0] in s_side and k[1] not in s_side]
        self.play(
            *[arrow_mobs[k].animate.set_color(HIGHLIGHT_EDGE).set_stroke(width=7) for k in cut_edges],
            run_time=0.7,
        )

        result = Text(
            f"Max Flow = Min Cut = {cur}",
            font_size=32,
            color=SUCCESS_COLOR,
            weight="BOLD",
        ).to_edge(DOWN, buff=0.2)
        rect = SurroundingRectangle(result, color=SUCCESS_COLOR, corner_radius=0.15, buff=0.2)
        self.play(Transform(no_more, result), Create(rect), run_time=1.0)
        self.play(Flash(result, color=SUCCESS_COLOR, flash_radius=1.0), run_time=1.0)
        self.wait(2.5)

        self.play(
            FadeOut(
                VGroup(
                    heading,
                    *node_mobs.values(),
                    *arrow_mobs.values(),
                    *cap_labels.values(),
                    flow_label,
                    no_more,
                    rect,
                )
            ),
            run_time=0.7,
        )


# ═════════════════════════════════════════════════════════════════════════
# P.  complexity_comparison
# ═════════════════════════════════════════════════════════════════════════
class ComplexityComparison(Scene):
    def construct(self):
        heading = indicated_title("Algorithm Comparison").to_edge(UP, buff=0.6)
        self.play(Write(heading), run_time=1.5)

        header = ["Algorithm", "Type", "Time", "P(success)"]
        rows = [
            ["Karger", "Rand.", "O(V²)", "≥ 2/(V(V-1))"],
            ["Karger–Stein", "Rand.", "O(V² log³ V)", "≥ 1/log V"],
            ["Stoer–Wagner", "Det.", "O(VE + V² log V)", "1"],
            ["Max-Flow", "Det.", "O(V·E²)", "1"],
        ]

        table = Table(
            rows,
            col_labels=[Text(h, color=ACTIVE_COLOR, weight="BOLD") for h in header],
            include_outer_lines=True,
            line_config={"stroke_color": EDGE_COLOR, "stroke_width": 2},
        ).scale(0.5)
        for entry in table.get_entries_without_labels():
            entry.set_color(TEXT_COLOR)
        table.move_to(ORIGIN + DOWN * 0.3)

        self.play(Create(table.get_horizontal_lines()), Create(table.get_vertical_lines()), run_time=1.5)
        # Write labels row.
        self.play(Write(VGroup(*table.get_col_labels())), run_time=1.2)

        # Reveal rows one by one.
        for r_idx in range(1, len(rows) + 1):
            row_cells = table.get_rows()[r_idx]
            self.play(FadeIn(row_cells, shift=DOWN * 0.1), run_time=0.7)

        # Highlight best in each column: lowest time → Stoer-Wagner/Max-Flow;
        # highest P(success) → deterministic; best trade-off → Karger-Stein.
        best_row = table.get_rows()[2]  # Karger-Stein
        rect = SurroundingRectangle(best_row, color=SUCCESS_COLOR, corner_radius=0.1, buff=0.05)
        self.play(Create(rect), run_time=0.8)
        callout = Text(
            "Best randomized trade-off",
            font_size=22,
            color=SUCCESS_COLOR,
            weight="BOLD",
        ).next_to(table, DOWN, buff=0.5)
        self.play(Write(callout), run_time=1.0)
        self.wait(2.5)
        self.play(FadeOut(VGroup(heading, table, rect, callout)), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# Q.  final_summary
# ═════════════════════════════════════════════════════════════════════════
class FinalSummary(Scene):
    def construct(self):
        heading = indicated_title("Key Takeaways", size=46).to_edge(UP, buff=0.6)
        self.play(Write(heading), run_time=1.5)

        takeaways = [
            "• Cuts partition a graph; min-cuts capture bottlenecks.",
            "• Karger is simple, randomized; success probability is tiny.",
            "• Karger–Stein improves success with recursive branching.",
            "• Stoer–Wagner is deterministic and works on weights.",
            "• Max-flow ↔ min-cut duality unlocks flow-based solutions.",
        ]
        bullets = VGroup(
            *[Text(t, font_size=26, color=TEXT_COLOR) for t in takeaways]
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
        bullets.next_to(heading, DOWN, buff=0.6)

        for line in bullets:
            self.play(FadeIn(line, shift=RIGHT * 0.25), run_time=0.7)
        self.wait(1.5)

        thanks = Text(
            "Thank You!", font_size=64, color=SUCCESS_COLOR, weight="BOLD"
        )
        authors = Text(
            "Presented by Graph Algorithms Group",
            font_size=26,
            color=TEXT_COLOR,
        ).next_to(thanks, DOWN, buff=0.4)
        course = Text(
            "CS 404 — Advanced Algorithms",
            font_size=22,
            color=NODE_COLOR,
        ).next_to(authors, DOWN, buff=0.3)

        final = VGroup(thanks, authors, course).move_to(ORIGIN + DOWN * 0.3)

        self.play(FadeOut(VGroup(heading, bullets)), run_time=0.7)
        self.play(Write(thanks), run_time=1.5)
        self.play(FadeIn(authors, shift=UP * 0.2), FadeIn(course, shift=UP * 0.2), run_time=1.0)
        self.play(Flash(thanks, color=SUCCESS_COLOR, flash_radius=1.8), run_time=1.2)
        self.wait(3)
        self.play(FadeOut(final), run_time=0.7)


# ═════════════════════════════════════════════════════════════════════════
# Master scene — plays everything back-to-back.
# ═════════════════════════════════════════════════════════════════════════
class FullLecture(Scene):
    def construct(self):
        for scene_cls in (
            IntroCredits,
            BasicsChapter,
            BasicsGraphDemo,
            ProblemStatement,
            KargersPseudocode,
            KargersFullDryRun,
            DryRunBestCase,
            DryRunWorstCase,
            DryRunMediumCase,
            KargerSteinPseudocode,
            KargerSteinRecursionTree,
            StoerWagnerPseudocode,
            StoerWagnerFullDryRun,
            MaxFlowTheory,
            MaxFlowDryRun,
            ComplexityComparison,
            FinalSummary,
        ):
            self.clear()
            scene_cls.construct(self)
