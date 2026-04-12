# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import matplotlib.pyplot as plt

from matplotlib import patches
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.figure import Figure

from .config import (AxisCfg,
                     BackgroundImageCfg,
                     DistributionPlotCfg,
                     ExportCfg,
                     GridCfg,
                     HeatmapPlotCfg,
                     LegendCfg,
                     MarkingObjectCfg,
                     PlotCfg,
                     SeriesCfg)

from .exporting import _export_figure

from .interactivity import (_capture_line_state,
                            _install_hover_highlight,
                            _install_legend_hide_unhide_all_keys,
                            _install_legend_toggle)

from .rendering import (_add_legend,
                        _apply_axis_cfg,
                        _apply_background_image,
                        _apply_grid,
                        _apply_markings,
                        _apply_partial_axis_limits)

from .styling import (_apply_dark_mode_post,
                      _flip_black_to_white_in_style,
                      _install_figsize_display,
                      _rcparams_from_plot_cfg,
                      _style_colorbar_for_plot_cfg,
                      _try_tint_window_background)

def _plot_multi_series_figure(series: Sequence[SeriesCfg],

                              markings: Optional[Sequence[MarkingObjectCfg]],

                              background: Optional[BackgroundImageCfg],

                              plot_cfg: PlotCfg,

                              x_axis_cfg: AxisCfg,
                              y_axis_cfg: AxisCfg,

                              grid_cfg: GridCfg,

                              legend_cfg: LegendCfg,

                              export_cfg: Optional[ExportCfg]) -> Figure:
    """
    Internal helper to plot multiple series on the same figure with shared axes, grids and legend.
    """

    fig_size = plot_cfg.figure_size if plot_cfg.figure_size is not None else (10, 5)

    with plt.rc_context(_rcparams_from_plot_cfg(plot_cfg)):
        fig, ax_left = plt.subplots(figsize = fig_size, constrained_layout = plot_cfg.use_constrained_layout)

        if plot_cfg.bottom_margin is not None:
            fig.subplots_adjust(bottom = plot_cfg.bottom_margin)

        if plot_cfg.plot_title:
            ax_left.set_title(plot_cfg.plot_title)

        _try_tint_window_background(fig, plot_cfg)

        ax_left.set_xlabel(x_axis_cfg.axis_label, fontsize = plot_cfg.base_font_size)
        ax_left.set_ylabel(y_axis_cfg.axis_label, fontsize = plot_cfg.base_font_size)

        _apply_axis_cfg(ax_left, x_axis_cfg, which_axis = "x", default_fontsize = plot_cfg.base_font_size)
        _apply_axis_cfg(ax_left, y_axis_cfg, which_axis = "y", default_fontsize = plot_cfg.base_font_size)

        _apply_grid(ax_left, grid_cfg)

        ax_right: Optional[Axes] = None

        plotted_lines: List[Line2D] = []
        line_meta: Dict[Line2D, Dict[str, Any]] = {}

        for s in series:
            if not s.is_visible:
                continue

            which_axis = (s.plot_on_which_y_axis or "left").strip().lower()

            if which_axis == "right":
                if ax_right is None:
                    ax_right = ax_left.twinx()

                    # Mirror the x-axis configuration on the right axis
                    ax_right.set_ylabel(y_axis_cfg.axis_label, fontsize = plot_cfg.base_font_size)

                    _apply_axis_cfg(ax_right, y_axis_cfg, which_axis = "y", default_fontsize = plot_cfg.base_font_size)

                ax = ax_right

            else:
                ax = ax_left

            _plot_single_series(ax, s, plotted_lines = plotted_lines, line_meta = line_meta, plot_cfg = plot_cfg)

            _apply_background_image(ax_left, background)

            _apply_partial_axis_limits(ax, which_axis = "x", axis_cfg = x_axis_cfg)
            _apply_partial_axis_limits(ax, which_axis = "y", axis_cfg = y_axis_cfg)

            if ax_right is not None:
                _apply_partial_axis_limits(ax, which_axis = "y", axis_cfg = y_axis_cfg)

        _apply_markings(fig, ax_left, ax_right, markings)

        # Apply axis inversion again after plotting and applying markings, so that the setting is not overridden by any of the other calls that might change the axis limits
        if x_axis_cfg.invert_axis:
            ax_left.invert_xaxis()

        if y_axis_cfg.invert_axis:
            ax_left.invert_yaxis()

            if ax_right is not None:
                ax_right.invert_yaxis()

        leg_obj = None

        if legend_cfg.show_legend:
            leg_obj = _add_legend(ax_left, legend_cfg)

        if legend_cfg.legend_is_clickable and leg_obj is not None:
            _install_legend_toggle(fig, leg_obj)

        if leg_obj is not None:
            _install_legend_hide_unhide_all_keys(fig, leg_obj)

        if plot_cfg.enable_hover_highlight and plotted_lines:
            _install_hover_highlight(fig = fig,
                                     axes = [ax_left] + ([ax_right] if ax_right is not None else []),
                                     pick_radius_px = plot_cfg.hover_pick_px_radius,
                                     dim_alpha = plot_cfg.hover_dim_alpha,
                                     emph_lw_scale = plot_cfg.hover_emphasis_linewidth_scale,
                                     show_tooltip = plot_cfg.hover_show_tooltip,
                                     plot_cfg = plot_cfg)

        if plot_cfg.use_tight_layout and not plot_cfg.use_constrained_layout:
            fig.tight_layout()

        _apply_dark_mode_post(fig, [ax_left] + ([ax_right] if ax_right is not None else []), plot_cfg)

        if export_cfg is not None:
            _export_figure(fig, export_cfg)

        _install_figsize_display(fig, plot_cfg)

        if plot_cfg.show_plot:
            plt.show()

        return fig

