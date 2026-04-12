# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.figure import Figure

from .config import PlotCfg

def _get_legend_handles(legend_obj) -> List[Any]:
    """
    Retrieve the concrete legend handle artists in display order.

    Depending on the Matplotlib version, these may be available under different attribute names.
    """

    handles = getattr(legend_obj, "legend_handles", None)

    if handles is None:
        handles = getattr(legend_obj, "legendHandles", None)

    if handles is None:
        handles = list(legend_obj.get_lines()) + list(legend_obj.get_patches())

    return list(handles)

def _is_artist_visible_recursive(obj: Any) -> bool:
    """
    Determine whether an artist-like object is currently visible.

    This mirrors the recursive handling in _set_artist_visibility_recursive(...), which is needed
    because some legend-backed plot handles are containers rather than simple Line2D objects.
    """

    if obj is None:
        return False

    if isinstance(obj, (list, tuple, set)):
        return any(_is_artist_visible_recursive(child) for child in obj)

    try:
        return bool(obj.get_visible())

    except Exception:
        pass

    for attr in ("lines", "collections", "patches", "artists", "children", "caplines", "barlinecols", "stemlines", "markerline", "baseline"):
        try:
            child = getattr(obj, attr)

        except Exception:
            continue

        if child is None:
            continue

        if _is_artist_visible_recursive(child):
            return True

    try:
        kids = obj.get_children()

    except Exception:
        kids = None

    if kids:
        return any(_is_artist_visible_recursive(child) for child in kids)

    return False

def _install_legend_toggle(fig: Figure, legend_obj) -> int:
    """
    Install click-to-toggle visibility behavior on the legend entries.
    When a legend entry is clicked, the corresponding plotted artist or artist container on the axes
    will toggle its visibility.
    """

    ax = getattr(legend_obj, "axes", None)

    label_to_artist: Dict[str, Any] = {}

    if ax is not None:
        try:
            handles, labels = ax.get_legend_handles_labels()

        except Exception:
            handles, labels = [], []

        for handle, label in zip(handles, labels):
            if label and not str(label).startswith("_"):
                label_to_artist.setdefault(label, handle)

    legend_handles = _get_legend_handles(legend_obj)

    for legend_handle in legend_handles:
        try:
            legend_handle.set_picker(True)

        except Exception:
            pass

        try:
            legend_handle.set_pickradius(5)

        except Exception:
            pass

    for legend_text in legend_obj.get_texts():
        legend_text.set_picker(True)

    handle_map: Dict[Any, str] = {}

    for legend_handle, legend_text in zip(legend_handles, legend_obj.get_texts()):
        handle_map[legend_handle] = legend_text.get_text()
        handle_map[legend_text] = legend_text.get_text()

    def on_pick(event):
        """
        Handle pick events on the legend to toggle the visibility of the corresponding plotted artist.
        """

        artist = event.artist

        if artist not in handle_map:
            return

        label = handle_map[artist]

        if label not in label_to_artist:
            return

        target = label_to_artist[label]
        target_visible = _is_artist_visible_recursive(target)

        _set_artist_visibility_recursive(target, not target_visible)

        new_visible = _is_artist_visible_recursive(target)

        # Dim the legend entry by changing its alpha to indicate whether the corresponding plot element is visible or not
        for h, lab in handle_map.items():
            if lab == label:
                try:
                    h.set_alpha(1.0 if new_visible else 0.2)

                except Exception:
                    pass

        fig.canvas.draw_idle()

    cid = fig.canvas.mpl_connect("pick_event", on_pick)

    return cid

def _set_artist_visibility_recursive(obj: Any, visible: bool) -> None:
    """
    Recursively set the visibility of an artist and all its children.
    Handles common Matplotlib container types like lists, tuples, sets, etc.,
    as well as objects with common container attributes like "lines", "collections", "patches", "artists", "children", etc.
    """

    if obj is None:
        return

    if isinstance(obj, (list, tuple, set)):
        for child in obj:
            _set_artist_visibility_recursive(child, visible)

        return

    try:
        obj.set_visible(visible)

    except Exception:
        pass

    # Check for common container attributes that may hold child artists and recursively set their visibility
    for attr in ("lines", "collections", "patches", "artists", "children", "caplines", "barlinecols", "stemlines", "markerline", "baseline"):
        try:
            child = getattr(obj, attr)

        except Exception:
            continue

        if child is None:
            continue

        _set_artist_visibility_recursive(child, visible)

    try:
        kids = obj.get_children()

    except Exception:
        kids = None

    if kids:
        for child in kids:
            _set_artist_visibility_recursive(child, visible)

