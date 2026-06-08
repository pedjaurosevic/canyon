/* CANYON docs — renders tables + SVG charts from window.CANYON_DATA (data.js). */
(function () {
  "use strict";
  var D = window.CANYON_DATA;
  var SVGNS = "http://www.w3.org/2000/svg";
  var SERIES = ["#83a598", "#d3869b", "#b8bb26", "#fabd2f", "#fb4934", "#fe8019", "#8ec07c"];
  var ACCESS = {
    "chat-api": { label: "chat API", color: "#83a598" },
    "claude-agent": { label: "Claude agent", color: "#d3869b" },
    "codex-agent": { label: "Codex agent", color: "#b8bb26" },
    "local-blackbox": { label: "local", color: "#fe8019" },
    "white-box": { label: "white-box", color: "#8ec07c" }
  };
  function accessColor(a) { return (ACCESS[a] || {}).color || "#83a598"; }
  function accessLabel(a) { return (ACCESS[a] || {}).label || a || "—"; }
  function scoreLabel(lb) { return lb && lb.score_type === "semantic_judge" ? "semantic judge" : "keyword screen"; }

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    (kids || []).forEach(function (k) { n.appendChild(typeof k === "string" ? document.createTextNode(k) : k); });
    return n;
  }
  function svg(tag, attrs) {
    var n = document.createElementNS(SVGNS, tag);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttributeNS(null, k, attrs[k]); });
    return n;
  }
  function cls(spi) { return spi >= 0.75 ? "good" : spi >= 0.5 ? "warn" : "bad"; }
  function langName(l) { return (D.lang_names && D.lang_names[l]) || l; }
  function ordered(obj) {
    var order = D.lang_order || [];
    var ks = Object.keys(obj);
    return order.filter(function (l) { return obj[l]; }).concat(ks.filter(function (l) { return order.indexOf(l) < 0; }));
  }

  if (!D || (!Object.keys(D.blackbox || {}).length && !Object.keys(D.whitebox || {}).length)) {
    var note = "Run the benchmark and scripts/build_report.py to populate this page.";
    ["bb-table", "drift-charts"].forEach(function (id) {
      var t = document.getElementById(id);
      if (t) t.appendChild(el("p", { class: "muted" }, [note]));
    });
    return;
  }

  /* ---- black-box: SPI table + bar chart ---- */
  function renderBlackbox() {
    var bb = D.blackbox || {};
    var langs = ordered(bb);
    if (!langs.length) return;

    var any = bb[langs[0]];
    var mEl = document.getElementById("bb-model");
    if (mEl) mEl.textContent = "Model: " + (any.model || "n/a") + " · " + langs.length + " languages";

    // table
    var thead = el("tr", {}, ["Language", "CP", "CR", "SI", "SPI", "", "Classification"].map(function (h, i) {
      return el("th", i >= 1 && i <= 4 ? { class: "num" } : {}, [h]);
    }));
    var rows = [thead];
    langs.forEach(function (l) {
      var m = bb[l].metrics, spi = m.stochastic_parrot_index;
      var bar = el("div", { class: "spibar" }, [el("span")]);
      bar.firstChild.style.width = Math.round(spi * 100) + "%";
      rows.push(el("tr", {}, [
        el("td", {}, [langName(l) + " (" + l + ")"]),
        el("td", { class: "num" }, [m.cp_score.toFixed(2)]),
        el("td", { class: "num" }, [m.cr_score.toFixed(2)]),
        el("td", { class: "num" }, [m.si_score.toFixed(2)]),
        el("td", { class: "num" }, [spi.toFixed(2)]),
        el("td", {}, [bar]),
        el("td", {}, [el("span", { class: "badge " + cls(spi) }, [bb[l].classification])])
      ]));
    });
    var host = document.getElementById("bb-table");
    host.innerHTML = "";
    host.appendChild(el("table", {}, rows));

    renderSpiBars(langs, bb);
  }

  function renderSpiBars(langs, bb) {
    var host = document.getElementById("spi-chart");
    if (!host) return;
    host.innerHTML = "";
    var W = Math.max(560, langs.length * 130), H = 240, padL = 40, padB = 40, padT = 16;
    var s = svg("svg", { viewBox: "0 0 " + W + " " + H, width: "100%" });
    // y grid 0..1
    [0, 0.25, 0.5, 0.75, 1].forEach(function (v) {
      var y = padT + (1 - v) * (H - padT - padB);
      s.appendChild(svg("line", { x1: padL, y1: y, x2: W, y2: y, stroke: "#3c3836", "stroke-width": 1 }));
      var tx = svg("text", { x: 6, y: y + 4 }); tx.textContent = v.toFixed(2); s.appendChild(tx);
    });
    // thresholds
    [[0.75, "#b8bb26"], [0.5, "#fabd2f"]].forEach(function (p) {
      var y = padT + (1 - p[0]) * (H - padT - padB);
      s.appendChild(svg("line", { x1: padL, y1: y, x2: W, y2: y, stroke: p[1], "stroke-dasharray": "5 5", "stroke-width": 1.2, opacity: .7 }));
    });
    var bw = (W - padL - 20) / langs.length;
    langs.forEach(function (l, i) {
      var spi = bb[l].metrics.stochastic_parrot_index;
      var h = spi * (H - padT - padB), x = padL + i * bw + bw * 0.2, y = padT + (H - padT - padB) - h, w = bw * 0.6;
      var r = svg("rect", { x: x, y: y, width: w, height: h, rx: 5, fill: "url(#g)" });
      s.appendChild(r);
      var v = svg("text", { x: x + w / 2, y: y - 6, "text-anchor": "middle", fill: "#ebdbb2" }); v.textContent = spi.toFixed(2); s.appendChild(v);
      var lab = svg("text", { x: x + w / 2, y: H - padB + 18, "text-anchor": "middle" }); lab.textContent = l; s.appendChild(lab);
    });
    var defs = svg("defs"), grad = svg("linearGradient", { id: "g", x1: "0", y1: "1", x2: "0", y2: "0" });
    grad.appendChild(svg("stop", { offset: "0", "stop-color": "#83a598" }));
    grad.appendChild(svg("stop", { offset: "1", "stop-color": "#d3869b" }));
    defs.appendChild(grad); s.appendChild(defs);
    host.appendChild(s);
    host.appendChild(el("p", { class: "muted", style: "margin-top:10px;font-size:13px" },
      ["Dashed lines: grounding thresholds (0.75 strong, 0.50 hybrid)."]));
  }

  /* ---- white-box: drift line charts ---- */
  function pts(traj) {
    return Object.keys(traj).map(function (k) {
      return { L: parseInt(k.split("_")[1], 10), v: traj[k] };
    }).filter(function (p) { return !isNaN(p.L); }).sort(function (a, b) { return a.L - b.L; });
  }

  function driftSvg(series) {
    // series: [{label, color, points:[{L,v}]}]
    var W = 640, H = 280, padL = 46, padB = 36, padT = 14, padR = 14;
    var all = [].concat.apply([], series.map(function (s) { return s.points; }));
    var Ls = all.map(function (p) { return p.L; }), vs = all.map(function (p) { return p.v; });
    var minL = Math.min.apply(null, Ls), maxL = Math.max.apply(null, Ls);
    var minV = Math.min.apply(null, vs), maxV = Math.max.apply(null, vs);
    var span = (maxV - minV) || 0.1; minV = Math.max(0, minV - span * 0.15); maxV = Math.min(1, maxV + span * 0.15);
    function X(L) { return padL + (maxL === minL ? 0.5 : (L - minL) / (maxL - minL)) * (W - padL - padR); }
    function Y(v) { return padT + (1 - (v - minV) / (maxV - minV)) * (H - padT - padB); }
    var s = svg("svg", { viewBox: "0 0 " + W + " " + H, width: "100%" });
    // y grid
    for (var g = 0; g <= 4; g++) {
      var v = minV + (g / 4) * (maxV - minV), y = Y(v);
      s.appendChild(svg("line", { x1: padL, y1: y, x2: W - padR, y2: y, stroke: "#3c3836", "stroke-width": 1 }));
      var t = svg("text", { x: 6, y: y + 4 }); t.textContent = v.toFixed(2); s.appendChild(t);
    }
    // x labels
    series[0].points.forEach(function (p) {
      var t = svg("text", { x: X(p.L), y: H - padB + 16, "text-anchor": "middle" }); t.textContent = "L" + p.L; s.appendChild(t);
    });
    series.forEach(function (ser) {
      var d = ser.points.map(function (p, i) { return (i ? "L" : "M") + X(p.L).toFixed(1) + " " + Y(p.v).toFixed(1); }).join(" ");
      s.appendChild(svg("path", { d: d, fill: "none", stroke: ser.color, "stroke-width": 2.2 }));
      ser.points.forEach(function (p) { s.appendChild(svg("circle", { cx: X(p.L), cy: Y(p.v), r: 3, fill: ser.color })); });
    });
    return s;
  }

  function renderWhitebox() {
    var wb = D.whitebox || {};
    var langs = ordered(wb);
    var host = document.getElementById("drift-charts");
    if (!host) return;
    if (!langs.length) { host.appendChild(el("p", { class: "muted" }, ["No white-box runs in results/."])); return; }

    var any = wb[langs[0]];
    var mEl = document.getElementById("wb-model");
    if (mEl) mEl.textContent = "Model: " + (any.model || "n/a") + " · real activations, layers 0–32";

    langs.forEach(function (l, li) {
      var drift = wb[l].drift_trajectories || {};
      Object.keys(drift).forEach(function (testId) {
        drift[testId].forEach(function (t) {
          var card = el("div", { class: "drift-card" });
          card.appendChild(el("h4", {}, [langName(l) + " (" + l + ") · " + testId]));
          card.appendChild(el("p", { class: "meta" }, ["step " + (t.from_step + 1) + " → " + (t.to_step + 1) + " · cosine similarity per layer"]));
          card.appendChild(driftSvg([{ label: l, color: SERIES[li % SERIES.length], points: pts(t.trajectory) }]));
          host.appendChild(card);
        });
      });
    });

    // overlay: same test across languages, if multiple
    var overlay = buildOverlay(wb, langs);
    if (overlay) host.insertBefore(overlay, host.firstChild);
  }

  function buildOverlay(wb, langs) {
    if (langs.length < 2) return null;
    // pick the first test id common to all
    var first = wb[langs[0]].drift_trajectories || {};
    var testIds = Object.keys(first);
    if (!testIds.length) return null;
    var testId = testIds[0];
    var series = [];
    langs.forEach(function (l, i) {
      var d = (wb[l].drift_trajectories || {})[testId];
      if (d && d[0]) series.push({ label: l, color: SERIES[i % SERIES.length], points: pts(d[0].trajectory) });
    });
    if (series.length < 2) return null;
    var card = el("div", { class: "drift-card" });
    card.appendChild(el("h4", {}, ["Cross-lingual overlay · " + testId]));
    card.appendChild(el("p", { class: "meta" }, ["Same counterfactual, every white-box language — overlapping curves = language-invariant internal state."]));
    card.appendChild(driftSvg(series));
    var legend = el("div", { class: "legend" });
    series.forEach(function (s) {
      var i = el("i"); i.style.background = s.color;
      legend.appendChild(el("span", {}, [i, langName(s.label) + " (" + s.label + ")"]));
    });
    card.appendChild(legend);
    return card;
  }

  /* ---- model leaderboard ---- */
  function shortModel(m) { return m.split("/").pop(); }
  function compactModel(m) {
    var parts = (m || "").split("/");
    return parts.length > 2 ? parts.slice(-2).join("/") : (m || "");
  }

  function renderTableAndChart(lb, tableId, chartId, metaId, filterFn) {
    var tHost = document.getElementById(tableId);
    var cHost = document.getElementById(chartId);
    if (!lb || !lb.models) return;
    
    // Filter the models based on the criteria
    var filteredModels = lb.models.filter(filterFn);
    
    var hasData = filteredModels.some(function (e) { return e.per_lang && Object.keys(e.per_lang).length; });
    if (!hasData) {
      if (tHost) tHost.innerHTML = "<p class='muted'>No models matched the filter criteria.</p>";
      if (cHost) cHost.style.display = "none";
      return;
    }
    
    var langs = lb.langs || [];
    var meta = document.getElementById(metaId);
    if (meta) {
      var judged = lb.judge ? " · judge " + lb.judge : "";
      meta.textContent = filteredModels.filter(function (e) { return e.per_lang && Object.keys(e.per_lang).length; }).length +
        " model runs · " + langs.length + " languages · " + scoreLabel(lb) + judged +
        " · generated " + (lb.generated_at || "");
    }

    var hasAccess = filteredModels.some(function (e) { return e.access_path; });
    var header = ["#", "Tested model"].concat(hasAccess ? ["Access"] : [])
      .concat(langs.map(function (l) { return l.toUpperCase(); })).concat(["Mean SPI", "Class"]);
    var numStart = hasAccess ? 3 : 2;
    var rows = [el("tr", {}, header.map(function (h, i) {
      return el("th", (i >= numStart && i <= langs.length + numStart) ? { class: "num" } : {}, [h]);
    }))];
    
    var rank = 0;
    filteredModels.forEach(function (e) {
      var ok = e.per_lang && Object.keys(e.per_lang).length;
      var tds = [];
      tds.push(el("td", { class: "rank" }, [ok ? String(++rank) : "–"]));
      var modelCell = el("td", { class: "model-cell" }, [el("code", { class: "model-id" }, [e.model])]);
      if (hasAccess) {
        var line = el("span", { class: "provider-line" });
        var dot = el("span", { class: "provider-dot" });
        dot.style.background = accessColor(e.access_path);
        line.appendChild(dot);
        line.appendChild(document.createTextNode(accessLabel(e.access_path)));
        modelCell.appendChild(line);
      }
      tds.push(modelCell);
      if (hasAccess) {
        var ai = el("i"); ai.style.background = accessColor(e.access_path);
        ai.style.cssText = "display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:6px;background:" + accessColor(e.access_path);
        tds.push(el("td", {}, [ai, accessLabel(e.access_path)]));
      }
      langs.forEach(function (l) {
        var v = ok && e.per_lang[l] ? e.per_lang[l].stochastic_parrot_index : null;
        tds.push(el("td", { class: "num" }, [v == null ? "—" : v.toFixed(2)]));
      });
      var mean = ok ? e.mean.stochastic_parrot_index : null;
      tds.push(el("td", { class: "num score-mean" }, [mean == null ? "—" : mean.toFixed(3)]));
      tds.push(el("td", {}, [ok
        ? el("span", { class: "badge " + cls(mean) }, [e.classification.split(" (")[0]])
        : el("span", { class: "badge bad" }, ["error"])]));
      rows.push(el("tr", {}, tds));
    });
    
    if (tHost) {
      tHost.innerHTML = "";
      tHost.appendChild(el("div", { class: "table-wrap" }, [el("table", {}, rows)]));
      if (lb.score_type === "semantic_judge") {
        tHost.appendChild(el("p", { class: "judge-note" }, [
          "Semantic judge scores are computed from saved full transcripts. Keyword-screen scores remain in results/leaderboard.json for reproducibility."
        ]));
      }
    }

    renderLbChartGeneric(filteredModels, cHost, lb, langs);
  }

  function renderLbChartGeneric(models, host, lb, langs) {
    if (!host) return;
    if (!models.length) { host.style.display = "none"; return; }
    host.style.display = "block";
    host.innerHTML = "";
    var spis = models.map(function (e) { return e.mean.stochastic_parrot_index; });
    var floor = Math.max(0, Math.floor((Math.min.apply(null, spis) - 0.02) * 20) / 20);
    var span = 1 - floor || 1;
    var W = Math.max(720, models.length * 108), H = 288, padL = 44, padB = 88, padT = 16;
    function Y(v) { return padT + (1 - (v - floor) / span) * (H - padT - padB); }
    var s = svg("svg", { viewBox: "0 0 " + W + " " + H, width: "100%" });
    for (var gi = 0; gi <= 4; gi++) {
      var gv = floor + (gi / 4) * span, gy = Y(gv);
      s.appendChild(svg("line", { x1: padL, y1: gy, x2: W, y2: gy, stroke: "#3c3836" }));
      var gt = svg("text", { x: 6, y: gy + 4 }); gt.textContent = gv.toFixed(2); s.appendChild(gt);
    }
    [[0.75, "#b8bb26"]].forEach(function (p) {
      if (p[0] < floor) return;
      var y = Y(p[0]);
      s.appendChild(svg("line", { x1: padL, y1: y, x2: W, y2: y, stroke: p[1], "stroke-dasharray": "5 5", opacity: .6 }));
    });
    var bw = (W - padL - 16) / models.length, base = Y(floor);
    var hasAccess = models.some(function (e) { return e.access_path; });
    models.forEach(function (e, i) {
      var spi = e.mean.stochastic_parrot_index, yTop = Y(spi), h = base - yTop;
      var x = padL + i * bw + bw * 0.18, w = bw * 0.64;
      var fill = e.access_path ? accessColor(e.access_path) : "url(#g)";
      s.appendChild(svg("rect", { x: x, y: yTop, width: w, height: h, rx: 4, fill: fill }));
      var v = svg("text", { x: x + w / 2, y: yTop - 5, "text-anchor": "middle", fill: "#ebdbb2", "font-size": "11" }); v.textContent = spi.toFixed(3); s.appendChild(v);
      var g = svg("g", { transform: "translate(" + (x + w / 2) + "," + (H - padB + 12) + ") rotate(40)" });
      var lab = svg("text", { x: 0, y: 0 }); lab.textContent = compactModel(e.model); g.appendChild(lab); s.appendChild(g);
    });
    var defs = svg("defs"), grad = svg("linearGradient", { id: "g", x1: "0", y1: "1", x2: "0", y2: "0" });
    grad.appendChild(svg("stop", { offset: "0", "stop-color": "#83a598" }));
    grad.appendChild(svg("stop", { offset: "1", "stop-color": "#d3869b" }));
    defs.appendChild(grad); s.appendChild(defs);
    host.appendChild(s);
    if (hasAccess) {
      var legend = el("div", { class: "legend" });
      var seen = {};
      models.forEach(function (e) {
        if (!e.access_path || seen[e.access_path]) return;
        seen[e.access_path] = 1;
        var ic = el("i"); ic.style.background = accessColor(e.access_path);
        legend.appendChild(el("span", {}, [ic, accessLabel(e.access_path)]));
      });
      host.appendChild(legend);
    }
    host.appendChild(el("p", { class: "muted", style: "margin-top:8px;font-size:13px" },
      ["y-axis starts at " + floor.toFixed(2) + " (zoomed) so the close ranking is visible. Bars use " + scoreLabel(lb) + " mean SPI; read small gaps as noise (~±0.03 to ±0.05)."]));
  }

  /* ---- access-path experiment: claude -p vs codex exec ---- */
  var PATH_COLOR = { "claude-agent": "#d3869b", "codex-agent": "#b8bb26" };

  function renderAgentAccess() {
    var ag = D.agent_access;
    var sec = document.getElementById("agent");
    if (!ag || !ag.paths || !ag.paths.length) { if (sec) sec.style.display = "none"; return; }
    var langs = ag.langs || [];

    // flatten models, keep path label/backend, sort by mean SPI desc
    var rows = [];
    ag.paths.forEach(function (p) {
      (p.models || []).forEach(function (e) {
        rows.push({ label: p.label, backend: p.backend, model: e.model,
                    mean: e.mean.stochastic_parrot_index, per_lang: e.per_lang,
                    cls: e.classification });
      });
    });
    rows.sort(function (a, b) { return b.mean - a.mean; });

    var meta = document.getElementById("ag-meta");
    if (meta) meta.textContent = rows.length + " models · " + ag.paths.length +
      " access paths · " + langs.length + " languages";

    // chart
    var host = document.getElementById("ag-chart");
    if (host) {
      host.innerHTML = "";
      var aspis = rows.map(function (r) { return r.mean; });
      var afloor = Math.max(0, Math.floor((Math.min.apply(null, aspis) - 0.02) * 20) / 20);
      var aspan = 1 - afloor || 1;
      var W = Math.max(560, rows.length * 110), H = 260, padL = 44, padB = 64, padT = 16;
      function AY(v) { return padT + (1 - (v - afloor) / aspan) * (H - padT - padB); }
      var s = svg("svg", { viewBox: "0 0 " + W + " " + H, width: "100%" });
      for (var ai = 0; ai <= 4; ai++) {
        var av = afloor + (ai / 4) * aspan, ay = AY(av);
        s.appendChild(svg("line", { x1: padL, y1: ay, x2: W, y2: ay, stroke: "#3c3836" }));
        var at = svg("text", { x: 6, y: ay + 4 }); at.textContent = av.toFixed(2); s.appendChild(at);
      }
      [[0.75, "#b8bb26"]].forEach(function (p) {
        if (p[0] < afloor) return;
        var y = AY(p[0]);
        s.appendChild(svg("line", { x1: padL, y1: y, x2: W, y2: y, stroke: p[1], "stroke-dasharray": "5 5", opacity: .6 }));
      });
      var bw = (W - padL - 16) / rows.length, abase = AY(afloor);
      rows.forEach(function (r, i) {
        var yTop = AY(r.mean), h = abase - yTop, x = padL + i * bw + bw * 0.18, w = bw * 0.64,
            color = PATH_COLOR[r.backend] || "#83a598";
        s.appendChild(svg("rect", { x: x, y: yTop, width: w, height: h, rx: 4, fill: color }));
        var v = svg("text", { x: x + w / 2, y: yTop - 5, "text-anchor": "middle", fill: "#ebdbb2", "font-size": "11" });
        v.textContent = r.mean.toFixed(3); s.appendChild(v);
        var lab = svg("text", { x: x + w / 2, y: H - padB + 16, "text-anchor": "middle" });
        lab.textContent = shortModel(r.model); s.appendChild(lab);
      });
      host.appendChild(s);
      host.appendChild(el("p", { class: "muted", style: "margin-top:6px;font-size:13px" },
        ["y-axis zoomed (starts at " + afloor.toFixed(2) + ")."]));
      // legend
      var legend = el("div", { class: "legend" });
      ag.paths.forEach(function (p) {
        var i = el("i"); i.style.background = PATH_COLOR[p.backend] || "#83a598";
        legend.appendChild(el("span", {}, [i, p.label]));
      });
      host.appendChild(legend);
    }

    // table
    var tHost = document.getElementById("ag-table");
    if (tHost) {
      var header = ["Access path", "Model"].concat(langs.map(function (l) { return l.toUpperCase(); })).concat(["Mean", "Class"]);
      var trows = [el("tr", {}, header.map(function (h, i) {
        return el("th", (i >= 2 && i <= langs.length + 1) ? { class: "num" } : {}, [h]);
      }))];
      rows.forEach(function (r) {
        var tds = [el("td", {}, [r.label]), el("td", {}, [el("code", {}, [shortModel(r.model)])])];
        langs.forEach(function (l) {
          var v = r.per_lang[l] ? r.per_lang[l].stochastic_parrot_index : null;
          tds.push(el("td", { class: "num" }, [v == null ? "—" : v.toFixed(2)]));
        });
        tds.push(el("td", { class: "num" }, [r.mean.toFixed(2)]));
        tds.push(el("td", {}, [el("span", { class: "badge " + cls(r.mean) }, [r.cls.split(" (")[0]])]));
        trows.push(el("tr", {}, tds));
      });
      tHost.innerHTML = "";
      tHost.appendChild(el("table", {}, trows));
    }

    var note = document.getElementById("ag-note");
    if (note && ag.robustness) {
      var rb = ag.robustness;
      note.textContent = "Noise check: re-running one language " + rb.repeats +
        "× per mode did not reproduce a tools-on/off difference (with-tools " +
        rb.with_tools.mean_spi.toFixed(2) + " vs tools-off " + rb.tools_off.mean_spi.toFixed(2) +
        "). Treat SPI gaps smaller than ~0.05 as noise, not signal.";
    }
  }

  function renderTargetedRerun() {
    var rr = D.targeted_rerun;
    var sec = document.getElementById("targeted-rerun");
    if (!rr || !rr.models || !rr.models.length) { if (sec) sec.style.display = "none"; return; }

    rr.score_type = "keyword_screen";
    var meta = document.getElementById("rerun-meta");
    if (meta) {
      meta.textContent = rr.models.length + " Codex model runs · " +
        (rr.langs || []).map(function (l) { return l.toUpperCase(); }).join(", ") +
        " targeted languages · generated " + (rr.generated_at || "");
    }

    renderTableAndChart(rr, "rerun-table", "rerun-chart", "rerun-meta", function () {
      return true;
    });
  }

  /* ---- open dataset card ---- */
  function renderDataset() {
    var ds = D.dataset;
    var sec = document.getElementById("dataset");
    if (!ds) { if (sec) sec.style.display = "none"; return; }
    var GH = "https://github.com/pedjaurosevic/canyon/blob/main/dataset/";

    var meta = document.getElementById("ds-meta");
    if (meta) meta.textContent = ds.conversations + " full conversations · " +
      ds.prompts + " prompts · " + (ds.languages || []).length + " languages";

    var cards = document.getElementById("ds-cards");
    if (cards) {
      cards.innerHTML = "";
      var items = [
        ["canyon_prompts.jsonl", "The probe bank", ds.prompts + " prompts across " +
          (ds.prompt_languages || []).length + " languages (incl. the Serbian reference), with grounded-answer markers and trap phrases."],
        ["canyon_conversations.jsonl", "Full transcripts", ds.conversations +
          " scored prompt+response turns from chat APIs, local, white-box and agent-CLI runs across " +
          (ds.languages || []).length + " languages."],
        ["canyon_samples_en.jsonl", "Chat-API previews", (ds.samples_en || 0) +
          " English answer previews retained for older keyword-only API runs (truncated, flagged partial)."]
      ];
      items.forEach(function (it) {
        var card = el("div", { class: "card" });
        card.appendChild(el("h3", {}, [it[1]]));
        card.appendChild(el("p", {}, [it[2]]));
        card.appendChild(el("p", {}, [el("a", { href: GH + it[0] }, [el("code", {}, [it[0]])])]));
        cards.appendChild(card);
      });
    }

    var note = document.getElementById("ds-note");
    if (note) {
      var runs = (ds.model_runs || []).map(function (r) { return shortModel(r.model); });
      note.textContent = "Full-transcript model runs: " + runs.join(", ") +
        ". See the dataset datasheet for schema, collection method and limitations.";
    }
  }

  renderBlackbox();
  // Render Primary Leaderboard (Standard API only)
  renderTableAndChart(D.leaderboard, "lb-table", "lb-chart", "lb-meta", function (e) {
    return e.access_path !== "claude-agent" && e.access_path !== "codex-agent";
  });
  
  // Render Experimental Leaderboard (Agent CLIs and Combined)
  renderTableAndChart(D.leaderboard, "lb-table-exp", "lb-chart-exp", "lb-meta-exp", function (e) {
    return true; // Show all runs
  });
  renderAgentAccess();
  renderTargetedRerun();
  renderDataset();
  renderWhitebox();
})();
