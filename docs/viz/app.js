/* Speaker simulations explainer: charts, diagrams and the per-simulation controllers. */
(function () {
  "use strict";
  var SVGNS = "http://www.w3.org/2000/svg";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var CHARTS = [];

  // ------------------------------------------------------------------ utilities
  function tok(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888"; }
  function col(c) { return c && c.indexOf("--") === 0 ? tok(c) : c; }
  function svgEl(tag, attrs, parent) {
    var e = document.createElementNS(SVGNS, tag);
    for (var k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function fmtHz(v) {
    if (v >= 1e6) return +(v / 1e6).toPrecision(3) + " MHz";
    if (v >= 1e3) return +(v / 1e3).toPrecision(3) + " kHz";
    return +v.toPrecision(3) + " Hz";
  }
  function fmtTick(v) {
    var a = Math.abs(v);
    if (a >= 1e6) return +(v / 1e6).toPrecision(3) + "M";
    if (a >= 1e3) return +(v / 1e3).toPrecision(3) + "k";
    if (a > 0 && a < 0.01) return v.toExponential(0);
    return String(+v.toPrecision(3));
  }
  function niceStep(span, n) {
    var raw = span / Math.max(1, n), p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p;
    return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 2.5 ? 2.5 : m <= 5 ? 5 : 10) * p;
  }
  function niceTicks(a, b, n) {
    var st = niceStep(b - a, n), out = [];
    for (var v = Math.ceil(a / st - 1e-9) * st; v <= b + st * 1e-6; v += st) out.push(+v.toPrecision(12));
    return out;
  }
  function logTicks(a, b, px) {
    var d0 = Math.floor(Math.log10(a)), d1 = Math.ceil(Math.log10(b)), dec = Math.log10(b / a);
    var perDec = px / dec, mults = perDec > 150 ? [1, 2, 5] : perDec > 70 ? [1, 3] : [1];
    if (perDec < 34) mults = [];
    var major = [], minor = [];
    for (var d = d0; d <= d1; d++) for (var m = 1; m < 10; m++) {
      var v = m * Math.pow(10, d);
      if (v < a * 0.999 || v > b * 1.001) continue;
      if (mults.indexOf(m) >= 0) major.push(v); else minor.push(v);
    }
    if (!mults.length) {
      var step = Math.ceil(34 / perDec);
      for (var e = d0; e <= d1; e++) { var v2 = Math.pow(10, e); if (v2 >= a * 0.999 && v2 <= b * 1.001 && e % step === 0) major.push(v2); }
    }
    return { major: major, minor: minor };
  }
  function bsearch(xs, x) { // index of nearest in ascending xs
    var lo = 0, hi = xs.length - 1;
    if (x <= xs[0]) return 0;
    if (x >= xs[hi]) return hi;
    while (hi - lo > 1) { var m = (lo + hi) >> 1; if (xs[m] <= x) lo = m; else hi = m; }
    return (x - xs[lo] < xs[hi] - x) ? lo : hi;
  }
  function interp(x, xs, ys) { return window.Bass.interp(x, xs, ys); }
  function round(v, n) { return v == null || !isFinite(v) ? "—" : v.toFixed(n); }
  function seg(host, items, value, onChange) {
    host.setAttribute("role", "group");
    var btns = items.map(function (it) {
      var b = h("button", null, it.l); b.type = "button"; b.dataset.v = String(it.v);
      b.setAttribute("aria-pressed", String(String(it.v) === String(value)));
      b.addEventListener("click", function () { set(it.v); onChange(it.v); });
      host.appendChild(b); return b;
    });
    function set(v) { value = v; btns.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.v === String(v))); }); }
    return { set: set, get: function () { return value; } };
  }
  function chip(ok, text, mid) { return '<span class="chip ' + (mid ? "mid" : ok ? "ok" : "bad") + '">' + text + "</span>"; }

  // ------------------------------------------------------------------ line chart
  var uid = 0;
  function LineChart(host, opts) {
    var self = this; this.o = opts; this.id = "c" + (++uid);
    host.innerHTML = "";
    this.ttlEl = h("div", "ttl"); host.appendChild(this.ttlEl);
    this.subEl = h("div", "sub"); host.appendChild(this.subEl);
    this.legend = h("div", "legend"); host.appendChild(this.legend);
    this.box = h("div", "plot"); host.appendChild(this.box);
    this.tip = h("div", "tip"); this.tip.hidden = true;
    this.host = host;
    var pend = false;
    if (window.ResizeObserver) new ResizeObserver(function () { if (pend) return; pend = true; requestAnimationFrame(function () { pend = false; self.render(); }); }).observe(this.box);
    CHARTS.push(this);
    this.render();
  }
  LineChart.prototype.set = function (patch) { for (var k in patch) this.o[k] = patch[k]; this.render(); };
  LineChart.prototype.render = function () {
    var o = this.o, self = this, box = this.box;
    this.ttlEl.textContent = o.title || ""; this.ttlEl.hidden = !o.title;
    this.subEl.textContent = o.sub || ""; this.subEl.hidden = !o.sub;
    var W = Math.max(260, box.clientWidth || 600), H = o.height || 250;
    var X = o.x, Y = o.y, vis = o.series.filter(function (s) { return !s.hidden; });
    // y domain
    var ymin = Y.min, ymax = Y.max;
    if (ymin == null || ymax == null) {
      var lo = Infinity, hi = -Infinity;
      vis.forEach(function (s) { s.x.forEach(function (xv, i) { var yv = s.y[i]; if (yv == null || !isFinite(yv) || xv < X.min || xv > X.max) return; if (Y.log && yv <= 0) return; lo = Math.min(lo, yv); hi = Math.max(hi, yv); }); });
      (o.refs || []).forEach(function (r) { lo = Math.min(lo, r.y); hi = Math.max(hi, r.y); });
      if (!isFinite(lo)) { lo = 0; hi = 1; }
      if (Y.log) { ymin = ymin == null ? Math.pow(10, Math.floor(Math.log10(lo))) : ymin; ymax = ymax == null ? Math.pow(10, Math.ceil(Math.log10(hi))) : ymax; }
      else { var pad = (hi - lo) * 0.06 || 1; ymin = ymin == null ? lo - pad : ymin; ymax = ymax == null ? hi + pad : ymax; var st = niceStep(ymax - ymin, 5); if (Y.min == null) ymin = Math.floor(ymin / st) * st; if (Y.max == null) ymax = Math.ceil(ymax / st) * st; }
    }
    var yt = Y.log ? logTicks(ymin, ymax, H / 2).major : (Y.ticks || niceTicks(ymin, ymax, Math.max(3, Math.round((H - 50) / 42))));
    var yf = Y.tick || fmtTick;
    var maxLab = yt.reduce(function (m, v) { return Math.max(m, yf(v).length); }, 1);
    var m = { l: 12 + maxLab * 6.6, r: o.rightPad || 12, t: 20, b: 34 };
    var pw = W - m.l - m.r, ph = H - m.t - m.b;
    var lx0 = Math.log(X.min), lx1 = Math.log(X.max), ly0 = Math.log(ymin), ly1 = Math.log(ymax);
    var xs = X.log ? function (v) { return m.l + (Math.log(v) - lx0) / (lx1 - lx0) * pw; } : function (v) { return m.l + (v - X.min) / (X.max - X.min) * pw; };
    var xinv = X.log ? function (p) { return Math.exp(lx0 + (p - m.l) / pw * (lx1 - lx0)); } : function (p) { return X.min + (p - m.l) / pw * (X.max - X.min); };
    var ys = Y.log ? function (v) { return m.t + (1 - (Math.log(v) - ly0) / (ly1 - ly0)) * ph; } : function (v) { return m.t + (1 - (v - ymin) / (ymax - ymin)) * ph; };
    box.innerHTML = ""; box.appendChild(this.tip);
    var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, role: "img", "aria-label": o.aria || o.title || "chart" }, null);
    box.insertBefore(svg, this.tip);
    var grid = tok("--grid"), rule = tok("--rule"), ink2 = tok("--ink-2"), surf = tok("--surface");
    var clipId = this.id + "-clip";
    var defs = svgEl("defs", {}, svg);
    var cp = svgEl("clipPath", { id: clipId }, defs); svgEl("rect", { x: m.l, y: m.t - 2, width: pw, height: ph + 4 }, cp);
    // bands
    (o.xbands || []).forEach(function (b) {
      var x0 = xs(Math.max(b.x0, X.min)), x1 = xs(Math.min(b.x1, X.max));
      svgEl("rect", { x: x0, y: m.t, width: Math.max(0, x1 - x0), height: ph, fill: col(b.color || "--band") }, svg);
      if (b.label) { var t = svgEl("text", { x: x0 + 4, y: m.t + 11, class: "reflbl" }, svg); t.textContent = b.label; }
    });
    (o.ybands || []).forEach(function (b) {
      var y0 = ys(b.y1), y1 = ys(b.y0);
      svgEl("rect", { x: m.l, y: y0, width: pw, height: Math.max(0, y1 - y0), fill: col(b.color || "--band") }, svg);
      if (b.label) { var t = svgEl("text", { x: m.l + 4, y: y0 + 11, class: "reflbl" }, svg); t.textContent = b.label; }
    });
    // grid
    var xt;
    if (X.log) { xt = logTicks(X.min, X.max, pw); xt.minor.forEach(function (v) { svgEl("line", { x1: xs(v), x2: xs(v), y1: m.t, y2: m.t + ph, stroke: grid, "stroke-width": 0.6 }, svg); }); xt = xt.major; }
    else xt = X.ticks || niceTicks(X.min, X.max, Math.max(3, Math.floor(pw / 80)));
    xt.forEach(function (v) {
      svgEl("line", { x1: xs(v), x2: xs(v), y1: m.t, y2: m.t + ph, stroke: grid, "stroke-width": 1 }, svg);
      var t = svgEl("text", { x: xs(v), y: m.t + ph + 14, "text-anchor": "middle" }, svg); t.textContent = (X.tick || fmtTick)(v);
    });
    yt.forEach(function (v) {
      if (v < ymin - 1e-9 || v > ymax + 1e-9) return;
      svgEl("line", { x1: m.l, x2: m.l + pw, y1: ys(v), y2: ys(v), stroke: grid, "stroke-width": 1 }, svg);
      var t = svgEl("text", { x: m.l - 6, y: ys(v) + 3.5, "text-anchor": "end" }, svg); t.textContent = yf(v);
    });
    svgEl("line", { x1: m.l, x2: m.l + pw, y1: m.t + ph, y2: m.t + ph, stroke: rule, "stroke-width": 1 }, svg);
    if (Y.label) { var yl = svgEl("text", { x: 0, y: 11, class: "axlbl" }, svg); yl.textContent = Y.label; }
    if (X.label) { var xl = svgEl("text", { x: m.l + pw, y: H - 3, "text-anchor": "end", class: "axlbl" }, svg); xl.textContent = X.label; }
    // reference lines
    var refG = svgEl("g", {}, svg);
    (o.refs || []).forEach(function (r) {
      if (r.y < ymin || r.y > ymax) return;
      var c = col(r.color || "--ink-2");
      svgEl("line", { x1: m.l, x2: m.l + pw, y1: ys(r.y), y2: ys(r.y), stroke: c, "stroke-width": 1.2, "stroke-dasharray": r.solid ? null : "5 4" }, refG);
      if (r.label) { var t = svgEl("text", { x: r.left ? m.l + 4 : m.l + pw - 4, y: ys(r.y) + (r.below ? 12 : -4), "text-anchor": r.left ? "start" : "end", class: "reflbl", style: "paint-order:stroke;stroke:" + surf + ";stroke-width:3px" }, refG); t.textContent = r.label; }
    });
    (o.vrefs || []).forEach(function (r, k) {
      if (r.x < X.min || r.x > X.max) return;
      var c = col(r.color || "--ink-2");
      svgEl("line", { x1: xs(r.x), x2: xs(r.x), y1: m.t, y2: m.t + ph, stroke: c, "stroke-width": 1, "stroke-dasharray": "3 3" }, refG);
      if (r.label) { var t = svgEl("text", { x: xs(r.x) + (r.left ? -4 : 4), y: m.t + 11 + (r.row || 0) * 12, "text-anchor": r.left ? "end" : "start", class: "reflbl", style: "paint-order:stroke;stroke:" + surf + ";stroke-width:3px" }, refG); t.textContent = r.label; }
    });
    // series
    var g = svgEl("g", { "clip-path": "url(#" + clipId + ")" }, svg);
    vis.forEach(function (s) {
      var c = col(s.color);
      if (s.line !== false) {
        var d = "", pen = false;
        for (var i = 0; i < s.x.length; i++) {
          var xv = s.x[i], yv = s.y[i];
          if (yv == null || !isFinite(yv) || (X.log && xv <= 0) || (Y.log && yv <= 0)) { pen = false; continue; }
          var py = ys(Math.max(Math.min(yv, ymax * (Y.log ? 10 : 1) + (Y.log ? 0 : (ymax - ymin) * 2)), Y.log ? ymin / 10 : ymin - (ymax - ymin) * 2));
          d += (pen ? "L" : "M") + xs(xv).toFixed(1) + " " + py.toFixed(1);
          pen = true;
        }
        svgEl("path", { d: d, fill: "none", stroke: c, "stroke-width": s.width || 2, "stroke-dasharray": s.dash || null, "stroke-linejoin": "round", "stroke-linecap": "round", opacity: s.opacity || null }, g);
      }
      if (s.markers) s.x.forEach(function (xv, i) { if (s.y[i] == null) return; svgEl("circle", { cx: xs(xv), cy: ys(s.y[i]), r: 4.5, fill: c, stroke: surf, "stroke-width": 2 }, g); });
    });
    // legend
    this.legend.innerHTML = "";
    o.series.forEach(function (s) {
      if (s.legend === false) return;
      var b = h("button"); b.type = "button"; b.setAttribute("aria-pressed", String(!s.hidden));
      var sw = h("span", "sw" + (s.markers && s.line === false ? " dot" : s.dash ? " dash" : ""));
      if (s.markers && s.line === false) sw.style.background = col(s.color); else sw.style.borderTopColor = col(s.color);
      b.appendChild(sw); b.appendChild(document.createTextNode(s.name));
      b.addEventListener("click", function () { s.hidden = !s.hidden; self.render(); });
      self.legend.appendChild(b);
    });
    // hover
    var hover = svgEl("g", { style: "pointer-events:none", visibility: "hidden" }, svg);
    var vline = svgEl("line", { y1: m.t, y2: m.t + ph, stroke: ink2, "stroke-width": 1 }, hover);
    var dots = vis.map(function (s) { return svgEl("circle", { r: 4, fill: col(s.color), stroke: surf, "stroke-width": 2 }, hover); });
    var ov = svgEl("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "transparent", style: "cursor:crosshair;touch-action:pan-y" }, svg);
    var tip = this.tip;
    function move(ev) {
      var rect = svg.getBoundingClientRect(), sx = W / rect.width;
      var px = (ev.clientX - rect.left) * sx;
      if (px < m.l || px > m.l + pw) return leave();
      var xv = xinv(px), html = '<div class="tx">' + (X.fmt || fmtHz)(xv) + "</div>", any = false;
      vis.forEach(function (s, k) {
        if (s.tip === false) { dots[k].setAttribute("visibility", "hidden"); return; }
        var i = bsearch(s.x, xv), yv = s.y[i];
        if (yv == null || !isFinite(yv) || s.x[i] < X.min || s.x[i] > X.max) { dots[k].setAttribute("visibility", "hidden"); return; }
        if (s.markers && s.line === false && Math.abs(xs(s.x[i]) - px) > 14) { dots[k].setAttribute("visibility", "hidden"); return; }
        dots[k].setAttribute("visibility", "visible");
        dots[k].setAttribute("cx", s.line === false ? xs(s.x[i]) : px);
        dots[k].setAttribute("cy", ys(s.line === false ? yv : interpY(s, xv)));
        var val = s.line === false ? yv : interpY(s, xv);
        html += '<div class="row"><span class="sw" style="background:' + col(s.color) + '"></span>' + s.name + "<b>" + (s.fmt || Y.fmt || function (v) { return v.toFixed(2); })(val) + (Y.unit ? " " + Y.unit : "") + "</b></div>";
        any = true;
      });
      if (o.tipExtra) html += o.tipExtra(xv);
      vline.setAttribute("x1", px); vline.setAttribute("x2", px);
      hover.setAttribute("visibility", "visible");
      if (!any && !o.tipExtra) { tip.hidden = true; return; }
      tip.innerHTML = html; tip.hidden = false;
      var bw = box.clientWidth, tw = tip.offsetWidth, cx = px / sx;
      tip.style.left = (cx + 14 + tw > bw ? Math.max(0, cx - 14 - tw) : cx + 14) + "px";
      tip.style.top = Math.max(0, (m.t + 6) / sx) + "px";
    }
    function interpY(s, xv) {
      var i = bsearch(s.x, xv), j = s.x[i] <= xv ? i + 1 : i - 1;
      if (j < 0 || j >= s.x.length || s.y[j] == null || s.y[i] == null) return s.y[i];
      var a = Math.min(i, j), b = Math.max(i, j);
      var t = X.log ? (Math.log(xv) - Math.log(s.x[a])) / (Math.log(s.x[b]) - Math.log(s.x[a])) : (xv - s.x[a]) / (s.x[b] - s.x[a]);
      return s.y[a] + (s.y[b] - s.y[a]) * Math.max(0, Math.min(1, t));
    }
    function leave() { hover.setAttribute("visibility", "hidden"); tip.hidden = true; }
    ov.addEventListener("pointermove", move);
    ov.addEventListener("pointerdown", move);
    ov.addEventListener("pointerleave", leave);
  };

  // ------------------------------------------------------------------ diagrams
  var dgN = 0;
  function diagram(host, o) {
    var id = "dg" + (++dgN), s = [];
    s.push('<svg viewBox="0 0 ' + o.w + " " + o.h + '" role="img" aria-label="' + o.aria + '" style="min-width:' + (o.minw || 440) + 'px">');
    s.push('<defs><marker id="' + id + 'a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 z" fill="currentColor"/></marker>');
    s.push('<marker id="' + id + 'h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 1 L9 5 L0 9 z" class="dg-hlf"/></marker></defs>');
    (o.edges || []).forEach(function (e) {
      var pts = e.p.map(function (p) { return p[0] + "," + p[1]; }).join(" ");
      s.push('<polyline points="' + pts + '" fill="none" class="' + (e.hl ? "dg-hle" : "dg-e") + '"' + (e.dash ? ' stroke-dasharray="4 3"' : "") + (e.noarrow ? "" : ' marker-end="url(#' + id + (e.hl ? "h" : "a") + ')"') + "/>");
      if (e.label) s.push('<text x="' + e.lx + '" y="' + e.ly + '" text-anchor="' + (e.anchor || "middle") + '" class="dg-el">' + e.label + "</text>");
    });
    (o.nodes || []).forEach(function (n) {
      if (n.kind === "sum") {
        s.push('<circle cx="' + n.x + '" cy="' + n.y + '" r="' + (n.r || 16) + '" class="dg-box"/><text x="' + n.x + '" y="' + (n.y + 5) + '" text-anchor="middle" class="dg-t1">Σ</text>');
        return;
      }
      if (n.kind === "dot") { s.push('<circle cx="' + n.x + '" cy="' + n.y + '" r="3.2" fill="currentColor"/>'); return; }
      s.push('<rect x="' + n.x + '" y="' + n.y + '" width="' + n.w + '" height="' + n.h + '" rx="5" class="' + (n.hl ? "dg-hl" : n.kind === "note" ? "dg-note" : "dg-box") + '"/>');
      var lines = n.t, lh = 14, y0 = n.y + n.h / 2 - (lines.length - 1) * lh / 2 + 4;
      lines.forEach(function (t, i) { s.push('<text x="' + (n.x + n.w / 2) + '" y="' + (y0 + i * lh) + '" text-anchor="middle" class="' + (i === 0 ? "dg-t1" : "dg-t2") + '">' + t + "</text>"); });
    });
    (o.texts || []).forEach(function (t) { s.push('<text x="' + t.x + '" y="' + t.y + '" text-anchor="' + (t.a || "start") + '" class="' + (t.c || "dg-t2") + '">' + t.t + "</text>"); });
    s.push("</svg>");
    host.innerHTML = s.join("");
  }
  var dgCss = document.createElement("style");
  dgCss.textContent = ".dg-box{fill:var(--surface);stroke:currentColor;stroke-opacity:.55;stroke-width:1.2}" +
    ".dg-note{fill:none;stroke:currentColor;stroke-opacity:.45;stroke-dasharray:4 3}" +
    ".dg-hl{fill:var(--accent-soft);stroke:var(--accent);stroke-width:1.6}" +
    ".dg-e{stroke:currentColor;stroke-opacity:.7;stroke-width:1.3}.dg-hle{stroke:var(--accent);stroke-width:1.8}.dg-hlf{fill:var(--accent)}" +
    ".dg-t1{font-size:12.5px;font-weight:600;fill:var(--ink)}.dg-t2{font-size:11px;fill:var(--ink-2)}" +
    ".dg-el{font-size:10.5px;fill:var(--ink-2);paint-order:stroke;stroke:var(--surface);stroke-width:3px}";
  document.head.appendChild(dgCss);

  function drawDiagrams() {
    diagram($("#dg-a1"), { w: 640, h: 300, aria: "Equivalent circuit: amplifier, voice coil, Bl gyrator, two woofer cones driving a shared box node that feeds two passive radiators; front and PR volume velocities sum into pressure at 1 m",
      nodes: [
        { x: 10, y: 20, w: 96, h: 50, t: ["Amplifier", "15.5 V pk, 4.5 A"] },
        { x: 126, y: 20, w: 104, h: 50, t: ["Voice coil", "Re + jωLe"] },
        { x: 250, y: 20, w: 76, h: 50, t: ["Bl", "gyrator"] },
        { x: 346, y: 20, w: 140, h: 50, t: ["Woofer cones ×2", "Mms, Cms, Rms, Sd"] },
        { x: 420, y: 148, w: 200, h: 68, t: ["Box air", "Cab = Vb·k / ρc²", "Rab (Q_A), leak Ral (Q_L)"], hl: true },
        { x: 190, y: 148, w: 190, h: 68, t: ["Passive radiators ×2", "Mmp + m_add", "Cmp, Rmp, Sp"], hl: true },
        { kind: "sum", x: 110, y: 182 },
        { x: 50, y: 240, w: 120, h: 46, t: ["Pressure, 1 m", "half space (2π)"] }],
      edges: [
        { p: [[106, 45], [126, 45]] }, { p: [[230, 45], [250, 45]] }, { p: [[326, 45], [346, 45]] },
        { p: [[440, 70], [440, 104], [520, 104], [520, 148]], label: "rear of cones", lx: 528, ly: 100, anchor: "start" },
        { p: [[420, 182], [380, 182]], label: "p_box", lx: 400, ly: 174 },
        { p: [[190, 182], [128, 182]], label: "U_p", lx: 160, ly: 174 },
        { p: [[376, 70], [376, 96], [110, 96], [110, 164]], label: "front of cones: U_d", lx: 244, ly: 90 },
        { p: [[110, 198], [110, 240]] }],
      texts: [{ x: 620, y: 238, a: "end", t: "k = stuffing × zeolite factor" }] });

    diagram($("#dg-a3"), { w: 640, h: 300, aria: "BEM flow: CAD parameters to mesh to bempp solve to six unit solutions, weighted by velocities to give pressure anywhere",
      nodes: [
        { x: 10, y: 20, w: 120, h: 56, t: ["CAD parameters", "speaker_concept.py"] },
        { x: 150, y: 20, w: 140, h: 56, t: ["gmsh hull mesh", "h ≤ λ/6, 2.8 mm", "at the tweeters"] },
        { x: 310, y: 20, w: 140, h: 56, t: ["bempp-cl solve", "CHIEF, 1 m/s", "on one piston"] },
        { x: 470, y: 20, w: 160, h: 56, t: ["6 unit solutions", "2 woofers, 2 PRs,", "2 tweeters"] },
        { x: 300, y: 140, w: 200, h: 56, t: ["Velocities per volt", "A1 cones and PRs,", "tweeter T/S model"] },
        { kind: "sum", x: 550, y: 168 },
        { x: 360, y: 232, w: 270, h: 56, t: ["Pressure anywhere", "polar maps, 15 seats,", "desk as an image source"] },
        { x: 10, y: 140, w: 250, h: 56, kind: "note", t: ["Checked against", "exact sphere piston ≤ 0.34 dB,", "Burton–Miller ≤ 0.15 dB"] }],
      edges: [
        { p: [[130, 48], [150, 48]] }, { p: [[290, 48], [310, 48]] }, { p: [[450, 48], [470, 48]] },
        { p: [[550, 76], [550, 152]] }, { p: [[500, 168], [534, 168]], label: "× weights", lx: 517, ly: 160 },
        { p: [[550, 184], [550, 232]] }] });

    diagram($("#dg-a4"), { w: 640, h: 220, aria: "FEM flow: STEP geometry and materials into a tied tetrahedral mesh, CalculiX eigenmodes, excitation indices, and the shell to woofer output ratio",
      nodes: [
        { x: 10, y: 20, w: 120, h: 56, t: ["Concept STEP", "shells, tray, caps"] },
        { x: 150, y: 20, w: 150, h: 56, t: ["gmsh, fragmented", "C3D10 at 3.5 mm", "0.5 M DOF, tied"] },
        { x: 320, y: 20, w: 130, h: 56, t: ["CalculiX", "*FREQUENCY", "30 modes"] },
        { x: 470, y: 20, w: 160, h: 56, t: ["Excitation index", "box pressure on skin", "+ cone reaction"] },
        { x: 150, y: 140, w: 150, h: 56, t: ["PETG + 40 % core", "point masses: woofers,", "PRs, battery"] },
        { x: 10, y: 140, w: 120, h: 56, t: ["What-ifs", "ribs, gussets,", "spine plate"], hl: true },
        { x: 470, y: 140, w: 160, h: 56, t: ["Shell ÷ woofer output", "modal sum, η = 0.03"] }],
      edges: [
        { p: [[130, 48], [150, 48]] }, { p: [[300, 48], [320, 48]] }, { p: [[450, 48], [470, 48]] },
        { p: [[225, 140], [225, 76]] }, { p: [[70, 140], [70, 110], [190, 110], [190, 76]], hl: true },
        { p: [[550, 76], [550, 140]] }] });

    var cx = function (i) { return 10 + i * 112; }, bw = 98;
    diagram($("#dg-a5"), { w: 740, h: 200, minw: 480, aria: "Signal chain for one side: input splits into woofer path (bass EQ, LR4 low-pass, amp, woofer and PR, BEM) and tweeter path (trim, LR4 high-pass, delay, amp and tweeter, BEM), summed at the listener",
      nodes: [
        { x: cx(0), y: 72, w: bw, h: 50, t: ["Input", "2.83 V ref."] },
        { x: cx(1), y: 10, w: bw, h: 50, t: ["Bass EQ", "4 biquads"] },
        { x: cx(2), y: 10, w: bw, h: 50, t: ["LR4 low-pass", "2.5 kHz"] },
        { x: cx(3), y: 10, w: bw, h: 50, t: ["Amp ch. A", "BTL"] },
        { x: cx(4), y: 10, w: bw, h: 50, t: ["Woofer + PR", "A1 velocities"] },
        { x: cx(5), y: 10, w: bw, h: 50, t: ["BEM transfer", "to listener"] },
        { x: cx(1), y: 134, w: bw, h: 50, t: ["Trim", "−9.7 dB"] },
        { x: cx(2), y: 134, w: bw, h: 50, t: ["LR4 high-pass", "2.5 kHz"] },
        { x: cx(3), y: 134, w: bw, h: 50, t: ["Delay", "110 µs"], hl: true },
        { x: cx(4), y: 134, w: bw, h: 50, t: ["Amp ch. B +", "tweeter T/S"] },
        { x: cx(5), y: 134, w: bw, h: 50, t: ["BEM transfer", "to listener"] },
        { kind: "sum", x: 712, y: 97 }],
      edges: [
        { p: [[cx(0) + 49, 72], [cx(0) + 49, 35], [cx(1), 35]] }, { p: [[cx(0) + 49, 122], [cx(0) + 49, 159], [cx(1), 159]] },
        { p: [[cx(1) + bw, 35], [cx(2), 35]] }, { p: [[cx(2) + bw, 35], [cx(3), 35]] }, { p: [[cx(3) + bw, 35], [cx(4), 35]] }, { p: [[cx(4) + bw, 35], [cx(5), 35]] },
        { p: [[cx(1) + bw, 159], [cx(2), 159]] }, { p: [[cx(2) + bw, 159], [cx(3), 159]], hl: true }, { p: [[cx(3) + bw, 159], [cx(4), 159]], hl: true }, { p: [[cx(4) + bw, 159], [cx(5), 159]] },
        { p: [[cx(5) + bw, 35], [712, 35], [712, 81]] }, { p: [[cx(5) + bw, 159], [712, 159], [712, 113]] }],
      texts: [{ x: 712, y: 192, a: "middle", t: "listener" }] });

    diagram($("#dg-s1"), { w: 640, h: 236, aria: "Boost control loop: power stage drives the output capacitor bank; the divider feeds the error amplifier whose compensation network sets the control voltage",
      nodes: [
        { x: 10, y: 20, w: 110, h: 56, t: ["VSYS", "6.0–8.4 V", "2S Li-ion"] },
        { x: 150, y: 20, w: 170, h: 56, t: ["Power stage", "Gm(1−D), RHP zero,", "sampling He(s)"] },
        { x: 350, y: 20, w: 170, h: 56, t: ["Output node Zo", "1.48 mF bank", "+ amp load (−R)"] },
        { x: 380, y: 132, w: 140, h: 56, t: ["Divider kFB", "300 k / 21.8 k"] },
        { x: 210, y: 132, w: 140, h: 56, t: ["Error amp", "gm 195 µS", "REA 20 MΩ"] },
        { x: 20, y: 132, w: 160, h: 56, t: ["Rc 33 k → 100 k", "Cc 47 n → 15 n", "Cp 10 p + 70 p int."], hl: true }],
      edges: [
        { p: [[120, 48], [150, 48]] }, { p: [[320, 48], [350, 48]], label: "iL", lx: 335, ly: 41 },
        { p: [[520, 48], [620, 48]], label: "PVDD 18 V", lx: 572, ly: 41 },
        { p: [[590, 48], [590, 160], [520, 160]] }, { p: [[380, 160], [350, 160]], label: "FB", lx: 365, ly: 152 },
        { p: [[210, 160], [180, 160]], hl: true }, { p: [[100, 132], [100, 104], [235, 104], [235, 76]], hl: true, label: "COMP (vc)", lx: 168, ly: 98 }],
      texts: [{ x: 320, y: 224, a: "middle", t: "T(s) = Gm(1−D)(1 − s/ωRHP)·He·Zo·kFB·GEA·Zc" }] });

    diagram($("#dg-s2"), { w: 640, h: 220, aria: "BTL output: two half-bridge legs each through a 10 microhenry inductor with a 1 microfarad capacitor to ground, into the driver model",
      nodes: [
        { x: 10, y: 40, w: 120, h: 130, t: ["TAS5805M", "two half-bridges", "PVDD 18 V", "768 kHz PWM", "BD or 1SPW"] },
        { x: 170, y: 40, w: 100, h: 40, t: ["L 10 µH", "68 mΩ"] },
        { x: 170, y: 130, w: 100, h: 40, t: ["L 10 µH", "68 mΩ"] },
        { kind: "dot", x: 328, y: 60 }, { kind: "dot", x: 328, y: 150 },
        { x: 286, y: 2, w: 84, h: 28, t: ["C 1 µF → GND"] },
        { x: 286, y: 182, w: 84, h: 28, t: ["C 1 µF → GND"] },
        { x: 430, y: 30, w: 200, h: 150, t: ["Driver electrical model", "Re + jωLe", "+ motional R‖L‖C at fs", "woofer: 7.4 Ω, 0.61 mH", "tweeter: 3.17 Ω, 10 µH"], hl: true }],
      edges: [
        { p: [[130, 60], [170, 60]], label: "leg A", lx: 150, ly: 53 }, { p: [[130, 150], [170, 150]], label: "leg B", lx: 150, ly: 143 },
        { p: [[270, 60], [430, 60]] }, { p: [[270, 150], [430, 150]] },
        { p: [[328, 60], [328, 30]], noarrow: true }, { p: [[328, 150], [328, 182]], noarrow: true }] });

    diagram($("#dg-s3"), { w: 600, h: 270, aria: "NTC divider: REGN through RT1 to the TS node, then RT2 in parallel with the NTC to ground; TS feeds the charger's four comparators",
      nodes: [
        { x: 40, y: 10, w: 160, h: 40, t: ["REGN"] },
        { x: 40, y: 80, w: 160, h: 44, t: ["RT1 5.1 k"] },
        { kind: "dot", x: 120, y: 152 },
        { x: 40, y: 180, w: 160, h: 50, t: ["RT2 30 k ‖ NTC 10 k", "B 3435 (or 3380)"], hl: true },
        { x: 300, y: 92, w: 280, h: 120, t: ["BQ25792 TS comparators", "VT1 73.3 %: cold stop", "TS_COOL 68.4 %: 20 % current", "TS_WARM 44.8 %: VREG − 400 mV", "VT5 34.2 %: hot stop"] }],
      edges: [{ p: [[120, 50], [120, 80]], noarrow: true }, { p: [[120, 124], [120, 180]], noarrow: true }, { p: [[120, 230], [120, 242]], noarrow: true }, { p: [[120, 152], [300, 152]], label: "TS = REGN × ratio", lx: 210, ly: 145 }],
      texts: [{ x: 120, y: 254, a: "middle", t: "GND" }] });

    diagram($("#dg-s4"), { w: 760, h: 180, minw: 480, aria: "Trim injection: GPIO PWM through two RC poles and a diode and 68k resistor into the boost feedback node, alongside the PVDD divider",
      nodes: [
        { x: 10, y: 20, w: 100, h: 50, t: ["GPIO", "20 kHz PWM"] },
        { x: 128, y: 20, w: 110, h: 50, t: ["R908 / C917", "10 k / 1 µF"] },
        { x: 256, y: 20, w: 110, h: 50, t: ["R909 / C918", "10 k / 1 µF"] },
        { x: 384, y: 20, w: 100, h: 50, t: ["D901", "1N4148W"], hl: true },
        { x: 502, y: 20, w: 90, h: 50, t: ["R907", "68 k"], hl: true },
        { kind: "dot", x: 620, y: 45 },
        { x: 650, y: 20, w: 100, h: 50, t: ["Boost EA", "FB → 1.198 V"] },
        { x: 540, y: 112, w: 160, h: 50, t: ["Divider", "300 k / 21.8 k"] },
        { x: 330, y: 112, w: 150, h: 50, t: ["PVDD", "12.2–18 V"] }],
      edges: [
        { p: [[110, 45], [128, 45]] }, { p: [[238, 45], [256, 45]] }, { p: [[366, 45], [384, 45]] }, { p: [[484, 45], [502, 45]], hl: true },
        { p: [[592, 45], [617, 45]], hl: true, label: "current into FB only", lx: 604, ly: 88 },
        { p: [[620, 45], [650, 45]] }, { p: [[620, 112], [620, 48]], noarrow: true }, { p: [[480, 137], [540, 137]] }] });

    diagram($("#dg-s5"), { w: 680, h: 196, aria: "Auto-reset: CH340C DTR and RTS cross-drive two transistors that pull ESP32 EN and GPIO0 low",
      nodes: [
        { x: 10, y: 20, w: 110, h: 44, t: ["CH340C", "DTR#"] },
        { x: 10, y: 130, w: 110, h: 44, t: ["CH340C", "RTS#"] },
        { x: 200, y: 20, w: 120, h: 44, t: ["Q201 2N3904", "pulls EN low"] },
        { x: 200, y: 130, w: 120, h: 44, t: ["Q202 2N3904", "pulls IO0 low"] },
        { x: 380, y: 20, w: 160, h: 44, t: ["EN: R101 10 k", "C103 1 → 2.2 µF"], hl: true },
        { x: 380, y: 130, w: 160, h: 44, t: ["GPIO0 strap", "10 k + 45 k pull-up"] },
        { x: 580, y: 54, w: 90, h: 86, t: ["ESP32", "samples IO0", "as EN rises"] }],
      edges: [
        { p: [[120, 42], [200, 42]], label: "base", lx: 160, ly: 35 }, { p: [[120, 152], [200, 152]], label: "base", lx: 160, ly: 166 },
        { p: [[120, 56], [200, 140]], dash: true }, { p: [[120, 138], [200, 54]], dash: true },
        { p: [[320, 42], [380, 42]] }, { p: [[320, 152], [380, 152]] }, { p: [[540, 42], [580, 80]] }, { p: [[540, 152], [580, 116]] }],
      texts: [{ x: 160, y: 99, a: "middle", t: "emitters" }] });

    var sx = function (i) { return 10 + i * 125; };
    diagram($("#dg-s6"), { w: 640, h: 200, aria: "Signal path: ESP32 pad, series resistor, main-board trace, connector, 200 millimetre FFC, connector, UI trace, display wiring, display input",
      nodes: [
        { x: sx(0), y: 20, w: 108, h: 52, t: ["ESP32 pad", "20–45 Ω, 0.6–2 ns"] },
        { x: sx(1), y: 20, w: 108, h: 52, t: ["Rs", "33 → 68 Ω"], hl: true },
        { x: sx(2), y: 20, w: 108, h: 52, t: ["Main board", "40 mm, 50 Ω"] },
        { x: sx(3), y: 20, w: 108, h: 52, t: ["Connector", "2 nH, 0.3 pF"] },
        { x: sx(4), y: 20, w: 108, h: 52, t: ["FFC 200 mm", "107 Ω, 0.83 ns"] },
        { x: sx(4), y: 128, w: 108, h: 52, t: ["Connector", "2 nH, 0.3 pF"] },
        { x: sx(3), y: 128, w: 108, h: 52, t: ["UI board", "25 mm, 55 Ω"] },
        { x: sx(2), y: 128, w: 108, h: 52, t: ["Display wiring", "30 mm, 70 Ω"] },
        { x: sx(1), y: 128, w: 108, h: 52, t: ["GC9A01", "6 pF input"] }],
      edges: [
        { p: [[sx(0) + 108, 46], [sx(1), 46]], hl: true }, { p: [[sx(1) + 108, 46], [sx(2), 46]] }, { p: [[sx(2) + 108, 46], [sx(3), 46]] }, { p: [[sx(3) + 108, 46], [sx(4), 46]] },
        { p: [[sx(4) + 54, 72], [sx(4) + 54, 128]] }, { p: [[sx(4), 154], [sx(3) + 108, 154]] }, { p: [[sx(3), 154], [sx(2) + 108, 154]] }, { p: [[sx(2), 154], [sx(1) + 108, 154]] }],
      texts: [{ x: sx(0) + 54, y: 150, a: "middle", t: "Z0 from own" }, { x: sx(0) + 54, y: 164, a: "middle", t: "2-D field solver" }] });

    diagram($("#dg-s7"), { w: 640, h: 200, aria: "PDN: for PVDD the boost loop branch feeds copper and the capacitor bank to the amps; for 3V3 the buck loop feeds copper and decoupling to the ESP32, UI and amps",
      nodes: [
        { x: 10, y: 20, w: 150, h: 56, t: ["Boost loop (S1)", "Zo / (1 + T)"], hl: true },
        { x: 180, y: 20, w: 120, h: 56, t: ["Copper", "R–L placeholder"] },
        { x: 320, y: 20, w: 170, h: 56, t: ["PVDD bank", "16 × 10 µF MLCC", "3 × 470 µF electrolytic"] },
        { x: 510, y: 20, w: 120, h: 56, t: ["Amp PVDD pins", "ΔI 5 A"] },
        { x: 10, y: 120, w: 150, h: 56, t: ["TPS62933 buck", "R‖L branch, fc 35 kHz"] },
        { x: 180, y: 120, w: 120, h: 56, t: ["Copper", "R–L placeholder"] },
        { x: 320, y: 120, w: 170, h: 56, t: ["Local decoupling", "MLCCs, ESL by case"] },
        { x: 510, y: 120, w: 120, h: 56, t: ["ESP32, UI, amps", "ΔI 0.33 A"] }],
      edges: [
        { p: [[160, 48], [180, 48]] }, { p: [[300, 48], [320, 48]] }, { p: [[490, 48], [510, 48]] },
        { p: [[160, 148], [180, 148]] }, { p: [[300, 148], [320, 148]] }, { p: [[490, 148], [510, 148]] }],
      texts: [{ x: 10, y: 100, t: "Below ~1 kHz the loop sets |Z|; above it, the capacitors." }] });
  }

  // ------------------------------------------------------------------ data loading
  var files = ["a1", "a2", "a3", "a4", "a5", "s1", "s2s3s6", "s4s5", "s7"];
  drawDiagrams();
  Promise.all(files.map(function (f) { return fetch("data/" + f + ".json").then(function (r) { if (!r.ok) throw new Error(f); return r.json(); }); }))
    .then(function (arr) {
      var D = {}; files.forEach(function (f, i) { D[f] = arr[i]; });
      [initA1, initA2, initA3, initA4, initA5, initS1, initS2, initS3, initS4, initS5, initS6, initS7].forEach(function (fn) {
        try { fn(D); } catch (e) { console.error(fn.name, e); }
      });
    })
    .catch(function (e) {
      document.querySelectorAll(".bench").forEach(function (b) { b.insertBefore(h("p", "calib", "The result data did not load (" + e.message + "). Charts need the data files published beside this page."), b.firstChild); });
    });

  // ------------------------------------------------------------------ A1 bass explorer
  function initA1(D) {
    var a1 = D.a1, B = window.Bass, W = a1.woofer, P = a1.pr;
    var F = B.logspace(10, 20000, 600);
    var st = { vb: 0.82, m: 3.5, z: 1, fill: "empty", ql: 10, eq: "shipped" };
    var FILL = { empty: { k: 1, qa: 100 }, light: { k: 1.10, qa: 30 }, heavy: { k: 1.20, qa: 10 } };
    function opts(s) {
      var f = FILL[s.fill], qa = f.qa;
      if (s.z > 1.0001) qa = Math.min(qa, 30);
      return { f: F, vb: s.vb * 1e-3, m_add: s.m * 1e-3, ql: s.ql, qa: qa, vb_factor: f.k * s.z,
        eqMode: s.eq === "off" ? "off" : s.eq === "shipped" ? "biquad" : "ideal", sos: a1.sos48k };
    }
    var BASE = {};
    ["off", "shipped", "refit"].forEach(function (e) { BASE[e] = B.evaluate(W, P, opts({ vb: 0.82, m: 3.5, z: 1, fill: "empty", ql: 10, eq: e })); });

    // calibration against the A1 result files, run live
    (function () {
      var fr = a1.ref.f, r = B.evaluate(W, P, { f: fr, vb: 0.82e-3, m_add: 3.5e-3, ql: 10, qa: 100, eqMode: "biquad", sos: a1.sos48k });
      var dS = 0, dX = 0, dZ = 0;
      fr.forEach(function (f, i) {
        var p = B.abs(r.sys.p_hs[i]);
        dS = Math.max(dS, Math.abs(B.splPk(p * 2.83 * Math.SQRT2) - a1.ref.spl_2v83[i]));
        dX = Math.max(dX, Math.abs(B.abs(r.sys.x_d[i]) * 15.5e3 - a1.ref.xd_15v5[i]), Math.abs(B.abs(r.sys.x_p[i]) * 15.5e3 - a1.ref.xp_15v5[i]));
        dZ = Math.max(dZ, Math.abs(B.abs(r.sys.zin[i]) - a1.ref.zmag[i]));
      });
      var b = BASE.shipped, s = a1.summary;
      $("#a1-calib").innerHTML = "<strong>Calibration check, run in your browser on load.</strong> At the A1 design point (0.82 L, 3.5 g, empty, Q<sub>L</sub> 10) this model gives f<sub>b</sub> " + b.sys.fb.toFixed(2) +
        " Hz, F3 " + b.f3eq.toFixed(2) + " Hz with the shipped EQ, and a pink-noise maximum of " + b.pink.db.toFixed(2) + " dB. A1 reported " + s.fb_hz.toFixed(2) + " Hz, " + s.f3_eq_biquad_hz.toFixed(2) + " Hz and " + s.pink_db.toFixed(2) +
        " dB. Its curves match <code>a1_spl_halfspace_1m.csv</code>, <code>a1_excursion_vs_xmax.csv</code> and <code>a1_impedance.csv</code> within " + dS.toFixed(3) + " dB, " + dX.toFixed(4) + " mm and " + dZ.toFixed(4) +
        " Ω from 10 Hz to 1 kHz. It is a line-for-line port of <code>bass_model.py</code>, so it sits far inside the 0.5 dB target.";
    })();

    var vbI = $("#a1-vb"), mI = $("#a1-m"), zI = $("#a1-z");
    var sFill = seg($("#a1-fill"), [{ v: "empty", l: "Empty" }, { v: "light", l: "Light polyfill" }, { v: "heavy", l: "Heavy polyfill" }], st.fill, function (v) { st.fill = v; upd(); });
    var sQl = seg($("#a1-ql"), [{ v: 5, l: "5 leaky" }, { v: 10, l: "10" }, { v: 20, l: "20 tight" }], st.ql, function (v) { st.ql = +v; upd(); });
    var sEq = seg($("#a1-eq"), [{ v: "off", l: "Off" }, { v: "shipped", l: "As shipped" }, { v: "refit", l: "Re-fitted" }], st.eq, function (v) { st.eq = v; upd(); });
    [vbI, mI, zI].forEach(function (i) { i.addEventListener("input", function () { st.vb = +vbI.value; st.m = +mI.value; st.z = +zI.value; sched(); }); });
    $("#a1-reset").addEventListener("click", function () {
      st = { vb: 0.82, m: 3.5, z: 1, fill: "empty", ql: 10, eq: "shipped" };
      vbI.value = 0.82; mI.value = 3.5; zI.value = 1; sFill.set("empty"); sQl.set(10); sEq.set("shipped"); upd();
    });
    var pend = false;
    function sched() { if (pend) return; pend = true; requestAnimationFrame(function () { pend = false; upd(); }); }

    var sel = []; F.forEach(function (f, i) { if (f >= 15 && f <= 1000) sel.push(i); });
    var fx = sel.map(function (i) { return F[i]; });
    var X = { log: true, min: 15, max: 1000, label: "Hz" };
    var cS = new LineChart($("#a1-spl"), { title: "SPL at 1 m, half space", sub: "", height: 290, x: X, y: { min: 40, max: 105, label: "dB SPL", unit: "dB", fmt: function (v) { return v.toFixed(1); } }, series: [] });
    var cX = new LineChart($("#a1-x"), { title: "Excursion vs limits", sub: "", height: 250, x: X, y: { min: 0, max: 8, label: "mm peak", unit: "mm" }, series: [] });
    var cZ = new LineChart($("#a1-imp"), { title: "Impedance of one woofer", sub: "In the PR box. The dip between the two peaks sits near f_b.", height: 250, x: X, y: { min: 0, label: "Ω", unit: "Ω", fmt: function (v) { return v.toFixed(2); } }, series: [] });

    function curves(r, eq) {
      var o = { spl: [], max: [], xd: [], xp: [], z: [] }, on = eq !== "off";
      sel.forEach(function (i) {
        var p = B.abs(r.sys.p_hs[i]), g = r.g[i];
        o.spl.push(B.splPk(p * 2.83 * Math.SQRT2 * g));
        o.max.push(on ? B.splPk(p * g * r.ceilV) : B.splPk(p * r.lim.v[i]));
        var drive = on ? g * r.ceilV : B.V_PK_MAX;
        o.xd.push(B.abs(r.sys.x_d[i]) * drive * 1e3); o.xp.push(B.abs(r.sys.x_p[i]) * drive * 1e3);
        o.z.push(B.abs(r.sys.zin[i]));
      });
      return o;
    }
    function upd() {
      $("#a1-vb-o").textContent = st.vb.toFixed(2) + " L";
      $("#a1-m-o").textContent = st.m.toFixed(2) + " g";
      $("#a1-z-o").textContent = st.z > 1.0001 ? "×" + st.z.toFixed(2) : "none";
      var r = B.evaluate(W, P, opts(st)), b = BASE[st.eq], on = st.eq !== "off";
      var c = curves(r, st.eq), cb = curves(b, st.eq);
      var lim = on ? "EQ'd ceiling " + r.ceilDb.toFixed(1) + " dB (set at " + Math.round(r.ceilF) + " Hz)" : "lowest of the four limits";
      cS.set({ sub: on ? "2.83 V per woofer through the bass EQ, and the highest flat level the EQ'd system can play cleanly." : "2.83 V per woofer with no EQ, and the maximum clean sine at each frequency (" + lim + ").",
        series: [
          { name: "A1 design, 2.83 V", x: fx, y: cb.spl, color: "--muted", dash: "5 4", width: 1.5 },
          { name: "This box, 2.83 V", x: fx, y: c.spl, color: "--s1" },
          { name: on ? "Max clean level with EQ" : "Max clean sine", x: fx, y: c.max, color: "--s2" }],
        vrefs: [{ x: r.sys.fb, label: "f_b " + r.sys.fb.toFixed(1) }, { x: r.sys.fp, label: "f_p " + r.sys.fp.toFixed(1), left: true }],
        tipExtra: function (xv) { var i = sel[bsearch(fx, xv)]; return on ? "" : '<div class="row">limited by<b>' + B.LIMITS[r.lim.which[i]] + "</b></div>"; } });
      cX.set({ sub: on ? "Drive: the EQ'd signal at the maximum clean level. The subsonic filter keeps the PRs off their stops." : "Drive: 15.5 V peak sine, the woofer limiter ceiling, no EQ.",
        series: [{ name: "Woofer", x: fx, y: c.xd, color: "--s1" }, { name: "Passive radiator", x: fx, y: c.xp, color: "--s2" }],
        refs: [{ y: 3.5, label: "Woofer Xmax 3.5 mm", color: "--s1" }, { y: 5, label: "PR usable 5 mm", color: "--s2" }] });
      cZ.set({ series: [{ name: "A1 design", x: fx, y: cb.z, color: "--muted", dash: "5 4", width: 1.5 }, { name: "This box", x: fx, y: c.z, color: "--s1" }] });
      var d = function (v, bv, n, u) { var dv = v - bv; return Math.abs(dv) < Math.pow(10, -n) / 2 ? "same as A1" : (dv > 0 ? "+" : "−") + Math.abs(dv).toFixed(n) + " " + u + " vs A1"; };
      var f3ok = r.f3eq <= 65, f6ok = r.f6eq <= 55, pk = r.pink.db;
      var ro = [
        ["Box tuning f<sub>b</sub>", r.sys.fb.toFixed(1), "Hz", d(r.sys.fb, b.sys.fb, 1, "Hz")],
        ["PR notch f<sub>p</sub>", r.sys.fp.toFixed(1), "Hz", d(r.sys.fp, b.sys.fp, 1, "Hz")],
        [on ? "F3 with EQ" : "F3, no EQ", r.f3eq.toFixed(1), "Hz", chip(f3ok, "≤ 65 Hz")],
        [on ? "F6 with EQ" : "F6, no EQ", r.f6eq.toFixed(1), "Hz", chip(f6ok, "≤ 55 Hz", !f6ok && r.f6eq < 56)],
        ["Pink-noise max", pk.toFixed(2), "dB", chip(pk >= 90, "≥ 90 dB", pk >= 90 && pk < 90.5) + " " + r.pink.limit],
        ["Max EQ boost", on ? r.maxBoost.toFixed(1) : "—", on ? "dB" : "", on ? d(r.maxBoost, b.maxBoost, 1, "dB") : "EQ off"],
        ["Minimum |Z|", r.zmin.toFixed(2), "Ω", "15 Hz–1 kHz"]];
      $("#a1-ro").innerHTML = ro.map(function (x) { return '<div class="ro"><span class="k">' + x[0] + '</span><span class="v">' + x[1] + "<small>" + x[2] + '</small></span><span class="d">' + x[3] + "</span></div>"; }).join("");
      var fq = [40, 50, 63, 80, 100, 150, 200];
      var rowsT = fq.map(function (f) { var i = bsearch(r.f, f), ib = i; return "<tr><td class='n'>" + f + " Hz</td><td class='n'>" + B.splPk(B.abs(r.sys.p_hs[i]) * r.lim.v[i]).toFixed(1) + "</td><td>" + B.LIMITS[r.lim.which[i]] + "</td><td class='n'>" + B.splPk(B.abs(BASE.off.sys.p_hs[ib]) * BASE.off.lim.v[ib]).toFixed(1) + "</td><td>" + B.LIMITS[BASE.off.lim.which[ib]] + "</td></tr>"; });
      $("#a1-lim").innerHTML = "<thead><tr><th>Sine, no EQ</th><th class='n'>This box, dB</th><th>Limited by</th><th class='n'>A1 design, dB</th><th>Limited by</th></tr></thead><tbody>" + rowsT.join("") + "</tbody>";
    }
    upd();
  }

  // ------------------------------------------------------------------ A2 tweeter directivity
  function rampColors() {
    var dark = document.documentElement.getAttribute("data-theme") === "dark" || (document.documentElement.getAttribute("data-theme") !== "light" && matchMedia("(prefers-color-scheme: dark)").matches);
    var light = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#0d366b"];
    return dark ? light.slice().reverse() : light;
  }
  function binOf(v) { return Math.max(0, Math.min(11, Math.floor((v + 36) / 3))); }

  function initA2(D) {
    var a2 = D.a2, F = a2.f, A = a2.angles;
    var st = { c: "bezel", p: "v", i: F.indexOf(5040) >= 0 ? F.indexOf(5040) : bsearch(F, 5000) };
    var CASES = { bezel: { l: "3 mm bezel (as built)", c: "--s1" }, waveguide: { l: "10 mm waveguide", c: "--s2" }, baffle: { l: "Flat baffle (analytic)", c: "--s3" } };
    var fI = $("#a2-f"); fI.max = F.length - 1; fI.value = st.i;
    seg($("#a2-case"), Object.keys(CASES).map(function (k) { return { v: k, l: CASES[k].l }; }), st.c, function (v) { st.c = v; draw(); });
    seg($("#a2-plane"), [{ v: "v", l: "Vertical (toward desk)" }, { v: "h", l: "Horizontal" }], st.p, function (v) { st.p = v; draw(); });
    fI.addEventListener("input", function () { st.i = +fI.value; draw(); });
    var heat = $("#a2-heat"), canvas = h("canvas"), osvg = svgEl("svg", {}), tip = h("div", "tip");
    tip.hidden = true; heat.appendChild(canvas); heat.appendChild(osvg); heat.appendChild(tip);
    function listenerAngle() { var L = st.c === "waveguide" ? a2.listener_wg : a2.listener; return st.p === "v" ? L.vertical_deg : L.horizontal_deg; }
    var geo = null;
    function drawHeat() {
      var data = a2.maps[st.c + "_" + st.p], W = Math.max(260, heat.clientWidth || 500), H = 300;
      var m = { l: 40, r: 8, t: 8, b: 26 }, pw = W - m.l - m.r, ph = H - m.t - m.b;
      var dpr = window.devicePixelRatio || 1;
      canvas.width = W * dpr; canvas.height = H * dpr; canvas.style.height = H + "px";
      var ctx = canvas.getContext("2d"); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      var l0 = Math.log(F[0] / Math.pow(2, 1 / 24)), l1 = Math.log(F[F.length - 1] * Math.pow(2, 1 / 24));
      var xs = function (f) { return m.l + (Math.log(f) - l0) / (l1 - l0) * pw; };
      var ys = function (a) { return m.t + (180 - a) / 360 * ph; };
      var cols = rampColors(), empty = tok("--surface-2");
      for (var i = 0; i < F.length; i++) {
        var x0 = xs(i ? Math.sqrt(F[i - 1] * F[i]) : F[0] / Math.pow(2, 1 / 24)), x1 = xs(i < F.length - 1 ? Math.sqrt(F[i] * F[i + 1]) : F[i] * Math.pow(2, 1 / 24));
        for (var j = 0; j < A.length; j++) {
          var v = data[i][j];
          ctx.fillStyle = v == null ? empty : cols[binOf(v)];
          var y0 = ys(A[j] + 1.25), y1 = ys(A[j] - 1.25);
          ctx.fillRect(x0, y0, x1 - x0 + 0.6, y1 - y0 + 0.6);
        }
      }
      geo = { m: m, pw: pw, ph: ph, xs: xs, ys: ys, l0: l0, l1: l1, W: W, H: H, data: data };
      osvg.setAttribute("viewBox", "0 0 " + W + " " + H); osvg.innerHTML = "";
      var ink2 = tok("--ink-2"), surf = tok("--surface");
      [1000, 2000, 5000, 10000, 16000].forEach(function (f) { var t = svgEl("text", { x: xs(f), y: H - 8, "text-anchor": "middle" }, osvg); t.textContent = fmtTick(f); });
      [-180, -90, 0, 90, 180].forEach(function (a) { var t = svgEl("text", { x: m.l - 5, y: ys(a) + 3.5, "text-anchor": "end" }, osvg); t.textContent = (a > 0 ? "+" : "") + a + "°"; });
      var la = listenerAngle();
      svgEl("line", { x1: m.l, x2: m.l + pw, y1: ys(la), y2: ys(la), stroke: surf, "stroke-width": 3 }, osvg);
      svgEl("line", { x1: m.l, x2: m.l + pw, y1: ys(la), y2: ys(la), stroke: tok("--ink"), "stroke-width": 1.4, "stroke-dasharray": "6 4" }, osvg);
      var ltxt = "seated listener " + la.toFixed(1) + "°", ly = ys(la) + (la < 0 ? 8 : -24);
      svgEl("rect", { x: m.l + 4, y: ly, width: ltxt.length * 5.9 + 10, height: 16, rx: 3, fill: surf, opacity: 0.92 }, osvg);
      var lt = svgEl("text", { x: m.l + 9, y: ly + 12, class: "reflbl", style: "fill:" + tok("--ink") }, osvg);
      lt.textContent = ltxt;
      var cx = xs(F[st.i]);
      svgEl("line", { x1: cx, x2: cx, y1: m.t, y2: m.t + ph, stroke: tok("--accent"), "stroke-width": 2 }, osvg);
      var tl = st.p === "v" ? "+ up and back over the top, − down toward the desk" : "+ toward the capsule centre";
      $("#a2-heat-ttl").textContent = CASES[st.c].l + ", " + (st.p === "v" ? "vertical" : "horizontal") + " plane";
      heat.title = tl;
      // ramp legend
      $("#a2-ramp").innerHTML = '<span>−36 dB</span><span class="bar" style="background:linear-gradient(90deg,' + cols.map(function (c, k) { return c + " " + (k / 12 * 100).toFixed(1) + "%," + c + " " + ((k + 1) / 12 * 100).toFixed(1) + "%"; }).join(",") + ')"></span><span>0 dB re on-axis, 3 dB steps</span><span class="rampnote">Angle: ' + tl + "</span>";
    }
    function pick(ev) {
      if (!geo) return null;
      var r = canvas.getBoundingClientRect(), px = (ev.clientX - r.left) * geo.W / r.width, py = (ev.clientY - r.top) * geo.H / r.height;
      if (px < geo.m.l || px > geo.m.l + geo.pw || py < geo.m.t || py > geo.m.t + geo.ph) return null;
      var f = Math.exp(geo.l0 + (px - geo.m.l) / geo.pw * (geo.l1 - geo.l0)), a = 180 - (py - geo.m.t) / geo.ph * 360;
      return { i: bsearch(F, f), j: bsearch(A, a), px: px * r.width / geo.W, py: py * r.height / geo.H };
    }
    heat.addEventListener("pointermove", function (ev) {
      var p = pick(ev); if (!p) { tip.hidden = true; return; }
      var v = geo.data[p.i][p.j];
      tip.innerHTML = '<div class="tx">' + fmtHz(F[p.i]) + ", " + A[p.j] + '°</div><div class="row">level re on-axis<b>' + (v == null ? "behind the baffle" : v.toFixed(1) + " dB") + "</b></div>";
      tip.hidden = false;
      var bw = heat.clientWidth, tw = tip.offsetWidth;
      tip.style.left = (p.px + 14 + tw > bw ? p.px - 14 - tw : p.px + 14) + "px"; tip.style.top = Math.max(0, p.py - 40) + "px";
    });
    heat.addEventListener("pointerleave", function () { tip.hidden = true; });
    heat.addEventListener("click", function (ev) { var p = pick(ev); if (p) { st.i = p.i; fI.value = p.i; draw(); } });

    var polarHost = $("#a2-polar"), pLegend = h("div", "legend"), pBox = h("div", "plot"), pTip = h("div", "tip");
    pTip.hidden = true; polarHost.appendChild(pLegend); polarHost.appendChild(pBox);
    function drawPolar() {
      var S = Math.min(360, Math.max(240, polarHost.clientWidth || 320)), c = S / 2, R = S / 2 - 26;
      var rad = function (v) { return R * (Math.max(-30, Math.min(3, v)) + 30) / 33; };
      var pt = function (a, v) { var t = a * Math.PI / 180; return [c + rad(v) * Math.cos(t), c - rad(v) * Math.sin(t)]; };
      pBox.innerHTML = ""; pBox.appendChild(pTip);
      var svg = svgEl("svg", { viewBox: "0 0 " + S + " " + S, width: S, height: S, role: "img", "aria-label": "Polar plot of the three hulls at " + fmtHz(F[st.i]) });
      svg.style.maxWidth = S + "px"; svg.style.margin = "0 auto";
      pBox.insertBefore(svg, pTip);
      var grid = tok("--grid"), ink2 = tok("--ink-2"), surf = tok("--surface");
      [0, -6, -12, -18, -24].forEach(function (v) {
        svgEl("circle", { cx: c, cy: c, r: rad(v), fill: "none", stroke: v === -6 ? tok("--rule") : grid, "stroke-width": v === 0 ? 1.4 : 1 }, svg);
        var t = svgEl("text", { x: c + 3, y: c - rad(v) + 11 }, svg); t.textContent = v + (v === 0 ? " dB" : "");
      });
      for (var a = -150; a <= 180; a += 30) {
        var q = pt(a, 3); svgEl("line", { x1: c, y1: c, x2: q[0], y2: q[1], stroke: grid, "stroke-width": 1 }, svg);
        var tq = pt(a, 7); var t = svgEl("text", { x: tq[0], y: tq[1] + 3.5, "text-anchor": "middle" }, svg); t.textContent = (a > 0 ? "+" : "") + a + "°";
      }
      var la = listenerAngle(), lq = pt(la, 3);
      svgEl("line", { x1: c, y1: c, x2: lq[0], y2: lq[1], stroke: tok("--ink"), "stroke-width": 1.3, "stroke-dasharray": "6 4" }, svg);
      var lt = pt(la, 0); var tt = svgEl("text", { x: lt[0] + 4, y: lt[1] + 14, class: "reflbl", style: "paint-order:stroke;stroke:" + surf + ";stroke-width:3px" }, svg); tt.textContent = "listener";
      var order = Object.keys(CASES).filter(function (k) { return k !== st.c; }).concat([st.c]);
      order.forEach(function (k) {
        var row = a2.maps[k + "_" + st.p][st.i], d = "", pen = false;
        for (var j = 0; j <= A.length; j++) {
          var jj = j % A.length, v = row[jj];
          if (v == null) { pen = false; continue; }
          var p = pt(A[jj], v); d += (pen ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); pen = true;
        }
        svgEl("path", { d: d, fill: "none", stroke: col(CASES[k].c), "stroke-width": k === st.c ? 2.6 : 1.5, opacity: k === st.c ? 1 : 0.75 }, svg);
      });
      pLegend.innerHTML = Object.keys(CASES).map(function (k) { return '<span style="display:inline-flex;align-items:center;gap:.35rem"><span class="sw" style="border-top-color:' + col(CASES[k].c) + ";border-top-width:" + (k === st.c ? 3 : 2) + 'px"></span>' + CASES[k].l + "</span>"; }).join("");
      svg.addEventListener("pointermove", function (ev) {
        var r = svg.getBoundingClientRect(), x = (ev.clientX - r.left) * S / r.width - c, y = c - (ev.clientY - r.top) * S / r.height;
        if (Math.hypot(x, y) > R + 10) { pTip.hidden = true; return; }
        var ang = Math.atan2(y, x) * 180 / Math.PI, j = bsearch(A, ang);
        pTip.innerHTML = '<div class="tx">' + fmtHz(F[st.i]) + ", " + A[j] + "°</div>" + Object.keys(CASES).map(function (k) { var v = a2.maps[k + "_" + st.p][st.i][j]; return '<div class="row"><span class="sw" style="background:' + col(CASES[k].c) + '"></span>' + CASES[k].l + "<b>" + (v == null ? "none" : v.toFixed(1) + " dB") + "</b></div>"; }).join("");
        pTip.hidden = false; pTip.style.left = "4px"; pTip.style.top = "4px";
      });
      svg.addEventListener("pointerleave", function () { pTip.hidden = true; });
      $("#a2-polar-ttl").textContent = "Polar plot at " + fmtHz(F[st.i]);
    }
    function drawTbl() {
      var i = st.i, la = a2.listener.vertical_deg;
      var rows = Object.keys(CASES).map(function (k) {
        var cs = a2.cases[k], lv = interp(la, A, a2.maps[k + "_v"][i].map(function (v) { return v == null ? NaN : v; }));
        return "<tr><td><span class='sw' style='display:inline-block;width:10px;height:10px;border-radius:2px;background:" + col(CASES[k].c) + "'></span> " + CASES[k].l + "</td><td class='n'>" + round(cs.beamwidth_h_deg[i], 0) + "°</td><td class='n'>" + round(cs.beamwidth_v_deg[i], 0) + "°</td><td class='n'>" + round(cs.DI_dB[i], 1) + " dB</td><td class='n'>" + (isFinite(lv) ? (lv > 0 ? "+" : "") + lv.toFixed(1) + " dB" : "—") + "</td></tr>";
      });
      $("#a2-tbl").innerHTML = "<thead><tr><th>At " + fmtHz(F[i]) + "</th><th class='n'>−6 dB beam, horiz.</th><th class='n'>−6 dB beam, vert.</th><th class='n'>Directivity index</th><th class='n'>Listener direction re on-axis</th></tr></thead><tbody>" + rows.join("") + "</tbody>";
    }
    var resp = a2.resp, rc = function (n) { return resp.data[resp.cols.indexOf(n)]; };
    var cR = new LineChart($("#a2-resp"), { title: "", sub: "", height: 250, x: { log: true, min: 1000, max: 16000, label: "Hz" }, y: { min: 65, max: 100, label: "dB SPL, 2.83 V, 1 m", unit: "dB", fmt: function (v) { return v.toFixed(1); } }, series: [] });
    function drawResp() {
      var k = st.c, s;
      if (k === "baffle") s = [{ name: "On axis", x: resp.f, y: rc("baffle_onaxis_spl_db_2v83"), color: "--s3" }];
      else s = [{ name: "On axis", x: resp.f, y: rc(k + "_onaxis_spl_db_2v83"), color: "--s1" }, { name: "Seated listener, free field", x: resp.f, y: rc(k + "_listen_free_spl_db_2v83"), color: "--s7" }, { name: "Seated listener, on the desk", x: resp.f, y: rc(k + "_listen_desk_spl_db_2v83"), color: "--s2" }];
      var sm = a2.summary[k];
      cR.set({ title: "Tweeter response, " + CASES[k].l, sub: k === "baffle" ? "Analytic piston, on axis only." : "The desk reflection notches the centre seat at " + fmtHz(sm.desk_dip_centre_seat_hz) + " (" + sm.desk_dip_centre_seat_db.toFixed(1) + " dB; " + sm.desk_dip_15seat_avg_db.toFixed(1) + " dB averaged over 15 seats). Free field, the listener is within 2 dB of on-axis to 10 kHz.", series: s, vrefs: [{ x: 2500, label: "crossover 2.5 kHz" }] });
    }
    function draw() { $("#a2-f-o").textContent = fmtHz(F[st.i]); drawHeat(); drawPolar(); drawTbl(); drawResp(); }
    draw();
    CHARTS.push({ render: function () { drawHeat(); drawPolar(); } });
    if (window.ResizeObserver) { var pd = false; new ResizeObserver(function () { if (pd) return; pd = true; requestAnimationFrame(function () { pd = false; drawHeat(); drawPolar(); }); }).observe(heat); }
  }

  // ------------------------------------------------------------------ A3
  function initA3(D) {
    var a = D.a3, c = function (n) { return a.data[a.cols.indexOf(n)]; };
    new LineChart($("#a3-list"), { title: "Woofers + PRs at the seated listener", sub: "2.83 V per woofer. On the desk the reflection adds about 5 dB up to 2 kHz, cancelling the baffle step.", height: 260,
      x: { log: true, min: 100, max: 5000, label: "Hz" }, y: { min: 60, max: 92, label: "dB SPL", unit: "dB", fmt: function (v) { return v.toFixed(1); } },
      series: [{ name: "On the desk, centre seat", x: a.f, y: c("listener_desk_spl"), color: "--s1" }, { name: "15-seat average", x: a.f, y: c("listener_grid_avg_spl"), color: "--s3" },
        { name: "Free field", x: a.f, y: c("listener_free_spl"), color: "--s2" }, { name: "A1 half-space model", x: a.f, y: c("a1_halfspace_spl"), color: "--muted", dash: "5 4", width: 1.5 }] });
    var t = a.tunnel;
    var cD = new LineChart($("#a3-diff"), { title: "Diffraction and the tunnel", sub: "Left: on-axis level re the same piston in an infinite baffle. Tunnel: as designed ÷ flush woofer.", height: 260,
      x: { log: true, min: 100, max: 8000, label: "Hz" }, y: { min: -8, max: 6, label: "dB", unit: "dB" },
      series: [{ name: "Baffle step (left woofer)", x: a.f, y: c("diffraction_L_db"), color: "--s1" },
        { name: "Tunnel effect, on axis (BEM)", x: t.f_hz, y: t.bem_onaxis_db, color: "--s2" }, { name: "Tunnel, radiated power (BEM)", x: t.f_hz, y: t.bem_power_db, color: "--s7" },
        { name: "Tunnel, lumped tube model", x: t.f_hz, y: t.lumped_mean_db, color: "--muted", dash: "5 4", width: 1.5 }],
      refs: [{ y: 0, label: "", solid: true, color: "--rule" }] });
  }

  // ------------------------------------------------------------------ A4
  function initA4(D) {
    var a = D.a4;
    var IMG = { main: { src: "img/a4_modes_main.png", w: 1510, h: 926, cap: "Main assembly as drawn (40 % core, woofer and PR masses, free-free). Mode 1 at 269 Hz is ovalling; mode 2 at 334 Hz squashes the tube and moves both woofer lands in phase, the most strongly driven low mode." },
      braces: { src: "img/a4_modes_braces.png", w: 1497, h: 531, cap: "With all braces (spine plate, top ribs, tray and cap gussets). The ovalling and squash modes are gone; the lowest mode is now about 450 Hz, the woofers rocking on the land." } };
    seg($("#a4-case"), [{ v: "main", l: "Main assembly (as drawn)" }, { v: "braces", l: "With all braces" }], "main", function (v) { var o = IMG[v]; var im = $("#a4-img"); im.src = o.src; im.width = o.w; im.height = o.h; im.alt = o.cap; $("#a4-cap").textContent = o.cap; });
    $("#a4-cap").textContent = IMG.main.cap;
    var rows = [["asm_infill40_free", "Shell only, no driver masses", "--muted"], ["asm_infill40_drivers", "Main (as drawn)", "--s2"], ["asm_infill40_drivers_batt", "Main + battery coupled", "--muted"],
      ["asm_infill40_drivers_rib_top", "+ top-arc ribs", "--muted"], ["asm_infill40_drivers_rib_top_tray", "+ ribs + tray gussets", "--muted"], ["asm_infill40_drivers_spine", "+ spine plate", "--s1"],
      ["asm_infill40_drivers_all_braces", "All braces", "--s1"], ["asm_infill40_drivers_batt_spine_top_tray", "Battery + spine + ribs + gussets", "--s1"]];
    var host = $("#a4-strip");
    host.innerHTML = '<div class="ttl">Where the modes sit</div><div class="sub">The 30 computed modes per case. Bigger dot = more strongly driven by the woofers (excitation index). Shaded: below 1 kHz; right column counts them. The battery cases hit the 30-mode limit below 1 kHz.</div>';
    var box = h("div", "plot"), tip = h("div", "tip"); tip.hidden = true; host.appendChild(box);
    function render() {
      var W = Math.max(280, box.clientWidth || 500), rowH = 26, m = { l: Math.min(200, W * 0.42), r: 28, t: 6, b: 26 }, H = m.t + rows.length * rowH + m.b, pw = W - m.l - m.r;
      var x0 = Math.log(180), x1 = Math.log(2200), xs = function (f) { return m.l + (Math.log(f) - x0) / (x1 - x0) * pw; };
      box.innerHTML = ""; box.appendChild(tip);
      var svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, width: W, height: H, role: "img", "aria-label": "Mode frequencies per case" }); box.insertBefore(svg, tip);
      svgEl("rect", { x: xs(180), y: m.t, width: xs(1000) - xs(180), height: rows.length * rowH, fill: tok("--band") }, svg);
      [200, 500, 1000, 2000].forEach(function (f) { svgEl("line", { x1: xs(f), x2: xs(f), y1: m.t, y2: m.t + rows.length * rowH, stroke: tok("--grid") }, svg); var t = svgEl("text", { x: xs(f), y: H - 8, "text-anchor": "middle" }, svg); t.textContent = fmtTick(f); });
      var pts = [];
      rows.forEach(function (r, k) {
        var cs = a.cases[r[0]], y = m.t + k * rowH + rowH / 2;
        svgEl("line", { x1: m.l, x2: m.l + pw, y1: y, y2: y, stroke: tok("--grid") }, svg);
        var t = svgEl("text", { x: m.l - 8, y: y + 3.5, "text-anchor": "end", class: "axlbl" }, svg); t.textContent = W < 420 ? r[1].slice(0, 22) : r[1];
        var n1k = 0;
        cs.modes.forEach(function (md) {
          var f = md[0], ix = md[1] == null ? -100 : md[1]; if (f < 1000) n1k++; if (f > 2200 || f < 180) return;
          var rr = 2 + 5 * Math.max(0, Math.min(1, (ix + 70) / 65));
          svgEl("circle", { cx: xs(f), cy: y, r: rr.toFixed(1), fill: col(r[2]), "fill-opacity": 0.85, stroke: tok("--surface"), "stroke-width": 1 }, svg);
          pts.push([xs(f), y, f, r[1], md[1], md[2]]);
        });
        var nt = svgEl("text", { x: W - 4, y: y + 3.5, "text-anchor": "end" }, svg); nt.textContent = n1k;
      });
      var hd = svgEl("text", { x: W - 4, y: H - 8, "text-anchor": "end", class: "axlbl" }, svg); hd.textContent = "n<1k";
      svg.addEventListener("pointermove", function (ev) {
        var rc = svg.getBoundingClientRect(), px = (ev.clientX - rc.left) * W / rc.width, py = (ev.clientY - rc.top) * H / rc.height, best = null, bd = 1e9;
        pts.forEach(function (p) { var dd = Math.hypot(p[0] - px, (p[1] - py) * 2); if (dd < bd) { bd = dd; best = p; } });
        if (!best || bd > 24) { tip.hidden = true; return; }
        tip.innerHTML = '<div class="tx">' + best[2].toFixed(0) + ' Hz</div><div class="row">' + best[3] + '</div><div class="row">excitation index<b>' + (best[4] == null ? "—" : best[4].toFixed(0) + " dB") + '</b></div><div class="row" style="white-space:normal">' + best[5] + "</div>"; tip.hidden = false;
        var cx = best[0] * rc.width / W; tip.style.left = (cx + 160 > rc.width ? cx - 170 : cx + 12) + "px"; tip.style.top = (best[1] * rc.height / H - 10) + "px";
      });
      svg.addEventListener("pointerleave", function () { tip.hidden = true; });
    }
    render(); CHARTS.push({ render: render });
    if (window.ResizeObserver) new ResizeObserver(function () { requestAnimationFrame(render); }).observe(box);
    var fr = a.frf;
    new LineChart($("#a4-frf"), { title: "Shell output relative to the woofers", sub: "Net outward volume velocity of the outer skin ÷ the two cones'. −20 dB ≈ ±1 dB of ripple in the sum.", height: 270,
      x: { log: true, min: 50, max: 2500, label: "Hz" }, y: { min: -70, max: 0, label: "dB re woofers", unit: "dB", fmt: function (v) { return v.toFixed(1); } },
      series: [{ name: "Main (as drawn)", x: a.frf_f, y: fr.asm_infill40_drivers_total_db, color: "--s2" }, { name: "+ spine plate", x: a.frf_f, y: fr.asm_infill40_drivers_spine_total_db, color: "--s1" },
        { name: "All braces", x: a.frf_f, y: fr.asm_infill40_drivers_all_braces_total_db, color: "--s7" }, { name: "Shell only, no driver masses", x: a.frf_f, y: fr.asm_infill40_free_total_db, color: "--muted", dash: "5 4", width: 1.5 },
        { name: "Main + battery coupled", x: a.frf_f, y: fr.asm_infill40_drivers_batt_total_db, color: "--s4", hidden: true }],
      refs: [{ y: -20, label: "−20 dB ≈ ±1 dB ripple", left: true }] });
  }

  // ------------------------------------------------------------------ A5
  function initA5(D) {
    var a = D.a5, F = a.f, al = a.alignment;
    var st = { pos: "seat", on: true, tau: Math.round(al.tau_us), pol: 1 };
    seg($("#a5-pos"), [{ v: "seat", l: "Seated listener, free field" }, { v: "axis", l: "Front axis, 1 m" }], st.pos, function (v) { st.pos = v; upd(); });
    var sD = seg($("#a5-dly"), [{ v: "on", l: "On" }, { v: "off", l: "Off (0 µs)" }], "on", function (v) { st.on = v === "on"; upd(); });
    seg($("#a5-pol"), [{ v: 1, l: "Normal" }, { v: -1, l: "Inverted" }], 1, function (v) { st.pol = +v; upd(); });
    var tI = $("#a5-tau"); tI.addEventListener("input", function () { st.tau = +tI.value; st.on = true; sD.set("on"); upd(); });
    var c = new LineChart($("#a5-chart"), { title: "Woofer branch, tweeter branch and their sum", sub: "", height: 290, x: { log: true, min: 200, max: 16000, label: "Hz" },
      y: { min: 50, max: 92, label: "dB SPL, 2.83 V, before EQ", unit: "dB", fmt: function (v) { return v.toFixed(1); } }, series: [], vrefs: [{ x: 2500, label: "2.5 kHz" }] });
    var db = function (re, im) { return 20 * Math.log10(Math.hypot(re, im) / 20e-6 + 1e-30); };
    function upd() {
      var tau = st.on ? st.tau * 1e-6 : 0;
      $("#a5-tau-o").textContent = (st.on ? st.tau : 0) + " µs";
      var src = a[st.pos], w = src.w, t = src.t, sw = [], stw = [], ss = [], si = [], err = [], ef = [];
      F.forEach(function (f, i) {
        var ph = -2 * Math.PI * f * tau, cr = Math.cos(ph), ci = Math.sin(ph);
        var tr = st.pol * (t.re[i] * cr - t.im[i] * ci), ti = st.pol * (t.re[i] * ci + t.im[i] * cr);
        sw.push(db(w.re[i], w.im[i])); stw.push(db(tr, ti));
        var sr = w.re[i] + tr, sim = w.im[i] + ti, ideal = Math.hypot(w.re[i], w.im[i]) + Math.hypot(tr, ti);
        ss.push(db(sr, sim)); si.push(20 * Math.log10(ideal / 20e-6));
        var e = 20 * Math.log10(Math.hypot(sr, sim) / ideal);
        if (f >= 1250 && f <= 5000) err.push(e);
        if (f >= 1000 && f <= 6000) ef.push(e);
      });
      var rms = Math.sqrt(err.reduce(function (s, v) { return s + v * v; }, 0) / err.length), dip = Math.min.apply(null, ef);
      c.set({ sub: (st.pos === "seat" ? "Centre seat, 1.0 m in front, ears 0.40 m above the desk, no desk reflection." : "1 m in front of the left woofer, free field.") + " Tweeter trimmed " + al.gt_db.toFixed(1) + " dB.",
        series: [{ name: "Ideal in-phase sum |W| + |T|", x: F, y: si, color: "--muted", dash: "5 4", width: 1.5 }, { name: "Woofer + PR branch", x: F, y: sw, color: "--s1" }, { name: "Tweeter branch", x: F, y: stw, color: "--s2" }, { name: "Acoustic sum", x: F, y: ss, color: "--ink", width: 2.6 }] });
      var good = rms < 0.2;
      $("#a5-ro").innerHTML = [
        ["Sum vs ideal, rms 1.25–5 kHz", rms.toFixed(2), "dB", chip(good, good ? "aligned" : "misaligned", !good && rms < 1)],
        ["Deepest dip vs ideal, 1–6 kHz", dip.toFixed(1), "dB", "A5 design: 0.05 dB rms"],
        ["Tweeter delay", (st.on ? st.tau : 0), "µs", ((st.on ? st.tau : 0) * 0.096).toFixed(1) + " samples at 96 kHz"],
        ["Tweeter polarity", st.pol > 0 ? "normal" : "inverted", "", "A5 chose normal"]].map(function (x) { return '<div class="ro"><span class="k">' + x[0] + '</span><span class="v">' + x[1] + "<small>" + x[2] + '</small></span><span class="d">' + x[3] + "</span></div>"; }).join("");
    }
    upd();
    var sc = function (n) { return a.sys[a.sys_cols.indexOf(n)]; }, avg = sc("15-seat_average_on_desk_spl_db"), eq = sc("eq_db");
    new LineChart($("#a5-eq"), { title: "15-seat average on the desk, before and after EQ", sub: "Unsmoothed. The ~3 kHz desk dip stays: the EQ lifts its edges only.", height: 250, x: { log: true, min: 150, max: 14000, label: "Hz" },
      y: { min: 65, max: 90, label: "dB SPL, 2.83 V per side", unit: "dB", fmt: function (v) { return v.toFixed(1); } },
      series: [{ name: "Before EQ", x: F, y: avg, color: "--s2" }, { name: "With the 7-biquad EQ", x: F, y: avg.map(function (v, i) { return v + eq[i]; }), color: "--s1" }], refs: [{ y: a.eq.target_db, label: "target " + a.eq.target_db.toFixed(1) + " dB" }] });
    $("#a5-eqtbl").innerHTML = "<thead><tr><th>#</th><th>Type</th><th class='n'>fc</th><th class='n'>Q</th><th class='n'>Gain</th></tr></thead><tbody>" + a.eq.table.slice().sort(function (p, q) { return p.fc_hz - q.fc_hz; }).map(function (r, i) { return "<tr><td>" + (i + 1) + "</td><td>" + r.type + "</td><td class='n'>" + Math.round(r.fc_hz) + " Hz</td><td class='n'>" + r.q.toFixed(2) + "</td><td class='n'>" + (r.gain_db > 0 ? "+" : "") + r.gain_db.toFixed(1) + " dB</td></tr>"; }).join("") + "</tbody>";
  }

  // ------------------------------------------------------------------ S1
  function initS1(D) {
    var s = D.s1, F = s.f, st = { vin: 7.4, nel: 3, load: "power" };
    seg($("#s1-vin"), [{ v: 6, l: "6.0 V" }, { v: 7.4, l: "7.4 V" }, { v: 8.4, l: "8.4 V" }], st.vin, function (v) { st.vin = +v; upd(); });
    seg($("#s1-nel"), [{ v: 0, l: "0 (72 µF)" }, { v: 1, l: "1" }, { v: 2, l: "2" }, { v: 3, l: "3 (1.48 mF)" }], st.nel, function (v) { st.nel = +v; upd(); });
    seg($("#s1-load"), [{ v: "power", l: "2.5 A, constant power" }, { v: "resistive", l: "0.5 A, resistive" }], st.load, function (v) { st.load = v; upd(); });
    var X = { log: true, min: 10, max: 290000, label: "Hz" };
    var cM = new LineChart($("#s1-mag"), { title: "Loop gain |T|", height: 260, x: X, y: { min: -60, max: 80, label: "dB", unit: "dB", fmt: function (v) { return v.toFixed(1); } }, series: [], refs: [{ y: 0, label: "0 dB", solid: true, color: "--ink-2" }] });
    var cP = new LineChart($("#s1-ph"), { title: "Loop phase", height: 260, x: X, y: { label: "degrees", unit: "°", fmt: function (v) { return v.toFixed(0); } }, series: [], refs: [{ y: -180, label: "−180°" }] });
    function find(comp, vin, nel, load) { return s.bode.filter(function (b) { return b.comp === comp && b.vin === vin && b.nel === nel && b.load === load; })[0]; }
    function zpk(b) { var m = 0, f0 = 0; F.forEach(function (f, i) { if (f < 20000 && b.zcl[i] > m) { m = b.zcl[i]; f0 = f; } }); return [m, f0]; }
    function upd() {
      var a = find("spec", st.vin, st.nel, st.load), b = find("eco", st.vin, st.nel, st.load);
      var ser = function (k) { return [{ name: "Spec 33 k / 47 nF", x: F, y: a[k], color: "--s2" }, { name: "ECO-001 100 k / 15 nF", x: F, y: b[k], color: "--s1" }]; };
      cM.set({ series: ser("mag"), vrefs: [{ x: a.fc, label: "fc " + fmtHz(a.fc), left: true }, { x: b.fc, label: "fc " + fmtHz(b.fc), row: 1 }] });
      cP.set({ series: ser("ph") });
      var za = zpk(a), zb = zpk(b);
      $("#s1-ro").innerHTML = [["Crossover", fmtHz(a.fc), fmtHz(b.fc)], ["Phase margin", a.pm.toFixed(1) + "°", b.pm.toFixed(1) + "°"], ["Gain margin", a.gm.toFixed(1) + " dB", b.gm.toFixed(1) + " dB"],
        ["Peak |Z| PVDD, audio band", za[0].toFixed(3) + " Ω", zb[0].toFixed(3) + " Ω"]].map(function (x) {
        return '<div class="ro"><span class="k">' + x[0] + '</span><span class="v" style="font-size:1rem"><span style="color:' + col("--s2") + '">' + x[1] + '</span> → <span style="color:' + col("--s1") + '">' + x[2] + '</span></span><span class="d">spec → ECO-001</span></div>';
      }).join("");
      var rows = [];
      [6, 7.4, 8.4].forEach(function (v) { [1, 2, 3].forEach(function (n) {
        var p = find("spec", v, n, st.load), q = find("eco", v, n, st.load), zp = zpk(p)[0], zq = zpk(q)[0];
        var sel = v === st.vin && n === st.nel ? " style='background:var(--accent-soft)'" : "";
        rows.push("<tr" + sel + "><td>" + v.toFixed(1) + " V</td><td>" + n + "</td><td class='n'>" + p.pm.toFixed(0) + "° → " + q.pm.toFixed(0) + "°</td><td class='n'>" + fmtHz(p.fc) + " → " + fmtHz(q.fc) + "</td><td class='n'>" + zp.toFixed(2) + " → " + zq.toFixed(2) + " Ω " + chip(zq <= 0.2, zq <= 0.137 ? "at target" : "near target", zq > 0.137 && zq <= 0.2) + "</td></tr>");
      }); });
      $("#s1-grid").innerHTML = "<thead><tr><th>VSYS</th><th>Electrolytics</th><th class='n'>Phase margin</th><th class='n'>Crossover</th><th class='n'>PVDD |Z| peak (target 0.137 Ω)</th></tr></thead><tbody>" + rows.join("") + "</tbody>";
    }
    upd();
    var S = s.start, cs = null, view = "v";
    function startSeries() {
      var k = view;
      return [{ name: "7.4 V, ILIM typ, spec comp", x: S.s1_start_typ.t, y: S.s1_start_typ[k], color: "--s7" },
        { name: "6.0 V, ILIM min, spec comp", x: S.s1_start_min.t, y: S.s1_start_min[k], color: "--s2" },
        { name: "6.0 V, ILIM min, ECO comp", x: S.s1_start_min_rc100k.t, y: S.s1_start_min_rc100k[k], color: "--s1", dash: "6 4" }];
    }
    cs = new LineChart($("#s1-start"), { title: "Start-up from a VSYS pre-bias", sub: "EN at t = 0. " + s.startup.start_min.label + ": " + s.startup.start_min.t_to_98pct_ms.toFixed(1) + " ms to 98 %, no hiccup (min " + s.startup.start_min.v_min_after_en.toFixed(2) + " V vs " + s.startup.start_min.hiccup_threshold_V.toFixed(2) + " V threshold).", height: 260,
      x: { min: 0, max: 22, label: "ms", fmt: function (v) { return v.toFixed(2) + " ms"; } }, y: { min: 4, max: 22, label: "PVDD, V", unit: "V" }, series: startSeries(),
      refs: [{ y: 17.97, label: "regulation 17.97 V", below: true }, { y: 20.5, label: "OVP 20.5 V min" }] });
    seg($("#s1-sv"), [{ v: "v", l: "PVDD" }, { v: "il", l: "Inductor current" }], "v", function (v) {
      view = v;
      cs.set({ series: startSeries(), y: v === "v" ? { min: 4, max: 22, label: "PVDD, V", unit: "V" } : { min: 0, max: 11, label: "inductor current, A", unit: "A" },
        refs: v === "v" ? [{ y: 17.97, label: "regulation 17.97 V", below: true }, { y: 20.5, label: "OVP 20.5 V min" }] : [{ y: 9.1, label: "ILIM typ 9.1 A" }, { y: 6.3, label: "ILIM min 6.3 A", below: true }] });
    });
    var P = s.step;
    new LineChart($("#s1-step"), { title: "Load step 0.2 → 2 → 0.2 A", sub: "TI switching model. Dip 0.97 V with the spec compensation (6.0 V) vs 0.34 V with ECO-001 (7.4 V).", height: 260,
      x: { min: 11, max: 17, label: "ms", fmt: function (v) { return v.toFixed(3) + " ms"; } }, y: { min: 16.8, max: 19.4, label: "PVDD, V", unit: "V", fmt: function (v) { return v.toFixed(3); } },
      series: [{ name: "Spec 33 k / 47 nF, 6.0 V", x: P.s1_step60.t, y: P.s1_step60.v, color: "--s2", width: 1.4 }, { name: "ECO-001 100 k / 15 nF, 7.4 V", x: P.s1_step74_rc100k.t, y: P.s1_step74_rc100k.v, color: "--s1", width: 1.4 }] });
  }

  // ------------------------------------------------------------------ S2
  function initS2(D) {
    var s = D.s2s3s6, fl = s.filt, st = { c: "0.75uF" };
    var LOADS = [["ND65-8 woofer model", "Woofer (ND65-8)", "--s1"], ["OT19NC00-04 tweeter model", "Tweeter (OT19NC00-04)", "--s2"], ["8 Ω resistor", "8 Ω resistor", "--s3"], ["4 Ω resistor", "4 Ω resistor", "--s7"], ["open (no load)", "Open", "--muted"]];
    var hidden = {};
    var cH = new LineChart($("#s2-h"), { title: "Filter transfer, speaker voltage ÷ bridge voltage", sub: "", height: 280, x: { log: true, min: 100, max: 2e6, label: "Hz" }, y: { min: -30, max: 26, label: "dB", unit: "dB" }, series: [],
      vrefs: [{ x: 20000, label: "20 kHz", left: true }, { x: 768000, label: "768 kHz PWM", left: true }] });
    function upd() {
      cH.set({ sub: "C = " + (st.c === "0.75uF" ? "0.75 µF (1 µF X7R at 9 V bias)" : "1.00 µF nominal") + ". Click a legend entry to hide it.",
        series: LOADS.map(function (L) { var k = "H_dB[" + L[0] + "|C=" + st.c + "]"; var sr = { name: L[1], x: fl.f, y: fl.data[fl.cols.indexOf(k)], color: L[2], hidden: L[0].indexOf("open") === 0 }; return sr; }) });
    }
    seg($("#s2-c"), [{ v: "0.75uF", l: "0.75 µF (biased)" }, { v: "1.00uF", l: "1.00 µF (nominal)" }], st.c, function (v) { st.c = v; upd(); });
    upd();
    new LineChart($("#s2-z"), { title: "Driver impedance models", sub: "Re + jωLe + motional RLC from T/S data. Pure Le overstates the woofer at high frequency.", height: 280, x: { log: true, min: 10, max: 2e6, label: "Hz" },
      y: { log: true, min: 1, max: 10000, label: "|Z|, Ω", unit: "Ω", fmt: function (v) { return v.toPrecision(3); } },
      series: [{ name: "Woofer ND65-8", x: s.zdrv.f, y: s.zdrv.woofer, color: "--s1" }, { name: "Tweeter OT19NC00-04", x: s.zdrv.f, y: s.zdrv.tweeter, color: "--s2" }] });
    var pk = s.s2.peaks, lab = { wf_15V5_150Hz: "Woofer 15.5 V pk, 150 Hz", wf_15V5_400Hz: "Woofer 15.5 V pk, 400 Hz (Z min)", wf_15V5_2k5Hz: "Woofer 15.5 V pk, 2.5 kHz", tw_8V_3kHz: "Tweeter 8 V pk, 3 kHz", tw_8V_10kHz: "Tweeter 8 V pk, 10 kHz", tw_8V_20kHz: "Tweeter 8 V pk, 20 kHz", tw_clip_3kHz: "Tweeter hard-clipped (limiter failed), 3 kHz" };
    $("#s2-tbl").innerHTML = "<thead><tr><th>Case (BD modulation)</th><th class='n'>Speaker V pk</th><th class='n'>Speaker I pk</th><th class='n'>Inductor I pk</th><th class='n'>Margin to OCP 5 A</th></tr></thead><tbody>" +
      Object.keys(lab).map(function (k) { var p = pk[k]; return "<tr><td>" + lab[k] + "</td><td class='n'>" + p.v_spk_pk.toFixed(1) + " V</td><td class='n'>" + p.i_spk_pk.toFixed(2) + " A</td><td class='n'>" + p.iL_pk.toFixed(2) + " A</td><td class='n'>" + (p.margin_to_OCP_A >= 0 ? "" : "−") + Math.abs(p.margin_to_OCP_A).toFixed(2) + " A " + chip(p.margin_to_OCP_A > 0, p.margin_to_OCP_A > 0 ? "ok" : "trips OCP") + "</td></tr>"; }).join("") + "</tbody>";
  }

  // ------------------------------------------------------------------ S3
  function initS3(D) {
    var n = D.s2s3s6.ntc, w = n.j.windows.B3435.typ, w2 = n.j.windows.B3380.typ;
    new LineChart($("#s3-chart"), { title: "TS / REGN vs temperature", sub: "Shaded: charging allowed with B = 3435 (" + w["VT1_rise (cold stop, 0 C)"].toFixed(1) + " to " + w["VT5_fall (hot stop, 60 C)"].toFixed(1) + " °C). Above " + w["VT3_fall TS_WARM=1h (45 C)"].toFixed(1) + " °C the charger only lowers VREG by 400 mV and keeps full current.", height: 300,
      x: { min: -30, max: 90, label: "°C", fmt: function (v) { return v.toFixed(1) + " °C"; } }, y: { min: 20, max: 90, label: "TS, % of REGN", unit: "%", fmt: function (v) { return v.toFixed(1); } },
      xbands: [{ x0: w["VT1_rise (cold stop, 0 C)"], x1: w["VT5_fall (hot stop, 60 C)"], label: "charging" }],
      series: [{ name: "NTC B = 3435", x: n.T, y: n.b3435, color: "--s1" }, { name: "NTC B = 3380", x: n.T, y: n.b3380, color: "--s2", dash: "6 4" }],
      refs: [{ y: 73.3, label: "VT1 73.3 %: cold stop" }, { y: 68.4, label: "TS_COOL 68.4 %", below: true }, { y: 44.8, label: "TS_WARM 44.8 %" }, { y: 34.2, label: "VT5 34.2 %: hot stop", below: true }] });
  }

  // ------------------------------------------------------------------ S4
  function initS4(D) {
    var t = D.s4s5.trim, sp = D.s4s5.s4.spec_table, sx = Object.keys(sp).map(Number).sort(function (a, b) { return a - b; });
    new LineChart($("#s4-chart"), { title: "PVDD vs PVDD_TRIM voltage", sub: "SPICE with the 1N4148W model at three temperatures, against the spec's hand table (0.45 V fixed diode drop).", height: 280,
      x: { min: 0, max: 3.3, label: "trim voltage, V", fmt: function (v) { return v.toFixed(2) + " V"; } }, y: { min: 11, max: 18.5, label: "PVDD, V", unit: "V", fmt: function (v) { return v.toFixed(2); } },
      series: [{ name: "0 °C", x: t.v, y: t.data[0], color: "--s1" }, { name: "25 °C", x: t.v, y: t.data[1], color: "--s3" }, { name: "60 °C", x: t.v, y: t.data[2], color: "--s2" },
        { name: "Spec hand table", x: sx, y: sx.map(function (k) { return sp[String(k)] != null ? sp[String(k)] : sp[k.toFixed(1)]; }), color: "--ink", markers: true, line: false }] });
  }

  // ------------------------------------------------------------------ S5
  function initS5(D) {
    var W = D.s4s5.waves, cases = D.s4s5.s5.cases;
    var LBL = { tight: "UnixTightReset (one call)", gap2ms: "Classic, 2 ms gap", gap3ms: "Classic, 3 ms gap", gap5ms: "Classic, 5 ms gap" };
    var c = new LineChart($("#s5-chart"), { title: "", height: 280, x: { min: 0, max: 60, label: "ms", fmt: function (v) { return v.toFixed(2) + " ms"; } }, y: { min: -0.2, max: 3.6, label: "V", unit: "V" }, series: [],
      ybands: [{ y0: 0.825, y1: 2.475, label: "EN threshold band (V_IL–V_IH)" }] });
    function upd(k) {
      var w = W[k], cs = cases[k];
      c.set({ title: LBL[k], series: [{ name: "DTR#", x: w.t_s, y: w.dtr_n, color: "--s7", width: 1.4 }, { name: "RTS#", x: w.t_s, y: w.rts_n, color: "--s5", width: 1.4 }, { name: "EN", x: w.t_s, y: w.en, color: "--s1" }, { name: "GPIO0", x: w.t_s, y: w.io0, color: "--s2" }] });
      $("#s5-chip").innerHTML = chip(cs.download_mode_ok, cs.download_mode_ok ? "enters download mode" : "boots normally: download fails") + ' <span class="note">GPIO0 max while EN crosses the band: ' + cs.io0_max_in_window_V.toFixed(2) + " V (needs &lt; 0.83 V)</span>";
    }
    seg($("#s5-case"), Object.keys(LBL).map(function (k) { return { v: k, l: LBL[k].replace("Classic, ", "") }; }), "gap3ms", upd);
    upd("gap3ms");
  }

  // ------------------------------------------------------------------ S6
  function initS6(D) {
    var s = D.s2s3s6, sc = s.sclk, j = s.s6;
    var RC = { 33: "--s2", 47: "--s4", 68: "--s1", 82: "--s7" };
    new LineChart($("#s6-sclk"), { title: "SCLK at the display, 40 MHz, nominal driver", sub: "Series resistor per trace; 47 and 82 Ω are hidden, click the legend to show them. Overshoot past 3.3 + 0.9 V conducts the receiver's ESD diodes.", height: 290,
      x: { min: 40, max: 120, label: "ns", fmt: function (v) { return v.toFixed(2) + " ns"; } }, y: { min: -1.2, max: 4.6, label: "V at GC9A01", unit: "V" },
      series: [33, 47, 68, 82].map(function (r) { return { name: r + " Ω" + (r === 33 ? " (original)" : r === 68 ? " (ECO-001)" : ""), x: sc[r].t, y: sc[r].v, color: RC[r], hidden: r === 47 || r === 82, width: r === 33 || r === 68 ? 2 : 1.6 }; }),
      refs: [{ y: 4.2, label: "ESD clamp ≈ 4.2 V" }, { y: 2.31, label: "V_IH 2.31", left: true }, { y: 0.99, label: "V_IL 0.99", left: true, below: true }, { y: -0.9, label: "−0.9 V", below: true }] });
    var cX = new LineChart($("#s6-xt"), { title: "", sub: "Far-end voltage on held-low victims while MOSI toggles at 40 MHz, fast driver corner.", height: 250, x: { min: 0, max: 120, label: "ns", fmt: function (v) { return v.toFixed(2) + " ns"; } }, y: { min: -0.8, max: 1.2, label: "V", unit: "V" }, series: [],
      refs: [{ y: 0.99, label: "V_IL 0.99 V" }] });
    function upd(r) {
      var x = s.xtalk[r];
      cX.set({ title: "Crosstalk from MOSI, " + r + " Ω sources", series: [{ name: "CS (victim)", x: x.cs.t, y: x.cs.v, color: "--s1" }, { name: "DC (victim)", x: x.dc.t, y: x.dc.v, color: "--s3" }, { name: "SCLK (victim)", x: x.sclk.t, y: x.sclk.v, color: "--s7" }, { name: "MOSI (aggressor)", x: x.mosi.t, y: x.mosi.v, color: "--muted", hidden: true, width: 1.2 }] });
    }
    seg($("#s6-xr"), [{ v: "33", l: "33 Ω" }, { v: "68", l: "68 Ω" }], "33", upd); upd("33");
    var L = j.ffc_lines_free_air, names = ["LCD_SCLK", "PDM_CLK", "LCD_MOSI", "PDM_DATA", "LCD_CS", "LCD_DC"];
    var fm = j.fmax;
    $("#s6-tbl").innerHTML = "<thead><tr><th>FFC line (free air)</th><th class='n'>Pin</th><th class='n'>Z0</th><th class='n'>εeff</th><th class='n'>Delay, 200 mm</th></tr></thead><tbody>" +
      names.map(function (n) { var l = L[n]; return "<tr><td>" + n + "</td><td class='n'>" + l.pin + "</td><td class='n'>" + l.z0_ohm.toFixed(0) + " Ω</td><td class='n'>" + l.eps_eff.toFixed(2) + "</td><td class='n'>" + l.td_200mm_ns.toFixed(2) + " ns</td></tr>"; }).join("") +
      "<tr><td colspan='5' style='padding-top:.8rem;color:var(--ink-2)'>Maximum safe SPI clock (no false edges, high/low ≥ 7 ns, overshoot &lt; 0.9 V): 33 Ω: fast corner " + (fm["33"].fast_fmax_MHz ? fm["33"].fast_fmax_MHz + " MHz" : "fails at any clock") + ", nominal " + fm["33"].nom_fmax_MHz + " MHz. 68 Ω: " + fm["68"].fast_fmax_MHz + " MHz in every corner.</td></tr></tbody>";
  }

  // ------------------------------------------------------------------ S7
  function initS7(D) {
    var s = D.s7, F = s.f, c = function (n) { return s.data[s.cols.indexOf(n)]; }, T = s.j.targets;
    var ch = new LineChart($("#s7-chart"), { title: "", height: 300, x: { log: true, min: 10, max: 1e8, label: "Hz" }, y: { log: true, min: 0.005, max: 2, label: "|Z|, Ω", unit: "Ω", fmt: function (v) { return v.toPrecision(3); } }, series: [] });
    function upd(r) {
      if (r === "pvdd") ch.set({ title: "PVDD at the right amplifier", sub: "Target " + T.PVDD.Z_ohm.toFixed(3) + " Ω over the audio band (5 A step, 0.68 V). The 150 Hz hump is the boost loop running out of gain.", x: { log: true, min: 10, max: 1e7, label: "Hz" },
        series: [{ name: "7.4 V, 2.5 A, spec comp", x: F, y: c("absZ_pvdd_7.4V_2.5A_power"), color: "--s2" }, { name: "6.0 V, 2.5 A, spec comp", x: F, y: c("absZ_pvdd_6.0V_2.5A_power"), color: "--s4" },
          { name: "8.4 V, 0.5 A, spec comp", x: F, y: c("absZ_pvdd_8.4V_0.5A_resistive"), color: "--s7", hidden: true }, { name: "7.4 V, 2.5 A, ECO-001 comp", x: F, y: c("absZ_pvdd_7.4V_2.5A_Rc100k"), color: "--s1" }],
        refs: [{ y: T.PVDD.Z_ohm, label: "target 0.137 Ω", color: "--crit" }], xbands: [{ x0: 10, x1: 20000, label: "audio band" }] });
      else ch.set({ title: "+3V3 at each load", sub: "Target " + T["3V3"].Z_ohm.toFixed(2) + " Ω (0.33 A Wi-Fi burst, 3 %). Buck crossover 35 kHz nominal, 20 and 60 kHz variants.", x: { log: true, min: 10, max: 1e8, label: "Hz" },
        series: [{ name: "At the ESP32", x: F, y: c("absZ_3v3_ESP"), color: "--s1" }, { name: "At the UI connector", x: F, y: c("absZ_3v3_UI"), color: "--s3" }, { name: "At the amps (DVDD)", x: F, y: c("absZ_3v3_AMPS"), color: "--s7" },
          { name: "ESP32, buck fc 20 kHz", x: F, y: c("absZ_3v3_ESP_fc20k"), color: "--s2", dash: "5 4", width: 1.5 }, { name: "ESP32, buck fc 60 kHz", x: F, y: c("absZ_3v3_ESP_fc60k"), color: "--s4", dash: "5 4", width: 1.5, hidden: true }],
        refs: [{ y: T["3V3"].Z_ohm, label: "target 0.30 Ω", color: "--crit" }], xbands: [] });
    }
    seg($("#s7-rail"), [{ v: "pvdd", l: "PVDD (18 V)" }, { v: "3v3", l: "+3V3" }], "pvdd", upd); upd("pvdd");
  }

  // ------------------------------------------------------------------ theme changes and the index highlight
  function rerender() { CHARTS.forEach(function (c) { try { c.render(); } catch (e) { console.error(e); } }); }
  try { matchMedia("(prefers-color-scheme: dark)").addEventListener("change", rerender); } catch (e) { /* old browsers */ }
  new MutationObserver(rerender).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  var links = Array.prototype.slice.call(document.querySelectorAll(".index a"));
  if (window.IntersectionObserver) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) links.forEach(function (a) { a.classList.toggle("on", a.getAttribute("href") === "#" + e.target.id); }); });
    }, { rootMargin: "-30% 0px -60% 0px" });
    document.querySelectorAll(".sim").forEach(function (s) { io.observe(s); });
  }
})();
