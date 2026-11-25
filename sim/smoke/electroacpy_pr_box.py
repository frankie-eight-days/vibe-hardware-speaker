"""Smoke test: ElectroacPy lumped-element sealed vs passive-radiator box with a generic 3" woofer.
Checks sealed-box fc against the closed-form fc = fs*sqrt(1+Vas/Vb) and finds the PR tuning (impedance dip)."""
import numpy as np
from electroacPy.speakerSim.electroAcousticDriver import electroAcousticDriver
from electroacPy.speakerSim.enclosureDesign import speakerBox
f = np.logspace(np.log10(20), np.log10(2000), 600)
rho, c = 1.22, 343.0
# generic 3" woofer (illustrative numbers, not a real part)
Re, Le, Bl, Mms, Sd, fs, Qms = 3.4, 0.15e-3, 4.0, 4.5e-3, 32e-4, 75.0, 3.0
Cms = 1 / ((2 * np.pi * fs) ** 2 * Mms); Rms = 2 * np.pi * fs * Mms / Qms
Vas = rho * c**2 * Sd**2 * Cms
drv = electroAcousticDriver(1, Le, Re, Cms, Mms, Rms, Bl, Sd, f)
Vb = 0.6e-3  # 0.6 L per side
sealed = speakerBox(Vb, frequencyRange=f); sealed.getDriverResponse(drv)
fc_lem = f[np.argmax(np.abs(sealed.Ze))]
fc_th = fs * np.sqrt(1 + Vas / Vb)
print(f"Vas={Vas*1e3:.2f} L  sealed fc: LEM {fc_lem:.1f} Hz vs closed-form {fc_th:.1f} Hz")
# passive radiator: Sd 2x woofer, heavy mass to tune ~55 Hz
Sd_pr = 2 * Sd; Mmd = 40e-3; Cmd = 0.5e-3; Rmd = 0.5
pr = speakerBox(Vb, frequencyRange=f, Mmd=Mmd, Cmd=Cmd, Rmd=Rmd, Sd=Sd_pr); pr.getDriverResponse(drv)
Ze = np.abs(pr.Ze); band = (f > 30) & (f < 150)
fb = f[band][np.argmin(Ze[band])]
p_tot = np.abs(pr.Q + pr.Qpr)  # far-field ~ total volume velocity * j*w (compare shapes)
spl = 20 * np.log10(p_tot * f / (p_tot * f)[np.argmin(np.abs(f - 500))])
f3 = f[np.where(spl > -3)[0][0]]
print(f"PR box: impedance-dip tuning fb ~ {fb:.1f} Hz, F3 ~ {f3:.1f} Hz (rel. to 500 Hz)")
Cab = Vb / (rho * c**2)
fp_th = np.sqrt((1 / Cmd + Sd_pr**2 / Cab) / Mmd) / (2 * np.pi)
print(f"PR closed-form box/PR resonance fp = {fp_th:.1f} Hz")
assert abs(fb - fp_th) / fp_th < 0.05
assert abs(fc_lem - fc_th) / fc_th < 0.05
print("PASS")