def _set_all_legend_entries_visibility(fig: Figure, legend_obj, visible: bool) -> None:
    """
    Set the visibility of all legend entries and their corresponding lines in the plot to either visible
    or dimmed (not fully hidden, to keep the legend layout intact).
    """

    if legend_obj is None:
        return

    ax = getattr(legend_obj, "axes", None)

    if ax is not None:
        try:
            handles, labels = ax.get_legend_handles_labels()

        except Exception:
            handles, labels = [], []

        for h, lab in zip(handles, labels):
            if not lab or str(lab).startswith("_"):
                continue

            _set_artist_visibility_recursive(h, visible)

    alpha = 1.0 if visible else 0.2

    # Set the alpha of the legend entries to indicate their visibility state, without fully hiding them,
    # so that the legend layout remains intact and users can still click on the entries to toggle visibility.
    try:
        for h in legend_obj.get_lines():
            try:
                h.set_alpha(alpha)

            except Exception:
                pass

        for t in legend_obj.get_texts():
            try:
                t.set_alpha(alpha)

            except Exception:
                pass

    except Exception:
        pass

    fig.canvas.draw_idle()

def _install_legend_hide_unhide_all_keys(fig: Figure, legend_obj) -> int:
    """
    Install keyboard shortcuts for hiding and showing all legend entries at once.
    """

    def on_key(event):
        k = (event.key or "").lower()

        if k == "h":
            _set_all_legend_entries_visibility(fig, legend_obj, visible = False)

        elif k == "u":
            _set_all_legend_entries_visibility(fig, legend_obj, visible = True)

    return fig.canvas.mpl_connect("key_press_event", on_key)

def _capture_line_state(line: Line2D) -> Dict[str, Any]:
    """
    Capture the current visual state of a line, including its alpha, linewidth and visibility.
    This is used to restore the line's appearance after hover interactions.
    """

    return {"alpha": line.get_alpha() if line.get_alpha() is not None else 1.0,
            "lw": line.get_linewidth() if line.get_linewidth() is not None else 1.5,
            "visible": line.get_visible()}

