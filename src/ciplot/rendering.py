# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import matplotlib.ticker as mticker

from matplotlib import patches
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from matplotlib.figure import Figure

from .config import (AxisCfg,
                     BackgroundImageCfg,
                     GridCfg,
                     LegendCfg,
                     MarkingCoords,
                     MarkingObjectCfg,
                     TickCfg)

def _add_legend(ax: Axes, legend_cfg: LegendCfg):
    """
    Add a legend to the given axes based on the provided configuration.
    """

    kwargs: Dict[str, Any] = dict(loc = legend_cfg.legend_location,
                                  ncol = legend_cfg.number_columns,
                                  frameon = legend_cfg.show_legend_frame,
                                  fancybox = legend_cfg.legend_fancybox,
                                  framealpha = legend_cfg.legend_frame_alpha)

    if legend_cfg.legend_fontsize is not None:
        kwargs["fontsize"] = legend_cfg.legend_fontsize

    if legend_cfg.put_legend_outside:
        kwargs["loc"] = "center left"

        kwargs["bbox_to_anchor"] = (1.02, 0.5)

        kwargs["borderaxespad"] = 0.0

    return ax.legend(**kwargs)

def _apply_axis_cfg(ax: Axes, axis_cfg: AxisCfg, which_axis: str, default_fontsize: int):
    """
    Apply axis configuration to the given axes for either x or y axis based on the provided configuration.
    """

    which_axis = which_axis.lower()

    if which_axis not in ("x", "y"):
        raise ValueError(f"The argument 'which_axis' must be either 'x' or 'y', not {which_axis}. \n")

    # Apply the axis scaling and inversion
    if which_axis == "x":
        ax.set_xscale(axis_cfg.axis_scaling)

        if axis_cfg.invert_axis:
            ax.invert_xaxis()

    else:
        ax.set_yscale(axis_cfg.axis_scaling)

        if axis_cfg.invert_axis:
            ax.invert_yaxis()

    # Apply the ticks configuration
    _apply_ticks(ax, axis_cfg.axis_ticks, which_axis = which_axis, default_fontsize = default_fontsize)

def _apply_ticks(ax: Axes, tick_cfg: TickCfg, which_axis: str, default_fontsize: int):
    """
    Apply the tick configuration to the given axes for either x or y axis based on the provided configuration.
    """

    fontsize = tick_cfg.tick_fontsize if tick_cfg.tick_fontsize is not None else default_fontsize

    axis = ax.xaxis if which_axis == "x" else ax.yaxis

    # Major locator
    if tick_cfg.tick_values is not None:
        axis.set_major_locator(mticker.FixedLocator(list(tick_cfg.tick_values)))

    elif tick_cfg.tick_step is not None:
        axis.set_major_locator(mticker.MultipleLocator(base = tick_cfg.tick_step))

    # Minor locator
    if tick_cfg.minor_tick_values is not None:
        axis.set_minor_locator(mticker.FixedLocator(list(tick_cfg.minor_tick_values)))

    elif tick_cfg.minor_tick_step is not None:
        axis.set_minor_locator(mticker.MultipleLocator(base = tick_cfg.minor_tick_step))

    # Apply a custom tick formatter if provided, which allows for custom tick label formatting based on the tick value and its position index.
    # It expects a function with the signature (value, index) -> str, where 'value' is the tick value and 'index' is its position index among the ticks.
    if tick_cfg.tick_formatter is not None:
        axis.set_major_formatter(mticker.FuncFormatter(lambda val, pos: tick_cfg.tick_formatter(val, -1 if pos is None else int(pos))))

    if tick_cfg.hide_ticks:
        ax.tick_params(axis = which_axis, which = "both", length = 0)

    if tick_cfg.hide_labels:
        if which_axis == "x":
            ax.tick_params(axis = "x", which = "both", labelbottom = False)

        else:
            ax.tick_params(axis = "y", which = "both", labelleft = False)

    # Apply fontsize and rotation
    labels = ax.get_xticklabels() if which_axis == "x" else ax.get_yticklabels()

    for lbl in labels:
        lbl.set_fontsize(fontsize)

        if tick_cfg.tick_rotation is not None:
            lbl.set_rotation(tick_cfg.tick_rotation)

def _apply_grid(ax: Axes, grid_cfg: GridCfg):
    """
    Apply grid configuration to the given axes based on the provided configuration.
    """

    if grid_cfg.show_major_grid:
        ax.grid(True, which = "major", **grid_cfg.major_grid_style)

    else:
        ax.grid(False, which = "major")

    if grid_cfg.show_minor_grid:
        ax.minorticks_on()

        ax.grid(True, which = "minor", **grid_cfg.minor_grid_style)

    else:
        ax.grid(False, which = "minor")

