"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const vars = ["net_issuance_pct_reference", "spread_quarterly_bp", "primary_balance_pct_reference"];
  const panels = ["borrowing", "spread", "fiscal"];
  const modelsAll = ["Ramsey", "Markov", "Reputation_p10", "Reputation_p50", "Reputation_p90"];
  const reputationModels = ["Reputation_p10", "Reputation_p50", "Reputation_p90", "Markov"];
  const repStyles = {Reputation_p10: ["Initial belief 10%", "#7950a2", "solid"], Reputation_p50: ["Initial belief 50%", "#148b88", "solid"], Reputation_p90: ["Initial belief 90%", "#cb8c18", "solid"], Markov: ["Markov reference", "#8593a0", "dash"]};
  const sections = {shocks: "shocks", implementation: "implementation", debt: "debt-section", longrun: "longrun", pricing: "pricing", methods: "methods"};
  let board, data, debts, shockCases, currentCase, ready = false, currentSection = "shocks", toastTimer;
  const params = new URLSearchParams(location.search);
  const safe = (value, allowed, fallback) => allowed.includes(value) ? value : fallback;
  function notify(message) { $("toast").textContent = message; $("toast").classList.add("visible"); clearTimeout(toastTimer); toastTimer = setTimeout(() => $("toast").classList.remove("visible"), 2500); }
  function updateUrl() {
    if (!ready) return;
    const q = new URLSearchParams();
    ["patience", "view", "debt", "prior", "scale", "horizon"].forEach(id => q.set(id, $(id).value));
    ImplementationExperiment.writeParams(q);
    const url = `${location.pathname}?${q.toString()}#${currentSection}`;
    history.replaceState(null, "", url);
  }
  function showSection(key, focus = false, scroll = false) {
    currentSection = Object.hasOwn(sections, key) ? key : "shocks";
    Object.entries(sections).forEach(([name,id]) => { $(id).hidden = name !== currentSection; $("tab-" + name).setAttribute("aria-selected", String(name === currentSection)); });
    updateUrl();
    if (currentSection === "shocks" && ready) requestAnimationFrame(() => panels.forEach(id => Plotly.Plots.resize($(id))));
    if (currentSection === "implementation" && ready) ImplementationExperiment.draw().catch(showError);
    if (focus) $("tab-" + currentSection).focus({preventScroll: true});
    if (scroll) requestAnimationFrame(() => {
      const offset = document.querySelector(".section-nav").getBoundingClientRect().height + 20;
      const top = $(sections[currentSection]).getBoundingClientRect().top + window.scrollY - offset;
      const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
      window.scrollTo({top: Math.max(0, top), behavior});
    });
  }
  document.querySelectorAll("[data-section]").forEach((button, index, buttons) => {
    button.addEventListener("click", () => showSection(button.dataset.section, false, true));
    button.addEventListener("keydown", event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const next = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
      showSection(buttons[next].dataset.section, true, true);
    });
  });
  function selectedModels() { return $("view").value === "reputation" ? reputationModels : ["Ramsey", "Markov", "Reputation_p" + $("prior").value]; }
  function style(model) {
    if ($("view").value === "reputation") return repStyles[model];
    if (model === "Ramsey") return ["Ramsey", "#2864a0", "solid"];
    if (model === "Markov") return ["Markov", "#d65a35", "solid"];
    return [`Reputation · initial belief ${$("prior").value}%`, "#17856b", "solid"];
  }
  function series(debt, model, variable) { return data[`${debt}|${model}|${variable}`].filter(row => row[0] <= +$("horizon").value); }
  function selectPatience(key) {
    key = safe(key, Object.keys(shockCases), "baseline");
    currentCase = shockCases[key]; ({data, debts} = currentCase);
    $("patience").value = key; $("debt-patience").value = key;
    const selectedDebt = $("debt").value;
    $("debt").replaceChildren();
    for (const [value, debt] of Object.entries(debts).sort((a,b) => a[1]-b[1])) {
      const option = document.createElement("option"); option.value = value; option.textContent = debt.toFixed(1)+"%"; $("debt").append(option);
    }
    $("debt").value = safe(selectedDebt, Object.keys(debts), "44");
    $("debt-case-note").textContent = `${currentCase.label} · annual β = ${currentCase.annual_beta.toFixed(2)}. Initial reputation is 50% in the model comparisons.`;
    for (const [figure, id] of Object.entries({reputation:"reputation-figure", debt_paths:"debt-paths-figure", debt_impact:"debt-impact-figure", fiscal_detail:"fiscal-detail-figure"})) {
      const element = $(id), path = currentCase.figures?.[figure]; element.hidden = !path;
      if (path) { element.querySelector("a").href = path; element.querySelector("img").src = path; }
    }
    $("debt-figures-pending").hidden = Boolean(currentCase.figures?.debt_paths);
    $("baseline-debt-insights").hidden = key !== "baseline";
    $("ramsey-history-note").textContent = key === "baseline" ? "Its lowest-debt pool has 78 histories; spread means retain rare tails." : "The lower-patience case uses its own inherited promise histories; history-pool diagnostics are included in the download.";
    const impact = (debt, model, variable) => data[`${debt}|${model}|${variable}`][0][1];
    const spreadOrdered = Object.keys(debts).every(d => impact(d,"Reputation_p10",vars[1]) >= impact(d,"Reputation_p50",vars[1]) && impact(d,"Reputation_p50",vars[1]) >= impact(d,"Reputation_p90",vars[1]));
    $("spread-insight-title").textContent = spreadOrdered ? "Reputation dampens the spread increase" : "The spread response depends on the state";
    $("spread-insight-text").textContent = spreadOrdered ? "At every tested debt in this patience case, a higher initial belief in the committed type reduces the immediate spread response." : "The immediate spread response is not uniformly ordered by initial reputation across the tested debts in this patience case.";
    const highDebt = Object.keys(debts).sort((a,b) => debts[b]-debts[a])[0];
    const fiscal = ["Reputation_p10", "Reputation_p50", "Reputation_p90"].map(m => impact(highDebt,m,vars[2]).toFixed(3));
    $("fiscal-insight-text").textContent = `At ${debts[highDebt].toFixed(1)}% debt, primary-balance responses are ${fiscal[0]}%, ${fiscal[1]}%, and ${fiscal[2]}% of pre-shock income for beliefs of 10%, 50%, and 90%.`;
  }
  function range(values) { const lo = Math.min(0, ...values), hi = Math.max(0, ...values), pad = Math.max((hi - lo) * .10, .015); return [lo - pad, hi + pad]; }
  function legend(models) {
    $("legend").replaceChildren();
    for (const model of models) {
      const [label, color, dash] = style(model), span = document.createElement("span"), line = document.createElement("i");
      line.className = "swatch"; line.style.borderColor = color; line.style.borderTopStyle = dash === "dash" ? "dashed" : "solid"; line.setAttribute("aria-hidden", "true");
      span.append(line, document.createTextNode(label)); $("legend").append(span);
    }
  }
  async function draw() {
    if (!ready) return;
    const debt = $("debt").value, prior = $("prior").value, view = $("view").value, horizon = +$("horizon").value;
    const models = selectedModels(), scaleModels = view === "reputation" ? reputationModels : modelsAll;
    $("prior").disabled = view === "reputation";
    $("prior-help").textContent = view === "reputation" ? "All three beliefs shown" : "Strategic actual government";
    legend(models); $("chart-grid").setAttribute("aria-busy", "true");
    const tasks = vars.map((variable, j) => {
      const traces = models.map(model => {
        const rows = series(debt, model, variable), [label,color,dash] = style(model);
        return {type: "scatter", mode: "lines", x: rows.map(r => r[0]), y: rows.map(r => r[1]), customdata: rows.map(r => r[2]), name: label,
          line: {color, width: 3, dash}, hovertemplate: "Quarter %{x}<br>Response %{y:.4f}<br>Monte Carlo SE %{customdata:.4f}<extra>" + label + "</extra>"};
      });
      const values = $("scale").value === "fixed" ? Object.values(shockCases).flatMap(c => Object.keys(c.debts).flatMap(d => scaleModels.flatMap(m => c.data[`${d}|${m}|${variable}`].filter(r => r[0] <= horizon).map(r => r[1])))) : traces.flatMap(t => t.y);
      const layout = {margin: {l: 88, r: 20, t: 22, b: 63}, font: {family: "Arial, sans-serif", size: 15, color: "#203448"}, paper_bgcolor: "white", plot_bgcolor: "white", showlegend: false,
        xaxis: {title: {text: "Quarters after income shock", font: {size: 14}}, range: [-.2,horizon+.2], tickvals: Array.from({length:6},(_,i) => i*horizon/5), showgrid: false, zeroline: false, automargin: true},
        yaxis: {title: {text: j === 1 ? "Quarterly basis points" : "% of pre-shock<br>quarterly income", font: {size: 14}}, range: range(values), nticks: 6, tickformat: j === 1 ? ".1f" : ".2f", gridcolor: "#e7edf3", zerolinecolor: "#92a1ad", zerolinewidth: 1, automargin: true}, hovermode: "x unified"};
      return Plotly.react(panels[j], traces, layout, {responsive: true, displaylogo: false, modeBarButtonsToRemove: ["select2d","lasso2d"], toImageButtonOptions: {format: "png", scale: 2, filename: `credibility_${panels[j]}_beta${currentCase.annual_beta.toFixed(2)}_debt${debt}`}});
    });
    const impact = vars.map(v => series(debt, "Reputation_p" + prior, v)[0][1]);
    const caseLabel = `${currentCase.label} · annual β = ${currentCase.annual_beta.toFixed(2)}. `;
    $("selection-summary").textContent = caseLabel + (view === "reputation" ? `Initial debt ${debts[debt].toFixed(1)}%. Three initial beliefs are shown together; dashed gray is the Markov reference. The actual reputation-model government remains strategic.` :
      `Initial debt ${debts[debt].toFixed(1)}%; initial reputation ${prior}%. Reputation at impact: borrowing ${impact[0].toFixed(3)}%, spread ${impact[1].toFixed(2)} quarterly bp, primary balance ${impact[2].toFixed(3)}% of pre-shock income.`);
    await Promise.all(tasks); $("chart-grid").setAttribute("aria-busy", "false"); updateUrl();
    document.documentElement.dataset.chartsReady = "true";
  }
  function downloads(items) {
    const labels = {shocks: "Income-shock experiments", income_shocks: "Income-shock experiments", debt: "Debt comparisons", longrun: "Long-run diagnostics", long_run: "Long-run diagnostics", pricing: "Pricing and narrative measurement", diagnostics: "Model diagnostics", replication: "Slide replication", methods: "Methods and verification", reputation: "Initial reputation"};
    const groups = new Map();
    for (const item of items || []) { const key = item.section || "Experiments"; if (!groups.has(key)) groups.set(key,[]); groups.get(key).push(item); }
    for (const [section, entries] of groups) {
      const article = document.createElement("article"), title = document.createElement("h4"), list = document.createElement("ul"); article.className = "download-group"; title.textContent = labels[section] || section;
      for (const item of entries) {
        if (!item.file || /^(?:[a-z]+:|\/\/)/i.test(item.file)) continue;
        const li = document.createElement("li"), a = document.createElement("a"), label = document.createElement("span"), kind = document.createElement("span");
        a.href = item.file; a.setAttribute("download", ""); label.textContent = item.label; kind.textContent = (item.kind || item.file.split(".").pop()).toUpperCase(); kind.className = "file-kind";
        a.append(label,kind); li.append(a); list.append(li);
      }
      article.append(title,list); $("downloads").append(article);
    }
  }
  function longRun(rows) {
    const fmt = value => Number.isFinite(Number(value)) && value !== null ? Number(value).toFixed(2) : "—";
    for (const row of rows || []) {
      const tr = document.createElement("tr");
      [row.model,fmt(row.debt),fmt(row.spread),`${fmt(row.low90)}–${fmt(row.high90)}`].forEach(value => {const td = document.createElement("td"); td.textContent = value; tr.append(td);}); $("longrun-table").append(tr);
    }
  }
  function parameterTable(meta) {
    const labels = {rstar:"Quarterly risk-free rate (r*)",dcrit:"Debt discount threshold (dcrit)",cbar:"c̄",δ:"Debt decay (δ)",ρy:"Income persistence (ρy)",σy:"Income innovation SD (σy)",γ:"γ",β:"Discount factor (β)",κ:"Coupon parameter (κ)",η:"Debt discount steepness (η)"};
    for (const [key,value] of Object.entries(meta.parameters || {})) {
      const tr = document.createElement("tr"), label = document.createElement("td"), val = document.createElement("td");
      label.textContent = labels[key] || key; val.textContent = Number(value).toPrecision(7).replace(/\.?0+$/,""); tr.append(label,val); $("parameters-table").append(tr);
    }
    $("committed-rule").textContent = `Committed issuance rule: a(b) = ${meta.rule_bstar} + ${meta.rule_lambda} × (b − ${meta.rule_bstar}). Fiscal implementation-shock scale: ${meta.implementation_scale}.`;
  }
  $("share-view").addEventListener("click", async () => { updateUrl(); try { await navigator.clipboard.writeText(location.href); notify("Link copied — this selection is included."); } catch { notify("Copy the address bar to share this selection."); } });
  $("download-selection").addEventListener("click", () => {
    const debt = $("debt").value, models = selectedModels();
    const csv = [["model","annual_beta","quarterly_beta","initial_debt_pct_annual_income","initial_belief","income_shock_pct","horizon_quarters","variable","response","monte_carlo_se"]];
    for (const model of models) for (const variable of vars) for (const row of series(debt,model,variable)) csv.push([model,currentCase.annual_beta,currentCase.quarterly_beta,debts[debt],model.startsWith("Reputation_p") ? +model.slice("Reputation_p".length)/100 : "",-3.360564197935123,row[0],variable,row[1],row[2]]);
    const blob = new Blob([csv.map(row => row.join(",")).join("\n") + "\n"], {type: "text/csv;charset=utf-8"}), url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = `credibility_shock_beta${currentCase.annual_beta.toFixed(2)}_debt${debt}_${$("view").value}.csv`; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url),1000); notify("Selected response data downloaded.");
  });
  ["view","debt","prior","scale","horizon"].forEach(id => $(id).addEventListener("change", () => { draw().catch(showError); }));
  ["patience", "debt-patience"].forEach(id => $(id).addEventListener("change", () => { selectPatience($(id).value); draw().catch(showError); }));
  function showError(error) { $("load-error").hidden = false; $("load-error").textContent = "The experiment data or charts could not be loaded. Please reload the page. " + (error.message || ""); }
  async function init() {
    const [base, implementation] = await Promise.all(["data/board-data.json", "data/implementation-shock.json"].map(async file => {
      const response = await fetch(file); if (!response.ok) throw new Error("Data request failed."); return response.json();
    })); board = base;
    shockCases = board.shock_cases || {baseline: {...board.shock, label:"Baseline", annual_beta:.90, quarterly_beta:.90**.25, figures:{reputation:"assets/figures/reputation_by_initial_debt.png",debt_paths:"assets/figures/income_shock_by_initial_debt.png",debt_impact:"assets/figures/income_shock_impact_by_debt.png",fiscal_detail:"assets/figures/income_shock_fiscal_detail.png"}}};
    if (!window.Plotly) throw new Error("Plotting library unavailable.");
    for (const id of ["patience", "debt-patience"]) {
      $(id).replaceChildren();
      for (const [key, c] of Object.entries(shockCases)) { const option = document.createElement("option"); option.value = key; option.textContent = `${c.label} · annual β ${c.annual_beta.toFixed(2)}`; $(id).append(option); }
      $(id).disabled = Object.keys(shockCases).length < 2;
    }
    selectPatience(safe(params.get("patience"),Object.keys(shockCases),"baseline"));
    $("debt").value = safe(params.get("debt"),Object.keys(debts),"44"); $("view").value = safe(params.get("view"),["models","reputation"],"reputation"); $("prior").value = safe(params.get("prior"),["10","50","90"],"50"); $("scale").value = safe(params.get("scale"),["fixed","zoom"],"fixed"); $("horizon").value = safe(params.get("horizon"),["20","40"],"20");
    $("debt").disabled = false; $("share-view").disabled = false; $("download-selection").disabled = false;
    ImplementationExperiment.init(implementation, {notify,updateUrl,showError}, params);
    longRun(board.long_run); downloads([...board.downloads, ...implementation.downloads]); parameterTable(board.metadata);
    $("julia-version").textContent = board.metadata.julia_version; $("solution-hash").textContent = board.metadata.solution_sha256;
    const date = new Date([board.metadata.date,implementation.metadata.date].sort().at(-1) + "T12:00:00Z"); if (!Number.isNaN(date.getTime())) $("updated-date").textContent = date.toLocaleDateString("en-GB",{day:"numeric",month:"long",year:"numeric",timeZone:"UTC"});
    ready = true;
    const requestedSection = location.hash.slice(1), explicitSection = Object.hasOwn(sections, requestedSection);
    const section = safe(requestedSection,Object.keys(sections),"shocks"); await draw(); showSection(section, false, explicitSection);
  }
  window.addEventListener("hashchange", () => showSection(location.hash.slice(1), false, true));
  init().catch(showError);
})();
