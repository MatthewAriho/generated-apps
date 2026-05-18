"""Canvas-based chart widgets for ClearSpend.

Lightweight charts drawn directly on Kivy canvas - no external dependencies.
All widgets use size_hint_y: None with a fixed height.
"""
from __future__ import annotations
import math

from kivy.graphics import Color, Rectangle, Line, Ellipse, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel


def _text_texture(text, font_size=12, color=(1, 1, 1, 1)):
    """Create a texture from text for canvas rendering."""
    lbl = CoreLabel(text=text, font_size=sp(font_size), color=color)
    lbl.refresh()
    return lbl.texture


class IncomeExpenseBar(Widget):
    """Two vertical bars side-by-side showing income vs expense."""

    income = NumericProperty(0)
    expense = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(130)
        self.bind(pos=self._draw, size=self._draw,
                  income=self._draw, expense=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size

        max_val = max(self.income, self.expense, 1)
        label_h  = dp(18)
        bottom_h = dp(20)  # space for "Income"/"Expense" labels
        bar_area_h = h - bottom_h - label_h - dp(4)
        bar_w = w * 0.25
        gap = w * 0.1

        # Income bar (left)
        inc_h = (self.income / max_val) * bar_area_h if max_val > 0 else 0
        inc_x = x + w * 0.5 - bar_w - gap * 0.5
        inc_y = y + bottom_h

        # Expense bar (right)
        exp_h = (self.expense / max_val) * bar_area_h if max_val > 0 else 0
        exp_x = x + w * 0.5 + gap * 0.5
        exp_y = y + bottom_h

        # Clamp value label tops so they never exceed widget bounds
        max_label_y = y + h - label_h
        inc_label_y = min(inc_y + inc_h + dp(2), max_label_y)
        exp_label_y = min(exp_y + exp_h + dp(2), max_label_y)

        with self.canvas:
            # Income bar
            Color(0.3, 0.85, 0.45, 1)
            RoundedRectangle(pos=(inc_x, inc_y), size=(bar_w, max(inc_h, dp(2))),
                             radius=[dp(4), dp(4), 0, 0])

            # Expense bar
            Color(0.9, 0.35, 0.35, 1)
            RoundedRectangle(pos=(exp_x, exp_y), size=(bar_w, max(exp_h, dp(2))),
                             radius=[dp(4), dp(4), 0, 0])

            # Income value label
            tex = _text_texture(f"${self.income:,.0f}", font_size=11,
                                color=(0.4, 1, 0.55, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex,
                      pos=(inc_x + bar_w / 2 - tex.width / 2, inc_label_y),
                      size=tex.size)

            # Expense value label
            tex2 = _text_texture(f"${self.expense:,.0f}", font_size=11,
                                 color=(1, 0.45, 0.45, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex2,
                      pos=(exp_x + bar_w / 2 - tex2.width / 2, exp_label_y),
                      size=tex2.size)

            # Bottom labels
            tex_inc = _text_texture("Income", font_size=10, color=(0.7, 0.7, 0.7, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex_inc,
                      pos=(inc_x + bar_w / 2 - tex_inc.width / 2, y + dp(2)),
                      size=tex_inc.size)

            tex_exp = _text_texture("Expense", font_size=10, color=(0.7, 0.7, 0.7, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex_exp,
                      pos=(exp_x + bar_w / 2 - tex_exp.width / 2, y + dp(2)),
                      size=tex_exp.size)


class MonthlyTrendLine(Widget):
    """Line chart showing spending trend across multiple months."""

    data_points = ListProperty([])  # list of (label, value) tuples

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(150)
        self.bind(pos=self._draw, size=self._draw, data_points=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        if not self.data_points:
            return

        x, y = self.pos
        w, h = self.size
        pad_l = dp(10)
        pad_r = dp(10)
        pad_b = dp(25)
        pad_t = dp(15)

        chart_w = w - pad_l - pad_r
        chart_h = h - pad_b - pad_t
        n = len(self.data_points)
        if n < 2:
            return

        values = [p[1] for p in self.data_points]
        max_val = max(values) if max(values) > 0 else 1

        # Compute points
        points = []
        for i, (label, val) in enumerate(self.data_points):
            px = x + pad_l + (i / (n - 1)) * chart_w
            py = y + pad_b + (val / max_val) * chart_h
            points.append((px, py))

        with self.canvas:
            # Grid lines (3 horizontal)
            Color(0.3, 0.3, 0.3, 0.5)
            for j in range(4):
                gy = y + pad_b + (j / 3) * chart_h
                Line(points=[x + pad_l, gy, x + w - pad_r, gy], width=0.5)

            # Fill area under line
            if len(points) >= 2:
                fill_pts = []
                fill_pts.append(points[0][0])
                fill_pts.append(y + pad_b)
                for px, py in points:
                    fill_pts.append(px)
                    fill_pts.append(py)
                fill_pts.append(points[-1][0])
                fill_pts.append(y + pad_b)

                Color(0.2, 0.7, 0.8, 0.15)
                from kivy.graphics import Mesh
                # Use triangles for fill - simpler approach: just draw the line
                pass

            # Line
            Color(0.2, 0.8, 0.7, 1)
            flat_pts = []
            for px, py in points:
                flat_pts.extend([px, py])
            Line(points=flat_pts, width=dp(2))

            # Dots on each point
            for px, py in points:
                Color(0.2, 0.8, 0.7, 1)
                Ellipse(pos=(px - dp(4), py - dp(4)), size=(dp(8), dp(8)))

            # Value labels on dots
            for i, (px, py) in enumerate(points):
                val = values[i]
                tex = _text_texture(f"${val:,.0f}", font_size=9,
                                    color=(0.8, 0.8, 0.8, 1))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex,
                           pos=(px - tex.width / 2, py + dp(5)),
                           size=tex.size)

            # Month labels at bottom
            for i, (label, _) in enumerate(self.data_points):
                px = x + pad_l + (i / (n - 1)) * chart_w
                tex = _text_texture(label, font_size=9, color=(0.6, 0.6, 0.6, 1))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex,
                           pos=(px - tex.width / 2, y + dp(4)),
                           size=tex.size)


class DonutChart(Widget):
    """Ring chart with colored slices for category proportions."""

    slices = ListProperty([])  # list of (label, value, (r, g, b, a)) tuples

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(200)
        self.bind(pos=self._draw, size=self._draw, slices=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        if not self.slices:
            return

        x, y = self.pos
        w, h = self.size

        total = sum(s[1] for s in self.slices if s[1] > 0)
        if total <= 0:
            return

        # Donut geometry
        cx = x + w * 0.35
        cy = y + h * 0.5
        radius = min(w * 0.3, h * 0.4)
        inner_radius = radius * 0.55

        with self.canvas:
            # Draw slices
            start_angle = 90  # start from top
            for label, value, color in self.slices:
                if value <= 0:
                    continue
                sweep = (value / total) * 360
                Color(*color)
                Ellipse(pos=(cx - radius, cy - radius),
                        size=(radius * 2, radius * 2),
                        angle_start=start_angle,
                        angle_end=start_angle + sweep)
                start_angle += sweep

            # Inner circle (creates donut hole)
            Color(0.12, 0.12, 0.12, 1)  # match dark bg
            Ellipse(pos=(cx - inner_radius, cy - inner_radius),
                    size=(inner_radius * 2, inner_radius * 2))

            # Center text
            tex = _text_texture(f"${total:,.0f}", font_size=13,
                                color=(1, 1, 1, 0.9))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex,
                      pos=(cx - tex.width / 2, cy + dp(2)),
                      size=tex.size)
            tex2 = _text_texture("total", font_size=9,
                                 color=(0.6, 0.6, 0.6, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex2,
                      pos=(cx - tex2.width / 2, cy - dp(12)),
                      size=tex2.size)

            # Legend (right side)
            legend_x = x + w * 0.65
            legend_y = y + h - dp(20)
            max_items = min(len(self.slices), 7)

            for i in range(max_items):
                label, value, color = self.slices[i]
                ly = legend_y - i * dp(22)
                if ly < y + dp(10):
                    break

                # Color dot
                Color(*color)
                Ellipse(pos=(legend_x, ly - dp(4)), size=(dp(8), dp(8)))

                # Label
                pct = (value / total * 100) if total > 0 else 0
                short_label = label[:12]
                tex = _text_texture(f"{short_label} {pct:.0f}%", font_size=9,
                                    color=(0.75, 0.75, 0.75, 1))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex,
                           pos=(legend_x + dp(14), ly - dp(6)),
                           size=tex.size)


class BudgetPaceBar(Widget):
    """Layered horizontal bar: spent (solid), projected (faded), budget (outline)."""

    spent = NumericProperty(0)
    projected = NumericProperty(0)
    budget = NumericProperty(0)
    label_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(70)
        self.bind(pos=self._draw, size=self._draw,
                  spent=self._draw, projected=self._draw, budget=self._draw)

    def _draw(self, *_):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size

        bar_h = dp(16)
        bar_y = y + dp(28)
        pad = dp(12)
        bar_w = w - pad * 2
        bar_x = x + pad

        max_val = max(self.budget, self.projected, self.spent, 1)

        spent_w = (self.spent / max_val) * bar_w
        proj_w = (self.projected / max_val) * bar_w
        budget_w = (self.budget / max_val) * bar_w

        over_budget = self.spent > self.budget
        spent_color = (0.9, 0.3, 0.3, 1) if over_budget else (0.2, 0.8, 0.7, 1)

        with self.canvas:
            # Budget outline (full width reference)
            Color(0.4, 0.4, 0.4, 0.6)
            RoundedRectangle(pos=(bar_x, bar_y), size=(budget_w, bar_h),
                             radius=[dp(4)])

            # Projected (faded)
            Color(0.5, 0.5, 0.5, 0.3)
            RoundedRectangle(pos=(bar_x, bar_y), size=(min(proj_w, bar_w), bar_h),
                             radius=[dp(4)])

            # Spent (solid)
            Color(*spent_color)
            RoundedRectangle(pos=(bar_x, bar_y), size=(min(spent_w, bar_w), bar_h),
                             radius=[dp(4)])

            # Budget marker line
            if budget_w < bar_w:
                Color(1, 1, 1, 0.7)
                Line(points=[bar_x + budget_w, bar_y - dp(2),
                             bar_x + budget_w, bar_y + bar_h + dp(2)],
                     width=dp(1.5))

            # Labels below bar
            tex_spent = _text_texture(
                f"Spent: ${self.spent:,.0f}", font_size=10,
                color=spent_color)
            Color(1, 1, 1, 1)
            Rectangle(texture=tex_spent,
                      pos=(bar_x, y + dp(8)),
                      size=tex_spent.size)

            tex_proj = _text_texture(
                f"Projected: ${self.projected:,.0f}", font_size=10,
                color=(0.6, 0.6, 0.6, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex_proj,
                      pos=(bar_x + bar_w / 2 - tex_proj.width / 2, y + dp(8)),
                      size=tex_proj.size)

            tex_bud = _text_texture(
                f"Budget: ${self.budget:,.0f}", font_size=10,
                color=(0.8, 0.8, 0.8, 1))
            Color(1, 1, 1, 1)
            Rectangle(texture=tex_bud,
                      pos=(bar_x + bar_w - tex_bud.width, y + dp(8)),
                      size=tex_bud.size)

            # Title above bar
            if self.label_text:
                tex_title = _text_texture(self.label_text, font_size=11,
                                          color=(0.85, 0.85, 0.85, 1))
                Color(1, 1, 1, 1)
                Rectangle(texture=tex_title,
                           pos=(bar_x, bar_y + bar_h + dp(6)),
                           size=tex_title.size)


# Predefined color palette for chart slices
CHART_COLORS = [
    (0.2, 0.8, 0.7, 1),   # teal
    (0.9, 0.35, 0.35, 1),  # red
    (0.3, 0.65, 0.95, 1),  # blue
    (0.95, 0.7, 0.2, 1),   # amber
    (0.6, 0.4, 0.9, 1),    # purple
    (0.3, 0.85, 0.45, 1),  # green
    (0.95, 0.5, 0.3, 1),   # orange
    (0.5, 0.8, 0.9, 1),    # light blue
    (0.85, 0.35, 0.7, 1),  # pink
    (0.7, 0.7, 0.3, 1),    # olive
]
