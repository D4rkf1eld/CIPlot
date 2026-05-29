# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple, Union, Literal

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

Number = Union[int, float]

AxisScale = Literal["linear", "log", "symlog", "logit"]

LegendLocation = Literal["best", "upper right", "upper left", "lower left", "lower right", "right", "center left", "center right", "lower center", "upper center", "center"]

GeneralLegendPlacement = Literal["figure", "subplot"]
GeneralLegendBBoxTransform = Literal["auto", "figure", "target_axes"]
GeneralLegendReserveSpace = Literal["none", "right", "left", "top", "bottom"]

ArrayLikeImg = Union[np.ndarray]
ArrayLike = Union[Sequence[Number], np.ndarray]

MarkingCoords = Literal["data", "axes"] # Interpret the marking coordinates as data coordinates or axes fraction (0..1).

MarkingAxis = Literal["left", "right"]

MarkingKind = Literal["hline", "vline", "line", "rectangle", "circle", "ellipse", "arrow", "text"]

@dataclass
class TickCfg:
    """
    Configure major and minor ticks for one axis.

    - tick_values: Explicit tick locations (overrides step if provided).
    - tick_step: Tick step size (ignored if values is provided).
    - minor_tick_values: Explicit minor tick locations (overrides minor_step if provided).
    - minor_tick_step: Minor tick step size (ignored if minor_values is provided).

    - hide_ticks: Hide tick marks.
    - hide_labels: Hide tick labels.

    - tick_rotation: Tick label rotation in degrees.
    - tick_formatter: Function with signature (value, index) -> str for custom tick labels.
    - tick_fontsize: Tick label font size.
    """

    tick_values: Optional[Sequence[Number]] = None
    tick_step: Optional[Number] = None
    minor_tick_values: Optional[Sequence[Number]] = None
    minor_tick_step: Optional[Number] = None

    hide_ticks: bool = False
    hide_labels: bool = False

    tick_rotation: Optional[Number] = None
    tick_formatter: Optional[Callable[[Number, int], str]] = None
    tick_fontsize: Optional[int] = None

@dataclass
class AxisCfg:
    """
    Configure x or y axis.

    - axis_label: The axis label.
    - axis_limits: Axis limits within min and max values. Can be a tuple of (min, max) where either can be None to preserve the current limit for that side.
    - axis_scaling: Scaling options of "linear", "log", "symlog", or "logit".
    - invert_axis: Invert the axis direction.
    - axis_ticks: Configuration of the ticks.
    """

    axis_label: str = ""
    axis_limits: Optional[Union[Tuple[Number, Number], Tuple[Number, None], Tuple[None, Number]]] = None
    axis_scaling: AxisScale = "linear"
    invert_axis: bool = False
    axis_ticks: TickCfg = field(default_factory = TickCfg)

@dataclass
class GridCfg:
    """
    Grid configuration.

    - show_minor_grid: Show minor grid lines.
    - show_major_grid: Show major grid lines.

    - minor_grid_style: Optional style overrides for minor grid lines (e.g. {"alpha": 0.2, "linestyle": "--"}).
    - major_grid_style: Optional style overrides for major grid lines.
    """

    show_minor_grid: bool = False
    show_major_grid: bool = False

    minor_grid_style: Dict[str, Any] = field(default_factory = dict)
    major_grid_style: Dict[str, Any] = field(default_factory = dict)

