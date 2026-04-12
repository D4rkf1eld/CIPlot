# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Mapping, Sequence, Tuple

import os
import json

from pathlib import Path

from matplotlib.figure import Figure

from .config import BrowseStructuredPageCfg, ExportCfg, PlotCfg, SeriesCfg
from .serialization import _to_json_serializable
from .shared import _check_label_uniqueness, _enforce_json_serializability

def _normalize_output_formats(output_formats: Tuple[str, ...]) -> Tuple[str, ...]:
    """
    Normalize the output formats for exporting the figure.
    It allows for a compact string representation of formats (e.g. "pdf" instead of ("p", "d", "f")) and ensures that the output is always a tuple of strings.
    """

    if not output_formats:
        return ("pdf",)

    if all(isinstance(x, str) and len(x) == 1 for x in output_formats):
        joined = "".join(output_formats)

        if joined.isalpha() and len(joined) > 1:

            return (joined,)

    return output_formats

def _export_figure(fig: Figure, export_cfg: ExportCfg):
    """
    Export the given figure to files based on the provided export configuration.
    """

    if not export_cfg.enable_export:
        return

    os.makedirs(export_cfg.output_directory, exist_ok = True)

    formats = _normalize_output_formats(export_cfg.output_formats)

    for fmt in formats:
        out_path = os.path.join(export_cfg.output_directory, f"{export_cfg.export_name}.{fmt}")

        fig.savefig(out_path, dpi = export_cfg.output_dpi, format = fmt, transparent = export_cfg.transparent_background, bbox_inches = export_cfg.bbox_inches)

def _export_series_data(series: Sequence[SeriesCfg], export_cfg: ExportCfg):
    """
    Export the data of the provided series list to a JSON file based on the provided export configuration.
    The exported JSON file will contain an array of series, where each series includes its label, x and y values, and optionally error bars and confidence intervals if they are provided in the SeriesCfg.
    Additionally, if the export configuration specifies to include style information, the plotting kind, style and y-axis assignment will also be included in the exported data for each series.
    This allows for a more complete representation of the series data and its visual styling in the exported JSON file.
    """

    if not export_cfg.enable_data_export:
        return

    _check_label_uniqueness(series)

    data_export_directory = Path(export_cfg.output_directory)
    data_export_directory.mkdir(parents = True, exist_ok = True)

    data_export_filepath = data_export_directory / Path(f"{export_cfg.export_data_name}.json")

    export_data: Dict[str, Any] = {}

    for s in series:
        s_data: Dict[str, Any] = {"x_values": _enforce_json_serializability(s.x_values),
                                  "y_values": _enforce_json_serializability(s.y_values)}

        if s.distribution_plot_cfg is not None:
            s_data["distribution_plot_cfg"] = _to_json_serializable(s.distribution_plot_cfg, path = f"series[{s.label if s.label else 'unnamed'}].distribution_plot_cfg")

        if s.heatmap_plot_cfg is not None:
            s_data["heatmap_plot_cfg"] = _to_json_serializable(s.heatmap_plot_cfg, path = f"series[{s.label if s.label else 'unnamed'}].heatmap_plot_cfg")

        if s.xerr_values is not None:
            s_data["xerr_values"] = _enforce_json_serializability(s.xerr_values)

        if s.yerr_values is not None:
            s_data["yerr_values"] = _enforce_json_serializability(s.yerr_values)

        if s.confidence_band_values is not None:
            s_data["confidence_band_values"] = _enforce_json_serializability(s.confidence_band_values)

        if export_cfg.data_export_with_style:
            if s.plotting_kind is not None:
                s_data["plotting_kind"] = s.plotting_kind

            if s.plotting_style is not None:
                s_data["plotting_style"] = s.plotting_style

            if s.plot_on_which_y_axis is not None:
                s_data["plot_on_which_y_axis"] = s.plot_on_which_y_axis

        export_data[s.label if s.label else f"series_{id(s)}"] = s_data

    _identifier_wrapper: Dict[str, Dict] = {"__series_cfg__": export_data}

    with open(data_export_filepath, "w") as f:
        json.dump(_identifier_wrapper, f, indent = 4)

