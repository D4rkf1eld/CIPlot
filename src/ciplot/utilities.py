# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import json

import copy

import numpy as np

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt

from pathlib import Path

from .config import (AxisCfg,
                     BackgroundImageCfg,
                     BrowsePageSettingsCfg,
                     BrowseStructuredPageCfg,
                     BrowseSubplotCfg,
                     DistributionPlotCfg,
                     ExportCfg,
                     GridCfg,
                     HeatmapPlotCfg,
                     LegendCfg,
                     PlotCfg,
                     SeriesCfg)

from .shared import _check_label_uniqueness

from .serialization import (_from_serialized_json,
                            _to_json_serializable,
                            _render_general_settings_import_block,
                            _render_general_settings_python_value,
                            _infer_general_settings_plot_function_name,
                            _render_general_settings_plot_call,
                            _make_restored_settings_safe)

from .browse_helpers import _restore_exported_structured_cfg_node

from .api import browse_series

def get_all_color_palette_names() -> List[str]:
    """
    Get a list of all available color palette names that can be used with the get_color_palette function to retrieve color codes for plotting.
    The returned list includes names of colormaps from matplotlib that are suitable for use as discrete color palettes, such as "tab10", "Set1", etc.

    Returns:
        List[str]: A list of strings representing the names of available color palettes that can be used with the get_color_palette function.
    """

    # Get all colormap names from matplotlib
    all_cmaps = plt.colormaps()

    return all_cmaps

def get_color_palette(num_colors: int, palette_name: Optional[str] = None) -> List[str]:
    """
    Get a list of color codes from a specified color palette, or use a default palette if none is specified.

    Arguments:
        num_colors (int): The number of distinct colors needed in the palette. Must be a non-negative integer. If zero, an empty list will be returned.

        palette_name (Optional[str]): The name of the matplotlib colormap to use as the color palette. If None, a default palette will be used (some examples can be found in this functions declaration).
        The colormap should be one that supports discrete colors (e.g. "tab10", "Set1", etc.) for best results when a specific number of distinct colors is needed.
    """

    if num_colors <= 0:
        return []

    if palette_name is not None:
        try:
            # Palette can be (extraced from get_all_color_palette_names()):
            # Blues, BrBG, BuGn, BuPu, CMRmap, GnBu, Greens, Greys, OrRd, Oranges, PRGn, PiYG, PuBu, PuBuGn, PuOr, PuRd, Purples, RdBu, RdGy, RdPu, RdYlBu, RdYlGn, Reds, Spectral, Wistia
            # YlGn, YlGnBu, YlOrBr, YlOrRd, afmhot, autumn, binary, bone, brg, bwr, cool, coolwarm, copper, cubehelix, flag, gist_earth, gist_gray, gist_heat, gist_ncar, gist_rainbow, gist_stern, gist_yarg, gnuplot, gnuplot2, gray
            # hot, hsv, jet, nipy_spectral, ocean, pink, prism, rainbow, seismic, spring, summer, terrain, winter, Accent, Dark2, Paired, Pastel1, Pastel2, Set1, Set2, Set3, tab10, tab20, tab20b, tab20c

            cmap = plt.get_cmap(palette_name)

            colors = [cmap(i / num_colors) for i in range(num_colors)]

            return [mcolors.to_hex(c) for c in colors]

        except ValueError:
            raise ValueError(f"Invalid palette name: {palette_name}. \n Please provide a valid matplotlib colormap name for the color palette. \n")

    # Default to tab10 which has 10 distinct colors, and repeat, if more colors are needed
    default_cmap = plt.get_cmap("tab10")

    colors = [default_cmap(i % 10) for i in range(num_colors)]

    return [mcolors.to_hex(c) for c in colors]

def apply_settings_with_values_to_series_elements(series: Sequence[SeriesCfg], settings_with_values: List[Dict[str, Any]]) -> Sequence[SeriesCfg]:
    """
    Apply the provided settings with values to the series in the series list in order, and return a new list of SeriesCfg with the settings applied.
    The settings will be applied across all series in order, and if there are more series than settings, the settings will be repeated in order until all series have the settings applied.

    Arguments:
        series (Sequence[SeriesCfg]): A list of SeriesCfg objects representing the series to which the settings should be applied.
        Each SeriesCfg in the list will be assigned settings from the provided settings_with_values list based on its position in the series.

        settings_with_values (List[Dict[str, Any]]): A list of dictionaries, where each dictionary contains setting names as keys and their corresponding values to apply to the series.
        The settings will be assigned to the series in order, and if there are more series than settings, the settings will be repeated from
        the beginning of the list until all series have the settings applied.

    Returns:
        Sequence[SeriesCfg]: A new list of SeriesCfg objects with the settings applied to each series in order.
    """

    if not settings_with_values:
        return series

    configured_series = []

    n_settings = len(settings_with_values)

    for i, s in enumerate(series):
        settings = settings_with_values[i % n_settings]

        s_configured = SeriesCfg(**s.__dict__)

        for setting_name, setting_value in settings.items():
            if hasattr(s_configured, setting_name):
                setattr(s_configured, setting_name, setting_value)

            else:
                raise ValueError(f"Invalid setting name: {setting_name}. \n The SeriesCfg does not have an attribute named '{setting_name}'. \n Please check the provided settings and ensure that they correspond to valid attributes of SeriesCfg. \n")

        configured_series.append(s_configured)

    return configured_series