def _apply_partial_axis_limits(ax: Axes, which_axis: str, axis_cfg: AxisCfg):
    """
    Apply axis limits to the given axes for either x or y axis based on the provided limits.
    The axis_limits argument can contain None for either the lower or upper limit, in which case the current limit will be preserved for that side.
    """

    if axis_cfg is None:
        return

    elif axis_cfg.axis_limits is None:
        return
    
    elif axis_cfg.axis_limits is not None:
        lo, hi = axis_cfg.axis_limits
        cur_lo, cur_hi = ax.get_xlim() if which_axis == "x" else ax.get_ylim()

        new_lo = cur_lo if lo is None else lo
        new_hi = cur_hi if hi is None else hi

        if which_axis == "x":
            ax.set_xlim(new_lo, new_hi)

        else:
            ax.set_ylim(new_lo, new_hi)

def _apply_background_image(ax: Axes, bg: Optional[BackgroundImageCfg]):
    """
    Apply a background image to the given axes based on the provided configuration.
    """

    if bg is None:
        return None

    img = bg.background_image

    if img is None:
        return None

    style = dict(bg.background_image_style)

    if bg.background_image_coords == "axes":
        extent = bg.background_image_extent if bg.background_image_extent is not None else (0.0, 1.0, 0.0, 1.0)

        im = ax.imshow(img,
                       extent = extent,
                       transform = ax.transAxes,
                       origin = bg.background_image_origin,
                       interpolation = bg.background_image_interpolation,
                       alpha = bg.background_image_alpha,
                       zorder = bg.background_image_zorder,
                       **style)

    else:
        if bg.background_image_extent is None:
            # Stretch the image to cover the entire axes area by default if no extent is provided, using the current axes limits to determine the extent in data coordinates.
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()

            extent = (xmin, xmax, ymin, ymax)

        else:
            extent = bg.background_image_extent # Use the provided extent in data coordinates.

        im = ax.imshow(img,
                       extent = extent,
                       origin = bg.background_image_origin,
                       interpolation = bg.background_image_interpolation,
                       alpha = bg.background_image_alpha,
                       zorder = bg.background_image_zorder,
                       **style)

    # Prevent imshow from forcing aspect = "equal" which can distort the image if the axes limits have different scales.
    ax.set_aspect("auto")

    return im

def _get_transform(fig: Figure, ax: Axes, coords: MarkingCoords):
    """
    Get the appropriate transform for the given coordinates type ("data" or "axes") on the specified axes.
    """

    if coords == "axes":
        return ax.transAxes

    return ax.transData