@dataclass
class LegendCfg:
    """
    Legend configuration, including optional click-to-toggle behavior.
    The behavior is differentiated between regular subplot legends and general/page-level legends for browse_structured_subplot_pages(...):

    Subplot legends:
    - show_legend: Whether to display the regular axes/subplot legend.
    - legend_location: Location of the legend (e.g. "best" or "upper right"). This is also used by the general/page-level legend.
    - put_legend_outside: If True, place the regular subplot legend outside the plot on the right. For the general/page-level legend, this also provides a useful default outside placement when no explicit general_legend_bbox_to_anchor is given.
    - number_columns: Number of columns in the legend. This is also used by the general/page-level legend.
    - legend_fontsize: Legend font size. This is also used by the general/page-level legend.
    - show_legend_frame: Whether to draw a frame around the legend. This is also used by the general/page-level legend.
    - legend_fancybox: Whether to use a fancy box for the legend frame. This is also used by the general/page-level legend.
    - legend_frame_alpha: Transparency of the legend frame (0.0 to 1.0). This is also used by the general/page-level legend.
    - legend_style: Additional keyword arguments forwarded to matplotlib legend creation. This is also used by the general/page-level legend.

    General/page-level legends for browse_structured_subplot_pages(...):
    - general_legend_show: Whether to display one legend collected from all subplots on the current structured page.
    - general_legend_placement: Place the general legend as a figure-level legend ("figure") or inside/on top of a specified subplot axes ("subplot").
    - general_legend_target_subplot: Target subplot cell (row_index, column_index) when general_legend_placement = "subplot". This can point to an empty cell to use it as a legend area.
    - general_legend_bbox_to_anchor: Optional bbox_to_anchor for the general legend. If None, CIPlot chooses a practical default based on placement and reserved space.
    - general_legend_bbox_transform: Coordinate system for general_legend_bbox_to_anchor. "auto" uses figure coordinates for figure legends and target-axes coordinates for subplot legends.
    - general_legend_deduplicate_labels: If True, only the first legend entry for a repeated label is displayed, while interactivity still targets all artists with that label.
    - general_legend_include_labels: Optional allow-list of labels to show in the general legend.
    - general_legend_exclude_labels: Labels to exclude from the general legend.
    - general_legend_label_order: Optional explicit label order. Labels not listed here are appended in discovery order.
    - general_legend_reserve_space: Reserve figure space ("right", "left", "top", "bottom") for the general legend to avoid blocking subplot content.
    - general_legend_reserve_fraction: Fraction of figure width/height reserved when general_legend_reserve_space is not "none".
    - general_legend_hide_subplot_legends: If True, suppress regular subplot legends on structured pages when the general legend is shown.

    - legend_is_clickable: If True, clicking legend items toggles the visibility of the corresponding artists. This also works for the general/page-level legend.
    """

    show_legend: bool = False
    legend_location: LegendLocation = "best"
    put_legend_outside: bool = False
    number_columns: int = 1
    legend_fontsize: Optional[int] = None
    show_legend_frame: bool = True
    legend_fancybox: bool = True
    legend_frame_alpha: float = 0.9
    legend_style: Dict[str, Any] = field(default_factory = dict)

    general_legend_show: bool = False
    general_legend_placement: GeneralLegendPlacement = "figure"
    general_legend_target_subplot: Optional[Tuple[int, int]] = None
    general_legend_bbox_to_anchor: Optional[Tuple[Number, Number]] = None
    general_legend_bbox_transform: GeneralLegendBBoxTransform = "auto"

    general_legend_deduplicate_labels: bool = True
    general_legend_include_labels: Optional[Sequence[str]] = None
    general_legend_exclude_labels: Sequence[str] = field(default_factory = tuple)
    general_legend_label_order: Optional[Sequence[str]] = None

    general_legend_reserve_space: GeneralLegendReserveSpace = "none"
    general_legend_reserve_fraction: float = 0.15
    general_legend_hide_subplot_legends: bool = False

    legend_is_clickable: bool = False

@dataclass
class ExportCfg:
    """
    Configuration for exporting the figure to files.

    - enable_export: Whether to enable exporting the figure.
    - enable_data_export: Whether to export the raw data used for plotting in addition to the figure to a JSON file.
    - data_export_with_style: Whether to also export the plotting style information for each series in addition to the raw data.

    - output_directory: Directory to save exported files.
    - export_name: Base name for exported files (without extension).
    - export_data_name: Base name for exported data files (without extension).
    - series_export_names: Optional list of names for each series in a multi-series plot (only works for browse_series() or plot_xy() with separate_figures_per_series = True)
    when exporting multiple series separately (overrides export_name if provided).
    - output_formats: Tuple of formats to export (e.g. ("pdf", "png")).

    - output_dpi: DPI for raster formats (e.g. 300 or "figure" to use figure's DPI).
    - transparent_background: Whether to use a transparent background for the exported figure.
    - bbox_inches: Bounding box option for saving figure (e.g. "tight", "standard", or None).
    """

    enable_export: bool
    enable_data_export: bool
    data_export_with_style: bool

    output_directory: Union[str, Path]
    export_name: str = "plot"
    export_data_name: str = "data"
    series_export_names: Optional[Sequence[str]] = None
    output_formats: Tuple[str, ...] = tuple("pdf")

    output_dpi: Union[int, str] = "figure"
    transparent_background: bool = False
    bbox_inches: Optional[str] = "tight"