def apply_settings_with_values_to_multi_series_elements(multi_series: Sequence[Sequence[SeriesCfg]], multi_settings_with_values: Union[Sequence[List[Dict[str, Any]]], List[Dict[str, Any]]]) -> Sequence[Sequence[SeriesCfg]]:
    """
    Apply the provided settings with values to the series in the multi-series list in order, and return a new multi-series list with the settings applied.
    The settings will be applied across all series in order across all pages, and if there are more series than settings, the settings will be repeated in order until all series have the settings applied.

    Arguments:
        multi_series (Sequence[Sequence[SeriesCfg]]): A list of pages, where each page is a list of SeriesCfg objects representing the series to which the settings should be applied.
        Each SeriesCfg in the multi-series list will be assigned settings from the provided multi_settings_with_values based on its position in the overall sequence of series across all pages.

        multi_settings_with_values (Union[Sequence[List[Dict[str, Any]]], List[Dict[str, Any]]]): A list of lists of dictionaries, where each inner list corresponds to a page and contains dictionaries with setting names as keys and their corresponding values to apply to the series on that page.
        Alternatively, if a single list of dictionaries is provided instead of a list of lists, it will be applied across all pages in order. In either case, if there are more series than settings, the settings will be repeated from
        the beginning of the list until all series have the settings applied.

    Returns:
        Sequence[Sequence[SeriesCfg]]: A new multi-series list with the settings applied to each series in order across all pages.
    """

    if not multi_settings_with_values:
        return multi_series

    if isinstance(multi_settings_with_values, list) and all(isinstance(s, dict) for s in multi_settings_with_values):
        # If a single list of dictionaries is provided, apply it across all pages
        multi_settings_with_values = [multi_settings_with_values] * len(multi_series)

    configured_multi_series = []

    n_settings_pages = len(multi_settings_with_values)

    i = 0

    for page_index, page in enumerate(multi_series):
        settings_page = multi_settings_with_values[page_index % n_settings_pages]

        configured_page = []

        i = 0

        for s in page:
            settings = settings_page[i % len(settings_page)]

            s_configured = SeriesCfg(**s.__dict__)

            for setting_name, setting_value in settings.items():
                if hasattr(s_configured, setting_name):
                    setattr(s_configured, setting_name, setting_value)

                else:
                    raise ValueError(f"Invalid setting name: {setting_name}. \n The SeriesCfg does not have an attribute named '{setting_name}'. \n Please check the provided settings and ensure that they correspond to valid attributes of SeriesCfg. \n")

            configured_page.append(s_configured)

            i += 1

        configured_multi_series.append(configured_page)

    return configured_multi_series

