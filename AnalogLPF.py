"""
bode_analog_lpf.py
------------------
Bode magnitude plot for the analog low-pass filter.

Usage:
  python bode_analog_lpf.py

Requirements:
  pip install pandas numpy plotly
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ── CONFIG ────────────────────────────────────────────────────────────────────

BASE = r"C:\Users\alxhu\OneDrive - University of New Brunswick\School\5th year\ENGG 4000\Data collection\Analog Filter"

FILTERS = [
    {
        "freq_hz":    10,
        "input_csv":  BASE + r"\10Hz.csv",
        "output_csv": BASE + r"\10HzAfterAnalog.csv",
    },
    {
        "freq_hz":    194,
        "input_csv":  BASE + r"\194Hz.csv",
        "output_csv": BASE + r"\194Hz_BW200Hz.csv",
    },
]

TIME_COL   = "Time (s)"
SIGNAL_COL = "Force (N)"

FREQ_MIN = 1.0
FREQ_MAX = 600.0

# ── FUNCTIONS ─────────────────────────────────────────────────────────────────

def load_signal(filepath: str):
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
    fs = fs_in

    N = min(len(sig_in), len(sig_out))
    sig_in  = sig_in[:N]
    sig_out = sig_out[:N]

    window  = np.hanning(N)
    fft_in  = np.abs(np.fft.rfft(sig_in  * window))
    fft_out = np.abs(np.fft.rfft(sig_out * window))
    freqs   = np.fft.rfftfreq(N, d=1.0 / fs)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(fft_in > 1e-10, fft_out / fft_in, np.nan)
        gain  = 20.0 * np.log10(ratio)

    return freqs, gain

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    fig = go.Figure()

    point_freqs = []
    point_db    = []
    all_freqs   = []
    all_gain    = []

    colours = ["royalblue", "crimson"]

    for idx_f, f in enumerate(FILTERS):
        test_freq = f["freq_hz"]
        colour    = colours[idx_f % len(colours)]
        print(f"\nProcessing {test_freq} Hz ...")

        freqs, gain = compute_attenuation(f["input_csv"], f["output_csv"])

        mask        = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)
        freqs_plot  = freqs[mask]
        gain_plot   = gain[mask]

        # Store for later use
        all_freqs.append(freqs_plot)
        all_gain.append(gain_plot)

        # Skip plotting the unfiltered (10 Hz) signal
        if test_freq == 10:
            continue

        fig.add_trace(go.Scatter(
            x=freqs_plot,
            y=gain_plot,
            mode="lines",
            name="Filtered Signal",
            line=dict(width=2, color=colour),
            opacity=0.8,
            hovertemplate="<b>%{x:.1f} Hz</b><br>%{y:.2f} dB<extra>Filtered Signal</extra>",
        ))

        # Measurement point at test frequency
        idx     = np.argmin(np.abs(freqs - test_freq))
        gain_at = gain[idx]
        print(f"  Gain at {freqs[idx]:.1f} Hz = {gain_at:.2f} dB")
        point_freqs.append(freqs[idx])
        point_db.append(gain_at)

        # Label showing gain at 194 Hz
        if test_freq == 194:
            fig.add_annotation(
                x=np.log10(freqs[idx]),
                y=gain_at,
                xref="x", yref="y",
                text=f"<b>{test_freq} Hz<br>{gain_at:.2f} dB</b>",
                showarrow=True,
                arrowhead=2,
                arrowcolor=colour,
                ax=-60, ay=50,
                font=dict(size=12, color=colour),
                bgcolor="white",
                bordercolor=colour,
                borderwidth=1,
            )

    # ── Passband gain from 10 Hz curve (low frequency region) ────────────────
    if len(all_freqs) >= 1:
        freqs_10 = all_freqs[0]
        gain_10  = all_gain[0]
        pb_mask  = (freqs_10 >= 1.0) & (freqs_10 <= 20.0)
        pb_vals  = gain_10[pb_mask]
        pb_vals  = pb_vals[~np.isnan(pb_vals)]
        if len(pb_vals) > 0:
            pb_mean = np.mean(pb_vals)
            pb_std  = np.std(pb_vals)
            pb_pct  = abs(pb_std / pb_mean * 100) if pb_mean != 0 else 0
            print(f"\n  Passband Gain: {pb_mean:.2f} dB +/- {pb_pct:.1f}%")

            fig.add_annotation(
                x=0.02, y=0.98,
                xref="paper", yref="paper",
                text=f"<b>Passband Gain = {pb_mean:.2f} dB ± {pb_pct:.1f}%</b>",
                showarrow=False,
                font=dict(size=12, color="royalblue"),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="royalblue",
                borderwidth=1,
                xanchor="left", yanchor="top",
            )

    # ── -3 dB reference line ──────────────────────────────────────────────────
    fig.add_hline(y=-3, line=dict(color="orange", dash="dash", width=1.5))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="lines",
        name="-3 dB cutoff",
        line=dict(color="orange", dash="dash", width=1.5),
        showlegend=True,
    ))

    # Find where the 194 Hz curve crosses -3 dB
    if len(all_freqs) >= 2:
        freqs_194 = all_freqs[1]
        gain_194  = all_gain[1]
        cutoff    = None

        for k in range(len(gain_194) - 1):
            a1, a2 = gain_194[k], gain_194[k + 1]
            if np.isnan(a1) or np.isnan(a2):
                continue
            if (a1 - (-3)) * (a2 - (-3)) <= 0:
                t      = (-3 - a1) / (a2 - a1)
                cutoff = freqs_194[k] + t * (freqs_194[k + 1] - freqs_194[k])
                break

        if cutoff is not None:
            print(f"  -3 dB cutoff: {cutoff:.1f} Hz")
            fig.add_vline(x=cutoff, line=dict(color="orange", dash="dot", width=1.5))
            fig.add_annotation(
                x=np.log10(cutoff), y=-3,
                xref="x", yref="y",
                text=f"<b>-3 dB cutoff<br>{cutoff:.1f} Hz</b>",
                showarrow=True, arrowhead=2, arrowcolor="orange",
                ax=50, ay=-40,
                font=dict(size=12, color="orange"),
                bgcolor="white", bordercolor="orange", borderwidth=1,
            )

    # ── 0 dB reference line ───────────────────────────────────────────────────
    fig.add_hline(
        y=0,
        line=dict(color="grey", dash="dash", width=1),
        annotation_text="0 dB",
        annotation_position="right",
    )

    fig.update_layout(
        title="Anti-aliasing LPF - Bode Plot",
        xaxis=dict(
            title="Frequency (Hz)",
            type="log",
            range=[np.log10(FREQ_MIN), np.log10(FREQ_MAX)],
            showgrid=True,
            gridcolor="lightgrey",
            minor=dict(showgrid=True, gridcolor="#eeeeee"),
        ),
        yaxis=dict(
            title="Gain (dB)",
            showgrid=True,
            gridcolor="lightgrey",
        ),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.01, y=0.01),
    )

    print("\nOpening Bode plot in browser...")
    fig.show()


if __name__ == "__main__":
    main()