# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, Optional, Sequence

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from .config import PlotCfg

def _style_colorbar_for_plot_cfg(colorbar_obj: Any, plot_cfg: Optional[PlotCfg]) -> None:
    """
    Apply best-effort CIPlot styling to a matplotlib colorbar, including dark-mode text and spine colors.
    """

    if colorbar_obj is None or plot_cfg is None:
        return

    if not plot_cfg.enable_dark_mode:
        return

    try:
        colorbar_obj.ax.set_facecolor(plot_cfg.dark_mode_axes_facecolor)

    except Exception:
        pass

    for axis_label in (getattr(colorbar_obj.ax, "xaxis", None), getattr(colorbar_obj.ax, "yaxis", None)):
        if axis_label is None:
            continue

        try:
            axis_label.label.set_color(plot_cfg.dark_mode_text_color)

        except Exception:
            pass

    try:
        colorbar_obj.ax.tick_params(colors = plot_cfg.dark_mode_text_color, which = "both")

    except Exception:
        pass

    try:
        outline = getattr(colorbar_obj, "outline", None)

        if outline is not None:
            outline.set_edgecolor(plot_cfg.dark_mode_spine_color)

    except Exception:
        pass

    try:
        for spine in colorbar_obj.ax.spines.values():
            spine.set_color(plot_cfg.dark_mode_spine_color)

    except Exception:
        pass

def _rcparams_from_plot_cfg(plot_cfg: PlotCfg) -> Dict[str, Any]:
    """
    Generate a dictionary of Matplotlib rcParams based on the provided
    PlotCfg configuration, applying dark mode settings if enabled.
    """

    rc: Dict[str, Any] = {"font.size": plot_cfg.base_font_size}

    if not plot_cfg.enable_dark_mode:
        return rc

    rc.update({# Parameters for the canvas (the "white stuff" around the axes)
               "figure.facecolor": plot_cfg.dark_mode_figure_facecolor,
               "figure.edgecolor": plot_cfg.dark_mode_figure_facecolor,
               "savefig.facecolor": plot_cfg.dark_mode_figure_facecolor,
               "savefig.edgecolor": plot_cfg.dark_mode_figure_facecolor,

               # Parameters for the axes
               "axes.facecolor": plot_cfg.dark_mode_axes_facecolor,
               "axes.edgecolor": plot_cfg.dark_mode_spine_color,

               # Parameters for the text (tick labels, axis labels, title, legend text, etc.)
               "text.color": plot_cfg.dark_mode_text_color,
               "axes.labelcolor": plot_cfg.dark_mode_text_color,
               "axes.titlecolor": plot_cfg.dark_mode_text_color,
               "xtick.color": plot_cfg.dark_mode_text_color,
               "ytick.color": plot_cfg.dark_mode_text_color,

               # Parameters for the grid and the legend
               "grid.color": plot_cfg.dark_mode_grid_color,
               "legend.facecolor": plot_cfg.dark_mode_axes_facecolor,
               "legend.edgecolor": plot_cfg.dark_mode_spine_color})

    return rc

def _apply_dark_mode_post(fig: Figure, axes: Sequence[Axes], plot_cfg: PlotCfg):
    """
    After the figure and axes have been created, apply dark mode styling directly to the figure
    and axes objects to ensure that all elements are styled correctly, including those that may
    not be fully covered by rcParams (e.g. certain patches, annotations, or interactive elements).
    """

    if not plot_cfg.enable_dark_mode:
        return

    fig.patch.set_facecolor(plot_cfg.dark_mode_figure_facecolor)
    fig.patch.set_edgecolor(plot_cfg.dark_mode_figure_facecolor)

    for ax in axes:
        ax.set_facecolor(plot_cfg.dark_mode_axes_facecolor)

        for sp in ax.spines.values():
            sp.set_color(plot_cfg.dark_mode_spine_color)

        ax.tick_params(colors = plot_cfg.dark_mode_text_color, which = "both")
        
        ax.xaxis.label.set_color(plot_cfg.dark_mode_text_color)
        ax.yaxis.label.set_color(plot_cfg.dark_mode_text_color)

        ax.title.set_color(plot_cfg.dark_mode_text_color)

def _try_tint_window_background(fig: Figure, plot_cfg: PlotCfg) -> None:
    """
    Attempt to tint the background of the window containing the figure to match the dark mode figure facecolor,
    if the configuration allows for it and if the backend supports it (a so-called "best effort" solution).
    """

    if not (plot_cfg.enable_dark_mode and plot_cfg.dark_mode_try_tint_window):
        return

    try:
        mgr = getattr(fig.canvas, "manager", None)

        win = getattr(mgr, "window", None)

        if win is None:
            return

        bg = plot_cfg.dark_mode_figure_facecolor

        # Handle the Qt5Agg and QtAgg backends
        if hasattr(win, "setStyleSheet"):
            win.setStyleSheet(f"background-color: {bg};")

            return

        # Handle the TkAgg backend 
        if hasattr(win, "configure"):
            try:
                win.configure(background = bg)

            except Exception:
                pass

    except Exception:
        pass

def _flip_black_to_white_in_style(style: Optional[Dict[str, Any]], plot_cfg: PlotCfg) -> Dict[str, Any]:
    """
    If dark mode is enabled and the configuration specifies to flip explicit black colors to white, this function
    takes a style dictionary (e.g. for a line or marker) and returns a new style dictionary where any color properties,
    that are explicitly set to black (e.g. "k", "black", "#000", "#000000", "#000000ff"), are changed to white ("#FFFFFF").
    """

    if not style:
        return {}

    if not (plot_cfg.enable_dark_mode and plot_cfg.dark_mode_flip_explicit_black):
        return dict(style)

    out = dict(style)

    for key in ("color", "c", "edgecolor", "ec", "facecolor", "fc"):
        v = out.get(key)

        if isinstance(v, str) and v.lower() in {"k", "black", "#000", "#000000", "#000000ff"}:
            out[key] = "#FFFFFF"

    return out

def _install_figsize_display(fig: Figure, plot_cfg: PlotCfg) -> Optional[int]:
    """
    Install a live figure-size display in figure coordinates that updates whenever the
    interactive window is resized.
    """

    if not plot_cfg.show_current_figure_size:
        return None

    text_color = plot_cfg.dark_mode_text_color if plot_cfg.enable_dark_mode else "black"
    bbox_facecolor = plot_cfg.dark_mode_axes_facecolor if plot_cfg.enable_dark_mode else "white"
    bbox_edgecolor = plot_cfg.dark_mode_spine_color if plot_cfg.enable_dark_mode else "black"

    figsize_text = fig.text(0.995,
                            0.005,
                            "",
                            ha = "right",
                            va = "bottom",
                            color = text_color,
                            fontsize = max(1, plot_cfg.base_font_size - 1),
                            bbox = dict(boxstyle = "round,pad=0.2",
                                        facecolor = bbox_facecolor,
                                        edgecolor = bbox_edgecolor,
                                        alpha = 0.75))

    # Keep this overlay out of layout calculations
    try:
        figsize_text.set_in_layout(False)

    except Exception:
        pass

    def _update_figsize_display(_event = None):
        w_in, h_in = fig.get_size_inches()
        dpi = fig.dpi

        w_px = int(round(w_in * dpi))
        h_px = int(round(h_in * dpi))

        figsize_text.set_text(f"Current figure size: {w_in:.2f} x {h_in:.2f} inches ({w_px} x {h_px} px @ {dpi} dpi)")
        fig.canvas.draw_idle()

    _update_figsize_display()

    return fig.canvas.mpl_connect("resize_event", _update_figsize_display)