def series_from_exported_series_data_json(filepath: Union[str, Path], restore_with_style: bool = False) -> Sequence[SeriesCfg]:
    """
    Load series data from a JSON file that was exported using the _export_series_data function, and return a list of SeriesCfg objects containing the loaded data.
    The JSON file is expected to have a specific structure with an identifier wrapper containing the series data, where each series includes its label, x and y values, and optionally error bars and confidence intervals if they were included in the export.
    If the restore_with_style flag is set to True, the function will also attempt to restore the plotting style information for each series if it is included in the exported JSON data.
    
    Example of expected JSON structure:
    {
        "__series_cfg__": {
            "series_label_1": {
                "x_values": [...],
                "y_values": [...],

                "xerr_values": [...], # Optional
                "yerr_values": [...], # Optional
                "confidence_band_values": [...] # Optional
            },

            "series_label_2": {...},

            ...
        }
    }

    Arguments:
        filepath (Union[str, Path]): The file path to the JSON file containing the exported series data. The file should have been created using the _export_series_data function, which ensures that the JSON structure is compatible with this loading function.

        restore_with_style (bool): Whether to also restore the plotting style information for each series if it is included in the exported JSON data.

    Returns:
        Sequence[SeriesCfg]: A list of SeriesCfg objects, each containing the data for one series as loaded from the JSON file.
    """

    with open(filepath, "r") as f:
        data = json.load(f)

    if "__series_cfg__" not in data:
        raise ValueError("The provided JSON file does not contain the expected '__series_cfg__' identifier. Please provide a valid JSON file that was exported using the _export_series_data function. \n")

    series_data = data["__series_cfg__"]

    series: Sequence[SeriesCfg] = []

    for label, s_data in series_data.items():
        distribution_plot_cfg = _restore_exported_structured_cfg_node(s_data.get("distribution_plot_cfg"), DistributionPlotCfg)

        heatmap_plot_cfg = _restore_exported_structured_cfg_node(s_data.get("heatmap_plot_cfg"), HeatmapPlotCfg)

        s_cfg = SeriesCfg(x_values = s_data.get("x_values"),
                          y_values = s_data.get("y_values"),

                          distribution_plot_cfg = distribution_plot_cfg,

                          heatmap_plot_cfg = heatmap_plot_cfg,

                          label = label,

                          xerr_values = s_data.get("xerr_values"),
                          yerr_values = s_data.get("yerr_values"),
                          confidence_band_values = s_data.get("confidence_band_values"))

        if restore_with_style and "plotting_kind" in s_data:
            s_cfg.plotting_kind = s_data["plotting_kind"]

        if restore_with_style and "plotting_style" in s_data:
            s_cfg.plotting_style = s_data["plotting_style"]

        if restore_with_style and "plot_on_which_y_axis" in s_data:
            s_cfg.plot_on_which_y_axis = s_data["plot_on_which_y_axis"]

        series.append(s_cfg)

    return series

def multi_series_from_exported_multi_series_data_json(filepath: Union[str, Path], restore_with_style: bool = False) -> Sequence[Sequence[SeriesCfg]]:
    """
    Load multi-series data from a JSON file that was exported using the _export_multi_series_data function, and return a list of pages, where each page is a list of SeriesCfg objects containing the loaded data for that page.
    The JSON file is expected to have a specific structure with an identifier wrapper containing the multi-series data, where each page is an array of series, and each series includes its label, x and y values, and optionally error bars and confidence intervals if they were included in the export.
    If the restore_with_style flag is set to True, the function will also attempt to restore the plotting style information for each series if it is included in the exported JSON data.

    Example of expected JSON structure:
    {
        "__multi_series_cfg__": {
            "pages": [
                [
                    {
                        "series_label_1": {
                            "x_values": [...],
                            "y_values": [...],

                            "xerr_values": [...], # Optional
                            "yerr_values": [...], # Optional
                            "confidence_band_values": [...] # Optional
                        }
                    },

                    {
                        "series_label_2": {...}
                    },

                    ...
                ],
                [
                    {
                        "series_label_XYZ": {...}
                    },

                    ...
                ],

                ...
            ]
        }
    }

    Arguments:
        filepath (Union[str, Path]): The file path to the JSON file containing the exported multi-series data. The file should have been created using the _export_multi_series_data function, which ensures that the JSON structure is compatible with this loading function.

        restore_with_style (bool): Whether to also restore the plotting style information for each series if it is included in the exported JSON data.

    Returns:
        Sequence[Sequence[SeriesCfg]]: A list of pages, where each page is a list of SeriesCfg objects containing the data for the series in that page as loaded from the JSON file.
    """

    with open(filepath, "r") as f:
        data = json.load(f)

    if "__multi_series_cfg__" not in data:
        raise ValueError("The provided JSON file does not contain the expected '__multi_series_cfg__' identifier. Please provide a valid JSON file that was exported using the _export_multi_series_data function. \n")

    multi_series_data = data["__multi_series_cfg__"]

    if "pages" not in multi_series_data:
        raise ValueError("The provided JSON file does not contain the expected 'pages' key within the '__multi_series_cfg__' identifier. Please provide a valid JSON file that was exported using the _export_multi_series_data function, which ensures that the JSON structure includes the 'pages' key. \n")

    pages_data = multi_series_data["pages"]

    multi_series: Sequence[Sequence[SeriesCfg]] = []

    for page in pages_data:
        page_series: List[SeriesCfg] = []

        for s_dict in page:
            for label, s_data in s_dict.items():
                distribution_plot_cfg = _restore_exported_structured_cfg_node(s_data.get("distribution_plot_cfg"), DistributionPlotCfg)

                heatmap_plot_cfg = _restore_exported_structured_cfg_node(s_data.get("heatmap_plot_cfg"), HeatmapPlotCfg)

                s_cfg = SeriesCfg(x_values = s_data.get("x_values"),
                                  y_values = s_data.get("y_values"),

                                  distribution_plot_cfg = distribution_plot_cfg,

                                  heatmap_plot_cfg = heatmap_plot_cfg,

                                  label = label,

                                  xerr_values = s_data.get("xerr_values"),
                                  yerr_values = s_data.get("yerr_values"),
                                  confidence_band_values = s_data.get("confidence_band_values"))

                if restore_with_style and "plotting_kind" in s_data:
                    s_cfg.plotting_kind = s_data["plotting_kind"]

                if restore_with_style and "plotting_style" in s_data:
                    s_cfg.plotting_style = s_data["plotting_style"]

                if restore_with_style and "plot_on_which_y_axis" in s_data:
                    s_cfg.plot_on_which_y_axis = s_data["plot_on_which_y_axis"]

                page_series.append(s_cfg)

        multi_series.append(page_series)

    return multi_series

