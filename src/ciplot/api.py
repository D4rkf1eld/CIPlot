# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Optional, Sequence

import dataclasses

import numpy as np

import matplotlib.pyplot as plt

from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.figure import Figure

from .config import (AxisCfg,
                     BackgroundImageCfg,
                     BrowsePageSettingsCfg,
                     BrowseStructuredPageCfg,
                     ExportCfg,
                     GridCfg,
                     LegendCfg,
                     MarkingObjectCfg,
                     PlotCfg,
                     SeriesCfg)

from .exporting import (_export_figure,
                        _export_multi_series_data,
                        _export_series_data,
                        _export_structured_subplot_pages_data)

from .plotting_helpers import _plot_multi_series_figure, _plot_single_series

from .browse_helpers import (_render_structured_subplot,
                             _resolve_browse_page_settings_cfg,
                             _resolve_structured_subplot_cfg)

from .styling import (_apply_dark_mode_post,
                      _apply_subplot_adjust,
                      _install_figsize_display,
                      _rcparams_from_plot_cfg,
                      _try_tint_window_background)

from .rendering import (_add_general_legend,
                        _add_legend,
                        _apply_axis_cfg,
                        _apply_background_image,
                        _apply_general_legend_reserved_space,
                        _apply_grid,
                        _apply_markings,
                        _apply_partial_axis_limits)

from .interactivity import (_install_hover_highlight,
                            _install_legend_toggle,
                            _set_all_legend_entries_visibility)

from .runtime import _close_tracked_figures, _track_figures

def plot_xy(series: Sequence[SeriesCfg],

            markings: Optional[Sequence[MarkingObjectCfg]] = None,

            background: Optional[BackgroundImageCfg] = None,

            plot_cfg: PlotCfg = PlotCfg(),

            x_axis_cfg: AxisCfg = AxisCfg(axis_label = "x"),
            y_axis_cfg: AxisCfg = AxisCfg(axis_label = "y"),

            grid_cfg: GridCfg = GridCfg(),

            legend_cfg: LegendCfg = LegendCfg(),

            export_cfg: Optional[ExportCfg] = None) -> List[Figure]:
    """
    Plot one or more series of x and y values with extensive configuration options for styling, layout, interactivity and exporting.
    """

    visible_series = [s for s in series if s.is_visible]

    if not visible_series:
        raise RuntimeError("There is no visible series to plot (all SeriesCfg.is_visible = False). \n Please set SeriesCfg.is_visible = True for at least one series to make it visible in the plot. \n")

    _close_tracked_figures("plot_xy")

    if plot_cfg.separate_figures_per_series:
        figs: List[Figure] = []

        single_plot_cfg = PlotCfg(**{**plot_cfg.__dict__, "separate_figures_per_series": False})

        if export_cfg is not None:
            if export_cfg.series_export_names is not None:
                if len(export_cfg.series_export_names) != len(visible_series):
                    raise ValueError(f"The length of series_export_names ({len(export_cfg.series_export_names)}) does not match number of visible series ({len(visible_series)}). \n Please ensure that series_export_names has the same number of entries as the number of visible series when separate_figures_per_series is True. \n")

        for i, s in enumerate(visible_series):
            per_export = None

            if export_cfg is not None:
                if export_cfg.series_export_names is not None:
                    export_name = export_cfg.series_export_names[i]

                else:
                    export_name = f"{export_cfg.export_name}_{i + 1}"

                per_export = ExportCfg(enable_export = export_cfg.enable_export,
                                       enable_data_export = export_cfg.enable_data_export,
                                       data_export_with_style = export_cfg.data_export_with_style,

                                       output_directory = export_cfg.output_directory,
                                       export_name = export_name,
                                       export_data_name = export_cfg.export_data_name,
                                       series_export_names = None,
                                       output_formats = export_cfg.output_formats,

                                       output_dpi = export_cfg.output_dpi,
                                       transparent_background = export_cfg.transparent_background,
                                       bbox_inches = export_cfg.bbox_inches)

            figs.append(_plot_multi_series_figure([s],

                                                  markings = markings,

                                                  background = background,

                                                  plot_cfg = single_plot_cfg,

                                                  x_axis_cfg = x_axis_cfg,
                                                  y_axis_cfg = y_axis_cfg,

                                                  grid_cfg = grid_cfg,

                                                  legend_cfg = legend_cfg,

                                                  export_cfg = per_export))

        _track_figures("plot_xy", figs)

        return figs

    fig = _plot_multi_series_figure(visible_series,

                                    markings = markings,

                                    background = background,

                                    plot_cfg = plot_cfg,

                                    x_axis_cfg = x_axis_cfg,
                                    y_axis_cfg = y_axis_cfg,

                                    grid_cfg = grid_cfg,

                                    legend_cfg = legend_cfg,

                                    export_cfg = export_cfg)

    if export_cfg is not None:
        if export_cfg.enable_data_export:
            _export_series_data(series, export_cfg)

    _track_figures("plot_xy", [fig])

    return [fig]