@dataclass
class DistributionPlotCfg:
    """
    Configuration payload for distribution-style plotting kinds such as "boxplot" and "violin".

    - distribution_values: One-dimensional sample values used to construct the distribution plot.
    - distribution_position: Optional x-axis position for this distribution. If None, matplotlib will place it automatically.
    - distribution_width: Optional width of the box / violin. If None, matplotlib uses its own default.
    - distribution_quantiles: Optional quantiles to draw on a violin plot.
    - distribution_manage_ticks: Whether matplotlib may automatically adjust axis ticks for this plot element.

    Boxplot-specific options:
    - boxplot_patch_artist: Whether to render the box as a patch, which enables facecolor-based styling.
    - boxplot_notch: Whether to draw notches around the median.
    - boxplot_showfliers: Whether to show outlier markers.
    - boxplot_showmeans: Whether to show the mean.
    - boxplot_meanline: Whether the mean should be shown as a line instead of a point if means are enabled.
    - boxplot_whis: Whisker range forwarded to matplotlib.
    - boxplot_autorange: Whether matplotlib may automatically expand whiskers for degenerate distributions.
    - boxplot_showcaps: Whether to draw caps on the whiskers.
    - boxplot_showbox: Whether to draw the box body.

    Violin-specific options:
    - violin_showmeans: Whether to show the mean line.
    - violin_showmedians: Whether to show the median line.
    - violin_showextrema: Whether to show extrema and center bars.
    - violin_points: Number of sample points used internally by matplotlib when evaluating the kernel density estimate.
    - violin_bandwidth_method: Optional bandwidth selection forwarded to matplotlib.
    """

    distribution_values: ArrayLike
    distribution_position: Optional[Number] = None
    distribution_width: Optional[Number] = None
    distribution_quantiles: Optional[Sequence[Number]] = None
    distribution_manage_ticks: bool = False

    boxplot_patch_artist: bool = True
    boxplot_notch: bool = False
    boxplot_showfliers: bool = True
    boxplot_showmeans: bool = False
    boxplot_meanline: bool = False
    boxplot_whis: Union[Number, Tuple[Number, Number], str] = 1.5
    boxplot_autorange: bool = False
    boxplot_showcaps: bool = True
    boxplot_showbox: bool = True

    violin_showmeans: bool = False
    violin_showmedians: bool = True
    violin_showextrema: bool = True
    violin_points: int = 100
    violin_bandwidth_method: Optional[Union[Number, str]] = None

@dataclass
class HeatmapPlotCfg:
    """
    Configuration payload for matrix-style plotting kinds such as "heatmap".

    - heatmap_values: Two-dimensional matrix of values rendered as an image-like heatmap.
    - heatmap_extent: Optional tuple of (x0, x1, y0, y1) forwarded to matplotlib.imshow(...).
    - heatmap_origin: The image origin, typically "upper" or "lower".
    - heatmap_interpolation: Interpolation method used for resampling the heatmap image.
    - heatmap_aspect: Aspect handling forwarded to the axes after rendering (e.g. "auto" or "equal").
    - heatmap_colormap: Optional matplotlib colormap name.
    - heatmap_vmin: Optional lower bound for color normalization.
    - heatmap_vmax: Optional upper bound for color normalization.
    - heatmap_alpha: Optional transparency override.

    Colorbar-specific options:
    - heatmap_show_colorbar: Whether to draw a colorbar for this heatmap.
    - heatmap_colorbar_label: Optional label for the colorbar.
    - heatmap_colorbar_orientation: Optional colorbar orientation ("vertical" or "horizontal").
    - heatmap_colorbar_shrink: Optional shrink factor forwarded to matplotlib.figure.Figure.colorbar(...).
    - heatmap_colorbar_pad: Optional spacing between the axes and the colorbar.
    - heatmap_colorbar_style: Additional keyword arguments forwarded to Figure.colorbar(...).
    """

    heatmap_values: Union[Sequence[Sequence[Number]], np.ndarray]
    heatmap_extent: Optional[Tuple[Number, Number, Number, Number]] = None
    heatmap_origin: Literal["upper", "lower"] = "upper"
    heatmap_interpolation: str = "nearest"
    heatmap_aspect: Union[str, Number] = "auto"
    heatmap_colormap: Optional[str] = None
    heatmap_vmin: Optional[Number] = None
    heatmap_vmax: Optional[Number] = None
    heatmap_alpha: Optional[float] = None

    heatmap_show_colorbar: bool = False
    heatmap_colorbar_label: Optional[str] = None
    heatmap_colorbar_orientation: Optional[Literal["vertical", "horizontal"]] = None
    heatmap_colorbar_shrink: Optional[float] = None
    heatmap_colorbar_pad: Optional[float] = None
    heatmap_colorbar_style: Dict[str, Any] = field(default_factory = dict)

