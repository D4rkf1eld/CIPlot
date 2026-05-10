# Copyright (c) D4rkf1eld 2026. All rights reserved.

from .utilities import (apply_settings_with_values_to_multi_series_elements,
                        apply_settings_with_values_to_series_elements,
                        convert_multi_series_to_series,
                        convert_structured_pages_to_multi_series,
                        exemplify_color_palettes_looks,
                        export_general_dataclasses_settings_to_json,
                        general_dataclasses_settings_to_python_code,
                        get_all_color_palette_names,
                        get_color_palette,
                        multi_series_from_exported_multi_series_data_json,
                        print_general_dataclasses_settings_from_json,
                        restore_general_dataclasses_settings_from_json,
                        series_from_exported_series_data_json,
                        structured_pages_from_exported_structured_subplot_pages_data_json,
                        swap_transpose_multi_series_pages_content_with_graphs)

from .api import plot_xy, browse_series, browse_structured_subplot_pages

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
                     MarkingObjectCfg,
                     PlotCfg,
                     SeriesCfg,
                     TickCfg)

__all__ = ["_get_version",

           "TickCfg",
           "AxisCfg",
           "GridCfg",
           "LegendCfg",
           "ExportCfg",
           "DistributionPlotCfg",
           "HeatmapPlotCfg",
           "SeriesCfg",
           "MarkingObjectCfg",
           "BackgroundImageCfg",
           "PlotCfg",
           "BrowsePageSettingsCfg",
           "BrowseSubplotCfg",
           "BrowseStructuredPageCfg",

           "plot_xy",
           "browse_series",
           "browse_structured_subplot_pages",

           "get_all_color_palette_names",
           "get_color_palette",
           "apply_settings_with_values_to_series_elements",
           "apply_settings_with_values_to_multi_series_elements",
           "series_from_exported_series_data_json",
           "multi_series_from_exported_multi_series_data_json",
           "convert_multi_series_to_series",
           "swap_transpose_multi_series_pages_content_with_graphs",
           "exemplify_color_palettes_looks",
           "export_general_dataclasses_settings_to_json",
           "general_dataclasses_settings_to_python_code",
           "print_general_dataclasses_settings_from_json",
           "restore_general_dataclasses_settings_from_json",
           "structured_pages_from_exported_structured_subplot_pages_data_json",
           "convert_structured_pages_to_multi_series"]

def _get_version() -> str:
    """
    Get the current version of the library.
    """

    from .version import __VERSION__

    return __VERSION__