def browse_series(series: Optional[Sequence[SeriesCfg]],
                  multi_series: Optional[Sequence[Sequence[SeriesCfg]]] = None,

                  markings: Optional[Sequence[MarkingObjectCfg]] = None,

                  background: Optional[BackgroundImageCfg] = None,

                  plot_cfg: PlotCfg = PlotCfg(),

                  x_axis_cfg: AxisCfg = AxisCfg(axis_label = "x"),
                  y_axis_cfg: AxisCfg = AxisCfg(axis_label = "y"),

                  grid_cfg: GridCfg = GridCfg(),

                  legend_cfg: LegendCfg = LegendCfg(),

                  export_cfg: Optional[ExportCfg] = None,

                  browse_page_settings_cfgs: Optional[Sequence[BrowsePageSettingsCfg]] = None,

                  start_index: int = 0,
                  export_all_pages: bool = True) -> Figure:
    """
    Browse through a list of series interactively using keyboard inputs in a matplotlib pyplot window.

    - If multi_series is None, each series in the provided series list is treated as a separate page.

    - If multi_series is provided, each inner list is one page, and all visible series in that list are drawn together.

    The user can navigate through the pages using the left and right arrow keys,
    and the plot will update to show the series corresponding to the current page index.
    
    The parameter "browse_page_settings_cfgs" allows for providing a list of page-specific configuration overrides,
    which will be applied on top of the global configurations when rendering each page.
    """

    if multi_series is None:
        if series is None:
            raise ValueError("If 'multi_series' is not provided, the 'series' parameter must be provided with a list of SeriesCfg objects to browse through. \n Please provide a valid series list when 'multi_series' is None. \n")

        if export_cfg is not None and export_cfg.enable_data_export:
            _export_series_data(series, export_cfg)

        raw_pages: List[List[SeriesCfg]] = [[s] for s in series]

    else:
        if export_cfg is not None and export_cfg.enable_data_export:
            _export_multi_series_data(multi_series, export_cfg)

        raw_pages = [list(page) for page in multi_series]

    if browse_page_settings_cfgs is None:
        raw_browse_page_settings_cfgs: List[Optional[BrowsePageSettingsCfg]] = [None] * len(raw_pages)

    else:
        raw_browse_page_settings_cfgs = list(browse_page_settings_cfgs)

        if len(raw_browse_page_settings_cfgs) != len(raw_pages):
            raise ValueError(f"The number of browse_page_settings_cfgs provided ({len(raw_browse_page_settings_cfgs)}) does not match the number of pages ({len(raw_pages)}). \n Please provide one BrowsePageSettingsCfg (or None) per raw page before visibility filtering. \n")

    pages: List[List[SeriesCfg]] = []

    filtered_browse_page_settings_cfgs: List[Optional[BrowsePageSettingsCfg]] = []

    for raw_page, raw_browse_page_settings_cfg in zip(raw_pages, raw_browse_page_settings_cfgs):
        page_vis = [s for s in raw_page if s.is_visible]

        if page_vis:
            pages.append(page_vis)

            filtered_browse_page_settings_cfgs.append(raw_browse_page_settings_cfg)

    if not pages:
        if multi_series is None:
            raise RuntimeError("There is no visible series to browse (all SeriesCfg.is_visible = False). \n Please set SeriesCfg.is_visible = True for at least one series to make it visible in the browser. \n")

        raise RuntimeError("There are no visible series to browse in multi_series. \n Each page was empty after filtering SeriesCfg.is_visible. \n")

    n_pages = len(pages)

    idx = int(np.clip(start_index, 0, n_pages - 1))

    _close_tracked_figures("browse_series")

    initial_effective_cfg = _resolve_browse_page_settings_cfg(page_cfg = filtered_browse_page_settings_cfgs[idx],
                                                              markings = markings,
                                                              background = background,
                                                              plot_cfg = plot_cfg,
                                                              x_axis_cfg = x_axis_cfg,
                                                              y_axis_cfg = y_axis_cfg,
                                                              grid_cfg = grid_cfg,
                                                              legend_cfg = legend_cfg)

    initial_plot_cfg = initial_effective_cfg.plot_cfg

    fig_size = initial_plot_cfg.figure_size if initial_plot_cfg.figure_size is not None else (10, 5)

    pick_cid = {"id": None}

    hover_cid = {"id": None}

    legend_state = {"obj": None}

    figsize_display_cid = {"id": None}

    def _refresh_hover(current_plot_cfg: PlotCfg):
        """
        Refresh the hover highlight event handler by disconnecting any existing handler
        and installing a new one with the current configuration settings.
        This prevents .cla() from resetting the hover settings.
        """

        if hover_cid["id"] is not None:
            fig.canvas.mpl_disconnect(hover_cid["id"])

            hover_cid["id"] = None

        if not current_plot_cfg.enable_hover_highlight:
            return

        hover_cid["id"] = _install_hover_highlight(fig = fig,
                                                   axes = [ax],
                                                   pick_radius_px = current_plot_cfg.hover_pick_px_radius,
                                                   dim_alpha = current_plot_cfg.hover_dim_alpha,
                                                   emph_lw_scale = current_plot_cfg.hover_emphasis_linewidth_scale,
                                                   show_tooltip = current_plot_cfg.hover_show_tooltip,
                                                   plot_cfg = current_plot_cfg)

    def _refresh_figsize_display(current_plot_cfg: PlotCfg):
        """
        Reinstall the figure size overlay when page-specific PlotCfg changes.
        """

        if figsize_display_cid["id"] is not None:
            fig.canvas.mpl_disconnect(figsize_display_cid["id"])

            figsize_display_cid["id"] = None

        figsize_display_cid["id"] = _install_figsize_display(fig, current_plot_cfg)

    with plt.rc_context(_rcparams_from_plot_cfg(initial_plot_cfg)):
        fig, ax = plt.subplots(figsize = fig_size, constrained_layout = initial_plot_cfg.use_constrained_layout)

        _track_figures("browse_series", [fig])

        _try_tint_window_background(fig, initial_plot_cfg)
        _apply_dark_mode_post(fig, [ax], initial_plot_cfg)

        _apply_subplot_adjust(fig, initial_plot_cfg)

        def render(page_index: int):
            """
            Render the page_index-th page (each page may contain multiple series).
            """

            effective_cfg = _resolve_browse_page_settings_cfg(page_cfg = filtered_browse_page_settings_cfgs[page_index],
                                                              markings = markings,
                                                              background = background,
                                                              plot_cfg = plot_cfg,
                                                              x_axis_cfg = x_axis_cfg,
                                                              y_axis_cfg = y_axis_cfg,
                                                              grid_cfg = grid_cfg,
                                                              legend_cfg = legend_cfg)

            current_markings = effective_cfg.markings
            current_background = effective_cfg.background

            current_plot_cfg = effective_cfg.plot_cfg

            current_x_axis_cfg = effective_cfg.x_axis_cfg
            current_y_axis_cfg = effective_cfg.y_axis_cfg

            current_grid_cfg = effective_cfg.grid_cfg
            current_legend_cfg = effective_cfg.legend_cfg

            ax.cla()

            page_fig_size = current_plot_cfg.figure_size if current_plot_cfg.figure_size is not None else (10, 5)
            fig.set_size_inches(*page_fig_size, forward = True)

            _try_tint_window_background(fig, current_plot_cfg)

            _apply_subplot_adjust(fig, current_plot_cfg)

            _apply_axis_cfg(ax, current_x_axis_cfg, which_axis = "x", default_fontsize = current_plot_cfg.base_font_size)
            _apply_axis_cfg(ax, current_y_axis_cfg, which_axis = "y", default_fontsize = current_plot_cfg.base_font_size)

            _apply_grid(ax, current_grid_cfg)

            page_series = pages[page_index]

            plotted_lines: List[Line2D] = []

            for s in page_series:
                _plot_single_series(ax, s, plotted_lines = plotted_lines, line_meta = None, plot_cfg = current_plot_cfg)

            # Autoscale to all curves in a page
            ax.relim()
            ax.autoscale_view()

            _apply_background_image(ax, current_background)

            _apply_partial_axis_limits(ax, which_axis = "x", axis_cfg = current_x_axis_cfg)
            _apply_partial_axis_limits(ax, which_axis = "y", axis_cfg = current_y_axis_cfg)

            ax.set_xlabel(current_x_axis_cfg.axis_label, fontsize = current_plot_cfg.base_font_size)
            ax.set_ylabel(current_y_axis_cfg.axis_label, fontsize = current_plot_cfg.base_font_size)

            head = current_plot_cfg.plot_title or ""

            page_label = None

            if len(page_series) == 1:
                s0 = page_series[0]

                page_label = s0.label if (s0.label and not s0.label.startswith("_")) else None

            if current_plot_cfg.show_page_index:
                tail = f"{page_index + 1}/{n_pages}" + (f" — {page_label}" if page_label else "")

            else:
                tail = f"{page_label}" if page_label else ""

            if len(head) > 0 and len(tail) > 0:
                ax.set_title(f"{head} — {tail}")

            elif len(head) > 0 and len(tail) <= 0:
                ax.set_title(head)

            elif len(head) <= 0 and len(tail) > 0:
                ax.set_title(tail)

            else:
                ax.set_title("Plot")

            leg_obj = None

            legend_state["obj"] = None

            # Prevent, that changing pages causes multiple pick event handlers to be registered on the figure, which would lead to multiple toggles per click after browsing through several pages.
            # Before rendering a new page, check if there is an existing pick event handler registered for the legend toggle functionality (indicated by pick_cid["id"] being not None).
            # If such a handler exists, disconnect it from the figure canvas to prevent it from being triggered multiple times when clicking on legend entries after navigating through pages.
            # After disconnecting the old handler, set pick_cid["id"] back to None to indicate that there is currently no active pick event handler for the legend toggle.
            if pick_cid["id"] is not None:
                fig.canvas.mpl_disconnect(pick_cid["id"])

                pick_cid["id"] = None

            if current_legend_cfg.show_legend:
                any_label = any((s.label is not None) and (not s.label.startswith("_")) for s in page_series)

                if any_label:
                    leg_obj = _add_legend(ax, current_legend_cfg)

            legend_state["obj"] = leg_obj

            if current_legend_cfg.legend_is_clickable and leg_obj is not None:
                pick_cid["id"] = _install_legend_toggle(fig, leg_obj)

            _apply_markings(fig = fig, ax_left = ax, ax_right = None, markings = current_markings)

            # Apply axis inversion again after plotting and applying markings, so that the setting is not overridden by any of the other calls that might change the axis limits
            if current_x_axis_cfg.invert_axis:
                ax.invert_xaxis()

            if current_y_axis_cfg.invert_axis:
                ax.invert_yaxis()

            if current_plot_cfg.use_tight_layout and not current_plot_cfg.use_constrained_layout:
                fig.tight_layout()

            fig.canvas.draw_idle()

            _apply_subplot_adjust(fig, current_plot_cfg)

            _apply_dark_mode_post(fig, [ax], current_plot_cfg)

            _refresh_hover(current_plot_cfg) # Changing pages with .cla() resets the hover settings (and thus the dark mode, blinding users...), so re-apply the hover settings after rendering each page.

            _refresh_figsize_display(current_plot_cfg)

        if export_cfg is not None and export_all_pages:
            if export_cfg.series_export_names is not None and len(export_cfg.series_export_names) != n_pages:
                raise ValueError(f"The number of series export names provided ({len(export_cfg.series_export_names)}) does not match the number of pages ({n_pages}). \n Please provide a list of export names with the same length as the number of pages, or set series_export_names to None to use default naming. \n")

            for i in range(n_pages):
                render(i)

                if export_cfg.series_export_names is not None:
                    export_name = export_cfg.series_export_names[i]

                else:
                    export_name = f"{export_cfg.export_name}_{i + 1}"

                _export_figure(fig,
                               ExportCfg(enable_export = export_cfg.enable_export,
                                         enable_data_export = False, # Data export is already handled separately, so disable it for individual page exports to avoid redundant exports.
                                         data_export_with_style = False,

                                         output_directory = export_cfg.output_directory,
                                         export_name = export_name,
                                         export_data_name = None,
                                         series_export_names = None,
                                         output_formats = export_cfg.output_formats,

                                         output_dpi = export_cfg.output_dpi,
                                         transparent_background = export_cfg.transparent_background,
                                         bbox_inches = export_cfg.bbox_inches))

        render(idx)

        def clamp_wrap(j: int) -> int:
            """
            Clamp the index j to the range [0, n_pages - 1] with wrapping around, so that it cycles through the pages when navigating left or right.
            """

            return (j + n_pages) % n_pages

        def on_key(event):
            """
            Handle key press events for browsing through the series.
            """

            nonlocal idx

            k = (event.key or "").lower()

            if k in ("q", "escape"):
                plt.close(fig)

                return

            if k == "h":
                if legend_state["obj"] is not None:
                    _set_all_legend_entries_visibility(fig, legend_state["obj"], visible = False)

                return

            if k == "u":
                if legend_state["obj"] is not None:
                    _set_all_legend_entries_visibility(fig, legend_state["obj"], visible = True)

                return

            if k in ("right", "d", "k"):
                idx = clamp_wrap(idx + 1)

                render(idx)

                return

            if k in ("left", "a", "j"):
                idx = clamp_wrap(idx - 1)

                render(idx)

                return

            if k == "home":
                idx = 0

                render(idx)

                return

            if k == "end":
                idx = n_pages - 1

                render(idx)

                return

        fig.canvas.mpl_connect("key_press_event", on_key)

        if initial_plot_cfg.show_plot:
            plt.show()

        return fig