@dataclass
class SeriesCfg:
    """
    Configuration to represent a single data series to be plotted.

    - x_values: x values of the series for line-like and bar-like plotting kinds. Optional for distribution-style kinds.
    - y_values: y values of the series for line-like and bar-like plotting kinds. Optional for distribution-style kinds.

    - distribution_plot_cfg: Optional payload for distribution-style plotting kinds such as boxplot and violin.

    - heatmap_plot_cfg: Optional payload for matrix-style plotting kinds such as heatmap.

    - label: Optional label for the series (used in legend and tooltips).

    - plotting_kind: The plotting/representation kind of the data, e.g. "line", "scatter", "step", "stem", "bar", "stacked_bar", "boxplot", "violin", or "heatmap".
    - plotting_style: Dictionary of matplotlib style options (e.g. {"color": "red", "marker": "o", "linestyle": "--"}).

    - is_visible: Whether the series is initially visible.
    - plot_on_which_y_axis: Which y-axis to plot on ("left" or "right").

    - xerr_values: Optional x error values for error bars.
    - yerr_values: Optional y error values for error bars.
    - confidence_band_values: Optional tuple of (y_lower, y_upper) for plotting a confidence band around the line.
    """

    x_values: Optional[ArrayLike] = None
    y_values: Optional[ArrayLike] = None

    distribution_plot_cfg: Optional[DistributionPlotCfg] = None

    heatmap_plot_cfg: Optional[HeatmapPlotCfg] = None

    label: Optional[str] = None

    plotting_kind: str = "line"
    plotting_style: Dict[str, Any] = field(default_factory = dict)

    is_visible: bool = True
    plot_on_which_y_axis: str = "left"

    # Optional uncertainty representations like error bars or confidence bands
    xerr_values: Optional[ArrayLike] = None
    yerr_values: Optional[ArrayLike] = None
    confidence_band_values: Optional[Tuple[ArrayLike, ArrayLike]] = None

@dataclass
class MarkingObjectCfg:
    """
    Represents one marking overlay to be drawn on an axis.

    Common fields:
        - marking_object_kind: The kind of marking to draw.
        - marking_object_coords: Whether the coordinates are in data units or axes fraction (0..1).
        - marking_object_target_axis: Whether to draw the marking on the left or right y-axis (if right axis is not present, it will be drawn on the left axis).
        - marking_object_style: Style parameters forwarded to the underlying matplotlib artist (e.g. color, linewidth, alpha, linestyle, zorder, etc.).
        - marking_object_clip_on: Whether the marking should be clipped to the axes area.
        - marking_object_zorder: Optional z-order for the marking (higher z-order means it will be drawn on top of lower z-order elements).

    Per marking object kind fields:
        - hline: Coordinates of y, optional x0 and x1 (if not provided, it will span the entire x-axis)
        - vline: Coordinates of x, optional y0 and y1 (if not provided, it will span the entire y-axis)
        - line: Coordinates of x0, y0, x1 and y1
        - rectangle: Coordinates of x and y, with the width and height and optionally the angle_deg for the angle in degrees (rotation around the top left corner)
        - circle: Coordinates of x and y with the radius
        - ellipse: Coordinates of x and y with the width, height and the angle_deg
        - arrow: Coordinates of x0, y0, x1 and y1
        - text: Coordinates of x and y with the text and the angle_deg for text rotation in degrees
    """

    marking_object_kind: MarkingKind

    marking_object_coords: MarkingCoords = "data"
    marking_object_target_axis: MarkingAxis = "left"

    # Free-form style forwarded to the underlying matplotlib artist
    marking_object_style: Dict[str, Any] = field(default_factory = dict)

    # Generic geometry fields (used depending on kind)
    x: Optional[Number] = None
    y: Optional[Number] = None

    x0: Optional[Number] = None
    y0: Optional[Number] = None
    x1: Optional[Number] = None
    y1: Optional[Number] = None

    width: Optional[Number] = None
    height: Optional[Number] = None

    radius: Optional[Number] = None

    angle_deg: Number = 0.0

    text: Optional[str] = None

    marking_object_clip_on: bool = True

    marking_object_zorder: Optional[Number] = None

