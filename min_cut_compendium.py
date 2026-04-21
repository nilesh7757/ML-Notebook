"""
Min-Cut Compendium v10
======================

A polished, extended Manim animation covering four classic Minimum-Cut
algorithms with step-by-step dry runs:

    1. Karger's Randomized Contraction
    2. Karger-Stein (Recursive)
    3. Stoer-Wagner (Deterministic, Max-Adjacency Search)
    4. Ford-Fulkerson Max-Flow / Min-Cut Duality

Render everything (high quality, slow):
    manim -pqh min_cut_compendium.py MinCutCompendium

Render a single chapter while iterating (medium quality):
    manim -pqm min_cut_compendium.py Chapter03_Karger
"""

from __future__ import annotations

import random

import networkx as nx
from manim import *

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CONFIG
# ─────────────────────────────────────────────────────────────────────────────
config.background_color = "#0D1117"

# Color palette (GitHub-dark inspired for aesthetic consistency)
BG = "#0D1117"
PANEL_BG = "#161B22"
NODE_COLOR = "#58A6FF"        # blue
NODE_FILL = "#1F6FEB"
EDGE_COLOR = "#30363D"        # dim
EDGE_LIGHT = "#484F58"
ACTIVE = "#F2CC60"            # gold
ALERT = "#FF7B72"             # crimson
SUCCESS = "#3FB950"           # green
TEXT = "#E6EDF3"              # near-white
MUTED = "#8B949E"
PURPLE = "#BC8CFF"
TEAL = "#39D0D8"
PINK = "#FF9BD2"

# Timing presets (multiplier on run_time).  The user asked for 0.5x / 0.7x-style
# pacing: we achieve the same by stretching or compressing run_time.
#   SLOW   → important "aha" moments (math, definitions, final reveals)
#   MEDIUM → regular teaching beat
#   NORMAL → default
#   FAST   → filler / repeated actions
#   BLINK  → near-instant state updates
SLOW = 1.8
MEDIUM = 1.3
NORMAL = 1.0
FAST = 0.6
BLINK = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fit_to_frame(mobj: Mobject, max_w: float = 11.5, max_h: float = 6.0) -> Mobject:
    """Scale *mobj* down so it fits within the given safe area.  Never scales up."""
    if mobj.width <= 0 or mobj.height <= 0:
        return mobj
    scale = min(max_w / mobj.width, max_h / mobj.height, 1.0)
    if scale < 1.0:
        mobj.scale(scale)
    return mobj


def node_radius_for(n: int) -> float:
    """Pick a sensible node radius based on vertex count."""
    if n <= 5:
        return 0.42
    if n <= 8:
        return 0.34
    if n <= 12:
        return 0.28
    if n <= 18:
        return 0.22
    return 0.18


def edge_width_for(n: int) -> float:
    if n <= 6:
        return 4.0
    if n <= 12:
        return 3.0
    return 2.0


def styled_graph(
    nodes,
    edges,
    layout="spring",
    labels: bool = True,
    seed: int | None = 7,
    highlight_edges=None,
    edge_colors: dict | None = None,
) -> Graph:
    """Build a Manim Graph with the house style."""
    r = node_radius_for(len(nodes))
    w = edge_width_for(len(nodes))

    vcfg = {
        "radius": r,
        "color": NODE_COLOR,
        "fill_color": NODE_FILL,
        "fill_opacity": 0.92,
        "stroke_color": NODE_COLOR,
        "stroke_width": 3,
    }
    if labels:
        label_font = max(14, int(22 * r / 0.32))
    ecfg_default = {
        "stroke_color": EDGE_COLOR,
        "stroke_width": w,
    }
    ecfg = {e: dict(ecfg_default) for e in edges}
    if highlight_edges:
        for e in highlight_edges:
            if e in ecfg:
                ecfg[e] = {"stroke_color": ACTIVE, "stroke_width": w + 2}
    if edge_colors:
        for e, c in edge_colors.items():
            if e in ecfg:
                ecfg[e]["stroke_color"] = c

    label_config = {"font_size": 26, "color": TEXT} if labels else None

    kwargs = dict(
        layout=layout,
        labels=labels,
        vertex_config=vcfg,
        edge_config=ecfg,
    )
    if isinstance(layout, str) and layout == "spring" and seed is not None:
        kwargs["layout_config"] = {"seed": seed}
    if label_config is not None:
        kwargs["label_fill_color"] = TEXT
    g = Graph(nodes, edges, **kwargs)
    return g


def panel(title: str, width: float = 4.2, height: float = 4.5) -> VGroup:
    """A stylized side-panel card (title + translucent body) for status info."""
    box = RoundedRectangle(
        corner_radius=0.18,
        width=width,
        height=height,
        stroke_color=ACTIVE,
        stroke_width=2,
        fill_color=PANEL_BG,
        fill_opacity=0.85,
    )
    title_txt = Text(title, color=ACTIVE, font_size=22, weight=BOLD)
    title_txt.move_to(box.get_top() + DOWN * 0.28)
    underline = Line(
        box.get_top() + DOWN * 0.55 + LEFT * (width / 2 - 0.3),
        box.get_top() + DOWN * 0.55 + RIGHT * (width / 2 - 0.3),
        stroke_color=ACTIVE,
        stroke_width=1,
    )
    return VGroup(box, title_txt, underline)


def chapter_card(scene: Scene, number: str, title: str, subtitle: str | None = None):
    """Animated chapter intro card."""
    ch_num = Text(number, color=ACTIVE, font_size=28, weight=BOLD)
    title_txt = Text(title, color=TEXT, font_size=52, weight=BOLD)
    rule = Line(LEFT * 3, RIGHT * 3, stroke_color=ACTIVE, stroke_width=3)
    group = VGroup(ch_num, rule, title_txt).arrange(DOWN, buff=0.4)
    if subtitle:
        sub = Text(subtitle, color=MUTED, font_size=28)
        group.add(sub)
        group.arrange(DOWN, buff=0.35)
    group.move_to(ORIGIN)

    scene.play(FadeIn(ch_num, shift=DOWN * 0.3), run_time=MEDIUM * 0.5)
    scene.play(GrowFromCenter(rule), run_time=MEDIUM * 0.5)
    scene.play(Write(title_txt), run_time=SLOW * 0.8)
    if subtitle:
        scene.play(FadeIn(sub, shift=UP * 0.2), run_time=MEDIUM * 0.7)
    scene.wait(1.2)
    scene.play(FadeOut(group, shift=UP * 0.2), run_time=MEDIUM * 0.6)


