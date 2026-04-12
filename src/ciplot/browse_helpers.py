# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Mapping, Optional, Sequence

import copy
import dataclasses

from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.figure import Figure

from .config import (AxisCfg,
                     BackgroundImageCfg,
                     BrowsePageSettingsCfg,
                     BrowseSubplotCfg,
                     GridCfg,
                     LegendCfg,
                     MarkingObjectCfg,
                     PlotCfg)

from .serialization import _from_serialized_json
from .shared import _resolve_cfg_override
from .plotting_helpers import _plot_single_series

from .rendering import (_add_legend,
                        _apply_axis_cfg,
                        _apply_background_image,
                        _apply_grid,
                        _apply_markings,
                        _apply_partial_axis_limits)

def _resolve_browse_page_settings_cfg(page_cfg: Optional[BrowsePageSettingsCfg], markings: Optional[Sequence[MarkingObjectCfg]], background: Optional[BackgroundImageCfg], plot_cfg: PlotCfg, x_axis_cfg: AxisCfg, y_axis_cfg: AxisCfg, grid_cfg: GridCfg, legend_cfg: LegendCfg) -> BrowsePageSettingsCfg:
    """
    Resolve the effective configuration for a browse page by merging the provided page configuration with the individual configuration components, applying overrides as needed.
    """

    page_cfg = page_cfg or BrowsePageSettingsCfg()

    return BrowsePageSettingsCfg(markings = copy.deepcopy(page_cfg.markings if page_cfg.markings is not None else markings),
                                 background = _resolve_cfg_override(background, page_cfg.background, BackgroundImageCfg),

                                 plot_cfg = _resolve_cfg_override(plot_cfg, page_cfg.plot_cfg, PlotCfg),

                                 x_axis_cfg = _resolve_cfg_override(x_axis_cfg, page_cfg.x_axis_cfg, AxisCfg),
                                 y_axis_cfg = _resolve_cfg_override(y_axis_cfg, page_cfg.y_axis_cfg, AxisCfg),

                                 grid_cfg = _resolve_cfg_override(grid_cfg, page_cfg.grid_cfg, GridCfg),
                                 legend_cfg = _resolve_cfg_override(legend_cfg, page_cfg.legend_cfg, LegendCfg))

def _merge_optional_markings(base_markings: Optional[Sequence[MarkingObjectCfg]], local_markings: Optional[Sequence[MarkingObjectCfg]]) -> Optional[List[MarkingObjectCfg]]:
    """
    Merge page-level or global markings with subplot-level markings, if both are provided, by concatenating the two lists of markings.
    """

    if base_markings is None and local_markings is None:
        return None

    merged: List[MarkingObjectCfg] = []

    if base_markings is not None:
        merged.extend(copy.deepcopy(list(base_markings)))

    if local_markings is not None:
        merged.extend(copy.deepcopy(list(local_markings)))

    return merged

def _resolve_structured_subplot_cfg(page_effective_cfg: BrowsePageSettingsCfg, subplot_cfg: BrowseSubplotCfg) -> BrowsePageSettingsCfg:
    """
    Resolve the effective configuration for one structured subplot.

    The merging order is as follows: start with the page-level effective configuration (which already incorporates global defaults and page-level overrides),
    and then apply subplot-level overrides on top of that.
    """

    return BrowsePageSettingsCfg(markings = _merge_optional_markings(page_effective_cfg.markings, subplot_cfg.markings),

                                 background = _resolve_cfg_override(page_effective_cfg.background,
                                                                    subplot_cfg.background,
                                                                    BackgroundImageCfg),

                                 plot_cfg = _resolve_cfg_override(page_effective_cfg.plot_cfg,
                                                                  subplot_cfg.plot_cfg,
                                                                  PlotCfg),

                                 x_axis_cfg = _resolve_cfg_override(page_effective_cfg.x_axis_cfg,
                                                                    subplot_cfg.x_axis_cfg,
                                                                    AxisCfg),

                                 y_axis_cfg = _resolve_cfg_override(page_effective_cfg.y_axis_cfg,
                                                                    subplot_cfg.y_axis_cfg,
                                                                    AxisCfg),

                                 grid_cfg = _resolve_cfg_override(page_effective_cfg.grid_cfg,
                                                                  subplot_cfg.grid_cfg,
                                                                  GridCfg),

                                 legend_cfg = _resolve_cfg_override(page_effective_cfg.legend_cfg,
                                                                    subplot_cfg.legend_cfg,
                                                                    LegendCfg))

