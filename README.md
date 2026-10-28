# Credibility model: experiment board

[Open the experiment board](https://aperaltaalva.github.io/credibility-experiments/)

Interactive comparisons of Ramsey, Markov, and reputation solutions, with baseline
annual discount factor 0.90 and one lower-patience case of 0.85. These are preliminary numerical experiments, not
empirical estimates or a completed calibration.

The board includes the same negative income shock at five initial debt levels and
three initial reputation beliefs, a separate implementation-shock tab, comparisons across models, long-run diagnostics,
state-conditioned pricing, an illustrative narrative measurement bridge, and
reproduced slide figures/tables. Figures and underlying CSVs can be downloaded.

## Read the experiments

- The income shock is **−3.36%**, approximately 1.37 innovation standard deviations.
- The patience selector changes income-shock and debt-comparison charts. The lower
  case changes quarterly β to `0.85^(1/4)` and solves equilibrium policies and prices
  again; all other primitives and the committed rule are held fixed. Fixed chart
  scales span both patience cases. Long-run, pricing, and slide results remain baseline.
- Reputation means the initial probability assigned to the committed type. In the
  shock experiments, the actual government remains strategic and beliefs update.
- The **Implementation shock** tab compares one-time borrowing overshoots and
  undershoots under both patience cases at debt 44.16% of annual income and prior
  credibility 50%. Its four charts hold the true government strategic. The separate
  predictive table weights both permanent types by the updated posterior; a rule
  exceedance is an illustrative event, not literal plan abandonment. The tab also
  reports the order-dependent debt/belief decomposition of the spread response.
- Shock flow responses use fixed pre-shock quarterly income; spreads are quarterly
  basis points. Fiscal adjustment is the primary resource balance `y-c`.
- Ramsey retains inherited promises and has no implementation noise. Its debt
  response is irregular and its spread means are sensitive to rare histories.
- Long-run diagnostics do not prove ergodicity or uniqueness. Monte Carlo errors
  do not include parameter, empirical, or equilibrium-approximation uncertainty.

## View locally

No build tools or package installation are needed to view the saved site:

```sh
python3 -m http.server 8000 --directory site
```

Open `http://localhost:8000`. The plotting library and all displayed data are
included; the board does not use an external analytics or data service.

## Refresh saved results

Full Julia simulation sources and the saved equilibrium are maintained in the
private research archive. This public repository contains the presentation code,
curated simulation outputs, figures, and a source-checksum/parameter manifest.
With a local research archive:

Refreshing the public data requires Python 3.11 or newer (for the standard TOML reader).

```sh
python3 scripts/refresh_data.py --research-root /path/to/theory_experiments
python3 scripts/check_site.py
```

To include the lower-patience outputs, add
`--lower-patience-dir /path/to/theory_experiments/output/lower_patience_20261027`
to the refresh command. It reads the solved experiment's CSV and metadata, and
includes its static figures when present. The existing baseline CSV stays unchanged.
Share the lower case with `?patience=lower#shocks` or `?patience=lower#debt`.

To refresh the Implementation shock tab, also supply
`--implementation-dir /path/to/theory_experiments/output/implementation_shock_20261028`.
The refresh imports the saved responses, forecasts, numerical checks, and static
overview without running Julia. Existing implementation data is preserved if this
option is omitted. Direct links use `#implementation`; its controls are saved in
the URL through `imp_arm`, `imp_patience`, `imp_scale`, `imp_horizon`, and
`imp_tolerance`. The Methods tab and data ZIP include its underlying outputs.

Results are selected from precomputed cases without interpolation. The website
does not run Julia or solve a new equilibrium in the browser.

After committing a checked update, maintainers publish the `site/` tree with
`python3 scripts/publish_site.py`. GitHub Pages serves the root of the `gh-pages`
branch; the repository's `main` branch retains the board source and refresh tools.

Published version: 28 October 2026. Julia version used for the equilibrium solutions: 1.13.3.