def _install_hover_highlight(fig: Figure,
                             axes: List[Axes],
                             pick_radius_px: float,
                             dim_alpha: float,
                             emph_lw_scale: float,
                             show_tooltip: bool,
                             plot_cfg: Optional[PlotCfg]) -> int:
    """
    Install hover-to-highlight behavior on the given axes list.
    When the mouse hovers near a line, that line will be emphasized by increasing its linewidth and restoring its alpha, while all other lines will be dimmed by reducing their alpha.
    """

    if not axes:
        raise ValueError("The axes list for hover highlight installation cannot be empty. \n")

    ann = None

    if show_tooltip:
        ax0 = axes[0]

        turn_dark = (plot_cfg is not None) and plot_cfg.enable_dark_mode

        bbox_fc = plot_cfg.dark_mode_tooltip_facecolor if turn_dark else "w"
        bbox_ec = plot_cfg.dark_mode_tooltip_edgecolor if turn_dark else "k"

        txt_c  = plot_cfg.dark_mode_text_color if turn_dark else "k"

        ann = ax0.annotate("",
                           xy = (0, 0),
                           xytext = (10, 10),
                           textcoords = "offset points",
                           bbox = dict(boxstyle = "round", fc = bbox_fc, ec = bbox_ec, alpha = (plot_cfg.dark_mode_tooltip_alpha if turn_dark else 0.8)),
                           arrowprops = dict(arrowstyle = "->", color = txt_c))

        ann.set_color(txt_c)
        ann.set_visible(False)

    pick_radius2 = float(pick_radius_px) ** 2

    line_meta: Dict[Line2D, Dict[str, Any]] = {}

    def current_lines() -> List[Line2D]:
        """
        Get the list of currently visible lines across all axes.
        """

        lines: List[Line2D] = []

        for ax in axes:
            for ln in ax.get_lines():
                if ln.get_visible():
                    lines.append(ln)

        return lines

    def ensure_meta(lines: List[Line2D]):
        """
        Ensure that the line_meta dictionary contains entries for all current lines, and remove any stale entries.
        """

        stale = [ln for ln in list(line_meta.keys()) if ln not in lines]

        for ln in stale:
            line_meta.pop(ln, None)

        for ln in lines:
            if ln not in line_meta:
                line_meta[ln] = _capture_line_state(ln)

    def ensure_annotation(ax_for_ann: Axes):
        """
        Ensure that the annotation object exists and is associated with the correct axes.
        """

        nonlocal ann # Modify the outer scope ann variable.

        if not show_tooltip:
            return None

        # If the annotation does not exist or was cleared by ax.cla(), or is associated with a different axes, create a new annotation on the current axes for showing the tooltip.
        if ann is None or ann.axes is None or ann.axes is not ax_for_ann:
            ann = ax_for_ann.annotate("",
                                      xy = (0, 0),
                                      xytext = (10, 10),
                                      textcoords = "offset points",
                                      bbox = dict(boxstyle = "round", fc = "w", alpha = 0.8),
                                      arrowprops = dict(arrowstyle = "->"))

            ann.set_visible(False)

        return ann

    def reset_all(lines: List[Line2D]):
        """
        Reset all lines to their original visual state (alpha, linewidth and visibility) and hide the tooltip annotation if it exists.
        """

        ensure_meta(lines)

        for ln in lines:
            meta = line_meta[ln]

            ln.set_alpha(meta["alpha"])
            ln.set_linewidth(meta["lw"])
            ln.set_visible(meta["visible"])

        if ann is not None:
            ann.set_visible(False)

    def dim_all_except(lines: List[Line2D], target: Line2D):
        """
        Dim all lines except the target line by reducing their alpha, and emphasize the target line by restoring its alpha and increasing its linewidth.
        """

        ensure_meta(lines)

        for ln in lines:
            meta = line_meta[ln]

            if ln is target:
                ln.set_alpha(meta["alpha"])
                ln.set_linewidth(meta["lw"] * emph_lw_scale)

            else:
                ln.set_alpha(min(dim_alpha, meta["alpha"]))
                ln.set_linewidth(meta["lw"])

    def nearest_line(event) -> Tuple[Optional[Line2D], Optional[Tuple[float, float]]]:
        """
        Find the nearest line to the mouse event within the pick radius.
        """

        if event.inaxes is None or event.x is None or event.y is None:
            return None, None

        if event.inaxes not in axes:
            return None, None

        e_x = event.x
        e_y = event.y

        best_ln = None
        best_pt = None

        best_d_squared = float("inf")

        # Search all axes and iterate over all lines and find the closest point on any line to the mouse event position in display coordinates, then determine which line is closest within the pick radius.
        for ax in axes:
            for ln in ax.get_lines():
                if not ln.get_visible():
                    continue

                xdata = ln.get_xdata(orig = False)
                ydata = ln.get_ydata(orig = False)

                if xdata is None or ydata is None or len(xdata) == 0:
                    continue

                pts = ax.transData.transform(np.column_stack([xdata, ydata]))

                # Compute the squared distance from the mouse event position to each point on the line in display coordinates.
                dx = pts[:, 0] - e_x
                dy = pts[:, 1] - e_y

                d_squared = dx ** 2 + dy ** 2

                idx = int(np.argmin(d_squared))

                d_squared_min = float(d_squared[idx])

                # If the closest point on this line is closer than the best one found so far, update the best line and point.
                if d_squared_min < best_d_squared:
                    best_d_squared = d_squared_min
                    best_ln = ln

                    best_pt = (float(xdata[idx]), float(ydata[idx]))

        if best_ln is None or best_d_squared > pick_radius2:
            return None, None

        return best_ln, best_pt

    def on_move(event):
        """
        Handle mouse move events to implement hover highlighting of lines and showing tooltips with line labels and coordinates.
        """

        lines = current_lines()

        if not lines:
            if ann is not None:
                ann.set_visible(False)

            return

        ln, pt = nearest_line(event)

        if ln is None:
            reset_all(lines)

            fig.canvas.draw_idle()

            return

        dim_all_except(lines, ln)

        if show_tooltip and event.inaxes is not None:
            ensure_annotation(event.inaxes)

        if ann is not None and pt is not None:
            ann.xy = pt

            label = ln.get_label()

            if not label or label.startswith("_"):
                label = "series"

            ann.set_text(f"{label}\n({pt[0]:.4g}, {pt[1]:.4g})")
            ann.set_visible(True)

        fig.canvas.draw_idle()

    def on_leave(_event):
        """
        Handle mouse leave events to reset all lines to their original visual state and hide the tooltip annotation.
        """

        lines = current_lines()

        if lines:
            reset_all(lines)

            fig.canvas.draw_idle()

    cid = fig.canvas.mpl_connect("motion_notify_event", on_move)
    fig.canvas.mpl_connect("figure_leave_event", on_leave)

    return cid