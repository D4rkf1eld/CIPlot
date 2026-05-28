# Copyright (c) D4rkf1eld 2026. All rights reserved.

from typing import Dict, Iterable, List

import matplotlib.pyplot as plt

from matplotlib.figure import Figure

_TRACKED_FIGURES: Dict[str, List[Figure]] = {}

def _close_tracked_figures(api_name: str):
    """
    Close all figures currently tracked for one public CIPlot API.
    This keeps repeated top-level calls from accumulating open matplotlib windows.
    """

    tracked_figures = _TRACKED_FIGURES.pop(api_name, [])

    for fig in tracked_figures:
        try:
            fig_number = getattr(fig, "number", None)

            if fig_number is None or plt.fignum_exists(fig_number):
                plt.close(fig)

        except Exception:
            pass

def _track_figures(api_name: str, figures: Iterable[Figure]):
    """
    Replace the tracked figure list for one public CIPlot API.
    """

    _TRACKED_FIGURES[api_name] = [fig for fig in figures if fig is not None]