def _infer_stacked_bar_bottom(ax: Axes, x_values: np.ndarray, y_values: np.ndarray) -> np.ndarray:
    """
    Infer automatic bottom values for a stacked bar series by inspecting already-existing
    bar containers on the same axes.

    Positive values are stacked on top of the highest existing positive bar at the same x position,
    while negative values are stacked below the lowest existing negative bar at the same x position.
    """

    x_arr = np.asarray(x_values, dtype = float)
    y_arr = np.asarray(y_values, dtype = float)

    positive_bottoms = np.zeros_like(y_arr, dtype = float)
    negative_bottoms = np.zeros_like(y_arr, dtype = float)

    for cont in getattr(ax, "containers", []):
        cont_patches = getattr(cont, "patches", None)

        if not cont_patches:
            continue

        for patch in cont_patches:
            if patch is getattr(ax, "patch", None):
                continue

            if not isinstance(patch, patches.Rectangle):
                continue

            center_x = float(patch.get_x()) + float(patch.get_width()) / 2.0

            patch_y0 = float(patch.get_y())
            patch_y1 = patch_y0 + float(patch.get_height())

            patch_positive_top = max(patch_y0, patch_y1)
            patch_negative_bottom = min(patch_y0, patch_y1)

            matching_x_mask = np.isclose(x_arr, center_x, rtol = 0.0, atol = 1e-12)

            if not np.any(matching_x_mask):
                continue

            positive_bottoms[matching_x_mask] = np.maximum(positive_bottoms[matching_x_mask], patch_positive_top)
            negative_bottoms[matching_x_mask] = np.minimum(negative_bottoms[matching_x_mask], patch_negative_bottom)

    return np.where(y_arr >= 0.0, positive_bottoms, negative_bottoms)

def _distribution_cfg_from_series(series: SeriesCfg, plotting_kind: str) -> DistributionPlotCfg:
    """
    Resolve and validate the distribution-style payload for one series.
    """

    if series.distribution_plot_cfg is not None:
        return series.distribution_plot_cfg

    raise ValueError(f"The plotting kind '{plotting_kind}' requires SeriesCfg.distribution_plot_cfg to be provided. \n Please attach a valid DistributionPlotCfg containing the sample values for this series. \n")

def _heatmap_cfg_from_series(series: SeriesCfg, plotting_kind: str) -> HeatmapPlotCfg:
    """
    Resolve and validate the heatmap-style payload for one series.
    """

    if series.heatmap_plot_cfg is not None:
        return series.heatmap_plot_cfg

    raise ValueError(f"The plotting kind '{plotting_kind}' requires SeriesCfg.heatmap_plot_cfg to be provided. \n Please attach a valid HeatmapPlotCfg containing the matrix values for this series. \n")