def browse_structured_subplot_pages(structured_pages: Sequence[BrowseStructuredPageCfg],

                                    markings: Optional[Sequence[MarkingObjectCfg]] = None,

                                    background: Optional[BackgroundImageCfg] = None,

                                    plot_cfg: PlotCfg = PlotCfg(),

                                    x_axis_cfg: AxisCfg = AxisCfg(axis_label = "x"),
                                    y_axis_cfg: AxisCfg = AxisCfg(axis_label = "y"),

                                    grid_cfg: GridCfg = GridCfg(),

                                    legend_cfg: LegendCfg = LegendCfg(),

                                    export_cfg: Optional[ExportCfg] = None,

                                    start_index: int = 0,
                                    export_all_pages: bool = True) -> Figure:
    """
    Browse a sequence of structured multi-subplot pages interactively.
    """

    if not structured_pages:
        raise ValueError("The 'structured_pages' argument cannot be empty. Please provide at least one BrowseStructuredPageCfg. \n")

    visible_pages: List[BrowseStructuredPageCfg] = []

    for page in structured_pages:
        page_has_visible_series = any(any(s.is_visible for s in subplot_cfg.series) for row in page.rows for subplot_cfg in row)

        if page_has_visible_series:
            visible_pages.append(page)

    if not visible_pages:
        raise RuntimeError("There are no visible structured pages to browse. Every page was empty after filtering SeriesCfg.is_visible and show_subplot. \n")

    if export_cfg is not None and export_cfg.enable_data_export:
        _export_structured_subplot_pages_data(visible_pages, export_cfg)

    n_pages = len(visible_pages)

    idx = int(np.clip(start_index, 0, n_pages - 1))

    _close_tracked_figures("browse_structured_subplot_pages")

    initial_page_effective_cfg = _resolve_browse_page_settings_cfg(page_cfg = visible_pages[idx].page_settings_cfg,

                                                                   markings = markings,
                                                                   background = background,

                                                                   plot_cfg = plot_cfg,

                                                                   x_axis_cfg = x_axis_cfg,
                                                                   y_axis_cfg = y_axis_cfg,

                                                                   grid_cfg = grid_cfg,
                                                                   legend_cfg = legend_cfg)

    initial_plot_cfg = initial_page_effective_cfg.plot_cfg

    initial_fig_size = initial_plot_cfg.figure_size if initial_plot_cfg.figure_size is not None else (10, 5)

    pick_cids: List[int] = []
    hover_cids: List[int] = []

    legend_state: Dict[str, List[Any]] = {"objects": []}
    figsize_display_cid: Dict[str, Optional[int]] = {"id": None}

    def _refresh_figsize_display(current_plot_cfg: PlotCfg):
        """
        Reinstall the figure size overlay when page-specific PlotCfg changes.
        """

        if figsize_display_cid["id"] is not None:
            fig.canvas.mpl_disconnect(figsize_display_cid["id"])

            figsize_display_cid["id"] = None

        figsize_display_cid["id"] = _install_figsize_display(fig, current_plot_cfg)

    with plt.rc_context(_rcparams_from_plot_cfg(initial_plot_cfg)):
        fig = plt.figure(figsize = initial_fig_size, constrained_layout = initial_plot_cfg.use_constrained_layout)

        _track_figures("browse_structured_subplot_pages", [fig])

        _try_tint_window_background(fig, initial_plot_cfg)

        def render(page_index: int):
            nonlocal pick_cids, hover_cids

            current_page_cfg = visible_pages[page_index]

            effective_page_cfg = _resolve_browse_page_settings_cfg(page_cfg = current_page_cfg.page_settings_cfg,

                                                                   markings = markings,
                                                                   background = background,

                                                                   plot_cfg = plot_cfg,

                                                                   x_axis_cfg = x_axis_cfg,
                                                                   y_axis_cfg = y_axis_cfg,

                                                                   grid_cfg = grid_cfg,
                                                                   legend_cfg = legend_cfg)

            current_page_plot_cfg = effective_page_cfg.plot_cfg
            current_page_legend_cfg = effective_page_cfg.legend_cfg

            for cid in pick_cids:
                if cid is None:
                    continue

                try:
                    fig.canvas.mpl_disconnect(cid)

                except Exception:
                    pass

            for cid in hover_cids:
                if cid is None:
                    continue

                try:
                    fig.canvas.mpl_disconnect(cid)

                except Exception:
                    pass

            pick_cids = []
            hover_cids = []

            legend_state["objects"] = []

            fig.clf()

            try:
                fig.set_constrained_layout(current_page_plot_cfg.use_constrained_layout)

            except Exception:
                pass

            page_fig_size = current_page_plot_cfg.figure_size if current_page_plot_cfg.figure_size is not None else (10, 5)
            fig.set_size_inches(*page_fig_size, forward = True)

            _try_tint_window_background(fig, current_page_plot_cfg)

            _apply_subplot_adjust(fig, current_page_plot_cfg)

            n_rows = max(1, len(current_page_cfg.rows))
            max_cols = max((len(row) for row in current_page_cfg.rows), default = 1)

            axes_grid = fig.subplots(n_rows, max_cols, squeeze = False)

            all_axes_for_dark_mode: List[Axes] = []

            for row_index in range(n_rows):
                row = current_page_cfg.rows[row_index] if row_index < len(current_page_cfg.rows) else []

                for col_index in range(max_cols):
                    ax_left = axes_grid[row_index][col_index]

                    if col_index >= len(row):
                        ax_left.set_visible(False)

                        continue

                    subplot_cfg = row[col_index]

                    effective_subplot_cfg = _resolve_structured_subplot_cfg(page_effective_cfg = effective_page_cfg, subplot_cfg = subplot_cfg)

                    if current_page_legend_cfg.general_legend_show and current_page_legend_cfg.general_legend_hide_subplot_legends:
                        effective_subplot_cfg = dataclasses.replace(effective_subplot_cfg,
                                                                    legend_cfg = dataclasses.replace(effective_subplot_cfg.legend_cfg, show_legend = False))

                    rendered = _render_structured_subplot(fig = fig,
                                                          ax_left = ax_left,
                                                          subplot_cfg = subplot_cfg,
                                                          effective_subplot_cfg = effective_subplot_cfg)

                    if not rendered["visible"]:
                        continue

                    subplot_axes = [rendered["ax_left"]] + ([rendered["ax_right"]] if rendered["ax_right"] is not None else [])

                    all_axes_for_dark_mode.extend(subplot_axes)

                    legend_obj = rendered["legend"]
                    plotted_lines = rendered["plotted_lines"]

                    subplot_plot_cfg = rendered["subplot_plot_cfg"]
                    subplot_legend_cfg = rendered["subplot_legend_cfg"]

                    if legend_obj is not None:
                        legend_state["objects"].append(legend_obj)

                    if subplot_legend_cfg.legend_is_clickable and legend_obj is not None:
                        pick_cids.append(_install_legend_toggle(fig, legend_obj))

                    if subplot_plot_cfg.enable_hover_highlight and plotted_lines:
                        hover_cids.append(_install_hover_highlight(fig = fig,
                                                                   axes = subplot_axes,
                                                                   pick_radius_px = subplot_plot_cfg.hover_pick_px_radius,
                                                                   dim_alpha = subplot_plot_cfg.hover_dim_alpha,
                                                                   emph_lw_scale = subplot_plot_cfg.hover_emphasis_linewidth_scale,
                                                                   show_tooltip = subplot_plot_cfg.hover_show_tooltip,
                                                                   plot_cfg = subplot_plot_cfg))

            page_title = "Plot"

            page_label = current_page_cfg.page_title or ""

            if current_page_plot_cfg.show_page_index:
                page_title = f"{page_index + 1}/{n_pages}" + (f" — {page_label}" if page_label else "")

            elif page_label:
                page_title = page_label

            if page_title:
                fig.suptitle(page_title, fontsize = current_page_plot_cfg.base_font_size + 1)

            if current_page_plot_cfg.use_tight_layout and not current_page_plot_cfg.use_constrained_layout:
                if page_title:
                    fig.tight_layout(rect = (0.0, 0.0, 1.0, 0.96))

                else:
                    fig.tight_layout()

            _apply_subplot_adjust(fig, current_page_plot_cfg)

            if current_page_legend_cfg.general_legend_show:
                _apply_general_legend_reserved_space(fig, current_page_legend_cfg)

                general_legend_obj = _add_general_legend(fig = fig,
                                                         axes_grid = axes_grid,
                                                         axes = all_axes_for_dark_mode,
                                                         legend_cfg = current_page_legend_cfg,
                                                         default_fontsize = current_page_plot_cfg.base_font_size)

                if general_legend_obj is not None:
                    legend_state["objects"].append(general_legend_obj)

                    if current_page_legend_cfg.legend_is_clickable:
                        pick_cids.append(_install_legend_toggle(fig, general_legend_obj))

            _apply_dark_mode_post(fig, all_axes_for_dark_mode, current_page_plot_cfg)

            _refresh_figsize_display(current_page_plot_cfg)

            fig.canvas.draw_idle()

        if export_cfg is not None and export_all_pages:
            if export_cfg.series_export_names is not None and len(export_cfg.series_export_names) != n_pages:
                raise ValueError(f"The number of series_export_names provided ({len(export_cfg.series_export_names)}) does not match the number of visible structured pages ({n_pages}). \n")

            for i in range(n_pages):
                render(i)

                if export_cfg.series_export_names is not None:
                    export_name = export_cfg.series_export_names[i]

                else:
                    base_export_name = export_cfg.export_name if export_cfg.export_name else "plot"
                    export_name = f"{base_export_name}_{i + 1}"

                _export_figure(fig,
                               ExportCfg(enable_export = export_cfg.enable_export,
                                         enable_data_export = False,
                                         data_export_with_style = False,

                                         output_directory = export_cfg.output_directory,
                                         export_name = export_name,
                                         export_data_name = export_cfg.export_data_name if export_cfg.export_data_name else "data",
                                         series_export_names = None,
                                         output_formats = export_cfg.output_formats,

                                         output_dpi = export_cfg.output_dpi,
                                         transparent_background = export_cfg.transparent_background,
                                         bbox_inches = export_cfg.bbox_inches))

        render(idx)

        def clamp_wrap(j: int) -> int:
            """
            Clamp the index j to the range [0, n_pages - 1] with wrapping around, so that it cycles through the pages when navigating left or right.
            """

            return (j + n_pages) % n_pages

        def on_key(event):
            nonlocal idx

            k = (event.key or "").lower()

            if k in ("q", "escape"):
                plt.close(fig)

                return

            if k == "h":
                for legend_obj in legend_state["objects"]:
                    _set_all_legend_entries_visibility(fig, legend_obj, visible = False)

                return

            if k == "u":
                for legend_obj in legend_state["objects"]:
                    _set_all_legend_entries_visibility(fig, legend_obj, visible = True)

                return

            if k in ("right", "d", "k"):
                idx = clamp_wrap(idx + 1)

                render(idx)

                return

            if k in ("left", "a", "j"):
                idx = clamp_wrap(idx - 1)

                render(idx)

                return

            if k == "home":
                idx = 0

                render(idx)

                return

            if k == "end":
                idx = n_pages - 1

                render(idx)

                return

        fig.canvas.mpl_connect("key_press_event", on_key)

        if initial_plot_cfg.show_plot:
            plt.show()

        return fig