def _apply_markings(fig: Figure, ax_left: Axes, ax_right: Optional[Axes], markings: Optional[Sequence[MarkingObjectCfg]]) -> List[Any]:
    """
    Apply the given markings (lines, rectangles, circles, text, etc.) to the specified axes based on their configuration.
    """

    if not markings:
        return []

    created_markings: List[Any] = []

    for m in markings:
        ax = ax_left if m.marking_object_target_axis == "left" else (ax_right if ax_right is not None else ax_left)

        transform = _get_transform(fig, ax, m.marking_object_coords)

        style = dict(m.marking_object_style)

        if m.marking_object_zorder is not None:
            style["zorder"] = m.marking_object_zorder

        k = m.marking_object_kind

        if k == "hline":
            if m.y is None:
                raise ValueError("The marking kind 'hline' requires the 'y' coordinate to be specified. \n Please provide a valid 'y' value in the MarkingObjectCfg for this marking. \n")

            # For horizontal lines, if the coordinates are in "axes" units, directly use the transform to position the line at the correct y-coordinate across the entire width of the axes.
            # If the coordinates are in "data" units, determine the x-limits of the axes to draw the line across the visible area.
            # In both cases, use Line2D to create the horizontal line and add it to the axes.
            # Determine the x0 and x1 coordinates for the horizontal line based on the marking configuration and the axes limits, then create a Line2D object to represent the horizontal line and add it to the axes.
            if m.marking_object_coords == "axes":
                # Axes coordinates are normalized from 0 to 1 on the respective axis
                x0 = 0.0 if m.x0 is None else float(m.x0)
                x1 = 1.0 if m.x1 is None else float(m.x1)

                ln = Line2D([x0, x1], [float(m.y), float(m.y)], transform = transform, clip_on = m.marking_object_clip_on, **style)

                ax.add_line(ln)

                created_markings.append(ln)

            else:
                x0 = float(np.nanmin(ax.get_xlim())) if m.x0 is None else float(m.x0)
                x1 = float(np.nanmax(ax.get_xlim())) if m.x1 is None else float(m.x1)

                ln = Line2D([x0, x1], [float(m.y), float(m.y)], transform = transform, clip_on = m.marking_object_clip_on, **style)

                ax.add_line(ln)

                created_markings.append(ln)

        elif k == "vline":
            if m.x is None:
                raise ValueError("The marking kind 'vline' requires the 'x' coordinate to be specified. \n Please provide a valid 'x' value in the MarkingObjectCfg for this marking. \n")

            if m.marking_object_coords == "axes":
                y0 = 0.0 if m.y0 is None else float(m.y0)
                y1 = 1.0 if m.y1 is None else float(m.y1)

                ln = Line2D([float(m.x), float(m.x)], [y0, y1], transform = transform, clip_on = m.marking_object_clip_on, **style)
                ax.add_line(ln)

                created_markings.append(ln)

            else:
                y0 = float(np.nanmin(ax.get_ylim())) if m.y0 is None else float(m.y0)
                y1 = float(np.nanmax(ax.get_ylim())) if m.y1 is None else float(m.y1)

                ln = Line2D([float(m.x), float(m.x)], [y0, y1], transform = transform, clip_on = m.marking_object_clip_on, **style)

                ax.add_line(ln)

                created_markings.append(ln)

        elif k == "line":
            if None in (m.x0, m.y0, m.x1, m.y1):
                raise ValueError("The marking kind 'line' requires the coordinates 'x0', 'y0', 'x1', and 'y1' to be specified. \n Please provide valid 'x0', 'y0', 'x1', and 'y1' values in the MarkingObjectCfg for this marking. \n")

            ln = Line2D([float(m.x0), float(m.x1)], [float(m.y0), float(m.y1)], transform = transform, clip_on = m.marking_object_clip_on, **style)

            ax.add_line(ln)

            created_markings.append(ln)

        elif k == "rectangle":
            if None in (m.x, m.y, m.width, m.height):
                raise ValueError("The marking kind 'rectangle' requires the coordinates 'x', 'y', as well as 'width', and 'height' to be specified. \n Please provide valid 'x', 'y', 'width', and 'height' values in the MarkingObjectCfg for this marking. \n")

            rect = patches.Rectangle((float(m.x), float(m.y)),
                                     float(m.width),
                                     float(m.height),
                                     angle = float(m.angle_deg),
                                     transform = transform,
                                     clip_on = m.marking_object_clip_on,
                                     **style)

            ax.add_patch(rect)

            created_markings.append(rect)

        elif k == "circle":
            if None in (m.x, m.y, m.radius):
                raise ValueError("The marking kind 'circle' requires the coordinates 'x', 'y', and the 'radius' to be specified. \n Please provide valid 'x', 'y', and 'radius' values in the MarkingObjectCfg for this marking. \n")

            circ = patches.Circle((float(m.x), float(m.y)),
                                  radius = float(m.radius),
                                  transform = transform,
                                  clip_on = m.marking_object_clip_on,
                                  **style)

            ax.add_patch(circ)

            created_markings.append(circ)

        elif k == "ellipse":
            if None in (m.x, m.y, m.width, m.height):
                raise ValueError("The marking kind 'ellipse' requires the coordinates 'x', 'y', as well as 'width', and 'height' to be specified. \n Please provide valid 'x', 'y', 'width', and 'height' values in the MarkingObjectCfg for this marking. \n")

            ell = patches.Ellipse((float(m.x), float(m.y)),
                                  width = float(m.width),
                                  height = float(m.height),
                                  angle = float(m.angle_deg),
                                  transform = transform,
                                  clip_on = m.marking_object_clip_on,
                                  **style)

            ax.add_patch(ell)

            created_markings.append(ell)

        elif k == "arrow":
            if None in (m.x0, m.y0, m.x1, m.y1):
                raise ValueError("The marking kind 'arrow' requires the coordinates 'x0', 'y0', 'x1', and 'y1' to be specified. \n Please provide valid 'x0', 'y0', 'x1', and 'y1' values in the MarkingObjectCfg for this marking. \n")

            arr = patches.FancyArrowPatch((float(m.x0), float(m.y0)),
                                          (float(m.x1), float(m.y1)),
                                          transform = transform,
                                          clip_on = m.marking_object_clip_on,
                                          **style)

            ax.add_patch(arr)

            created_markings.append(arr)

        elif k == "text":
            if None in (m.x, m.y) or m.text is None:
                raise ValueError("The marking kind 'text' requires the coordinates 'x', 'y', and the 'text' content to be specified. \n Please provide valid 'x', 'y', and 'text' values in the MarkingObjectCfg for this marking. \n")

            txt = ax.text(float(m.x),
                          float(m.y),
                          m.text,
                          rotation = float(m.angle_deg),
                          transform = transform,
                          clip_on = m.marking_object_clip_on,
                          **style)

            created_markings.append(txt)

        else:
            raise ValueError(f"Unsupported marking kind: {k}. \n The 'kind' field in MarkingObjectCfg must be one of 'hline', 'vline', 'line', 'rectangle', 'circle', 'ellipse', 'arrow', or 'text'. \n Please check the configuration of this marking object. \n")

    return created_markings