def _render_structured_subplot(fig: Figure,
                               ax_left: Axes,
                               subplot_cfg: BrowseSubplotCfg,
                               effective_subplot_cfg: BrowsePageSettingsCfg) -> Dict[str, Any]:
    """
    Render one structured subplot onto the provided axes.
    """

    current_markings = effective_subplot_cfg.markings
    current_background = effective_subplot_cfg.background

    current_plot_cfg = effective_subplot_cfg.plot_cfg

    current_x_axis_cfg = effective_subplot_cfg.x_axis_cfg
    current_y_axis_cfg = effective_subplot_cfg.y_axis_cfg

    current_grid_cfg = effective_subplot_cfg.grid_cfg
    current_legend_cfg = effective_subplot_cfg.legend_cfg

    visible_series = [s for s in subplot_cfg.series if s.is_visible]

    if current_plot_cfg is not None:
        if not current_plot_cfg.show_plot or not visible_series:
            ax_left.set_visible(False)

            return {"ax_left": ax_left,
                    "ax_right": None,
                    "legend": None,
                    "plotted_lines": [],
                    "visible": False,
                    "subplot_plot_cfg": current_plot_cfg,
                    "subplot_legend_cfg": current_legend_cfg}

    ax_left.set_visible(True)

    _apply_axis_cfg(ax_left, current_x_axis_cfg, which_axis = "x", default_fontsize = current_plot_cfg.base_font_size)
    _apply_axis_cfg(ax_left, current_y_axis_cfg, which_axis = "y", default_fontsize = current_plot_cfg.base_font_size)

    _apply_grid(ax_left, current_grid_cfg)

    ax_left.set_xlabel(current_x_axis_cfg.axis_label, fontsize = current_plot_cfg.base_font_size)
    ax_left.set_ylabel(current_y_axis_cfg.axis_label, fontsize = current_plot_cfg.base_font_size)

    if current_plot_cfg is not None:
        if current_plot_cfg.plot_title:
            ax_left.set_title(current_plot_cfg.plot_title, fontsize = current_plot_cfg.base_font_size)

    plotted_lines: List[Line2D] = []
    ax_right: Optional[Axes] = None

    for s in visible_series:
        which_axis = (s.plot_on_which_y_axis or "left").strip().lower()

        if which_axis == "right":
            if ax_right is None:
                ax_right = ax_left.twinx()

                ax_right.set_ylabel(current_y_axis_cfg.axis_label, fontsize = current_plot_cfg.base_font_size)
                _apply_axis_cfg(ax_right, current_y_axis_cfg, which_axis = "y", default_fontsize = current_plot_cfg.base_font_size)

            target_ax = ax_right

        else:
            target_ax = ax_left

        _plot_single_series(target_ax,
                            s,
                            plotted_lines = plotted_lines,
                            line_meta = None,
                            plot_cfg = current_plot_cfg)

    ax_left.relim()
    ax_left.autoscale_view()

    if ax_right is not None:
        ax_right.relim()
        ax_right.autoscale_view()

    _apply_background_image(ax_left, current_background)

    _apply_partial_axis_limits(ax_left, which_axis = "x", axis_cfg = current_x_axis_cfg)
    _apply_partial_axis_limits(ax_left, which_axis = "y", axis_cfg = current_y_axis_cfg)

    if ax_right is not None:
        _apply_partial_axis_limits(ax_right, which_axis = "y", axis_cfg = current_y_axis_cfg)

    _apply_markings(fig = fig, ax_left = ax_left, ax_right = ax_right, markings = current_markings)

    # Re-apply inversion after all autoscaling / markings
    if current_x_axis_cfg.invert_axis:
        ax_left.invert_xaxis()

    if current_y_axis_cfg.invert_axis:
        ax_left.invert_yaxis()

        if ax_right is not None:
            ax_right.invert_yaxis()

    legend_obj = None

    if current_legend_cfg.show_legend:
        any_label = any((s.label is not None) and (not s.label.startswith("_")) for s in visible_series)

        if any_label:
            legend_cfg_for_subplot = current_legend_cfg

            # Keep the legend's font size aligned with local subplot font size when not explicitly set
            if legend_cfg_for_subplot.legend_fontsize is None:
                legend_cfg_for_subplot = dataclasses.replace(legend_cfg_for_subplot, legend_fontsize = current_plot_cfg.base_font_size)

            legend_obj = _add_legend(ax_left, legend_cfg_for_subplot)

    return {"ax_left": ax_left,
            "ax_right": ax_right,
            "legend": legend_obj,
            "plotted_lines": plotted_lines,
            "visible": True,
            "subplot_plot_cfg": current_plot_cfg,
            "subplot_legend_cfg": current_legend_cfg}

def _restore_exported_structured_cfg_node(node: Any, expected_type: type) -> Optional[Any]:
    """
    Restore one serialized structured-export configuration node.
    """

    if node is None:
        return None

    restored = _from_serialized_json(node)

    if restored is None:
        return None

    if isinstance(restored, expected_type):
        return restored

    if isinstance(restored, Mapping):
        try:
            return expected_type(**dict(restored))

        except Exception as exc:
            raise TypeError("Failed to restore a configuration node from a mapping structure."
                            "This may be because the mapping does not have the correct fields or has invalid field names for the expected type. \n") from exc

    raise TypeError(f"Failed to restore a configuration node. Expected type {expected_type.__name__}, but got {type(restored).__name__}. \n")