def _extract_line_like_xy(series: SeriesCfg, plotting_kind: str) -> Tuple[np.ndarray, np.ndarray]:
    """
    Resolve and validate x/y values for line-like and bar-like plotting kinds.
    """

    if series.x_values is None or series.y_values is None:
        raise ValueError(f"The plotting kind '{plotting_kind}' requires both SeriesCfg.x_values and SeriesCfg.y_values to be provided. \n Please supply valid x/y values for this series. \n")

    return np.asarray(series.x_values), np.asarray(series.y_values)

def _style_boxplot_artists(boxplot_result: Dict[str, Any], style: Dict[str, Any], distribution_cfg: DistributionPlotCfg, label: Optional[str]) -> Any:
    """
    Apply CIPlot's generic plotting_style dictionary to a matplotlib boxplot result.
    """

    color = style.get("color")
    edgecolor = style.get("edgecolor", style.get("ec", color))
    facecolor = style.get("facecolor", style.get("fc", color))
    alpha = style.get("alpha")
    linewidth = style.get("linewidth", style.get("lw"))
    linestyle = style.get("linestyle", style.get("ls"))
    zorder = style.get("zorder")

    boxprops_override = dict(style.get("boxprops", {}))
    whiskerprops_override = dict(style.get("whiskerprops", {}))
    capprops_override = dict(style.get("capprops", {}))
    medianprops_override = dict(style.get("medianprops", {}))
    meanprops_override = dict(style.get("meanprops", {}))
    flierprops_override = dict(style.get("flierprops", {}))

    if distribution_cfg.boxplot_patch_artist:
        if facecolor is not None:
            boxprops_override.setdefault("facecolor", facecolor)

        if edgecolor is not None:
            boxprops_override.setdefault("edgecolor", edgecolor)

    elif color is not None:
        boxprops_override.setdefault("color", color)

    if linewidth is not None:
        boxprops_override.setdefault("linewidth", linewidth)
        whiskerprops_override.setdefault("linewidth", linewidth)
        capprops_override.setdefault("linewidth", linewidth)
        medianprops_override.setdefault("linewidth", linewidth)
        meanprops_override.setdefault("linewidth", linewidth)

    if linestyle is not None:
        boxprops_override.setdefault("linestyle", linestyle)
        whiskerprops_override.setdefault("linestyle", linestyle)
        capprops_override.setdefault("linestyle", linestyle)

    if edgecolor is not None:
        whiskerprops_override.setdefault("color", edgecolor)
        capprops_override.setdefault("color", edgecolor)
        medianprops_override.setdefault("color", edgecolor)
        meanprops_override.setdefault("color", edgecolor)
        flierprops_override.setdefault("markeredgecolor", edgecolor)

    if facecolor is not None:
        flierprops_override.setdefault("markerfacecolor", facecolor)

    representative_artist = None

    for box in boxplot_result.get("boxes", []):
        for prop_name, prop_value in boxprops_override.items():
            try:
                setter = getattr(box, f"set_{prop_name}")
                setter(prop_value)

            except Exception:
                pass

        if alpha is not None:
            try:
                box.set_alpha(alpha)

            except Exception:
                pass

        if zorder is not None:
            try:
                box.set_zorder(zorder)

            except Exception:
                pass

        if representative_artist is None:
            representative_artist = box

    for key, override in (("whiskers", whiskerprops_override), ("caps", capprops_override), ("medians", medianprops_override), ("means", meanprops_override), ("fliers", flierprops_override)):
        for artist in boxplot_result.get(key, []):
            for prop_name, prop_value in override.items():
                try:
                    setter = getattr(artist, f"set_{prop_name}")
                    setter(prop_value)

                except Exception:
                    pass

            if alpha is not None:
                try:
                    artist.set_alpha(alpha)

                except Exception:
                    pass

            if zorder is not None:
                try:
                    artist.set_zorder(zorder)

                except Exception:
                    pass

            if representative_artist is None:
                representative_artist = artist

    if representative_artist is None:
        for key in ("medians", "boxes", "means", "whiskers", "caps", "fliers"):
            artists = boxplot_result.get(key, [])

            if artists:
                representative_artist = artists[0]

                break

    if representative_artist is not None and label is not None:
        try:
            representative_artist.set_label(label)

        except Exception:
            pass

    return representative_artist