def convert_multi_series_to_series(multi_series: Sequence[Sequence[SeriesCfg]]) -> Sequence[SeriesCfg]:
    """
    Convert a multi-series structure (a list of pages, where each page is a list of SeriesCfg) into a flat list of SeriesCfg by concatenating all the series from all pages into a single list.
    All series labels must be unique across the entire multi-series structure to avoid label conflicts in the resulting flat series list.

    Arguments:
        multi_series (Sequence[Sequence[SeriesCfg]]): The multi-series structure to convert, where each inner list represents a page containing multiple SeriesCfg objects.

    Returns:
        Sequence[SeriesCfg]: A flat list of SeriesCfg objects containing all the series from all pages in the multi-series structure.
    """

    all_series: List[SeriesCfg] = []

    for page in multi_series:
        all_series.extend(page)

    _check_label_uniqueness(all_series)

    return all_series

def swap_transpose_multi_series_pages_content_with_graphs(multi_series: Sequence[Sequence[SeriesCfg]]) -> Sequence[Sequence[SeriesCfg]]:
    """
    Swap the content of a multi-series list split between pages with a split by graphs, by transposing the structure of the multi-series list.
    For example, if the input multi-series list has the structure [[s11, s12, s13], [s21, s22]], where s_ij represents the j-th series in the i-th page, the output will have the structure [[s11, s21], [s12, s22], [s13]].
    This can be useful for reorganizing the structure of the multi-series data when the current split by pages does not align well with the desired grouping of series in the plots.

    Arguments:
        multi_series (Sequence[Sequence[SeriesCfg]]): The multi-series structure to transpose, where each inner list represents a page containing multiple SeriesCfg objects.

    Returns:
        Sequence[Sequence[SeriesCfg]]: A new multi-series structure with the content swapped between pages and graphs, where the series are reorganized according to the transposed structure.
    """

    if not multi_series:
        return multi_series

    n_pages = len(multi_series)

    max_series_per_page = max(len(page) for page in multi_series)

    transposed_multi_series: List[List[SeriesCfg]] = [[] for _ in range(max_series_per_page)]

    for i in range(max_series_per_page):
        for j in range(n_pages):
            if i < len(multi_series[j]):
                transposed_multi_series[i].append(multi_series[j][i])

    return transposed_multi_series