def _export_multi_series_data(multi_series: Sequence[Sequence[SeriesCfg]], export_cfg: ExportCfg):
    """
    Export the data of the provided multi-series list to a JSON file based on the provided export configuration.
    The exported JSON file will contain an array of pages, where each page is an array of series, and each series includes its label,
    x and y values, and optionally error bars and confidence intervals if they are provided in the SeriesCfg.
    Additionally, if the export configuration specifies to include style information, the plotting kind, style and y-axis assignment will also be included in the exported data for each series.
    This allows for a more complete representation of the multi-series data and its visual styling in the exported JSON file, while maintaining a clear structure that differentiates between different pages of series.
    """

    if not export_cfg.enable_data_export:
        return
    
    for page in multi_series:
        _check_label_uniqueness(page) # Check label uniqueness for each page separately, as labels only need to be unique within the same page for the export format. Per page differentiation is guaranteed anyway by the page structure in the exported JSON.

    data_export_directory = Path(export_cfg.output_directory)
    data_export_directory.mkdir(parents = True, exist_ok = True)

    data_export_filepath = data_export_directory / Path(f"{export_cfg.export_data_name}.json")

    export_data: Dict[str, Any] = {"pages": []}

    for page in multi_series:
        page_data = []

        for s in page:
            s_data: Dict[str, Any] = {"x_values": _enforce_json_serializability(s.x_values),
                                      "y_values": _enforce_json_serializability(s.y_values)}

            if s.distribution_plot_cfg is not None:
                s_data["distribution_plot_cfg"] = _to_json_serializable(s.distribution_plot_cfg, path = f"pages[{len(export_data['pages'])}].series[{s.label if s.label else 'unnamed'}].distribution_plot_cfg")

            if s.heatmap_plot_cfg is not None:
                s_data["heatmap_plot_cfg"] = _to_json_serializable(s.heatmap_plot_cfg, path = f"pages[{len(export_data['pages'])}].series[{s.label if s.label else 'unnamed'}].heatmap_plot_cfg")

            if s.xerr_values is not None:
                s_data["xerr_values"] = _enforce_json_serializability(s.xerr_values)

            if s.yerr_values is not None:
                s_data["yerr_values"] = _enforce_json_serializability(s.yerr_values)

            if s.confidence_band_values is not None:
                s_data["confidence_band_values"] = _enforce_json_serializability(s.confidence_band_values)

            if export_cfg.data_export_with_style:
                if s.plotting_kind is not None:
                    s_data["plotting_kind"] = s.plotting_kind

                if s.plotting_style is not None:
                    s_data["plotting_style"] = s.plotting_style

                if s.plot_on_which_y_axis is not None:
                    s_data["plot_on_which_y_axis"] = s.plot_on_which_y_axis

            page_data.append({s.label if s.label else f"series_{id(s)}": s_data})

        export_data["pages"].append(page_data)

    _identifier_wrapper: Dict[str, Dict] = {"__multi_series_cfg__": export_data}

    with open(data_export_filepath, "w") as f:
        json.dump(_identifier_wrapper, f, indent = 4)