def bullet_list(
    scene: Scene,
    lines,
    title: str | None = None,
    per_line_pause: float = 1.1,
    tail_pause: float = 2.5,
    bullet_color: str = ACTIVE,
):
    """Sequentially reveal a titled bullet list with breathing room."""
    if title:
        heading = Text(title, color=ACTIVE, font_size=40, weight=BOLD).to_edge(UP, buff=0.8)
        underline = Line(
            heading.get_left() + DOWN * 0.25,
            heading.get_right() + DOWN * 0.25,
            stroke_color=ACTIVE,
            stroke_width=2,
        )
        scene.play(Write(heading), run_time=MEDIUM)
        scene.play(Create(underline), run_time=FAST)

    items = VGroup()
    for line in lines:
        arrow = Triangle(color=bullet_color, fill_color=bullet_color, fill_opacity=1).scale(0.12)
        arrow.rotate(-PI / 2)
        body = Text(line, color=TEXT, font_size=26)
        items.add(VGroup(arrow, body).arrange(RIGHT, buff=0.35, aligned_edge=UP))

    items.arrange(DOWN, aligned_edge=LEFT, buff=0.45)
    if title:
        items.next_to(underline, DOWN, buff=0.7).align_to(heading, LEFT)
    else:
        items.move_to(ORIGIN)

    for item in items:
        scene.play(FadeIn(item, shift=RIGHT * 0.3), run_time=MEDIUM * 0.7)
        scene.wait(per_line_pause)

    scene.wait(tail_pause)
    fade_targets = [items]
    if title:
        fade_targets.extend([heading, underline])
    scene.play(*[FadeOut(m) for m in fade_targets], run_time=MEDIUM * 0.6)


def gentle_clear(scene: Scene, run_time: float = 0.6):
    """Fade out every mobject currently on screen rather than hard-clearing."""
    if scene.mobjects:
        scene.play(*[FadeOut(m) for m in scene.mobjects], run_time=run_time)


