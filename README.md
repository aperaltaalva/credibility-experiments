# Credibility model: experiment board

[Open the experiment board](https://aperaltaalva.github.io/credibility-experiments/)

Interactive comparisons of the supplied Ramsey, Markov, and reputation solutions
at their existing parameters. These are preliminary numerical experiments, not
empirical estimates or a completed calibration.

The board includes the same negative income shock at five initial debt levels and
three initial reputation beliefs, comparisons across models, long-run diagnostics,
state-conditioned pricing, an illustrative narrative measurement bridge, and
reproduced slide figures/tables. Figures and underlying CSVs can be downloaded.

## Read the experiments

- The income shock is **−3.36%**, approximately 1.37 innovation standard deviations.
- Reputation means the initial probability assigned to the committed type. In the
  shock experiments, the actual government remains strategic and beliefs update.
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

Results are selected from precomputed cases without interpolation. The website
does not run Julia or solve a new equilibrium in the browser.

After committing a checked update, maintainers publish the `site/` tree with
`python3 scripts/publish_site.py`. GitHub Pages serves the root of the `gh-pages`
branch; the repository's `main` branch retains the board source and refresh tools.

Published version: 27 October 2026. Julia version used for the experiments: 1.13.3.
