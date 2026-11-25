/* Lumped bass model: a line-for-line port of sim/acoustics/bass_model.py (system, ideal_eq,
   f_at_level, sine_limits, pink_estimate). Two woofers + two passive radiators in one box,
   half space, 1 m. Everything is per 1 V peak on each woofer unless noted. */
(function (root) {
  "use strict";
  var RHO = 1.2, C0 = 343.0, P_REF = 20e-6, V_PK_MAX = 15.5, I_PK_MAX = 4.5;

  // complex helpers: [re, im]
  function c(re, im) { return [re, im || 0]; }
  function add(a, b) { return [a[0] + b[0], a[1] + b[1]]; }
  function sub(a, b) { return [a[0] - b[0], a[1] - b[1]]; }
  function mul(a, b) { return [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]]; }
  function div(a, b) { var d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; }
  function sc(a, k) { return [a[0] * k, a[1] * k]; }
  function inv(a) { return div([1, 0], a); }
  function abs(a) { return Math.hypot(a[0], a[1]); }

  function logspace(a, b, n) {
    var out = [], la = Math.log10(a), lb = Math.log10(b);
    for (var i = 0; i < n; i++) out.push(Math.pow(10, la + (lb - la) * i / (n - 1)));
    return out;
  }
  // numpy.interp (x ascending)
  function interp(x, xs, ys) {
    if (x <= xs[0]) return ys[0];
    var n = xs.length;
    if (x >= xs[n - 1]) return ys[n - 1];
    var lo = 0, hi = n - 1;
    while (hi - lo > 1) { var m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
    return ys[lo] + (ys[hi] - ys[lo]) * (x - xs[lo]) / (xs[hi] - xs[lo]);
  }

  function system(f, w, p, o) {
    var vb = o.vb, m_add = o.m_add || 0, ql = o.ql == null ? 10 : o.ql, qa = o.qa == null ? Infinity : o.qa;
    var nd = 2, np_ = 2, vbf = o.vb_factor || 1, r = 1.0;
    var cab = vb * vbf / (RHO * C0 * C0);
    var sp = p.sd_m2, cmp_ = p.cms_m_per_n, rmp = p.rms_kg_per_s, mmp = p.mms_kg + m_add;
    var cap = cmp_ * sp * sp * np_, map_ = mmp / sp / sp / np_;
    var fb = Math.sqrt((1 / cap + 1 / cab) / map_) / (2 * Math.PI);
    var fp = 1 / (2 * Math.PI * Math.sqrt(mmp * cmp_));
    var fcs = w.fs_hz * Math.sqrt(1 + nd * w.sd_m2 * w.sd_m2 * w.cms_m_per_n / cab);
    var wref = 2 * Math.PI * fb;
    var ral = ql / (wref * cab);
    var rab = isFinite(qa) ? 1 / (wref * cab * qa) : 0;
    var out = { f: f, v_d: [], v_p: [], x_d: [], x_p: [], p_hs: [], zin: [], fb: fb, fp: fp, fc: fcs, cab: cab };
    for (var i = 0; i < f.length; i++) {
      var om = 2 * Math.PI * f[i], s = [0, om];
      var ze = add(c(w.re_ohm), mul(s, c(w.le_h || 0)));
      var zmd = add(add(c(w.rms_kg_per_s), sc(s, w.mms_kg)), inv(sc(s, w.cms_m_per_n)));
      var zmp = add(add(c(rmp), sc(s, mmp)), inv(sc(s, cmp_)));
      var ypr = div(c(np_ * sp * sp), zmp);
      var yb = add(inv(add(c(rab), inv(sc(s, cab)))), c(1 / ral));
      var ytot = add(yb, ypr);
      var bl = w.bl_tm, sd = w.sd_m2;
      var num = div(c(bl), ze);
      var den = add(add(zmd, div(c(bl * bl), ze)), div(c(nd * sd * sd), ytot));
      var vd = div(num, den);
      var pbox = sc(div(vd, ytot), -nd * sd);
      var vp = sc(div(pbox, zmp), sp);
      var u = add(sc(vd, nd * sd), sc(vp, np_ * sp));
      var phs = sc(mul(s, u), RHO / (2 * Math.PI * r));
      var icoil = div(sub(c(1), sc(vd, bl)), ze);
      out.v_d.push(vd); out.v_p.push(vp);
      out.x_d.push(div(vd, s)); out.x_p.push(div(vp, s));
      out.p_hs.push(phs); out.zin.push(inv(icoil));
    }
    return out;
  }

  function splPk(a) { return 20 * Math.log10(a / Math.SQRT2 / P_REF + 1e-30); }
  function bwhp(f, fc, n) { return 1 / Math.sqrt(1 + Math.pow(fc / f, 2 * n)); }
  function target(f, f3) { return bwhp(f, f3, 4) * bwhp(f, 0.45 * f3, 2); }

  function idealEq(f, sys, f3, maxBoostDb) {
    f3 = f3 || 63; maxBoostDb = maxBoostDb == null ? 18 : maxBoostDb;
    var h = sys.p_hs.map(abs), sum = 0, n = 0, i;
    for (i = 0; i < f.length; i++) if (f[i] > 300 && f[i] < 600) { sum += h[i]; n++; }
    var href = sum / n, cap = Math.pow(10, maxBoostDb / 20);
    var g = f.map(function (fi, k) { return Math.min(target(fi, f3) * href / h[k], cap); });
    var ff = 0.75 * f3, gf = interp(ff, f, g);
    for (i = 0; i < f.length; i++) {
      if (f[i] < ff) g[i] = Math.min(g[i], gf * Math.pow(f[i] / ff, 4));
      var wf = Math.min(1, Math.max(0, Math.log(600 / f[i]) / Math.log(2)));
      g[i] = Math.pow(10, wf * Math.log10(g[i]));
    }
    return { g: g, href: href };
  }

  function fAtLevel(f, lev, ref, drop, fmax) {
    fmax = fmax || 300;
    var k = -1;
    for (var i = 0; i < f.length; i++) if (lev[i] - ref < -drop && f[i] < fmax) k = i;
    if (k < 0) return f[0];
    var x0 = Math.log(f[k]), x1 = Math.log(f[k + 1]);
    var y0 = lev[k] - ref + drop, y1 = lev[k + 1] - ref + drop;
    return y1 !== y0 ? Math.exp(x0 + (x1 - x0) * (-y0) / (y1 - y0)) : f[k];
  }

  var LIMITS = ["amp voltage", "amp current", "woofer Xmax", "PR excursion"];
  function sineLimits(sys, w, p) {
    var v = [], which = [];
    for (var i = 0; i < sys.f.length; i++) {
      var cand = [V_PK_MAX, I_PK_MAX * abs(sys.zin[i]), w.xmax_m / abs(sys.x_d[i]), p.xlim_model_m / Math.max(abs(sys.x_p[i]), 1e-30)];
      var k = 0;
      for (var j = 1; j < 4; j++) if (cand[j] < cand[k]) k = j;
      v.push(cand[k]); which.push(k);
    }
    return { v: v, which: which };
  }

  function pinkEstimate(f, sys, w, p, g, href, crest, fx) {
    crest = crest || 3; fx = fx || 2500;
    var lf = f.map(Math.log), fc = [], k;
    for (k = -17; k < 14; k++) fc.push(1000 * Math.pow(2, k / 3));
    var rr = f.map(function (_, i) { return abs(sys.p_hs[i]) * g[i] / href; });
    var axd = sys.x_d.map(abs), axp = sys.x_p.map(abs);
    var zre = sys.zin.map(function (z) { return z[0]; }), zim = sys.zin.map(function (z) { return z[1]; });
    var tot = 0, sv = 0, sx = 0, sxp = 0, si = 0, sp = 0;
    fc.forEach(function (fcb) {
      var l = Math.log(fcb);
      var rb = fcb < 1000 ? interp(l, lf, rr) : 1;
      tot += rb * rb;
      var gb = interp(l, lf, g) / (1 + Math.pow(fcb / fx, 4));
      var vb = P_REF * gb / href;
      var zr = interp(l, lf, zre), zi = interp(l, lf, zim);
      var ib = vb / Math.hypot(zr, zi);
      sv += vb * vb; sx += Math.pow(interp(l, lf, axd) * vb, 2); sxp += Math.pow(interp(l, lf, axp) * vb, 2);
      si += ib * ib; sp += ib * ib * zr;
    });
    var totRel = 10 * Math.log10(tot);
    var cand = {
      "amp voltage": V_PK_MAX / (crest * Math.sqrt(sv)),
      "amp current": I_PK_MAX / (crest * Math.sqrt(si)),
      "woofer thermal": Math.sqrt(w.power_rms_w / (si * w.re_ohm)),
      "woofer Xmax": w.xmax_m / (crest * Math.sqrt(sx)),
      "PR excursion": p.xlim_model_m / (crest * Math.sqrt(sxp))
    };
    var lim = null;
    Object.keys(cand).forEach(function (kk) { if (lim === null || cand[kk] < cand[lim]) lim = kk; });
    var dbs = {};
    Object.keys(cand).forEach(function (kk) { dbs[kk] = 20 * Math.log10(cand[kk]) + totRel; });
    return { db: dbs[lim], limit: lim, all: dbs, pElec: sp * cand[lim] * cand[lim] };
  }

  /* |H| of a cascade of biquads [b0,b1,b2,a0,a1,a2] at sample rate fs. */
  function sosMag(sos, f, fs) {
    return f.map(function (fi) {
      var wz = 2 * Math.PI * fi / fs, z1 = [Math.cos(-wz), Math.sin(-wz)], z2 = [Math.cos(-2 * wz), Math.sin(-2 * wz)];
      var h = 1;
      sos.forEach(function (q) {
        var nu = add(add(c(q[0]), sc(z1, q[1])), sc(z2, q[2]));
        var de = add(add(c(q[3]), sc(z1, q[4])), sc(z2, q[5]));
        h *= abs(nu) / abs(de);
      });
      return h;
    });
  }

  /* Full evaluation, the same steps as a1_bass_lumped.evaluate(). o.eqMode: "ideal" (re-fitted to the
     F3 = 63 Hz target for this box, as A1's what-ifs do) or "biquad" (the four fixed biquads in o.sos). */
  function evaluate(w, p, o) {
    var f = o.f || logspace(10, 20000, 600);
    var sys = system(f, w, p, o);
    var eq = idealEq(f, sys, 63, 18);
    if (o.eqMode === "biquad" && o.sos) eq = { g: sosMag(o.sos, f, 48000), href: eq.href };
    var pink = pinkEstimate(f, sys, w, p, eq.g, eq.href, 3, 2500);
    var ndb = sys.p_hs.map(function (z) { return splPk(abs(z)); });
    var rdb = sys.p_hs.map(function (z, i) { return 20 * Math.log10(abs(z) * eq.g[i] / eq.href); });
    var s = 0, n = 0, i;
    for (i = 0; i < f.length; i++) if (f[i] > 300 && f[i] < 600) { s += ndb[i]; n++; }
    var nref = s / n;
    var lim = sineLimits(sys, w, p);
    var maxBoost = -1e9, ceilV = Infinity, ceilF = 0, zmin = Infinity;
    for (i = 0; i < f.length; i++) {
      if (f[i] >= 15 && f[i] <= 1000) {
        maxBoost = Math.max(maxBoost, 20 * Math.log10(eq.g[i]));
        var vc = lim.v[i] / eq.g[i];
        if (vc < ceilV) { ceilV = vc; ceilF = f[i]; }
        zmin = Math.min(zmin, abs(sys.zin[i]));
      }
    }
    return {
      f: f, sys: sys, g: eq.g, href: eq.href, pink: pink, nref: nref,
      f3eq: fAtLevel(f, rdb, 0, 3), f6eq: fAtLevel(f, rdb, 0, 6),
      f3nat: fAtLevel(f, ndb, nref, 3), f6nat: fAtLevel(f, ndb, nref, 6),
      maxBoost: maxBoost, lim: lim, ceilV: ceilV, ceilF: ceilF,
      ceilDb: splPk(ceilV * eq.href), zmin: zmin,
      sens400: splPk(abs(sys.p_hs[nearest(f, 400)]) * 2.83 * Math.SQRT2)
    };
  }
  function nearest(f, x) { var k = 0; for (var i = 1; i < f.length; i++) if (Math.abs(f[i] - x) < Math.abs(f[k] - x)) k = i; return k; }

  root.Bass = { sosMag: sosMag, system: system, evaluate: evaluate, idealEq: idealEq, splPk: splPk, abs: abs, logspace: logspace,
    interp: interp, LIMITS: LIMITS, V_PK_MAX: V_PK_MAX, I_PK_MAX: I_PK_MAX };
})(typeof window !== "undefined" ? window : globalThis);
