"""
bode_butterworth.py
-------------------
Bode magnitude plot for the Butterworth LPF at different cutoff frequencies.
Compares attenuation of BW80Hz, BW120Hz, and BW150Hz against the unfiltered signal.

Usage:
  python bode_butterworth.py

Requirements:
  pip install pandas numpy plotly
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# ── CONFIG ────────────────────────────────────────────────────────────────────

BASE = r"C:\Users\alxhu\OneDrive - University of New Brunswick\School\5th year\ENGG 4000\Data collection\Butterworth"

INPUT_CSV = BASE + r"\LPF_80Hz.csv"

FILTERS = [
    {
        "label":       "BW 80 Hz",
        "output_csv":  BASE + r"\LPF_BW80Hz.csv",
        "color":       "royalblue",
        # List of (frequency, target_db) pairs to annotate
        "annotations": [
            {"freq": 80,  "target_db": -3},
            {"freq": 120, "target_db": -14},
        ],
    },
]

TIME_COL   = "Time (s)"
SIGNAL_COL = "Force (N)"

FREQ_MIN = 1.0
FREQ_MAX = 600.0

# ── FUNCTIONS ─────────────────────────────────────────────────────────────────

def load_signal(filepath):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    df[TIME_COL]   = pd.to_numeric(df[TIME_COL],   errors="coerce")
    df[SIGNAL_COL] = pd.to_numeric(df[SIGNAL_COL], errors="coerce")
    df = df.dropna(subset=[TIME_COL, SIGNAL_COL]).sort_values(TIME_COL)
    fs = 1.0 / df[TIME_COL].diff().median()
    return df[SIGNAL_COL].values, fs


def compute_attenuation(input_csv, output_csv):
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
        atten = 20.0 * np.log10(ratio)

    return freqs, atten

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    fig = go.Figure()

    for f in FILTERS:
        print(f"\nProcessing {f['label']} ...")
        freqs, atten = compute_attenuation(INPUT_CSV, f["output_csv"])

        mask       = (freqs >= FREQ_MIN) & (freqs <= FREQ_MAX)
        freqs_plot = freqs[mask]
        atten_plot = atten[mask]

        fig.add_trace(go.Scatter(
            x=freqs_plot,
            y=atten_plot,
            mode="lines",
            name=f["label"],
            line=dict(color=f["color"], width=2),
            hovertemplate=f"<b>%{{x:.1f}} Hz</b><br>%{{y:.2f}} dB<extra>{f['label']}</extra>",
        ))

        # Annotate each specified frequency point
        ax_offsets = [60, -60]  # alternate left/right to avoid overlap
        for ann_idx, ann in enumerate(f.get("annotations", [])):
            target_freq = ann["freq"]
            target_db   = ann["target_db"]
            idx         = np.argmin(np.abs(freqs - target_freq))
            atten_at    = atten[idx]
            error_db    = atten_at - target_db
            error_str   = f"+{error_db:.2f}" if error_db >= 0 else f"{error_db:.2f}"
            print(f"  At {target_freq} Hz: {atten_at:.2f} dB (target {target_db} dB, error {error_str} dB)")

            fig.add_annotation(
                x=np.log10(freqs[idx]),
                y=atten_at,
                xref="x", yref="y",
                text=f"<b>{target_freq} Hz</b><br>{atten_at:.2f} dB<br>Error from {target_db} dB: {error_str} dB",
                showarrow=True,
                arrowhead=2,
                arrowcolor=f["color"],
                font=dict(color=f["color"], size=11),
                bgcolor="white",
                bordercolor=f["color"],
                borderwidth=1,
                ax=ax_offsets[ann_idx % 2], ay=-55,
            )

            # Dotted reference line at target dB
            fig.add_hline(
                y=target_db,
                line=dict(color=f["color"], dash="dot", width=1),
                annotation_text=f"{target_db} dB",
                annotation_position="right",
                annotation_font_color=f["color"],
            )

    # -3 dB reference line
    fig.add_hline(y=-3, line=dict(color="orange", dash="dash", width=1.5))
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="lines",
        name="-3 dB cutoff",
        line=dict(color="orange", dash="dash", width=1.5),
    ))

    # 0 dB reference line
    fig.add_hline(y=0, line=dict(color="grey", dash="dash", width=1),
                  annotation_text="0 dB", annotation_position="right")

    fig.update_layout(
        title="Bode Plot — Butterworth LPF Attenuation",
        xaxis=dict(
            title="Frequency (Hz)",
            type="log",
            range=[np.log10(FREQ_MIN), np.log10(FREQ_MAX)],
            showgrid=True, gridcolor="lightgrey",
            minor=dict(showgrid=True, gridcolor="#eeeeee"),
        ),
        yaxis=dict(
            title="Attenuation (dB)",
            showgrid=True, gridcolor="lightgrey",
        ),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.01, y=0.01),
    )

    print("\nOpening Bode plot in browser...")
    fig.show()


if __name__ == "__main__":
    main()