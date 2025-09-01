import matplotlib.pyplot as plt
import numpy as np
def plot_tco_comparison(all_tco: list[dict], all_names: list[str], colors) -> plt.Figure:
    # Collect all possible keys
    all_keys = sorted({k for d in all_tco for k in d.keys()})

    # Convert dicts to aligned arrays
    values = np.array([[d.get(k, 0) for k in all_keys] for d in all_tco])

    # Plot
    fig, ax = plt.subplots(figsize=(15, 10), constrained_layout=True)

    x = np.arange(len(all_tco))
    bottom = np.zeros(len(all_tco))

    for i, key in enumerate(all_keys):
        current_bar = ax.bar(x, values[:, i], bottom=bottom, label=key, color=colors[key])
        bottom += values[:, i]
        ax.bar_label(current_bar, label_type="center", padding=3, fmt="%.2f")

    totals = values.sum(axis=1)
    for xi, total in zip(x, totals):
        ax.text(round(xi, 2), total + 0.3, str(round(total, 2)), ha="center", va="bottom", fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([all_names[i] for i in range(len(all_tco))])
    ax.set_ylabel("Value")
    ax.legend(title="Keys", loc="upper left", bbox_to_anchor=(1.05, 1))
    return fig