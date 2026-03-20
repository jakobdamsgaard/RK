from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from tkinter import font as tkfont


@dataclass(frozen=True)
class Series:
    name: str
    points: tuple[tuple[float, float], ...]
    color: str
    width: int = 2
    dash: tuple[int, ...] = ()
    marker_radius: int = 0


@dataclass(frozen=True)
class Marker:
    label: str
    point: tuple[float, float]
    color: str
    size: int = 4


@dataclass(frozen=True)
class ChartSpec:
    title: str
    x_label: str
    y_label: str
    series: tuple[Series, ...]
    markers: tuple[Marker, ...] = ()
    note: str = ""
    slope_field_function: Callable[[float, float], float] | None = None
    x_range: tuple[float, float] | None = None
    y_range: tuple[float, float] | None = None
    show_legend: bool = True


class PlotCanvas(tk.Canvas):
    def __init__(self, master, **kwargs) -> None:
        super().__init__(
            master,
            background="#F7F9FC",
            highlightthickness=1,
            highlightbackground="#D4DAE3",
            **kwargs,
        )
        self._chart_spec: ChartSpec | None = None
        self._placeholder = "Ingen data enda."
        self._redraw_after_id: str | None = None
        self.bind("<Configure>", self._queue_redraw)

    def set_chart(self, spec: ChartSpec) -> None:
        self._chart_spec = spec
        self._queue_redraw()

    def clear(self, message: str) -> None:
        self._chart_spec = None
        self._placeholder = message
        self._queue_redraw()

    def _queue_redraw(self, *_args) -> None:
        if self._redraw_after_id is not None:
            self.after_cancel(self._redraw_after_id)
        self._redraw_after_id = self.after(10, self._redraw)

    def _redraw(self) -> None:
        self._redraw_after_id = None
        self.delete("all")

        width = max(self.winfo_width(), int(self.cget("width")))
        height = max(self.winfo_height(), int(self.cget("height")))

        if width < 160 or height < 120:
            return

        if self._chart_spec is None:
            self.create_text(
                width / 2,
                height / 2,
                text=self._placeholder,
                fill="#52616B",
                font=("Helvetica", 12),
            )
            return

        spec = self._chart_spec
        all_points = self._collect_points(spec)
        if not all_points:
            self.create_text(
                width / 2,
                height / 2,
                text="Ingen plottbare punkter i denne visningen.",
                fill="#52616B",
                font=("Helvetica", 12),
            )
            return

        plot_left = 76
        plot_top = 52
        plot_right = width - 22
        plot_bottom = height - 60

        if plot_right <= plot_left or plot_bottom <= plot_top:
            return

        x_min, x_max = self._resolve_axis_range(
            [point[0] for point in all_points],
            spec.x_range,
        )
        y_min, y_max = self._resolve_axis_range(
            [point[1] for point in all_points],
            spec.y_range,
        )

        self.create_rectangle(
            plot_left,
            plot_top,
            plot_right,
            plot_bottom,
            fill="#FFFFFF",
            outline="#D7DDE5",
        )

        self._draw_grid(
            plot_left,
            plot_top,
            plot_right,
            plot_bottom,
            x_min,
            x_max,
            y_min,
            y_max,
        )
        if spec.slope_field_function is not None:
            self._draw_slope_field(
                spec.slope_field_function,
                plot_left,
                plot_top,
                plot_right,
                plot_bottom,
                x_min,
                x_max,
                y_min,
                y_max,
            )

        def to_screen(x_value: float, y_value: float) -> tuple[float, float]:
            x_ratio = (x_value - x_min) / (x_max - x_min)
            y_ratio = (y_value - y_min) / (y_max - y_min)
            x_screen = plot_left + x_ratio * (plot_right - plot_left)
            y_screen = plot_bottom - y_ratio * (plot_bottom - plot_top)
            return (x_screen, y_screen)

        self._draw_axes(
            plot_left,
            plot_top,
            plot_right,
            plot_bottom,
            x_min,
            x_max,
            y_min,
            y_max,
            to_screen,
        )
        self._draw_series(spec.series, to_screen)
        self._draw_markers(spec.markers, to_screen)
        self._draw_labels(spec, width, plot_left, plot_top, plot_right, plot_bottom)

    def _collect_points(self, spec: ChartSpec) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        for series in spec.series:
            for point in series.points:
                if math.isfinite(point[0]) and math.isfinite(point[1]):
                    points.append(point)
        for marker in spec.markers:
            x_value, y_value = marker.point
            if math.isfinite(x_value) and math.isfinite(y_value):
                points.append(marker.point)
        return points

    def _resolve_axis_range(
        self,
        values: list[float],
        explicit_range: tuple[float, float] | None,
    ) -> tuple[float, float]:
        if explicit_range is not None:
            start, stop = explicit_range
            if start == stop:
                stop = start + 1.0
            return (start, stop)

        lower = min(values)
        upper = max(values)
        if math.isclose(lower, upper):
            padding = 1.0 if math.isclose(lower, 0.0) else abs(lower) * 0.25
            return (lower - padding, upper + padding)
        padding = (upper - lower) * 0.12
        return (lower - padding, upper + padding)

    def _draw_grid(
        self,
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        for tick_index in range(6):
            x_ratio = tick_index / 5
            y_ratio = tick_index / 5
            x_screen = plot_left + x_ratio * (plot_right - plot_left)
            y_screen = plot_bottom - y_ratio * (plot_bottom - plot_top)
            self.create_line(
                x_screen,
                plot_top,
                x_screen,
                plot_bottom,
                fill="#EFF3F8",
            )
            self.create_line(
                plot_left,
                y_screen,
                plot_right,
                y_screen,
                fill="#EFF3F8",
            )
            x_value = x_min + x_ratio * (x_max - x_min)
            y_value = y_min + y_ratio * (y_max - y_min)
            self.create_text(
                x_screen,
                plot_bottom + 18,
                text=f"{x_value:.3g}",
                fill="#62707C",
                font=("Helvetica", 10),
            )
            self.create_text(
                plot_left - 10,
                y_screen,
                text=f"{y_value:.3g}",
                fill="#62707C",
                font=("Helvetica", 10),
                anchor="e",
            )

    def _draw_slope_field(
        self,
        function,
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        x_scale = (plot_right - plot_left) / (x_max - x_min)
        y_scale = (plot_bottom - plot_top) / (y_max - y_min)

        def to_screen(x_value: float, y_value: float) -> tuple[float, float]:
            x_ratio = (x_value - x_min) / (x_max - x_min)
            y_ratio = (y_value - y_min) / (y_max - y_min)
            x_screen = plot_left + x_ratio * (plot_right - plot_left)
            y_screen = plot_bottom - y_ratio * (plot_bottom - plot_top)
            return (x_screen, y_screen)

        columns = 18
        rows = 12
        half_length_px = 10.0
        for column in range(columns):
            x_value = x_min + (column + 0.5) * (x_max - x_min) / columns
            for row in range(rows):
                y_value = y_min + (row + 0.5) * (y_max - y_min) / rows
                try:
                    slope = float(function(x_value, y_value))
                except Exception:
                    continue

                vx = x_scale
                vy = -slope * y_scale
                norm = math.hypot(vx, vy)
                if not math.isfinite(norm) or norm == 0.0:
                    dx = half_length_px
                    dy = 0.0
                else:
                    dx = half_length_px * vx / norm
                    dy = half_length_px * vy / norm
                center_x, center_y = to_screen(x_value, y_value)
                self.create_line(
                    center_x - dx,
                    center_y - dy,
                    center_x + dx,
                    center_y + dy,
                    fill="#DAE2EC",
                    width=1,
                )

    def _draw_axes(
        self,
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        to_screen,
    ) -> None:
        if x_min <= 0.0 <= x_max:
            x_screen, _ = to_screen(0.0, y_min)
            self.create_line(
                x_screen,
                plot_top,
                x_screen,
                plot_bottom,
                fill="#B8C4D3",
            )
        if y_min <= 0.0 <= y_max:
            _, y_screen = to_screen(x_min, 0.0)
            self.create_line(
                plot_left,
                y_screen,
                plot_right,
                y_screen,
                fill="#B8C4D3",
            )

    def _draw_series(self, series_list: tuple[Series, ...], to_screen) -> None:
        for series in series_list:
            filtered_points = [
                to_screen(point[0], point[1])
                for point in series.points
                if math.isfinite(point[0]) and math.isfinite(point[1])
            ]
            if not filtered_points:
                continue
            if len(filtered_points) == 1:
                x_screen, y_screen = filtered_points[0]
                radius = max(series.marker_radius, 3)
                self.create_oval(
                    x_screen - radius,
                    y_screen - radius,
                    x_screen + radius,
                    y_screen + radius,
                    fill=series.color,
                    outline=series.color,
                )
                continue

            flattened = [value for point in filtered_points for value in point]
            self.create_line(
                *flattened,
                fill=series.color,
                width=series.width,
                smooth=False,
                dash=series.dash if series.dash else None,
            )
            if series.marker_radius > 0:
                radius = series.marker_radius
                for x_screen, y_screen in filtered_points:
                    self.create_oval(
                        x_screen - radius,
                        y_screen - radius,
                        x_screen + radius,
                        y_screen + radius,
                        fill=series.color,
                        outline=series.color,
                    )

    def _draw_markers(self, markers: tuple[Marker, ...], to_screen) -> None:
        for marker in markers:
            x_value, y_value = marker.point
            if not math.isfinite(x_value) or not math.isfinite(y_value):
                continue
            x_screen, y_screen = to_screen(x_value, y_value)
            self.create_oval(
                x_screen - marker.size,
                y_screen - marker.size,
                x_screen + marker.size,
                y_screen + marker.size,
                fill=marker.color,
                outline="#FFFFFF",
                width=1,
            )
            self.create_text(
                x_screen + 9,
                y_screen - 9,
                text=marker.label,
                fill="#203040",
                anchor="sw",
                font=("Helvetica", 10, "bold"),
            )

    def _draw_labels(
        self,
        spec: ChartSpec,
        width: int,
        plot_left: int,
        plot_top: int,
        plot_right: int,
        plot_bottom: int,
    ) -> None:
        self.create_text(
            width / 2,
            24,
            text=spec.title,
            fill="#16202A",
            font=("Helvetica", 14, "bold"),
        )
        self.create_text(
            (plot_left + plot_right) / 2,
            plot_bottom + 42,
            text=spec.x_label,
            fill="#2F3D4A",
            font=("Helvetica", 11),
        )
        self.create_text(
            plot_left,
            plot_top - 28,
            text=spec.y_label,
            fill="#2F3D4A",
            font=("Helvetica", 11),
            anchor="w",
        )
        if spec.note:
            self.create_text(
                plot_left,
                plot_bottom + 22,
                text=spec.note,
                fill="#52616B",
                font=("Helvetica", 10),
                anchor="w",
            )
        if spec.show_legend:
            self._draw_legend(spec.series, plot_right - 8, plot_top + 8)

    def _draw_legend(
        self,
        series_list: tuple[Series, ...],
        right_edge: int,
        top_edge: int,
    ) -> None:
        legend_entries = [series for series in series_list if series.name]
        if not legend_entries:
            return

        font = tkfont.nametofont("TkDefaultFont")
        content_width = max(font.measure(series.name) for series in legend_entries)
        box_width = content_width + 54
        box_height = 14 + 20 * len(legend_entries)
        left_edge = right_edge - box_width
        bottom_edge = top_edge + box_height

        self.create_rectangle(
            left_edge,
            top_edge,
            right_edge,
            bottom_edge,
            fill="#FFFFFF",
            outline="#D7DDE5",
        )

        for entry_index, series in enumerate(legend_entries):
            y_position = top_edge + 14 + entry_index * 20
            self.create_line(
                left_edge + 10,
                y_position,
                left_edge + 30,
                y_position,
                fill=series.color,
                width=series.width,
                dash=series.dash if series.dash else None,
            )
            self.create_text(
                left_edge + 36,
                y_position,
                text=series.name,
                fill="#203040",
                font=font,
                anchor="w",
            )