@dataclass
class BackgroundImageCfg:
    """
    Draw an image behind the plot.

    - background_image: The image to draw as background.

    - background_image_coords: Whether the coordinates are in data units or axes fraction (0..1).
    - background_image_origin: The origin of the image, either "upper" or "lower".

    - background_image_extent: Optional tuple of (x0, x1, y0, y1) to specify the bounding box of the image in data coordinates (if coords = "data") or axes fraction (if coords = "axes").
    If not provided, the image will be stretched to cover the entire axes area.

    - background_image_alpha: The alpha transparency of the image (0.0 to 1.0).
    - background_image_interpolation: The interpolation method for resampling the image (e.g. "nearest", "bilinear", "bicubic", etc.).

    - background_image_zorder: Optional z-order for the image (higher z-order means it will be drawn on top of lower z-order elements).

    - background_image_style: Additional style parameters forwarded to the underlying matplotlib artist (e.g. color, alpha, etc.).
    """

    background_image: ArrayLikeImg

    background_image_coords: MarkingCoords = "data"
    background_image_origin: Literal["upper", "lower"] = "upper"

    background_image_extent: Optional[Tuple[Number, Number, Number, Number]] = None

    background_image_alpha: float = 1.0
    background_image_interpolation: str = "bilinear"

    background_image_zorder: Number = 0

    background_image_style: Dict[str, Any] = field(default_factory = dict)

@dataclass
class PlotCfg:
    """
    Overall plot configuration.

    - plot_title: Title of the plot.

    - show_page_index: Whether to show the page index and total pages in the title when using browse_series (e.g. "2/10").
    If False, only the optional series label will be shown in the title (e.g. "Experiment A"), without the page index.

    - figure_size: Size of the figure in inches (width, height).
    - show_current_figure_size: Whether to show the current figure size as a live overlay in the interactive figure window.

    - font_family: Font family for all text in the plot (e.g. "serif", "sans-serif", "monospace", or a specific font name).
    - base_font_size: Base font size for all text in the plot.

    - left_margin: Optional left margin as a fraction of figure width (e.g. 0.1).
    - right_margin: Optional right margin as a fraction of figure width (e.g. 0.9).
    - top_margin: Optional top margin as a fraction of figure height (e.g. 0.8).
    - bottom_margin: Optional bottom margin as a fraction of figure height (e.g. 0.2).

    - wspace: Optional width space between subplots when using multiple subplots.
    - hspace: Optional height space between subplots when using multiple subplots.

    - use_tight_layout: Whether to use tight_layout for automatic spacing.
    - use_constrained_layout: Whether to use constrained_layout for automatic spacing.

    - separate_figures_per_series: If True, each series gets its own figure.
    - show_plot: Whether to call plt.show() after plotting.

    - enable_hover_highlight: If True, hovering over lines highlights them and shows a tooltip.
    - hover_pick_px_radius: Pixel radius for detecting hover over lines.
    - hover_dim_alpha: Alpha value to dim non-hovered lines when hovering.
    - hover_emphasis_linewidth_scale: Linewidth scale factor for hovered line (e.g. 1.8 to make it 80% thicker).
    - hover_show_tooltip: Whether to show a tooltip with the series label and coordinates when hovering.

    - enable_dark_mode: Whether to enable dark mode styling for the plot.

    - dark_mode_figure_facecolor: Figure background color in dark mode.
    - dark_mode_axes_facecolor: Axes background color in dark mode.
    - dark_mode_text_color: Text color in dark mode.
    - dark_mode_grid_color: Grid color in dark mode.
    - dark_mode_spine_color: Spine (axis line) color in dark mode.

    - dark_mode_flip_explicit_black: Whether to flip explicit black colors (e.g. "k" or "black") to white in dark mode.
    - dark_mode_try_tint_window: Whether to try tinting the window background in dark mode (a backend-specific "best effort").

    - dark_mode_tooltip_facecolor: Tooltip face color in dark mode.
    - dark_mode_tooltip_edgecolor: Tooltip edge color in dark mode.
    - dark_mode_tooltip_alpha: Tooltip alpha transparency in dark mode.

    - rc_params: Additional matplotlib rcParams to apply globally (e.g. {"lines.linewidth": 2, "axes.grid": True}).
    """

    plot_title: Optional[str] = None

    show_page_index: bool = True

    figure_size: Optional[Tuple[Number, Number]] = None
    show_current_figure_size: bool = False

    font_family: Optional[Union[str, Sequence[str]]] = None
    base_font_size: int = 10

    left_margin: Optional[float] = None
    right_margin: Optional[float] = None
    top_margin: Optional[float] = None
    bottom_margin: Optional[float] = None

    wspace: Optional[float] = None
    hspace: Optional[float] = None

    use_tight_layout: bool = True
    use_constrained_layout: bool = False

    separate_figures_per_series: bool = False
    show_plot: bool = True

    # Interactivity
    enable_hover_highlight: bool = False
    hover_pick_px_radius: float = 10.0
    hover_dim_alpha: float = 0.20
    hover_emphasis_linewidth_scale: float = 1.8
    hover_show_tooltip: bool = False

    # Dark Mode (du weißt Bescheid...)
    enable_dark_mode: bool = False

    dark_mode_figure_facecolor: str = "#222222"
    dark_mode_axes_facecolor: str = "#222222"
    dark_mode_text_color: str = "#EEEEEE"
    dark_mode_grid_color: str = "#444444"
    dark_mode_spine_color: str = "#AAAAAA"

    dark_mode_flip_explicit_black: bool = True
    dark_mode_try_tint_window: bool = True

    dark_mode_tooltip_facecolor: str = "#333333"
    dark_mode_tooltip_edgecolor: str = "#777777"
    dark_mode_tooltip_alpha: float = 0.90

    rc_params: Dict[str, Any] = field(default_factory = dict)