def _export_structured_subplot_pages_data(structured_pages: Sequence[BrowseStructuredPageCfg], export_cfg: ExportCfg):
    """
    Export structured pages browse data as JSON, including all series data and optionally style information,
    in a structured format that reflects the page and subplot hierarchy.
    """

    if not export_cfg.enable_data_export:
        return

    data_export_directory = Path(export_cfg.output_directory)
    data_export_directory.mkdir(parents = True, exist_ok = True)

    export_data_name = export_cfg.export_data_name if export_cfg.export_data_name else "data"
    data_export_filepath = data_export_directory / Path(f"{export_data_name}.json")

    export_data: Dict[str, Any] = {"pages": []}

    for page_index, page_cfg in enumerate(structured_pages):
        page_payload = {"page_index": page_index, "page_title": page_cfg.page_title, "rows": []}

        if export_cfg.data_export_with_style:
            page_payload["page_settings_cfg"] = _to_json_serializable(page_cfg.page_settings_cfg, path = f"pages[{page_index}].page_settings_cfg")

        for row_index, row in enumerate(page_cfg.rows):
            row_payload: List[Dict[str, Any]] = []

            for col_index, subplot_cfg in enumerate(row):
                subplot_title = "Plot"
                show_subplot = True

                if isinstance(subplot_cfg.plot_cfg, PlotCfg):
                    subplot_title = subplot_cfg.plot_cfg.plot_title or "Plot"
                    show_subplot = subplot_cfg.plot_cfg.show_plot

                elif isinstance(subplot_cfg.plot_cfg, Mapping):
                    subplot_title = subplot_cfg.plot_cfg.get("plot_title") or "Plot"
                    show_subplot = subplot_cfg.plot_cfg.get("show_plot", True)

                subplot_payload = {"row_index": row_index,
                                   "column_index": col_index,
                                   "subplot_title": subplot_title,
                                   "show_subplot": show_subplot,
                                   "series": []}

                if export_cfg.data_export_with_style:
                    subplot_payload["subplot_overrides"] = {"markings": _to_json_serializable(subplot_cfg.markings, path = f"pages[{page_index}].rows[{row_index}][{col_index}].markings"),
                                                            "background": _to_json_serializable(subplot_cfg.background, path = f"pages[{page_index}].rows[{row_index}][{col_index}].background"),

                                                            "plot_cfg": _to_json_serializable(subplot_cfg.plot_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].plot_cfg"),

                                                            "x_axis_cfg": _to_json_serializable(subplot_cfg.x_axis_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].x_axis_cfg"),
                                                            "y_axis_cfg": _to_json_serializable(subplot_cfg.y_axis_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].y_axis_cfg"),

                                                            "grid_cfg": _to_json_serializable(subplot_cfg.grid_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].grid_cfg"),
                                                            "legend_cfg": _to_json_serializable(subplot_cfg.legend_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].legend_cfg")}

                for series_index, s in enumerate(subplot_cfg.series):
                    s_payload = {"label": s.label,

                                 "is_visible": s.is_visible,

                                 "x_values": _enforce_json_serializability(s.x_values),
                                 "y_values": _enforce_json_serializability(s.y_values)}

                    if s.distribution_plot_cfg is not None:
                        s_payload["distribution_plot_cfg"] = _to_json_serializable(s.distribution_plot_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].series[{series_index if 'series_index' in locals() else 0}].distribution_plot_cfg")

                    if s.heatmap_plot_cfg is not None:
                        s_payload["heatmap_plot_cfg"] = _to_json_serializable(s.heatmap_plot_cfg, path = f"pages[{page_index}].rows[{row_index}][{col_index}].series[{series_index if 'series_index' in locals() else 0}].heatmap_plot_cfg")

                    if s.xerr_values is not None:
                        s_payload["xerr_values"] = _enforce_json_serializability(s.xerr_values)

                    if s.yerr_values is not None:
                        s_payload["yerr_values"] = _enforce_json_serializability(s.yerr_values)

                    if s.confidence_band_values is not None:
                        s_payload["confidence_band_values"] = _enforce_json_serializability(s.confidence_band_values)

                    if export_cfg.data_export_with_style:
                        s_payload["plotting_kind"] = s.plotting_kind

                        s_payload["plotting_style"] = s.plotting_style

                        s_payload["plot_on_which_y_axis"] = s.plot_on_which_y_axis

                    subplot_payload["series"].append(s_payload)

                row_payload.append(subplot_payload)

            page_payload["rows"].append(row_payload)

        export_data["pages"].append(page_payload)

    _identifier_wrapper: Dict[str, Any] = {"__structured_subplot_pages_cfg__": export_data}

    with data_export_filepath.open("w", encoding = "utf-8") as f:
        json.dump(_identifier_wrapper, f, indent = 4, ensure_ascii = False)