# ─────────────────────────────────────────────────────────────────────────────
# CHAPTER MIXIN — every sub-method is a "chapter" that operates on `self`
# ─────────────────────────────────────────────────────────────────────────────
class _MinCutChapters:
    """Scene-agnostic chapters.  Mixed into MinCutCompendium and each Chapter*Scene."""

    # ── 00. Title + credits ──────────────────────────────────────────────
    def intro_credits(self):
        title = Text("IT584 — Approximation Algorithms", color=NODE_COLOR, font_size=44, weight=BOLD)
        subtitle = Text("The Minimum-Cut Compendium", color=TEXT, font_size=52, weight=BOLD)
        version = Text("v10.0", color=MUTED, font_size=28)
        group = VGroup(title, subtitle, version).arrange(DOWN, buff=0.4)
        self.play(FadeIn(title, shift=DOWN * 0.3), run_time=SLOW * 0.8)
        self.play(Write(subtitle), run_time=SLOW)
        self.play(FadeIn(version), run_time=MEDIUM * 0.6)
        self.wait(2.2)
        self.play(FadeOut(group, shift=UP * 0.3), run_time=MEDIUM)

        names = VGroup(
            Text("Nilesh Mori — 202301473", color=TEXT, font_size=32),
            Text("Harsh Maheriya — 202301470", color=TEXT, font_size=32),
            Text("Under the guidance of Prof. Rachit Chaya", color=ACTIVE, font_size=30, slant=ITALIC),
        ).arrange(DOWN, buff=0.5)

        rule = Line(LEFT * 3, RIGHT * 3, stroke_color=ACTIVE, stroke_width=2).next_to(names, UP, buff=0.6)
        self.play(GrowFromCenter(rule), run_time=MEDIUM)
        for n in names:
            self.play(FadeIn(n, shift=UP * 0.15), run_time=MEDIUM * 0.7)
        self.wait(2.0)
        self.play(FadeOut(VGroup(names, rule), shift=UP * 0.2), run_time=MEDIUM)

    # ── 01. Foundations ─────────────────────────────────────────────────
    def foundations_theory(self):
        chapter_card(self, "Chapter 01", "The Foundations", "Graphs, cuts, and the language we'll speak")
        bullet_list(
            self,
            [
                "A graph G = (V, E) is a set of vertices V joined by edges E.",
                "Degree of a vertex = number of edges incident to it.",
                "A multigraph allows parallel edges between the same two vertices.",
                "A cut partitions V into two non-empty sets S and V\u2216S.",
                "The cost of a cut = number (or total weight) of crossing edges.",
            ],
            title="Graph Theory Refresher",
            per_line_pause=1.3,
            tail_pause=2.0,
        )

    def foundations_graph_demo(self):
        nodes = [1, 2, 3, 4, 5, 6]
        edges = [(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (1, 3), (2, 5)]
        g = styled_graph(nodes, edges, layout="circular")
        g.scale(2.1)
        fit_to_frame(g, 10, 6)

        self.play(Create(g), run_time=SLOW * 2)
        self.wait(1.2)

        # Annotate vertex
        v = g.vertices[1]
        arrow_v = Arrow(
            start=v.get_center() + UL * 2.2,
            end=v.get_center() + UL * 0.55,
            buff=0.05,
            color=ACTIVE,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.22,
        )
        lbl_v = Text("Vertex  (node)", color=ACTIVE, font_size=26, weight=BOLD).next_to(arrow_v, UP, buff=0.15)
        self.play(Create(arrow_v), Write(lbl_v), run_time=MEDIUM)
        self.play(Indicate(v, color=ACTIVE, scale_factor=1.35), run_time=MEDIUM)
        self.wait(1.4)

        # Annotate edge
        e = g.edges[(1, 2)]
        arrow_e = Arrow(
            start=e.get_center() + DR * 2.2,
            end=e.get_center() + DR * 0.45,
            buff=0.05,
            color=ACTIVE,
            stroke_width=5,
            max_tip_length_to_length_ratio=0.22,
        )
        lbl_e = Text("Edge  (connection)", color=ACTIVE, font_size=26, weight=BOLD).next_to(arrow_e, DOWN, buff=0.15)
        self.play(Create(arrow_e), Write(lbl_e), run_time=MEDIUM)
        self.play(e.animate.set_stroke(color=ACTIVE, width=7), run_time=MEDIUM)
        self.wait(1.4)

        # Show a cut visually: S = {1,2,6}, rest = {3,4,5}
        cut_line = DashedLine(
            start=g.get_center() + UP * 2.5 + LEFT * 0.4,
            end=g.get_center() + DOWN * 2.5 + RIGHT * 0.4,
            dash_length=0.18,
            stroke_color=ALERT,
            stroke_width=5,
        )
        crossing = [(2, 3), (5, 6)]
        self.play(Create(cut_line), run_time=MEDIUM)
        self.play(
            *[g.edges[e].animate.set_stroke(color=ALERT, width=7) for e in crossing],
            run_time=MEDIUM,
        )
        cut_label = Text("Cost of this cut = 2", color=ALERT, font_size=28, weight=BOLD).to_edge(DOWN, buff=0.8)
        self.play(Write(cut_label), run_time=MEDIUM)
        self.wait(2.2)

        self.play(
            FadeOut(VGroup(g, arrow_v, lbl_v, arrow_e, lbl_e, cut_line, cut_label)),
            run_time=MEDIUM * 0.8,
        )

    # ── 02. Problem statement ───────────────────────────────────────────
    def problem_statement(self):
        chapter_card(self, "Chapter 02", "The Minimum-Cut Problem", "What exactly are we trying to find?")
        bullet_list(
            self,
            [
                "Global Min-Cut: minimum-cost partition of V into two non-empty sides.",
                "No fixed source s or sink t — any valid partition is a candidate.",
                "For unweighted graphs, the cost is the count of crossing edges.",
                "Used in network reliability, clustering, image segmentation, VLSI...",
                "We'll compare randomized, recursive, deterministic, and flow-based attacks.",
            ],
            title="Problem Statement",
            per_line_pause=1.4,
            tail_pause=2.3,
        )

    # ── 03. Karger's theory ─────────────────────────────────────────────
    def kargers_theory(self):
        chapter_card(self, "Chapter 03", "Karger's Contraction", "Randomness beats determinism — sometimes.")
        bullet_list(
            self,
            [
                "Repeatedly pick a random edge (u, v) and contract it.",
                "Contraction: merge u and v, keep parallel edges, drop self-loops.",
                "Stop when only 2 super-nodes remain.",
                "The remaining edges define a cut of the original graph.",
                "Min-cut edges are rare, so random picks usually miss them.",
                "Success probability: Pr[finding min-cut] \u2265 2 / (n (n - 1)).",
            ],
            title="Karger's Big Idea",
            per_line_pause=1.2,
            tail_pause=2.2,
        )

    # ── 04. Karger's DETAILED dry run on a small graph ──────────────────
    def kargers_dry_run(self):
        """Animate a complete run of Karger's on a small graph, step by step."""
        title = Text("Karger — Full Dry Run", color=ACTIVE, font_size=36, weight=BOLD).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=MEDIUM)

        # Small 5-node graph with obvious min-cut of 2
        nodes = ["A", "B", "C", "D", "E"]
        edges = [
            ("A", "B"), ("B", "C"), ("A", "C"),     # triangle 1
            ("D", "E"),                               # edge 2
            ("C", "D"), ("C", "E"),                   # bridges (min-cut)
        ]
        pos = {
            "A": [-3.4, 1.3, 0],
            "B": [-3.4, -1.3, 0],
            "C": [-0.8, 0.0, 0],
            "D": [2.8, 1.3, 0],
            "E": [2.8, -1.3, 0],
        }

        g = styled_graph(nodes, edges, layout=pos)
        g.shift(LEFT * 2.5 + DOWN * 0.4)

        # Side panel: edge pool + log
        side = panel("Karger State", width=4.6, height=5.5)
        side.to_edge(RIGHT, buff=0.4).shift(DOWN * 0.4)
        pool_title = Text("Edge Pool", color=TEXT, font_size=22, weight=BOLD)
        pool_title.move_to(side[0].get_top() + DOWN * 0.9)
        log_title = Text("Action Log", color=TEXT, font_size=22, weight=BOLD)
        log_title.move_to(side[0].get_center() + DOWN * 0.3)

        self.play(Create(side), Write(pool_title), Write(log_title), run_time=MEDIUM)
        self.play(Create(g), run_time=SLOW * 1.5)
        self.wait(1.0)

        # Mutable state containers
        pool_box = side[0]

        def render_pool(edge_list, group_holder):
            """Return a VGroup of edge labels placed inside the top half of side panel."""
            rows = VGroup()
            for u, v in edge_list:
                rows.add(Text(f"({u},{v})", color=TEXT, font_size=18))
            rows.arrange_in_grid(rows=3, cols=3, buff=0.2)
            rows.next_to(pool_title, DOWN, buff=0.25)
            return rows

        def render_log(messages):
            rows = VGroup()
            for m in messages[-4:]:  # keep last 4 lines
                rows.add(Text(m, color=MUTED, font_size=16))
            if rows:
                rows.arrange(DOWN, aligned_edge=LEFT, buff=0.15)
                rows.next_to(log_title, DOWN, buff=0.25).align_to(log_title, LEFT)
            return rows

        multiset = list(edges)  # with multiplicities
        node_alias = {n: n for n in nodes}  # merged-into mapping
        super_label = {n: n for n in nodes}  # current super-node label per original node
        log_history: list[str] = []

        pool_mob = render_pool(multiset, None)
        log_mob = render_log(log_history)
        self.play(FadeIn(pool_mob), FadeIn(log_mob), run_time=FAST)

        # Contraction plan — hand-chosen so the dry-run is educational:
        contractions = [("A", "B"), ("A", "C"), ("D", "E")]

        step_colors = [PURPLE, TEAL, PINK]

        for step_idx, (u, v) in enumerate(contractions):
            color_step = step_colors[step_idx]

            step_banner = Text(
                f"Step {step_idx + 1}: contract edge ({u}, {v})",
                color=color_step,
                font_size=26,
                weight=BOLD,
            ).to_edge(DOWN, buff=0.6)
            self.play(FadeIn(step_banner, shift=UP * 0.2), run_time=MEDIUM * 0.7)

            # Highlight the chosen edge(s) in the graph.  Parallel edges are
            # represented by multiple entries in the multiset, but only one
            # Graph-edge exists — that's OK, we're showing logic here.
            if (u, v) in g.edges:
                edge_obj = g.edges[(u, v)]
            elif (v, u) in g.edges:
                edge_obj = g.edges[(v, u)]
            else:
                edge_obj = None

            if edge_obj is not None:
                self.play(
                    edge_obj.animate.set_stroke(color=color_step, width=9),
                    Flash(edge_obj, color=color_step, flash_radius=0.45),
                    run_time=MEDIUM,
                )
                self.wait(0.6)

            # Merge v into u visually.
            v_node = g.vertices[v]
            u_node = g.vertices[u]
            self.play(
                v_node.animate.move_to(u_node.get_center()),
                run_time=SLOW,
            )
            # Fade the merged node so it visually "disappears" into u.
            self.play(
                v_node.animate.set_opacity(0.0),
                run_time=FAST,
            )

            # Update multiset: remove chosen edge, relabel v→u, drop self-loops.
            new_multiset = []
            for a, b in multiset:
                if {a, b} == {u, v}:
                    continue  # dropped (the picked edge and its parallels)
                a2 = u if a == v else a
                b2 = u if b == v else b
                if a2 == b2:
                    continue  # self-loop removed
                new_multiset.append((a2, b2))
            multiset = new_multiset

            log_history.append(f"{step_idx + 1}. merged {v} \u2192 {u}")
            if step_idx == 0:
                log_history.append("   parallel (A,C) kept")
            if step_idx == 1:
                log_history.append("   self-loops dropped")

            new_pool = render_pool(multiset, None)
            new_log = render_log(log_history)
            self.play(
                FadeOut(pool_mob),
                FadeOut(log_mob),
                run_time=FAST,
            )
            pool_mob = new_pool
            log_mob = new_log
            self.play(FadeIn(pool_mob, shift=UP * 0.15), FadeIn(log_mob, shift=UP * 0.15), run_time=FAST)

            self.play(FadeOut(step_banner, shift=DOWN * 0.2), run_time=FAST)
            self.wait(0.8)

        # At the end there should be exactly 2 super-nodes with some edges between.
        remaining = Text(
            f"Only {len(set(sum(([a, b] for a, b in multiset), [])))} super-nodes remain",
            color=SUCCESS,
            font_size=26,
            weight=BOLD,
        ).to_edge(DOWN, buff=1.1)
        cut_lbl = Text(
            f"Cut value from this run = {len(multiset)}",
            color=SUCCESS,
            font_size=30,
            weight=BOLD,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(remaining, shift=UP * 0.2), run_time=MEDIUM)
        self.wait(1.2)
        self.play(FadeIn(cut_lbl, shift=UP * 0.2), run_time=MEDIUM)
        self.wait(3.0)

        self.play(
            *[FadeOut(m) for m in [title, g, side, pool_title, log_title, pool_mob, log_mob, remaining, cut_lbl]],
            run_time=MEDIUM,
        )

    # ── 05. Case studies: best / worst / medium ─────────────────────────
    def case_best_dumbbell(self):
        chapter_card(self, "Case Study", "Best Case — The Dumbbell", "Two dense cliques, one fragile bridge")
        nodes = list(range(1, 11))
        pos = {
            1: [-5.2, 1.6, 0], 2: [-6.2, 0.0, 0], 3: [-5.2, -1.6, 0],
            4: [-3.8, -1.0, 0], 5: [-3.8, 1.0, 0],
            6: [5.2, 1.6, 0], 7: [6.2, 0.0, 0], 8: [5.2, -1.6, 0],
            9: [3.8, -1.0, 0], 10: [3.8, 1.0, 0],
        }
        intra_left = [(1,2),(2,3),(3,4),(4,5),(5,1),(1,3),(2,4),(3,5),(1,4)]
        intra_right = [(6,7),(7,8),(8,9),(9,10),(10,6),(6,8),(7,9),(8,10),(6,9)]
        bridge = [(5, 10)]
        edges = intra_left + intra_right + bridge

        g = styled_graph(nodes, edges, layout=pos)
        fit_to_frame(g, 11.5, 6.0)
        self.play(Create(g), run_time=SLOW * 2)
        self.wait(1.0)

        # Highlight each clique
        left_ring = SurroundingRectangle(
            VGroup(*[g.vertices[i] for i in [1,2,3,4,5]]),
            corner_radius=0.25, color=PURPLE, stroke_width=2, buff=0.3,
        )
        right_ring = SurroundingRectangle(
            VGroup(*[g.vertices[i] for i in [6,7,8,9,10]]),
            corner_radius=0.25, color=TEAL, stroke_width=2, buff=0.3,
        )
        self.play(Create(left_ring), Create(right_ring), run_time=MEDIUM)
        self.wait(1.0)

        bridge_edge = g.edges[(5, 10)]
        self.play(
            bridge_edge.animate.set_stroke(color=ACTIVE, width=10),
            Flash(bridge_edge, color=ACTIVE, flash_radius=0.55),
            run_time=MEDIUM,
        )
        bridge_lbl = Text("Min-cut bridge", color=ACTIVE, font_size=24, weight=BOLD)
        bridge_lbl.next_to(bridge_edge, UP, buff=0.2)
        self.play(Write(bridge_lbl), run_time=MEDIUM)
        self.wait(1.0)

        prob = MathTex(
            r"\Pr[\text{bridge picked}] = \frac{1}{|E|} = \frac{1}{19}",
            color=SUCCESS,
            font_size=32,
        ).to_edge(DOWN, buff=0.7)
        self.play(Write(prob), run_time=SLOW)
        self.wait(3.0)
        self.play(FadeOut(VGroup(g, left_ring, right_ring, bridge_lbl, prob)), run_time=MEDIUM)

    def case_worst_cycle(self):
        chapter_card(self, "Case Study", "Worst Case — The Cycle", "Uniform risk, no shielding")
        n = 10
        G_cycle = nx.cycle_graph(n)
        g = styled_graph(list(G_cycle.nodes()), list(G_cycle.edges()), layout="circular")
        g.scale(2.4)
        fit_to_frame(g, 10, 6.2)
        self.play(Create(g), run_time=SLOW * 1.6)
        self.wait(1.0)

        # Highlight any two edges as "the min cut"
        e1 = g.edges[(0, 1)]
        e2 = g.edges[(4, 5)]
        self.play(
            e1.animate.set_stroke(color=ACTIVE, width=9),
            e2.animate.set_stroke(color=ACTIVE, width=9),
            run_time=MEDIUM,
        )
        lbl = Text("Any two non-adjacent edges form a min-cut of size 2",
                   color=ACTIVE, font_size=22).to_edge(UP, buff=0.4)
        self.play(FadeIn(lbl, shift=DOWN * 0.15), run_time=MEDIUM)
        self.wait(1.2)

        prob = MathTex(
            r"\Pr[\text{bad contraction}] \approx \frac{2}{n}",
            color=ALERT,
            font_size=32,
        ).to_edge(DOWN, buff=0.7)
        note = Text("Every contraction is dangerous — no safe moves.",
                    color=ALERT, font_size=22).next_to(prob, UP, buff=0.25)
        self.play(Write(prob), run_time=SLOW)
        self.play(FadeIn(note, shift=UP * 0.1), run_time=MEDIUM)
        self.wait(3.0)
        self.play(FadeOut(VGroup(g, lbl, prob, note)), run_time=MEDIUM)

    def case_medium_random(self):
        chapter_card(self, "Case Study", "Medium Case — Random G(n, p)", "Real-world densities")
        G_mid = nx.gnp_random_graph(15, 0.28, seed=42)
        g = styled_graph(
            list(G_mid.nodes()), list(G_mid.edges()), layout="spring", seed=42,
        )
        g.scale(2.0)
        fit_to_frame(g, 11, 6.0)
        self.play(Create(g), run_time=SLOW * 1.8)
        self.wait(1.2)

        msg = Text(
            f"{G_mid.number_of_nodes()} nodes, {G_mid.number_of_edges()} edges — balanced success probability",
            color=TEAL,
            font_size=24,
        ).to_edge(DOWN, buff=0.6)
        self.play(Write(msg), run_time=MEDIUM)
        self.wait(2.8)
        self.play(FadeOut(VGroup(g, msg)), run_time=MEDIUM)

    # ── 06. Karger-Stein ────────────────────────────────────────────────
    def karger_stein_theory(self):
        chapter_card(self, "Chapter 04", "Karger-Stein", "Recursion rescues the tail")
        bullet_list(
            self,
            [
                "Karger's bad moves pile up near the end (few nodes left).",
                "Fix: contract down to n / \u221A2 nodes, then FORK into two recursive calls.",
                "Each fork repeats contraction independently — doubling chances to dodge the cut.",
                "Runtime: O(V\u00B2 log\u00B3 V), Success: \u03A9(1 / log V) per run.",
                "Final answer: minimum of all leaves of the recursion tree.",
            ],
            title="Karger-Stein — Recursive Contraction",
            per_line_pause=1.3,
            tail_pause=2.0,
        )

    def karger_stein_tree_demo(self):
        title = Text("Recursion Tree — levels shrink by \u221A2", color=ACTIVE, font_size=30, weight=BOLD).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=MEDIUM)

        # Tree data: (label, position)
        levels = {
            "root": (0, 2.6),
            "L": (-3.6, 0.6), "R": (3.6, 0.6),
            "LL": (-5.0, -1.4), "LR": (-2.3, -1.4),
            "RL": (2.3, -1.4), "RR": (5.0, -1.4),
            "LLL": (-5.6, -3.1), "LLR": (-4.3, -3.1),
            "LRL": (-2.9, -3.1), "LRR": (-1.6, -3.1),
            "RLL": (1.6, -3.1), "RLR": (2.9, -3.1),
            "RRL": (4.3, -3.1), "RRR": (5.6, -3.1),
        }
        dots = {k: Dot(point=[x, y, 0], color=NODE_COLOR, radius=0.18) for k, (x, y) in levels.items()}

        size_labels = {
            "root": "n",
            "L": "n/\u221A2", "R": "n/\u221A2",
            "LL": "n/2", "LR": "n/2", "RL": "n/2", "RR": "n/2",
        }

        edges_spec = [
            ("root", "L"), ("root", "R"),
            ("L", "LL"), ("L", "LR"),
            ("R", "RL"), ("R", "RR"),
            ("LL", "LLL"), ("LL", "LLR"),
            ("LR", "LRL"), ("LR", "LRR"),
            ("RL", "RLL"), ("RL", "RLR"),
            ("RR", "RRL"), ("RR", "RRR"),
        ]
        lines = {
            (a, b): Line(dots[a].get_center(), dots[b].get_center(), stroke_color=EDGE_LIGHT, stroke_width=2)
            for a, b in edges_spec
        }

        # Root appears
        self.play(GrowFromCenter(dots["root"]), run_time=MEDIUM)
        lbl_root = Text(size_labels["root"], color=TEXT, font_size=22).next_to(dots["root"], UP, buff=0.15)
        self.play(Write(lbl_root), run_time=MEDIUM * 0.6)

        # Level 1
        self.play(
            Create(lines[("root", "L")]), Create(lines[("root", "R")]),
            GrowFromCenter(dots["L"]), GrowFromCenter(dots["R"]),
            run_time=MEDIUM,
        )
        lbl_l = Text(size_labels["L"], color=TEXT, font_size=20).next_to(dots["L"], LEFT, buff=0.15)
        lbl_r = Text(size_labels["R"], color=TEXT, font_size=20).next_to(dots["R"], RIGHT, buff=0.15)
        self.play(Write(lbl_l), Write(lbl_r), run_time=MEDIUM * 0.6)

        # Level 2
        self.play(
            *[Create(lines[(p, c)]) for p, c in [("L", "LL"), ("L", "LR"), ("R", "RL"), ("R", "RR")]],
            *[GrowFromCenter(dots[k]) for k in ["LL", "LR", "RL", "RR"]],
            run_time=MEDIUM,
        )

        # Level 3
        self.play(
            *[Create(lines[(p, c)]) for p, c in [
                ("LL", "LLL"), ("LL", "LLR"),
                ("LR", "LRL"), ("LR", "LRR"),
                ("RL", "RLL"), ("RL", "RLR"),
                ("RR", "RRL"), ("RR", "RRR"),
            ]],
            *[GrowFromCenter(dots[k]) for k in ["LLL","LLR","LRL","LRR","RLL","RLR","RRL","RRR"]],
            run_time=SLOW,
        )
        # Highlight one of the leaves as "found the min-cut"
        best_leaf = dots["LRR"]
        self.play(best_leaf.animate.set_color(SUCCESS).scale(1.6), run_time=MEDIUM)
        success_label = Text("best min-cut found here", color=SUCCESS, font_size=20).next_to(best_leaf, DOWN, buff=0.2)
        self.play(Write(success_label), run_time=MEDIUM * 0.7)
        self.wait(1.2)

        note = Text(
            "Each leaf is an independent Karger run — we keep the smallest result.",
            color=TEXT,
            font_size=22,
        ).to_edge(DOWN, buff=0.5)
        self.play(FadeIn(note, shift=UP * 0.2), run_time=MEDIUM)
        self.wait(3.2)

        all_mobs = [title, lbl_root, lbl_l, lbl_r, success_label, note] + list(dots.values()) + list(lines.values())
        self.play(*[FadeOut(m) for m in all_mobs], run_time=MEDIUM)

    # ── 07. Stoer-Wagner ────────────────────────────────────────────────
    def stoer_wagner_theory(self):
        chapter_card(self, "Chapter 05", "Stoer-Wagner", "Deterministic, elegant, correct")
        bullet_list(
            self,
            [
                "No randomness, no flows — just clever orderings.",
                "Core idea: Maximum Adjacency Search (MAS).",
                "Start from any node a, repeatedly add the node with the largest cumulative edge weight into the visited set.",
                "Let s, t be the last two nodes added in a phase.",
                "Cut-of-phase = sum of edge weights from t to everything already visited.",
                "Merge s and t, repeat; minimum cut-of-phase = global min-cut.",
                "Runtime: O(V E + V\u00B2 log V). Always exact.",
            ],
            title="Stoer-Wagner — MAS + merge",
            per_line_pause=1.25,
            tail_pause=2.2,
        )

    def stoer_wagner_phase_demo(self):
        """Animate one full MAS phase on a 4-node weighted graph."""
        title = Text("Stoer-Wagner — One Phase of MAS",
                     color=ACTIVE, font_size=30, weight=BOLD).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=MEDIUM)

        nodes = ["a", "b", "c", "d"]
        pos = {
            "a": [-4, 1.5, 0],
            "b": [-1.5, -1.5, 0],
            "c": [1.5, 1.5, 0],
            "d": [4, -1.5, 0],
        }
        edges = [("a", "b"), ("a", "c"), ("b", "c"), ("b", "d"), ("c", "d")]
        weights = {("a","b"): 3, ("a","c"): 1, ("b","c"): 2, ("b","d"): 4, ("c","d"): 5}

        g = styled_graph(nodes, edges, layout=pos)
        g.shift(LEFT * 1.6 + DOWN * 0.2)
        self.play(Create(g), run_time=SLOW)

        # Draw weight labels
        w_labels = VGroup()
        for e, w in weights.items():
            edge_obj = g.edges[e]
            mid = edge_obj.get_center()
            w_lbl = Text(str(w), color=MUTED, font_size=22, weight=BOLD).move_to(mid)
            # Nudge off the edge a little
            direction = edge_obj.get_unit_vector()
            offset = np.array([-direction[1], direction[0], 0]) * 0.28
            w_lbl.shift(offset)
            w_labels.add(w_lbl)
        self.play(FadeIn(w_labels), run_time=MEDIUM)
        self.wait(0.8)

        # Side panel: visited set + connection weights
        side = panel("MAS Tracker", width=4.2, height=5.2)
        side.to_edge(RIGHT, buff=0.4).shift(DOWN * 0.2)
        visited_title = Text("Visited set A", color=TEXT, font_size=20, weight=BOLD)
        visited_title.move_to(side[0].get_top() + DOWN * 0.9)
        weights_title = Text("w(A, v) for v \u2209 A", color=TEXT, font_size=20, weight=BOLD)
        weights_title.move_to(side[0].get_center() + DOWN * 0.0)
        self.play(Create(side), Write(visited_title), Write(weights_title), run_time=MEDIUM)

        visited: list[str] = ["a"]
        self.play(g.vertices["a"].animate.set_color(ACTIVE).set_fill(ACTIVE, 0.6),
                  run_time=MEDIUM * 0.7)

        # MAS step-by-step
        mas_steps = [
            ("b", {"b": 3, "c": 1, "d": 0}),
            ("d", {"c": 1 + 2, "d": 0 + 4}),
            ("c", {"c": 1 + 2 + 5}),
        ]

        v_mobs = None
        w_mobs = None

        def render_visited():
            rows = VGroup()
            for n in visited:
                rows.add(Text(n, color=ACTIVE, font_size=24, weight=BOLD))
            rows.arrange(RIGHT, buff=0.3)
            rows.next_to(visited_title, DOWN, buff=0.3)
            return rows

        def render_weights(m):
            rows = VGroup()
            for k, v in sorted(m.items(), key=lambda kv: -kv[1]):
                line = Text(f"w(A, {k}) = {v}", color=TEXT, font_size=20)
                rows.add(line)
            rows.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            rows.next_to(weights_title, DOWN, buff=0.3).align_to(weights_title, LEFT)
            return rows

        v_mobs = render_visited()
        self.play(FadeIn(v_mobs), run_time=FAST)

        for idx, (next_node, wts) in enumerate(mas_steps):
            new_w_mobs = render_weights(wts)
            if w_mobs is None:
                self.play(FadeIn(new_w_mobs), run_time=FAST)
            else:
                self.play(Transform(w_mobs, new_w_mobs), run_time=MEDIUM)
            w_mobs = new_w_mobs

            # Highlight the edges contributing to w(A, next)
            contributing = []
            for n in visited:
                if (n, next_node) in g.edges:
                    contributing.append(g.edges[(n, next_node)])
                elif (next_node, n) in g.edges:
                    contributing.append(g.edges[(next_node, n)])
            self.play(*[e.animate.set_stroke(color=PURPLE, width=8) for e in contributing], run_time=MEDIUM)

            step_lbl = Text(
                f"MAS pick: {next_node} (largest w = {wts[next_node]})",
                color=PURPLE, font_size=22, weight=BOLD,
            ).to_edge(DOWN, buff=0.45)
            self.play(Write(step_lbl), run_time=MEDIUM * 0.8)
            self.wait(0.8)

            # Move node into visited set
            visited.append(next_node)
            self.play(
                g.vertices[next_node].animate.set_color(ACTIVE).set_fill(ACTIVE, 0.5),
                run_time=MEDIUM,
            )

            new_v_mobs = render_visited()
            self.play(Transform(v_mobs, new_v_mobs), run_time=FAST)
            self.play(FadeOut(step_lbl), run_time=FAST)
            # Reset contributing edge colors unless it's the final "cut of phase"
            if idx < len(mas_steps) - 1:
                self.play(*[e.animate.set_stroke(color=EDGE_COLOR, width=edge_width_for(len(nodes))) for e in contributing], run_time=FAST)

        # Declare cut of phase
        cut_txt = Text(
            "Cut of phase = w(A, t) = 8   (t = c, s = d)",
            color=SUCCESS, font_size=26, weight=BOLD,
        ).to_edge(DOWN, buff=0.55)
        self.play(Write(cut_txt), run_time=SLOW)
        self.wait(2.0)

        # Now merge s and d into a single super-node
        merge_lbl = Text("Merge s = d  and  t = c  →  super-node 'cd'",
                         color=TEAL, font_size=22).next_to(cut_txt, UP, buff=0.2)
        self.play(Write(merge_lbl), run_time=MEDIUM)
        self.play(
            g.vertices["d"].animate.move_to(g.vertices["c"].get_center()),
            run_time=SLOW,
        )
        self.play(g.vertices["d"].animate.set_opacity(0.0), run_time=FAST)

        self.wait(2.5)

        self.play(
            *[FadeOut(m) for m in [title, g, w_labels, side, visited_title, weights_title, v_mobs, w_mobs, cut_txt, merge_lbl]],
            run_time=MEDIUM,
        )

    # ── 08. Max-Flow / Ford-Fulkerson ───────────────────────────────────
    def max_flow_theory(self):
        chapter_card(self, "Chapter 06", "Max-Flow Min-Cut", "Duality at its finest")
        bullet_list(
            self,
            [
                "Pick a source s and a sink t. Capacities live on edges.",
                "Ford-Fulkerson: repeatedly find an augmenting s-t path in the residual graph.",
                "Push bottleneck capacity along the path; update residuals (including back-edges).",
                "Terminate when no augmenting path exists.",
                "Max-Flow = Min-Cut: edges saturated from the s-reachable side form a cut.",
                "For global min-cut: run the flow for multiple (s, t) pairs and keep the best.",
            ],
            title="Flow-based Min-Cut",
            per_line_pause=1.25,
            tail_pause=2.2,
        )

    def max_flow_dry_run(self):
        title = Text("Ford-Fulkerson — Dry Run",
                     color=ACTIVE, font_size=30, weight=BOLD).to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=MEDIUM)

        # 4-node flow network
        nodes = ["s", "a", "b", "t"]
        pos = {
            "s": [-4.5, 0, 0],
            "a": [-1.2, 1.8, 0],
            "b": [-1.2, -1.8, 0],
            "t": [2.2, 0, 0],
        }
        # Directed capacities
        caps = {
            ("s", "a"): 3,
            ("s", "b"): 2,
            ("a", "b"): 1,
            ("a", "t"): 2,
            ("b", "t"): 3,
        }
        # Use Graph for layout but draw directional arrows separately
        g = styled_graph(nodes, [], layout=pos, labels=True)
        g.shift(LEFT * 1.0)
        self.play(FadeIn(g), run_time=MEDIUM)

        # Colour s and t distinctively
        self.play(
            g.vertices["s"].animate.set_fill(SUCCESS, 0.8).set_stroke(SUCCESS, 3),
            g.vertices["t"].animate.set_fill(ALERT, 0.8).set_stroke(ALERT, 3),
            run_time=MEDIUM,
        )

        # Draw directed arrows with capacity labels.
        arrow_objs: dict = {}
        cap_labels: dict = {}
        for (u, v), c in caps.items():
            start = g.vertices[u].get_center()
            end = g.vertices[v].get_center()
            arr = Arrow(
                start=start, end=end, buff=0.45,
                color=EDGE_COLOR, stroke_width=5,
                max_tip_length_to_length_ratio=0.12,
            )
            arrow_objs[(u, v)] = arr
            mid = arr.get_center()
            direction = arr.get_unit_vector()
            normal = np.array([-direction[1], direction[0], 0]) * 0.35
            lbl = Text(f"{c}", color=MUTED, font_size=22, weight=BOLD).move_to(mid + normal)
            cap_labels[(u, v)] = lbl
        self.play(
            *[Create(a) for a in arrow_objs.values()],
            *[FadeIn(lbl) for lbl in cap_labels.values()],
            run_time=SLOW,
        )
        self.wait(1.0)

        # Side panel: flow accumulator
        side = panel("Flow Tracker", width=3.8, height=5.0)
        side.to_edge(RIGHT, buff=0.3).shift(DOWN * 0.2)
        flow_title = Text("Augmenting paths", color=TEXT, font_size=20, weight=BOLD)
        flow_title.move_to(side[0].get_top() + DOWN * 0.9)
        total_title = Text("Total flow", color=TEXT, font_size=20, weight=BOLD)
        total_title.move_to(side[0].get_bottom() + UP * 1.1)
        self.play(Create(side), Write(flow_title), Write(total_title), run_time=MEDIUM)

        history: list[str] = []
        total = [0]
        hist_mob = VGroup()
        total_mob = Text("0", color=SUCCESS, font_size=42, weight=BOLD)
        total_mob.next_to(total_title, DOWN, buff=0.2)
        self.play(Write(total_mob), run_time=FAST)

        residual = dict(caps)  # forward residuals only (simplified: augment along simple paths)

        def animate_path(path, bottleneck, color):
            edge_list = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            arrows_to_flash = [arrow_objs[e] for e in edge_list]
            # Highlight the path
            self.play(*[a.animate.set_color(color).set_stroke(width=9) for a in arrows_to_flash], run_time=MEDIUM)
            # "Water" animation: a dot traveling along the path
            dot = Dot(color=color, radius=0.14).move_to(g.vertices[path[0]].get_center())
            self.add(dot)
            for u, v in edge_list:
                self.play(
                    dot.animate.move_to(g.vertices[v].get_center()),
                    run_time=FAST,
                )
            self.remove(dot)
            self.play(
                *[a.animate.set_color(EDGE_LIGHT).set_stroke(width=5) for a in arrows_to_flash],
                run_time=FAST,
            )
            return edge_list

        # Path 1: s→a→t, bottleneck = 2
        p1_lbl = Text("Path 1: s → a → t   Δ = 2", color=PURPLE, font_size=22, weight=BOLD).to_edge(DOWN, buff=0.5)
        self.play(Write(p1_lbl), run_time=MEDIUM)
        p1_edges = animate_path(["s", "a", "t"], 2, PURPLE)
        for e in p1_edges:
            residual[e] -= 2
            new_lbl = Text(str(residual[e]), color=PURPLE, font_size=22, weight=BOLD).move_to(cap_labels[e].get_center())
            self.play(Transform(cap_labels[e], new_lbl), run_time=FAST)
        total[0] += 2
        self.play(Transform(total_mob, Text("2", color=SUCCESS, font_size=42, weight=BOLD).next_to(total_title, DOWN, buff=0.2)), run_time=FAST)
        self.play(FadeOut(p1_lbl), run_time=FAST)

        # Path 2: s→b→t, bottleneck = 2
        p2_lbl = Text("Path 2: s → b → t   Δ = 2", color=TEAL, font_size=22, weight=BOLD).to_edge(DOWN, buff=0.5)
        self.play(Write(p2_lbl), run_time=MEDIUM)
        p2_edges = animate_path(["s", "b", "t"], 2, TEAL)
        for e in p2_edges:
            residual[e] -= 2
            new_lbl = Text(str(residual[e]), color=TEAL, font_size=22, weight=BOLD).move_to(cap_labels[e].get_center())
            self.play(Transform(cap_labels[e], new_lbl), run_time=FAST)
        total[0] += 2
        self.play(Transform(total_mob, Text("4", color=SUCCESS, font_size=42, weight=BOLD).next_to(total_title, DOWN, buff=0.2)), run_time=FAST)
        self.play(FadeOut(p2_lbl), run_time=FAST)

        # Path 3: s→a→b→t (uses cross-edge a→b)
        # s-a residual = 1, a-b = 1, b-t = 1 → bottleneck 1.
        p3_lbl = Text("Path 3: s → a → b → t   Δ = 1", color=PINK, font_size=22, weight=BOLD).to_edge(DOWN, buff=0.5)
        self.play(Write(p3_lbl), run_time=MEDIUM)
        p3_edges = animate_path(["s", "a", "b", "t"], 1, PINK)
        for e in p3_edges:
            residual[e] -= 1
            new_lbl = Text(str(residual[e]), color=PINK, font_size=22, weight=BOLD).move_to(cap_labels[e].get_center())
            self.play(Transform(cap_labels[e], new_lbl), run_time=FAST)
        total[0] += 1
        self.play(Transform(total_mob, Text("5", color=SUCCESS, font_size=42, weight=BOLD).next_to(total_title, DOWN, buff=0.2)), run_time=FAST)
        self.play(FadeOut(p3_lbl), run_time=FAST)

        # No more augmenting paths
        final_msg = Text(
            "No augmenting paths remain → Max-Flow = 5",
            color=SUCCESS, font_size=28, weight=BOLD,
        ).to_edge(DOWN, buff=0.55)
        self.play(Write(final_msg), run_time=SLOW)
        self.wait(1.5)

        # Show min-cut visually: {s} reachable side; cut edges = s→a (cap 3), s→b (cap 2); total 5
        cut_line = DashedLine(
            start=g.vertices["s"].get_center() + RIGHT * 1.3 + UP * 3.0,
            end=g.vertices["s"].get_center() + RIGHT * 1.3 + DOWN * 3.0,
            dash_length=0.2, stroke_color=ALERT, stroke_width=5,
        )
        self.play(Create(cut_line), run_time=MEDIUM)
        cut_label = Text("Min cut = {s} | {a, b, t},  capacity = 3 + 2 = 5",
                         color=ALERT, font_size=22, weight=BOLD).next_to(final_msg, UP, buff=0.25)
        self.play(Write(cut_label), run_time=SLOW)
        self.wait(3.0)

        mobs = [title, g, side, flow_title, total_title, total_mob, final_msg, cut_label, cut_line]
        mobs += list(arrow_objs.values()) + list(cap_labels.values())
        self.play(*[FadeOut(m) for m in mobs], run_time=MEDIUM)

    # ── 09. Final summary table ─────────────────────────────────────────
    def final_summary(self):
        chapter_card(self, "Chapter 07", "Side-by-Side Compendium", "When to reach for which algorithm")

        title = Text("Min-Cut Algorithms — Summary",
                     color=ACTIVE, font_size=36, weight=BOLD).to_edge(UP, buff=0.6)
        self.play(Write(title), run_time=MEDIUM)

        table = Table(
            [
                ["Karger",        "Randomized",    "O(V\u00B2 E)",              "2 / (V(V-1))"],
                ["Karger-Stein",  "Recursive",     "O(V\u00B2 log\u00B3 V)",    "\u03A9(1 / log V)"],
                ["Stoer-Wagner",  "Deterministic", "O(V E + V\u00B2 log V)",    "100%"],
                ["Ford-Fulkerson","Flow (s,t)",    "O(V E\u00B2)",              "100% per (s,t)"],
            ],
            col_labels=[
                Text("Algorithm",  color=ACTIVE, weight=BOLD),
                Text("Approach",   color=ACTIVE, weight=BOLD),
                Text("Complexity", color=ACTIVE, weight=BOLD),
                Text("Success prob.", color=ACTIVE, weight=BOLD),
            ],
            include_outer_lines=True,
            line_config={"stroke_color": EDGE_LIGHT, "stroke_width": 1.5},
            v_buff=0.35,
            h_buff=0.65,
        ).scale(0.6).next_to(title, DOWN, buff=0.6)
        # Style inner text
        for entry in table.get_entries():
            entry.set_color(TEXT)
        for entry in table.get_col_labels():
            entry.set_color(ACTIVE)

        self.play(Create(table), run_time=SLOW * 2)
        self.wait(1.2)

        # Highlight each row one at a time
        for i in range(4):
            row = table.get_rows()[i + 1]  # +1 because row 0 is labels
            self.play(row.animate.set_color(ACTIVE), run_time=MEDIUM * 0.6)
            self.wait(0.9)
            self.play(row.animate.set_color(TEXT), run_time=MEDIUM * 0.4)

        takeaway = Text(
            "Approximation ≈ trading certainty for efficiency.",
            color=NODE_COLOR, font_size=30, weight=BOLD, slant=ITALIC,
        ).to_edge(DOWN, buff=0.7)
        self.play(FadeIn(takeaway, shift=UP * 0.2), run_time=SLOW)
        self.wait(3.5)

        self.play(FadeOut(VGroup(title, table, takeaway)), run_time=MEDIUM)

        # Closing card
        end = Text("Thank you!", color=ACTIVE, font_size=60, weight=BOLD)
        self.play(Write(end), run_time=SLOW)
        self.wait(2.5)
        self.play(FadeOut(end), run_time=MEDIUM)