def _style_violin_artists(violin_result: Dict[str, Any], style: Dict[str, Any], label: Optional[str]) -> Any:
    """
    Apply CIPlot's generic plotting_style dictionary to a matplotlib violin plot result.
    """

    color = style.get("color")
    edgecolor = style.get("edgecolor", style.get("ec", color))
    facecolor = style.get("facecolor", style.get("fc", color))
    alpha = style.get("alpha")
    linewidth = style.get("linewidth", style.get("lw"))
    linestyle = style.get("linestyle", style.get("ls"))
    zorder = style.get("zorder")

    body_style = dict(style.get("body_style", {}))
    extrema_style = dict(style.get("extrema_style", {}))
    median_style = dict(style.get("median_style", {}))
    mean_style = dict(style.get("mean_style", {}))
    bar_style = dict(style.get("bar_style", {}))

    if facecolor is not None:
        body_style.setdefault("facecolor", facecolor)

    if edgecolor is not None:
        body_style.setdefault("edgecolor", edgecolor)
        extrema_style.setdefault("color", edgecolor)
        median_style.setdefault("color", edgecolor)
        mean_style.setdefault("color", edgecolor)
        bar_style.setdefault("color", edgecolor)

    if linewidth is not None:
        body_style.setdefault("linewidth", linewidth)
        extrema_style.setdefault("linewidth", linewidth)
        median_style.setdefault("linewidth", linewidth)
        mean_style.setdefault("linewidth", linewidth)
        bar_style.setdefault("linewidth", linewidth)

    if linestyle is not None:
        body_style.setdefault("linestyle", linestyle)
        extrema_style.setdefault("linestyle", linestyle)
        median_style.setdefault("linestyle", linestyle)
        mean_style.setdefault("linestyle", linestyle)
        bar_style.setdefault("linestyle", linestyle)

    representative_artist = None

    for body in violin_result.get("bodies", []):
        for prop_name, prop_value in body_style.items():
            try:
                setter = getattr(body, f"set_{prop_name}")
                setter(prop_value)

            except Exception:
                pass

        if alpha is not None:
            try:
                body.set_alpha(alpha)

            except Exception:
                pass

        if zorder is not None:
            try:
                body.set_zorder(zorder)

            except Exception:
                pass

        if representative_artist is None:
            representative_artist = body

    for key, override in (("cmins", extrema_style), ("cmaxes", extrema_style), ("cbars", bar_style), ("cmedians", median_style), ("cmeans", mean_style)):
        artist = violin_result.get(key)

        if artist is None:
            continue

        for prop_name, prop_value in override.items():
            try:
                setter = getattr(artist, f"set_{prop_name}")
                setter(prop_value)

            except Exception:
                pass

        if alpha is not None:
            try:
                artist.set_alpha(alpha)

            except Exception:
                pass

        if zorder is not None:
            try:
                artist.set_zorder(zorder)

            except Exception:
                pass

    if representative_artist is not None and label is not None:
        try:
            representative_artist.set_label(label)

        except Exception:
            pass

    return representative_artist

