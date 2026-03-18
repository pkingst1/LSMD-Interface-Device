"""
bode_plot.py
------------
Calculates and plots the attenuation (dB) of one or more filters on the same
interactive Bode magnitude plot. Labels each notch frequency with its Hz and dB value.

Usage:
  python bode_plot.py

Requirements:
  pip install pandas numpy plotly
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ── CONFIG ────────────────────────────────────────────────────────────────────

FILTERS = [
    {
        "label":      "Notch 50 Hz",
        "input_csv":  r"C:\Users\alxhu\OneDrive - University of New Brunswick\School\5th year\ENGG 4000\Data collection\Notch 50Hz\50Hz_NF.csv",
        "output_csv": r"C:\Users\alxhu\OneDrive - University of New Brunswick\School\5th year\ENGG 4000\Data collection\Notch 50Hz\50Hz_N50Hz.csv",
        "color":      "royalblue",
        # Frequencies to label (Hz) — add/remove as needed
        "notch_freqs": [50, 60, 100, 120, 150],
    },
]

TIME_COL   = "Time (s)"
SIGNAL_COL = "Force (N)"

# Frequency range to display (Hz)
FREQ_MIN = 1.0
FREQ_MAX = 600.0

# ── LOAD ──────────────────────────────────────────────────────────────────────

def load_signal(filepath: str) -> tuple[np.ndarray, float]:
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df[TIME_COL]   = pd.to_numeric(df[TIME_COL],   errors="coerce")
    df[SIGNAL_COL] = pd.to_numeric(df[SIGNAL_COL], errors="coerce")
    df = df.dropna(subset=[TIME_COL, SIGNAL_COL]).sort_values(TIME_COL)
    fs = 1.0 / df[TIME_COL].diff().median()
    return df[SIGNAL_COL].values, fs


def compute_attenuation(input_csv: str, output_csv: str):
    sig_in,  fs_in  = load_signal(input_csv)
    sig_out, fs_out = load_signal(output_csv)

    if abs(fs_in - fs_out) > 1:
        print(f"  Warning: sample rates differ ({fs_in:.1f} vs {fs_out:.1f} Hz). Using input rate.")
    fs = fs_in
    print(f"  Sample rate : {fs:.1f} Hz")

    N = min(len(sig_in), len(sig_out))
    sig_in  = sig_in[:N]
    sig_out = sig_out[:N]

    window  = np.hanning(N)
    fft_in  = np.abs(np.fft.rfft(sig_in  * window))
    fft_out = np.abs(np.fft.rfft(sig_out * window))
    freqs   = np.fft.rfftfreq(N, d=1.0 / fs)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio          = np.where(fft_in > 1e-10, fft_out / fft_in, np.nan)
        attenuation_db = 20.0 * np.log10(ratio)

    return freqs, attenuation_db

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    fig = go.Figure()

    for f in FILTERS:
        print(f"\nLoading: {f['label']}")
        freqs, attenuation_db = compute_attenuation(f["input_csv"], f["output_csv"])

        # Clip to display range
        mask       = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)
        freqs_plot = freqs[mask]
        atten_plot = attenuation_db[mask]

        fig.add_trace(go.Scatter(
            x=freqs_plot,
            y=atten_plot,
            mode="lines",
            name=f["label"],
            line=dict(color=f["color"], width=2),
            hovertemplate=f"<b>%{{x:.1f}} Hz</b><br>%{{y:.2f}} dB<extra>{f['label']}</extra>",
        ))

        # Annotate each notch frequency — find local minimum near each target
        search_window = 8  # Hz either side to find the true notch tip
        for notch_idx, target_hz in enumerate(f.get("notch_freqs", [])):
            # Find FFT bins within the search window around the target frequency
            window_mask = (freqs >= target_hz - search_window) & (freqs <= target_hz + search_window)
            if not np.any(window_mask):
                continue
            local_freqs = freqs[window_mask]
            local_atten = attenuation_db[window_mask]
            valid       = ~np.isnan(local_atten)
            if not np.any(valid):
                continue
            # Pick the deepest point in the window
            local_min_idx = np.nanargmin(local_atten[valid])
            notch_freq    = local_freqs[valid][local_min_idx]
            notch_db      = local_atten[valid][local_min_idx]

            print(f"  {target_hz} Hz notch: {notch_db:.2f} dB at {notch_freq:.1f} Hz")

            # Fully manual offsets per frequency to guarantee no overlap
            offsets = {
                50:  (-80,  80),
                60:  (-30,  40),
                100: (-80,  80),
                120: ( 80,  80),
                150: ( 80, 120),
            }
            ax_off, ay_off = offsets.get(target_hz, (0, 80))
            fig.add_annotation(
                x=np.log10(notch_freq),
                y=notch_db,
                xref="x",
                yref="y",
                text=f"<b>{target_hz} Hz</b><br>{notch_db:.1f} dB",
                showarrow=True,
                arrowhead=2,
                arrowcolor=f["color"],
                font=dict(color=f["color"], size=11),
                bgcolor="white",
                bordercolor=f["color"],
                borderwidth=1,
                ax=ax_off,
                ay=ay_off,
                standoff=4,
            )

    # 0 dB reference line
    fig.add_hline(
        y=0,
        line=dict(color="grey", dash="dash", width=1),
        annotation_text="0 dB",
        annotation_position="right",
    )

    fig.update_layout(
        title="Bode Plot — Notch Filter Attenuation",
        xaxis=dict(
            title="Frequency (Hz)",
            type="log",
            range=[np.log10(FREQ_MIN), np.log10(FREQ_MAX)],
            showgrid=True,
            gridcolor="lightgrey",
            minor=dict(showgrid=True, gridcolor="#eeeeee"),
        ),
        yaxis=dict(
            title="Attenuation (dB)",
            showgrid=True,
            gridcolor="lightgrey",
        ),
        template="plotly_white",
        hovermode="x unified",
        showlegend=False,
    )

    print("\nOpening Bode plot in browser…")
    fig.show()


if __name__ == "__main__":
    main()