def exemplify_color_palettes_looks(curves_to_plot: int = 10,

                                   show_plot: bool = True,

                                   x_range: Tuple[float, float] = (0, 10),
                                   y_range: Tuple[float, float] = (-1, 1),

                                   palette_names: Union[Sequence[str], str] = "all",

                                   export_color_palette_examples: bool = False,
                                   export_color_palette_output_directory: Optional[Union[str, Path]] = None) -> Tuple[Sequence[Sequence[SeriesCfg]], PlotCfg, LegendCfg, Union[Sequence[str], str]]:
    """
    Generate example plots of different color palettes by creating multiple curves and applying the specified color palettes to them, allowing for a visual comparison of how the colors in each palette look when applied to a set of curves.
    The function creates a specified number of curves with random frequencies and phases, applies the specified color palettes to them, and displays the plots for visual comparison.
    It also provides options for exporting the generated plots and the underlying data for further analysis or use in other contexts.

    Arguments:
        curves_to_plot (int): The number of curves to generate and plot for each color palette. Each curve will have a different random frequency and phase to create a visually distinct set of curves for demonstrating the color palettes.

        show_plot (bool): Whether to display the generated plots after creating them. If False, the plots will be created but not shown, allowing for programmatic use without displaying the figures.

        x_range (Tuple[float, float]): The range of x values for the generated curves, specified as a tuple (min_x, max_x). The curves will be generated with x values evenly spaced within this range.

        y_range (Tuple[float, float]): The range of y values for the generated curves, specified as a tuple (min_y, max_y). The curves will be scaled to fit within this y range.

        palette_names (Union[Sequence[str], str]): The names of the color palettes to exemplify. This can be a list of valid matplotlib colormap names (e.g. ["tab10", "Set1"]) to specify specific palettes, or the string "all" to exemplify all available color palettes.

        export_color_palette_examples (bool): Whether to export the generated color palette example plots and their underlying data. If True, the plots will be saved to files in the specified output directory.

        export_color_palette_output_directory (Optional[Union[str, Path]]): The directory where the generated color palette example plots and their underlying data should be exported if export_color_palette_examples is True.
    """

    xs = np.linspace(x_range[0], x_range[1], 100)

    multi_ys: List[np.ndarray] = []

    for i in range(curves_to_plot):
        frequency = np.random.rand() * 0.5 + i * 0.5

        phase = i * np.pi / (np.random.randint(1, 20))

        argument = frequency * xs + phase

        if np.random.rand() < 0.5:
            f_of_x = np.cos(argument)

        else:
            f_of_x = np.sin(argument)

        # Adjust f_of_x such, that the amplitude is in y_range
        amplitude = (y_range[1] - y_range[0]) / 2

        f_of_x = f_of_x * amplitude + (y_range[0] + y_range[1]) / 2

        multi_ys.append(f_of_x)

    if palette_names == "all":
        _palette_names = get_all_color_palette_names()

    elif isinstance(palette_names, list) and all(isinstance(p, str) for p in palette_names):
        _palette_names = palette_names

    else:
        raise ValueError("Invalid palette_names argument. \n Please provide 'all' to exemplify all available color palettes, or a list of valid matplotlib colormap names to exemplify specific palettes. \n")

    multi_series: List[List[SeriesCfg]] = []

    for palette_name in _palette_names:
        colors = get_color_palette(curves_to_plot, palette_name)

        series: List[SeriesCfg] = []

        for i, y in enumerate(multi_ys):
            series.append(SeriesCfg(x_values = xs.tolist(),
                                    y_values = y.tolist(),

                                    distribution_plot_cfg = None,

                                    heatmap_plot_cfg = None,

                                    label = f"'{palette_name}' example {i + 1}",

                                    plotting_kind = "line",
                                    plotting_style = dict(linestyle = "--", marker = "o", color = colors[i], linewidth = 2, markersize = 6, alpha = 0.8),

                                    is_visible = True,
                                    plot_on_which_y_axis = "left",

                                    xerr_values = None,
                                    yerr_values = None,
                                    confidence_band_values = None))

        multi_series.append(series)

    plot_cfg = PlotCfg(show_plot = show_plot, plot_title = "Color Palette Examples")

    legend_cfg = LegendCfg(show_legend = True)

    export_cfg = ExportCfg(enable_export = export_color_palette_examples,
                           enable_data_export = False,
                           data_export_with_style = False,

                           output_directory = export_color_palette_output_directory,
                           export_name = None,
                           export_data_name = None,
                           series_export_names = _palette_names,
                           output_formats = None,

                           output_dpi = "figure",
                           transparent_background = False,
                           bbox_inches = "tight")

    browse_series(series = None, multi_series = multi_series, markings = None, background = None, plot_cfg = plot_cfg, legend_cfg = legend_cfg, export_cfg = export_cfg)

    return multi_series, plot_cfg, legend_cfg, palette_names

def export_general_dataclasses_settings_to_json(filepath: Union[str, Path], **kwargs: Any) -> None:
    """
    Export general settings (including dataclasses) to a JSON file, with type tags for restoration.
    The provided keyword arguments can include any JSON-serializable values, as well as dataclass instances,
    which will be serialized with type information to allow for accurate restoration later.
    The resulting JSON file will contain a structured representation of the provided settings, including type tags for any dataclasses,
    allowing for accurate restoration of the original settings using the corresponding restore function.

    Arguments:
        filepath (Union[str, Path]): The file path where the JSON file containing the exported settings should be saved.
        The file will be created if it does not exist, and overwritten if it does exist.

        **kwargs: Arbitrary keyword arguments representing the settings to be exported.
        The values can be any JSON-serializable types, as well as dataclass instances, which will be serialized with type information for later restoration.
    """

    path = Path(filepath)
    path.parent.mkdir(parents = True, exist_ok = True)

    serializable_json: Dict[str, Any] = {}

    for k, v in kwargs.items():
        serializable_json[k] = _to_json_serializable(v, path = k)

    with path.open("w", encoding = "utf-8") as f:
        # Use indent for pretty-printing, sort_keys for consistent ordering, ensure_ascii = False to allow Unicode characters,
        # and allow_nan = False to enforce strict JSON compliance by rejecting NaN and Infinity values.
        json.dump(serializable_json, f, indent = 4, sort_keys = True, ensure_ascii = False, allow_nan = False)

