"use strict";
window.ImplementationExperiment = (() => {
  const $ = id => document.getElementById(id);
  const controls = {
    arm: ["positive", "negative"], patience: ["both", "baseline", "lower"],
    scale: ["fixed", "zoom"], horizon: ["20", "40"], tolerance: ["0.025", "0.05", "0.1"]
  };
  const defaults = {arm:"positive", patience:"both", scale:"fixed", horizon:"40", tolerance:"0.05"};
  const panels = [
    ["belief_end", "implementation-belief", "Percentage points", 100],
    ["spread_quarterly_bp", "implementation-spread", "Quarterly basis points", 1],
    ["net_issuance_pct_reference", "implementation-borrowing", "% of reference<br>quarterly income", 1],
    ["primary_balance_pct_reference", "implementation-fiscal", "% of reference<br>quarterly income", 1]
  ];
  const styles = {baseline:["Baseline · annual β 0.90", "#167d9a", "solid"], lower:["Lower patience · annual β 0.85", "#d77835", "dash"]};
  let dataset, callbacks;
  const value = key => $("implementation-" + key).value;
  const selectedCases = () => value("patience") === "both" ? ["baseline", "lower"] : [value("patience")];
  const signed = (x, digits=2) => (x > 0 ? "+" : "") + x.toFixed(digits);
  const pct = x => (100*x).toFixed(2) + "%";
  const epsilon = () => dataset.arms[value("arm")].epsilon0;
  const series = (caseKey, variable) => dataset.responses[`${caseKey}|${value("arm")}|${variable}`].filter(r => r[0] <= +value("horizon"));
  function writeParams(params) {
    for (const key of Object.keys(controls)) params.set("imp_" + key, value(key));
  }
  function cells(parent, values) {
    const tr = document.createElement("tr");
    for (const text of values) { const td = document.createElement("td"); td.textContent = text; tr.append(td); }
    parent.append(tr);
  }
  function tables() {
    $("implementation-impact-table").replaceChildren();
    $("implementation-predictive-table").replaceChildren();
    const threshold = +value("tolerance"), yref = dataset.metadata.reference_quarterly_income;
    $("implementation-predictive-definition").textContent = `Excess means realized borrowing exceeds that quarter’s committed rule by more than ${threshold.toFixed(3)} debt units (${(100*threshold/yref).toFixed(2)}% of reference quarterly income). Each entry compares the zero-noise observation with the selected ${epsilon() > 0 ? "overshoot" : "undershoot"}.`;
    for (const caseKey of selectedCases()) {
      const impact = dataset.impacts.find(r => r.beta_case === caseKey && r.epsilon0 === epsilon());
      cells($("implementation-impact-table"), [styles[caseKey][0], `${pct(impact.zero_posterior)} → ${pct(impact.posterior)}`,
        signed(impact.debt_first_component_bp), signed(impact.learning_at_new_debt_component_bp), signed(impact.total_spread_response_bp)]);
      for (const h of [1,2,4]) {
        const predictiveCase = caseKey === "lower" ? "lower_patience" : caseKey;
        const r = dataset.predictive.find(r => r.patience === predictiveCase && r.observation_offset_from_strategic_target === epsilon() && r.horizon === h && r.illustrative_tolerance === threshold);
        const p = r.probability_any_excess_through_horizon, change = r.probability_any_excess_change_from_zero;
        cells($("implementation-predictive-table"), [`${dataset.patience_cases[caseKey].label} · ${h === 1 ? "next quarter" : `next ${h} quarters`}`,
          pct(p-change), pct(p), signed(100*change), (100*r.probability_any_excess_change_mcse).toFixed(3)]);
      }
    }
  }
  function textAndLegend() {
    const yref = dataset.metadata.reference_quarterly_income, overshoot = epsilon() > 0;
    $("implementation-size").textContent = signed(epsilon());
    $("implementation-shock-label").textContent = `Borrowing ${overshoot ? "overshoot" : "undershoot"} at quarter 0`;
    $("implementation-design").textContent = `${signed(100*epsilon()/yref)}% of reference quarterly income; 0.55 shock standard deviations in magnitude. Starting debt: 44.16% of annual income. Prior credibility: 50%. Same future income and implementation draws.`;
    $("implementation-legend").replaceChildren();
    for (const caseKey of selectedCases()) {
      const [label, color, dash] = styles[caseKey], span = document.createElement("span"), line = document.createElement("i");
      line.className = "swatch"; line.style.borderColor = color; line.style.borderTopStyle = dash === "dash" ? "dashed" : "solid"; line.setAttribute("aria-hidden", "true");
      span.append(line, document.createTextNode(label)); $("implementation-legend").append(span);
    }
    $("implementation-summary").textContent = selectedCases().map(c => {
      const belief = series(c,"belief_end")[0][1]*100, spread = series(c,"spread_quarterly_bp")[0][1];
      return `${dataset.patience_cases[c].label}: impact credibility ${signed(belief)} pp; spread ${signed(spread)} quarterly bp.`;
    }).join(" ") + " Responses use 2,000 paired paths per case.";
    $("implementation-policy-title").textContent = overshoot ? "A miss does not imply immediate policy slippage" : "Intended policy responds after the surprise";
    const gaps = selectedCases().map(c => `${dataset.patience_cases[c].label.toLowerCase()}: ${signed(series(c,"intended_rule_gap_pct_reference")[1][1],3)}%`).join("; ");
    $("implementation-policy").textContent = `Intended borrowing is unchanged on impact. Next quarter, the intended borrowing-minus-rule gap changes by ${gaps} of reference quarterly income. A negative change means intended borrowing moves closer to the rule from above. This holds the government’s true type fixed.`;
  }
  async function draw() {
    if (!dataset) return;
    textAndLegend(); tables();
    $("implementation-grid").setAttribute("aria-busy", "true");
    const horizon = +value("horizon");
    await Promise.all(panels.map(([variable, id, unit, multiplier]) => {
      const traces = selectedCases().map(c => {
        const rows = series(c, variable), [label, color, dash] = styles[c];
        return {type:"scatter", mode:"lines", name:label, x:rows.map(r => r[0]), y:rows.map(r => multiplier*r[1]), customdata:rows.map(r => multiplier*r[2]),
          line:{color,dash,width:3}, hovertemplate:"Quarter %{x}<br>Response %{y:.4f}<br>Paired Monte Carlo SE %{customdata:.4f}<extra>" + label + "</extra>"};
      });
      const cases = value("scale") === "fixed" ? ["baseline","lower"] : selectedCases();
      const values = cases.flatMap(c => series(c,variable).map(r => multiplier*r[1]));
      const lo = Math.min(0,...values), hi = Math.max(0,...values), pad = Math.max((hi-lo)*.10,.015);
      return Plotly.react(id, traces, {
        margin:{l:83,r:20,t:22,b:63}, font:{family:"Arial, sans-serif",size:15,color:"#203448"}, paper_bgcolor:"white",plot_bgcolor:"white",showlegend:false,hovermode:"x unified",
        xaxis:{title:{text:"Quarters after implementation shock",font:{size:13}},range:[-.2,horizon+.2],tickvals:Array.from({length:5},(_,i)=>i*horizon/4),showgrid:false,zeroline:false,automargin:true},
        yaxis:{title:{text:unit,font:{size:14}},range:[lo-pad,hi+pad],nticks:6,tickformat:".2f",gridcolor:"#e7edf3",zerolinecolor:"#92a1ad",zerolinewidth:1,automargin:true}
      }, {responsive:true,displaylogo:false,modeBarButtonsToRemove:["select2d","lasso2d"],toImageButtonOptions:{format:"png",scale:2,filename:`${id}_${value("arm")}_${value("patience")}`}});
    }));
    $("implementation-grid").setAttribute("aria-busy", "false");
    document.documentElement.dataset.implementationReady = "true";
  }
  function download() {
    const csv = [["patience_case","annual_beta","shock_debt_units","initial_debt_pct_annual_income","initial_prior","horizon_quarters","variable","units","response","paired_monte_carlo_se","zero_noise_mean","shock_mean"]];
    const variables = [...panels.map(p=>p[0]),"intended_rule_gap_pct_reference"];
    for (const c of selectedCases()) for (const v of variables) for (const row of series(c,v)) {
      const units = v === "belief_end" ? "probability" : v === "spread_quarterly_bp" ? "quarterly_basis_points" : "percent_reference_quarterly_income";
      csv.push([c,dataset.patience_cases[c].annual_beta,epsilon(),dataset.metadata.initial_debt_pct_annual,dataset.metadata.initial_prior,row[0],v,units,...row.slice(1)]);
    }
    const blob = new Blob([csv.map(r=>r.join(",")).join("\n")+"\n"],{type:"text/csv;charset=utf-8"});
    const url = URL.createObjectURL(blob), a = document.createElement("a");
    a.href = url; a.download = `implementation_${value("arm")}_${value("patience")}.csv`; document.body.append(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),1000);
    callbacks.notify("Selected data downloaded. Belief values in the CSV are probabilities.");
  }
  function init(payload, hooks, params) {
    dataset = payload; callbacks = hooks;
    for (const [key, allowed] of Object.entries(controls)) {
      const requested = params.get("imp_"+key);
      $("implementation-"+key).value = allowed.includes(requested) ? requested : defaults[key];
      $("implementation-"+key).addEventListener("change", () => {
        callbacks.updateUrl();
        if (key === "tolerance") tables(); else draw().catch(callbacks.showError);
      });
    }
    $("implementation-share").disabled = false; $("implementation-download").disabled = false;
    $("implementation-share").addEventListener("click", async () => {
      callbacks.updateUrl();
      try { await navigator.clipboard.writeText(location.href); callbacks.notify("Link copied — this implementation experiment is included."); }
      catch { callbacks.notify("Copy the address bar to share this selection."); }
    });
    $("implementation-download").addEventListener("click", download);
  }
  return {init, draw, writeParams};
})();