@dataclass
class BrowsePageSettingsCfg:
    """
    Configuration for a single page in browse_series(),
    overriding the default plot configuration for that page.

    If a configuration is not provided for a specific aspect,
    the globally provided configuration will be used.

    When a configuration is provided as a dict, it will be
    merged with the global configuration for that page,
    allowing you to override only specific fields
    without having to repeat the entire configuration.
    """

    markings: Optional[Sequence[MarkingObjectCfg]] = None
    background: Optional[Union[BackgroundImageCfg, Mapping[str, Any]]] = None

    plot_cfg: Optional[Union[PlotCfg, Mapping[str, Any]]] = None

    x_axis_cfg: Optional[Union[AxisCfg, Mapping[str, Any]]] = None
    y_axis_cfg: Optional[Union[AxisCfg, Mapping[str, Any]]] = None

    grid_cfg: Optional[Union[GridCfg, Mapping[str, Any]]] = None
    legend_cfg: Optional[Union[LegendCfg, Mapping[str, Any]]] = None

@dataclass
class BrowseSubplotCfg:
    """
    Represents one subplot in a browsable structured page.
    """

    series: Sequence[SeriesCfg]

    markings: Optional[Sequence[MarkingObjectCfg]] = None
    background: Optional[Union[BackgroundImageCfg, Mapping[str, Any]]] = None

    plot_cfg: Optional[Union[PlotCfg, Mapping[str, Any]]] = None

    x_axis_cfg: Optional[Union[AxisCfg, Mapping[str, Any]]] = None
    y_axis_cfg: Optional[Union[AxisCfg, Mapping[str, Any]]] = None

    grid_cfg: Optional[Union[GridCfg, Mapping[str, Any]]] = None
    legend_cfg: Optional[Union[LegendCfg, Mapping[str, Any]]] = None

@dataclass
class BrowseStructuredPageCfg:
    """
    Represents a structured page with multiple subplots arranged in rows,
    where each subplot has its own configuration and data series.

    Hierarchy:
        Page
        ├── Row
        │    ├── BrowseSubplotCfg
        │    ├── BrowseSubplotCfg
        │    └── ...
        ├── Row
        │    └── ...
        └── ...

    With page_settings_cfg, you can also provide default settings for the entire page,
    that will be applied to all subplots, which can be overridden by the individual subplot
    configurations if needed.
    """

    rows: Sequence[Sequence[BrowseSubplotCfg]]

    page_title: Optional[str] = None

    page_settings_cfg: Optional[BrowsePageSettingsCfg] = None