def general_dataclasses_settings_to_python_code(filepath: Union[str, Path],
                                                include_imports: bool = True,
                                                import_from: str = "ciplot",
                                                include_plot_call: bool = False,
                                                plot_function_name: Optional[str] = None,
                                                indent_size: int = 4) -> str:
    """
    Convert a JSON file created with export_general_dataclasses_settings_to_json(...)
    into copyable Python code containing the same configuration structure.

    Arguments:
        filepath (Union[str, Path]): Path to the JSON file created by export_general_dataclasses_settings_to_json(...).

        include_imports (bool): If True, prepend import lines for pathlib.Path and the CIPlot dataclasses used by the serialized content.

        import_from (str): Package/module used in the generated import line, for example "ciplot" or "base.utils.CIPlot.src.ciplot".

        include_plot_call (bool): If True, append a best-effort CIPlot API call such as browse_series(...), plot_xy(...),
        or browse_structured_subplot_pages(...), using the variables generated from the JSON keys.

        plot_function_name (Optional[str]): Explicit plot function name to use for the optional plot call.
        If None, the function tries to infer it from the top-level keys.

        indent_size (int): Number of spaces used for one indentation level.

    Returns:
        str: The generated Python code.
    """

    path = Path(filepath)

    with path.open("r", encoding = "utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise TypeError(f"Expected the JSON file to contain a dictionary at the top level, but got {type(raw).__name__}. \n")

    blocks: List[str] = []

    if include_imports:
        import_block = _render_general_settings_import_block(raw, import_from = import_from)

        if import_block:
            blocks.append(import_block)

    assignments: List[str] = []

    for name, value in raw.items():
        assignments.append(f"{name} = {_render_general_settings_python_value(value, indent_level = 0, indent_size = indent_size)}")

    blocks.append("\n\n".join(assignments))

    if include_plot_call:
        resolved_plot_function_name = plot_function_name or _infer_general_settings_plot_function_name(raw)

        if resolved_plot_function_name is None:
            raise ValueError("Could not infer a plot function from the exported top-level keys. Please pass plot_function_name explicitly. \n")

        if include_imports:
            # Add the API function import next to the generated code instead of hiding it in the dataclass import collector
            api_import = f"from {import_from} import {resolved_plot_function_name}"

            blocks.insert(1 if blocks else 0, api_import)

        blocks.append(_render_general_settings_plot_call(raw, resolved_plot_function_name, indent_size = indent_size))

    return "\n\n".join(blocks)

def print_general_dataclasses_settings_from_json(filepath: Union[str, Path],
                                                 include_imports: bool = True,
                                                 import_from: str = "ciplot",
                                                 include_plot_call: bool = False,
                                                 plot_function_name: Optional[str] = None,
                                                 indent_size: int = 4) -> str:
    """
    Print and return copyable Python code for a JSON file created with
    export_general_dataclasses_settings_to_json(...).
    """

    code = general_dataclasses_settings_to_python_code(filepath = filepath,
                                                       include_imports = include_imports,
                                                       import_from = import_from,
                                                       include_plot_call = include_plot_call,
                                                       plot_function_name = plot_function_name,
                                                       indent_size = indent_size)

    print(code)

    return code

def restore_general_dataclasses_settings_from_json(filepath: Union[str, Path], allow_restored_export_actions: bool = False) -> Dict[str, Any]:
    """
    Restore settings from a JSON file previously created by export_general_dataclasses_settings_to_json().

    Arguments:
        filepath (Union[str, Path]): The file path to the JSON file containing the exported settings.
        The file should have been created using the export_general_dataclasses_settings_to_json function,
        which ensures that the JSON structure is compatible with this restoration function.

        allow_restored_export_actions (bool): Whether to allow restored settings that correspond to export actions (e.g. ExportCfg) to be
        returned as their original dataclass instances with all their attributes. If False, any restored settings that correspond to export actions
        will be made safe by removing attributes, that could trigger export actions.

    Returns:
        Dict[str, Any]: A dictionary containing the restored settings, where the keys correspond to the original keyword argument names provided during export,
        and the values are the restored Python objects, including any dataclass instances that were serialized with type information for accurate restoration.

    Note:
        The dataclass restoration requires the dataclass types to be importable (module + qualname) in current environment.
    """

    path = Path(filepath)

    with path.open("r", encoding = "utf-8") as f:
        raw = json.load(f)

    if not isinstance(raw, dict):
        raise TypeError(f"Expected the JSON file to contain a dictionary at the top level, but got {type(raw).__name__}. \n")

    restored_dataclasses: Dict[str, Any] = {}

    for k, v in raw.items():
        restored = _from_serialized_json(v)

        if not allow_restored_export_actions:
            restored = _make_restored_settings_safe(restored)

        restored_dataclasses[k] = restored

    return restored_dataclasses

def structured_pages_from_exported_structured_subplot_pages_data_json(filepath: Union[str, Path], restore_with_style: bool = False) -> Sequence[BrowseStructuredPageCfg]:
    """
    Load structured subplot pages from a JSON file that was exported by _export_structured_subplot_pages_data(...), and reconstruct them as a list of BrowseStructuredPageCfg objects.
    If restore_with_style = False, only the page, row and subplot structure and series data are restored.

    If restore_with_style = True, page settings and subplot-local overrides are restored as far as possible.
    Nodes that could not be serialized exactly during export are restored as None.

    Expected JSON structure:
    {
        "__structured_subplot_pages_cfg__": {
            "pages": [
                {
                    "page_index": 0,
                    "page_label": "...",
                    "page_settings_cfg": ..., # Optional
                    "rows": [
                        [
                            {
                                "row_index": 0,
                                "column_index": 0,
                                "subplot_title": "...",
                                "show_subplot": true,
                                "subplot_overrides": ..., # Optional
                                "series": [
                                    {
                                        "label": "...",
                                        "is_visible": true,
                                        "x_values": [...],
                                        "y_values": [...],
                                        ...
                                    }
                                ]
                            }
                        ]
                    ]
                }
            ]
        }
    }
    """

    path = Path(filepath)

    with path.open("r", encoding = "utf-8") as f:
        data = json.load(f)

    if "__structured_subplot_pages_cfg__" not in data:
        raise ValueError("The provided JSON file does not contain the expected '__structured_subplot_pages_cfg__' identifier. \n" "Please provide a valid JSON file that was exported using _export_structured_subplot_pages_data(...). \n")

    structured_data = data["__structured_subplot_pages_cfg__"]

    if not isinstance(structured_data, dict):
        raise TypeError("The value stored under '__structured_subplot_pages_cfg__' must be a dictionary. \n")

    if "pages" not in structured_data:
        raise ValueError("The provided JSON file does not contain the expected 'pages' key inside '__structured_subplot_pages_cfg__'. \n")

    pages_data = structured_data["pages"]

    if not isinstance(pages_data, list):
        raise TypeError("The 'pages' entry inside '__structured_subplot_pages_cfg__' must be a list. \n")

    structured_pages: List[BrowseStructuredPageCfg] = []

    for page_index, page_data in enumerate(pages_data):
        if not isinstance(page_data, dict):
            raise TypeError(f"Expected page entry {page_index} to be a dictionary, got {type(page_data).__name__}. \n")

        page_title = page_data.get("page_title")

        page_settings_cfg = None

        if restore_with_style and "page_settings_cfg" in page_data:
            page_settings_cfg = _restore_exported_structured_cfg_node(page_data.get("page_settings_cfg"), BrowsePageSettingsCfg)

        rows_data = page_data.get("rows")

        if rows_data is None:
            raise ValueError(f"Structured page {page_index} is missing the required 'rows' key. \n")

        if not isinstance(rows_data, list):
            raise TypeError(f"The 'rows' entry for structured page {page_index} must be a list, got {type(rows_data).__name__}. \n")

        restored_rows: List[List[BrowseSubplotCfg]] = []

        for row_index, row_data in enumerate(rows_data):
            if not isinstance(row_data, list):
                raise TypeError(f"Expected row {row_index} of structured page {page_index} to be a list, got {type(row_data).__name__}. \n")

            restored_row: List[BrowseSubplotCfg] = []

            for col_index, subplot_data in enumerate(row_data):
                if not isinstance(subplot_data, dict):
                    raise TypeError(f"Expected subplot ({row_index}, {col_index}) of structured page {page_index} to be a dictionary, got {type(subplot_data).__name__}. \n")

                series_payload = subplot_data.get("series", [])

                if not isinstance(series_payload, list):
                    raise TypeError(f"The 'series' entry for structured page {page_index}, row {row_index}, column {col_index} must be a list. \n")

                restored_series: List[SeriesCfg] = []

                for series_index, s_data in enumerate(series_payload):
                    if not isinstance(s_data, dict):
                        raise TypeError(f"Expected series entry {series_index} in structured page {page_index}, row {row_index}, column {col_index} to be a dictionary, got {type(s_data).__name__}. \n")

                    if "x_values" not in s_data or "y_values" not in s_data:
                        raise ValueError(f"Series entry {series_index} in structured page {page_index}, row {row_index}, column {col_index} is missing 'x_values' and/or 'y_values'. \n")

                    distribution_plot_cfg = _restore_exported_structured_cfg_node(s_data.get("distribution_plot_cfg"), DistributionPlotCfg)

                    heatmap_plot_cfg = _restore_exported_structured_cfg_node(s_data.get("heatmap_plot_cfg"), HeatmapPlotCfg)

                    s_cfg = SeriesCfg(x_values = s_data.get("x_values"),
                                      y_values = s_data.get("y_values"),

                                      distribution_plot_cfg = distribution_plot_cfg,

                                      heatmap_plot_cfg = heatmap_plot_cfg,

                                      label = s_data.get("label"),

                                      plotting_kind = s_data.get("plotting_kind", "line") if restore_with_style else "line",
                                      plotting_style = s_data.get("plotting_style", {}) if restore_with_style else {},

                                      is_visible = s_data.get("is_visible", True),
                                      plot_on_which_y_axis = s_data.get("plot_on_which_y_axis", "left") if restore_with_style else "left",

                                      xerr_values = s_data.get("xerr_values"),
                                      yerr_values = s_data.get("yerr_values"),
                                      confidence_band_values = s_data.get("confidence_band_values"))

                    restored_series.append(s_cfg)

                subplot_kwargs: Dict[str, Any] = {"series": restored_series}

                if restore_with_style:
                    overrides = subplot_data.get("subplot_overrides", {})

                    if overrides is None:
                        overrides = {}

                    if not isinstance(overrides, dict):
                        raise TypeError(f"The 'subplot_overrides' entry for structured page {page_index}, row {row_index}, column {col_index} must be a dictionary if present. \n")

                    markings_node = overrides.get("markings")

                    if markings_node is not None:
                        restored_markings = _from_serialized_json(markings_node)

                        subplot_kwargs["markings"] = restored_markings

                    subplot_kwargs["background"] = _restore_exported_structured_cfg_node(overrides.get("background"), BackgroundImageCfg)

                    subplot_kwargs["plot_cfg"] = _restore_exported_structured_cfg_node(overrides.get("plot_cfg"), PlotCfg)

                    subplot_kwargs["x_axis_cfg"] = _restore_exported_structured_cfg_node(overrides.get("x_axis_cfg"), AxisCfg)

                    subplot_kwargs["y_axis_cfg"] = _restore_exported_structured_cfg_node(overrides.get("y_axis_cfg"), AxisCfg)

                    subplot_kwargs["grid_cfg"] = _restore_exported_structured_cfg_node(overrides.get("grid_cfg"), GridCfg)

                    subplot_kwargs["legend_cfg"] = _restore_exported_structured_cfg_node(overrides.get("legend_cfg"), LegendCfg)

                restored_row.append(BrowseSubplotCfg(**subplot_kwargs))

            restored_rows.append(restored_row)

        structured_pages.append(BrowseStructuredPageCfg(rows = restored_rows,
                                                        page_title = page_title,
                                                        page_settings_cfg = page_settings_cfg))

    return structured_pages

def convert_structured_pages_to_multi_series(structured_pages: Sequence[BrowseStructuredPageCfg]) -> Sequence[Sequence[SeriesCfg]]:
    """
    Flatten the structured pages container into the multi_series representation.
    """

    flat_multi_series: List[List[SeriesCfg]] = []

    for page_index, page_cfg in enumerate(structured_pages):
        if not isinstance(page_cfg, BrowseStructuredPageCfg):
            raise TypeError(f"Expected structured_pages[{page_index}] to be a BrowseStructuredPageCfg, got {type(page_cfg).__name__}. \n")

        flat_page: List[SeriesCfg] = []

        for row_index, row in enumerate(page_cfg.rows):
            if not isinstance(row, Sequence):
                raise TypeError(f"Expected row {row_index} of structured_pages[{page_index}] to be a sequence, got {type(row).__name__}. \n")

            for col_index, subplot_cfg in enumerate(row):
                if not isinstance(subplot_cfg, BrowseSubplotCfg):
                    raise TypeError(f"Expected subplot ({row_index}, {col_index}) of structured_pages[{page_index}] to be a BrowseSubplotCfg, got {type(subplot_cfg).__name__}. \n")

                for s in subplot_cfg.series:
                    flat_page.append(copy.deepcopy(s))

        flat_multi_series.append(flat_page)

    return flat_multi_series