# ─────────────────────────────────────────────────────────────────────────────
# MASTER SCENE — renders everything
# ─────────────────────────────────────────────────────────────────────────────
class MinCutCompendium(Scene, _MinCutChapters):
    """Full animation — ~10–12 minutes at high quality."""

    def construct(self):
        self.intro_credits()

        self.foundations_theory()
        self.foundations_graph_demo()

        self.problem_statement()

        self.kargers_theory()
        self.kargers_dry_run()

        self.case_best_dumbbell()
        self.case_worst_cycle()
        self.case_medium_random()

        self.karger_stein_theory()
        self.karger_stein_tree_demo()

        self.stoer_wagner_theory()
        self.stoer_wagner_phase_demo()

        self.max_flow_theory()
        self.max_flow_dry_run()

        self.final_summary()


# ─────────────────────────────────────────────────────────────────────────────
# INDIVIDUAL CHAPTER SCENES — useful when iterating
# ─────────────────────────────────────────────────────────────────────────────
class Chapter00_Intro(Scene, _MinCutChapters):
    def construct(self):
        self.intro_credits()


class Chapter01_Foundations(Scene, _MinCutChapters):
    def construct(self):
        self.foundations_theory()
        self.foundations_graph_demo()


class Chapter02_Problem(Scene, _MinCutChapters):
    def construct(self):
        self.problem_statement()


class Chapter03_Karger(Scene, _MinCutChapters):
    def construct(self):
        self.kargers_theory()
        self.kargers_dry_run()


class Chapter03b_Cases(Scene, _MinCutChapters):
    def construct(self):
        self.case_best_dumbbell()
        self.case_worst_cycle()
        self.case_medium_random()


class Chapter04_KargerStein(Scene, _MinCutChapters):
    def construct(self):
        self.karger_stein_theory()
        self.karger_stein_tree_demo()


class Chapter05_StoerWagner(Scene, _MinCutChapters):
    def construct(self):
        self.stoer_wagner_theory()
        self.stoer_wagner_phase_demo()


class Chapter06_MaxFlow(Scene, _MinCutChapters):
    def construct(self):
        self.max_flow_theory()
        self.max_flow_dry_run()


class Chapter07_Summary(Scene, _MinCutChapters):
    def construct(self):
        self.final_summary()
