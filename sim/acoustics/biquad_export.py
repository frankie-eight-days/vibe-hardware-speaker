"""Export every DSP biquad (A1 bass EQ, A5 crossover + system EQ) for the TAS5805M.

The amp DSP runs at 96 kHz (TAS5805M process flow 1 resamples 44.1/48 kHz input to 96 kHz; see
research/firmware_and_tools.md), so the 96 kHz table is the one to load.  48 kHz is kept for reference.
Each filter is defined by (type, fc, Q, gain) and turned into RBJ-cookbook coefficients at each rate;
coefficients are encoded with tools/tas5805m_bq.py (signed 5.27, big-endian, order b0 b1 b2 -a1 -a2,
20 bytes per biquad, written as one burst starting at the biquad's B0 register).
Check: the 96 kHz and 48 kHz realisations of each chain agree within the printed tolerance (20 Hz-16 kHz),
and every encoded biquad decodes back to its float coefficients within 2^-27.
Output: results/biquads_tas5805m.json and results/biquads_tas5805m.csv.
"""
import json
import os
import sys

import numpy as np

import common
import bass_model as bm

sys.path.insert(0, os.path.join(common.ROOT, "tools"))
import tas5805m_bq as tq                                    # noqa: E402

RATES = (96000.0, 48000.0)
TYPE_MAP = {"highpass": "hp", "lowpass": "lp", "low shelf": "lowshelf", "high shelf": "highshelf", "peaking": "peak"}


def kind_of(t):
    for k, v in TYPE_MAP.items():
        if t.startswith(k):
            return v
    raise ValueError(t)


def a1_filters():
    a1 = json.load(open(os.path.join(common.RESULTS, "a1_bass_summary.json")))
    return [dict(type=b["type"], kind=kind_of(b["type"]), fc_hz=b["fc_hz"], q=b["q"], gain_db=b.get("gain_db", 0.0))
            for b in a1["biquads_fs48k"]]


def sos_of(filters, fs):
    return np.vstack([bm.rbj(f["kind"], f["fc_hz"], fs, q=f["q"], gain_db=f["gain_db"]) for f in filters])


def a1_sos(fs):
    return sos_of(a1_filters(), fs)


def lr4_filters(fx, kind):
    t = "lowpass" if kind == "lp" else "highpass"
    return [dict(type=f"{t} (LR4 = 2 x BW2, stage {i})", kind=kind, fc_hz=fx, q=0.7071067811865476, gain_db=0.0) for i in (1, 2)]


def encode(filters, fs):
    rows = []
    for f, s in zip(filters, sos_of(filters, fs)):
        b, a = s[:3], s[3:]
        raw = tq.encode_bq(b, a)
        bd, ad = tq.decode_bq(raw)
        assert np.allclose(bd, b, atol=2 ** -26) and np.allclose(ad, a, atol=2 ** -26)
        rows.append(dict(f, fs_hz=fs, b=b.tolist(), a=a.tolist(), tas5805m_hex=raw.hex()))
    return rows


def main():
    chains = {"A1 bass EQ (woofer channel)": a1_filters()}
    a5p = os.path.join(common.RESULTS, "a5_crossover_system.json")
    extra = {}
    if os.path.exists(a5p):
        a5 = json.load(open(a5p))
        al = a5["alignment"]
        chains["A5 woofer low-pass"] = lr4_filters(al["fx"], "lp")
        chains["A5 tweeter high-pass"] = lr4_filters(al["fx"], "hp")
        chains["A5 system EQ (both channels of a side)"] = [
            dict(type=t["type"], kind=kind_of(t["type"]), fc_hz=t["fc_hz"], q=t["q"], gain_db=t["gain_db"]) for t in a5["eq"]["table"]]
        extra = dict(tweeter_trim_db=al["gt_db"], tweeter_polarity=al["polarity"], tweeter_delay_us=al["tau_us"],
                     tweeter_delay_samples_96k=round(al["tau_us"] * 1e-6 * 96000, 2),
                     tweeter_delay_samples_48k=round(al["tau_us"] * 1e-6 * 48000, 2))
    f = np.logspace(np.log10(20), np.log10(16000), 400)
    out = dict(note="Load the fs = 96000 rows into the TAS5805M (process flow 1 runs the DSP at 96 kHz). "
                    "Coefficients: signed 5.27, big-endian, order b0 b1 b2 -a1 -a2; register addresses depend on the PPC3 flow.",
               chains={}, rate_check_db={}, channel_settings=extra)
    rows_csv = []
    for name, flt in chains.items():
        out["chains"][name] = {str(int(fs)): encode(flt, fs) for fs in RATES}
        h96 = 20 * np.log10(np.abs(bm.sos_response(sos_of(flt, 96000.0), f, 96000.0)))
        h48 = 20 * np.log10(np.abs(bm.sos_response(sos_of(flt, 48000.0), f, 48000.0)))
        lo = f <= 2000
        out["rate_check_db"][name] = dict(max_diff_20_2000hz=float(np.max(np.abs(h96 - h48)[lo])),
                                          max_diff_20_16000hz=float(np.max(np.abs(h96 - h48))))
        for fs in RATES:
            for r in out["chains"][name][str(int(fs))]:
                rows_csv.append([name, int(fs), r["type"], f"{r['fc_hz']:.2f}", f"{r['q']:.4f}", f"{r['gain_db']:.2f}"]
                                + [f"{x:.10f}" for x in r["b"] + r["a"][1:]] + [r["tas5805m_hex"]])
    common.save_json(out, "biquads_tas5805m.json")
    path = os.path.join(common.RESULTS, "biquads_tas5805m.csv")
    with open(path, "w") as fh:
        fh.write("chain,fs_hz,type,fc_hz,q,gain_db,b0,b1,b2,a1,a2,tas5805m_hex_b0_b1_b2_-a1_-a2\n")
        for r in rows_csv:
            fh.write(",".join(f'"{x}"' if "," in str(x) or " " in str(x) else str(x) for x in r) + "\n")
    print("results:", path)
    print(json.dumps(out["rate_check_db"], indent=1), extra)


if __name__ == "__main__":
    main()
