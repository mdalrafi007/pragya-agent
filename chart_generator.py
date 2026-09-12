"""chart_generator.py - matplotlib charts with EN/BN titles, headless-safe."""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["axes.unicode_minus"] = False


def generate_chart(series_dict, title_en, title_bn, xlabel, ylabel, out_path):
    """
    series_dict: {label: pandas.Series} - one or more series to plot together.
    out_path: where to save the PNG.

    Note: the default matplotlib font (DejaVu Sans) doesn't include Bengali
    glyphs, so the Bangla title may render as boxes unless a Bengali-capable
    font (e.g. "Noto Sans Bengali") is installed and set via
    plt.rcParams['font.family']. English labels always render fine.
    """
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    plt.figure(figsize=(9, 5))
    for label, series in series_dict.items():
        s = series.dropna().sort_index()
        if len(s):
            plt.plot(s.index, s.values, marker="o", label=label)

    plt.title(f"{title_en}\n{title_bn}", fontsize=12)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130)
    plt.close()
    return out_path
