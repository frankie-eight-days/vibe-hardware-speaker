"""TAS5805M biquad coefficient encoder (Book 0xAA, signed 5.27 big-endian, order b0 b1 b2 -a1 -a2).

Format verified against a PPC3-generated dump (sonocotta/esp32-tas5805m-dac, eq/tas5805m_eq.h,
BQ1-Left 20 Hz peaking -15 dB): no halving of b1/a1 despite SLOA263 Table 3 wording.
Register addresses depend on the PPC3 process flow loaded at boot; SLOA263A Table 6 (2.0 mode)
puts CH-L BQ1 at Book 0xAA, Page 0x24, Reg 0x18, 20 bytes per biquad, auto-incrementing.
"""
import numpy as np

Q527 = 2**27

def rbj_peaking(f0, gain_db, q, fs):
    A = 10 ** (gain_db / 40); w = 2 * np.pi * f0 / fs; al = np.sin(w) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w), 1 - al * A]); a = np.array([1 + al / A, -2 * np.cos(w), 1 - al / A])
    return b / a[0], a / a[0]

def to_527(x):
    v = int(round(x * Q527))
    if not -2**31 <= v < 2**31:
        raise ValueError(f"coefficient {x} out of 5.27 range (+-16)")
    return v & 0xFFFFFFFF

def encode_bq(b, a):
    """Return 20 bytes to burst-write starting at the biquad's B0 register."""
    words = [b[0], b[1], b[2], -a[1], -a[2]]
    return b"".join(to_527(w).to_bytes(4, "big") for w in words)

def decode_bq(raw20):
    w = [int.from_bytes(raw20[i:i + 4], "big", signed=True) / Q527 for i in range(0, 20, 4)]
    return np.array(w[:3]), np.array([1.0, -w[3], -w[4]])

if __name__ == "__main__":
    ppc3 = bytes.fromhex("07fce834" "f0078701" "07fb91b0" "0ff878ff" "f8078611")
    b, a = decode_bq(ppc3)
    print("PPC3 dump decoded  b =", np.round(b, 6), " a =", np.round(a, 6))
    b2, a2 = rbj_peaking(20, -15, 2, 48000)
    print("RBJ 20Hz/-15dB/Q2  b =", np.round(b2, 6), " a =", np.round(a2, 6))
    print("encoded:", encode_bq(b2, a2).hex(" ", 4))
    assert np.allclose(b, b2, atol=2e-3) and np.allclose(a, a2, atol=2e-3)
    print("PASS: layout/format consistent with PPC3 output (small diffs = PPC3's own Q definition)")