def _plot_single_series(ax: Axes, series: SeriesCfg, plotted_lines: Optional[List[Line2D]], line_meta: Optional[Dict[Line2D, Dict[str, Any]]], plot_cfg: Optional[PlotCfg]):
    """
    Plot a single data series on the given axes according to the provided configuration.

    Supported plotting kinds include regular line-based plots, bar-based plots, distribution-style plots and matrix-style heatmaps.
    """

    label = series.label

    style = dict(series.plotting_style)

    kind = (series.plotting_kind or "line").lower().strip()

    if plot_cfg is not None:
        style = _flip_black_to_white_in_style(style, plot_cfg)

    if kind in ("boxplot", "box"):
        distribution_cfg = _distribution_cfg_from_series(series, kind)
        samples = np.asarray(distribution_cfg.distribution_values, dtype = float).ravel()

        positions = None if distribution_cfg.distribution_position is None else [float(distribution_cfg.distribution_position)]
        widths = distribution_cfg.distribution_width

        if widths is None:
            widths = style.pop("width", None)

        boxplot_kwargs: Dict[str, Any] = dict(patch_artist = distribution_cfg.boxplot_patch_artist,
                                              notch = distribution_cfg.boxplot_notch,
                                              showfliers = distribution_cfg.boxplot_showfliers,
                                              showmeans = distribution_cfg.boxplot_showmeans,
                                              meanline = distribution_cfg.boxplot_meanline,
                                              whis = distribution_cfg.boxplot_whis,
                                              autorange = distribution_cfg.boxplot_autorange,
                                              showcaps = distribution_cfg.boxplot_showcaps,
                                              showbox = distribution_cfg.boxplot_showbox,
                                              manage_ticks = distribution_cfg.distribution_manage_ticks)

        if positions is not None:
            boxplot_kwargs["positions"] = positions

        if widths is not None:
            boxplot_kwargs["widths"] = widths

        boxplot_result = ax.boxplot(samples, **boxplot_kwargs)

        _style_boxplot_artists(boxplot_result, style, distribution_cfg, label)

        return

    if kind in ("violin", "violinplot"):
        distribution_cfg = _distribution_cfg_from_series(series, kind)
        samples = np.asarray(distribution_cfg.distribution_values, dtype = float).ravel()

        positions = None if distribution_cfg.distribution_position is None else [float(distribution_cfg.distribution_position)]
        widths = distribution_cfg.distribution_width

        if widths is None:
            widths = style.pop("width", None)

        quantiles = None

        if distribution_cfg.distribution_quantiles is not None:
            quantiles = [list(distribution_cfg.distribution_quantiles)]

        violin_kwargs: Dict[str, Any] = dict(showmeans = distribution_cfg.violin_showmeans,
                                             showmedians = distribution_cfg.violin_showmedians,
                                             showextrema = distribution_cfg.violin_showextrema,
                                             points = distribution_cfg.violin_points)

        if positions is not None:
            violin_kwargs["positions"] = positions

        if widths is not None:
            violin_kwargs["widths"] = widths

        if distribution_cfg.violin_bandwidth_method is not None:
            violin_kwargs["bw_method"] = distribution_cfg.violin_bandwidth_method

        if quantiles is not None:
            violin_kwargs["quantiles"] = quantiles

        violin_result = ax.violinplot(samples, **violin_kwargs)

        _style_violin_artists(violin_result, style, label)

        return

    if kind in ("heatmap", "imshow"):
        heatmap_cfg = _heatmap_cfg_from_series(series, kind)
        matrix = np.asarray(heatmap_cfg.heatmap_values, dtype = float)

        if matrix.ndim != 2:
            raise ValueError(f"The plotting kind '{kind}' requires HeatmapPlotCfg.heatmap_values to be a two-dimensional matrix. \n Please provide a valid 2D array-like object for this series. \n")

        interpolation = style.pop("interpolation", heatmap_cfg.heatmap_interpolation)
        cmap = style.pop("cmap", heatmap_cfg.heatmap_colormap)
        vmin = style.pop("vmin", heatmap_cfg.heatmap_vmin)
        vmax = style.pop("vmax", heatmap_cfg.heatmap_vmax)
        alpha = style.pop("alpha", heatmap_cfg.heatmap_alpha)
        aspect = style.pop("aspect", heatmap_cfg.heatmap_aspect)
        origin = style.pop("origin", heatmap_cfg.heatmap_origin)
        extent = style.pop("extent", heatmap_cfg.heatmap_extent)

        heatmap_kwargs: Dict[str, Any] = dict(origin = origin, interpolation = interpolation)

        if cmap is not None:
            heatmap_kwargs["cmap"] = cmap

        if vmin is not None:
            heatmap_kwargs["vmin"] = vmin

        if vmax is not None:
            heatmap_kwargs["vmax"] = vmax

        if alpha is not None:
            heatmap_kwargs["alpha"] = alpha

        if extent is not None:
            heatmap_kwargs["extent"] = extent

        image = ax.imshow(matrix, **heatmap_kwargs, **style)

        try:
            ax.set_aspect(aspect)

        except Exception:
            pass

        if label is not None:
            try:
                image.set_label(label)

            except Exception:
                pass

        if heatmap_cfg.heatmap_show_colorbar:
            colorbar_kwargs = dict(heatmap_cfg.heatmap_colorbar_style)

            if heatmap_cfg.heatmap_colorbar_orientation is not None:
                colorbar_kwargs.setdefault("orientation", heatmap_cfg.heatmap_colorbar_orientation)

            if heatmap_cfg.heatmap_colorbar_shrink is not None:
                colorbar_kwargs.setdefault("shrink", heatmap_cfg.heatmap_colorbar_shrink)

            if heatmap_cfg.heatmap_colorbar_pad is not None:
                colorbar_kwargs.setdefault("pad", heatmap_cfg.heatmap_colorbar_pad)

            colorbar_obj = ax.figure.colorbar(image, ax = ax, **colorbar_kwargs)

            if heatmap_cfg.heatmap_colorbar_label is not None:
                try:
                    colorbar_obj.set_label(heatmap_cfg.heatmap_colorbar_label)

                except Exception:
                    pass

            _style_colorbar_for_plot_cfg(colorbar_obj, plot_cfg)

        return

    x, y = _extract_line_like_xy(series, kind)

    # Apply the confidence band if provided (drawn before the main line so it appears behind it)
    if series.confidence_band_values is not None:
        y_lo = np.asarray(series.confidence_band_values[0])
        y_hi = np.asarray(series.confidence_band_values[1])

        band_style: Dict[str, Any] = {"alpha": 0.15}

        if "color" in style:
            band_style["color"] = style["color"]

        if "zorder" in style:
            band_style["zorder"] = style["zorder"]

        ax.fill_between(x, y_lo, y_hi, **band_style)

    if kind == "scatter":
        ax.scatter(x, y, label = label, **style)

        return

    if kind in ("bar", "bars", "grouped_bar", "grouped_bars"):
        x_offset = style.pop("x_offset", style.pop("bar_offset", 0.0))
        bar_x = np.asarray(x, dtype = float) + float(x_offset)

        ax.bar(bar_x,
               y,
               label = label,
               xerr = series.xerr_values,
               yerr = series.yerr_values,
               **style)

        return

    if kind in ("stacked_bar", "stacked_bars", "bar_stacked"):
        x_offset = style.pop("x_offset", style.pop("bar_offset", 0.0))
        bar_x = np.asarray(x, dtype = float) + float(x_offset)

        bottom = style.pop("bottom", style.pop("bottom_values", None))

        if bottom is None:
            bottom = _infer_stacked_bar_bottom(ax, bar_x, y)

        ax.bar(bar_x,
               y,
               bottom = bottom,
               label = label,
               xerr = series.xerr_values,
               yerr = series.yerr_values,
               **style)

        return

    if kind == "step":
        ln = ax.step(x, y, label = label, **style)

        if ln and plotted_lines is not None:
            line = ln[0]

            plotted_lines.append(line)

            if line_meta is not None:
                line_meta[line] = _capture_line_state(line)

        return

    if kind == "stem":
        markerfmt = style.pop("markerfmt", style.pop("marker", "o"))
        linefmt = style.pop("linefmt", style.pop("linestyle", "-"))
        basefmt = style.pop("basefmt", " ")

        cont = ax.stem(x, y, label = label, markerfmt = markerfmt, linefmt = linefmt, basefmt = basefmt)

        if hasattr(cont, "markerline") and isinstance(cont.markerline, Line2D) and plotted_lines is not None:
            plotted_lines.append(cont.markerline)

            if line_meta is not None:
                line_meta[cont.markerline] = _capture_line_state(cont.markerline)

        return

    # For "line" and any other kind, use a regular plot (with error bars if provided)
    if series.yerr_values is not None or series.xerr_values is not None:
        eb = ax.errorbar(x, y, yerr = series.yerr_values, xerr = series.xerr_values, label = label, **style)

        if eb.lines and isinstance(eb.lines[0], Line2D) and plotted_lines is not None:
            line = eb.lines[0]

            plotted_lines.append(line)

            if line_meta is not None:
                line_meta[line] = _capture_line_state(line)

    else:
        ln = ax.plot(x, y, label = label, **style)

        if ln and plotted_lines is not None:
            line = ln[0]

            plotted_lines.append(line)

            if line_meta is not None:
                line_meta[line] = _capture_line_state(line)