"""Refresh the public board from a local copy of the Julia research archive."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import shutil
import tomllib
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--research-root', type=Path, required=True)
parser.add_argument('--plotly-js', type=Path)
parser.add_argument('--lower-patience-dir', type=Path,
                    help='Directory containing the solved annual-beta 0.85 experiment')
args = parser.parse_args()
src = args.research_root.resolve()
site = Path(__file__).resolve().parents[1] / 'site'
for d in ['assets/figures', 'data', 'downloads']:
    (site / d).mkdir(parents=True, exist_ok=True)
downloads = []
provenance = {}

def copy_file(relative, destination, label, section):
    origin, target = src / relative, site / destination
    shutil.copyfile(origin, target)
    downloads.append(dict(label=label, file=destination, kind=target.suffix[1:].upper(), section=section))
    provenance[destination] = dict(source=relative, sha256=hashlib.sha256(target.read_bytes()).hexdigest())

def public_metadata(value):
    """Retain reproducibility details without exposing local filesystem locations."""
    if isinstance(value, dict):
        return {key: public_metadata(item) for key, item in value.items()}
    if isinstance(value, list):
        return [public_metadata(item) for item in value]
    if isinstance(value, str):
        value = value.replace(str(src) + '/', '').replace(str(src), '.')
        assert '/Users/' not in value and '/home/' not in value, 'Unrecognized local path in metadata'
    return value

groups = {
    'output/income_shock_reputation_20261027': [
        ('responses_all_debts_priors.csv', 'All income-shock responses and Monte Carlo standard errors', 'Income shocks'),
        ('reputation_by_initial_debt.pdf', 'Reputation comparison figure', 'Income shocks'),
        ('verification.txt', 'Independent income-shock verification', 'Methods'),
        ('results_note.txt', 'Reputation experiment findings and qualifications', 'Methods')],
    'output/income_shock_debt_comparison_20261027': [
        ('impact_summary.csv', 'Immediate responses by starting debt', 'Debt comparisons'),
        ('income_shock_by_initial_debt.pdf', 'Five-debt response paths', 'Debt comparisons'),
        ('income_shock_impact_by_debt.pdf', 'Immediate response by debt', 'Debt comparisons')],
    'output/income_shock_20261027': [
        ('income_shock_comparison.pdf', 'Three-model income-shock comparison', 'Income shocks'),
        ('income_shock_fiscal_detail.pdf', 'Cash financing and consumption responses', 'Income shocks')],
    'output/model_diagnostics_20261027': [
        ('moments.csv', 'Finite-horizon moments', 'Transitions and pricing'),
        ('comovements.csv', 'Finite-horizon comovements', 'Transitions and pricing'),
        ('trajectories.csv', 'Finite-horizon mean paths', 'Transitions and pricing'),
        ('state_comparisons.csv', 'State-conditioned pricing and choices', 'Transitions and pricing'),
        ('narrative_bridge.csv', 'Illustrative narrative measurement bridge', 'Transitions and pricing'),
        ('implementation_news.csv', 'Implementation-news experiments', 'Transitions and pricing'),
        ('long_run_moments.csv', 'Long-run moments by starting condition and window', 'Long-run diagnostics'),
        ('long_run_ergodic_debt_quantiles.csv', 'Pooled final-window debt quantiles', 'Long-run diagnostics'),
        ('long_run_state_bins.csv', 'State-conditioned long-run bins', 'Long-run diagnostics'),
        ('long_run_start_comparisons.csv', 'Comparisons across initial conditions', 'Long-run diagnostics'),
        ('long_run_window_changes.csv', 'Comparisons across time windows', 'Long-run diagnostics'),
        ('long_run_boundaries.csv', 'Long-run numerical boundary diagnostics', 'Long-run diagnostics')]
}
for folder, entries in groups.items():
    for name, label, section in entries:
        destination = ('data/' if name.endswith('.csv') else 'downloads/') + name
        copy_file(f'{folder}/{name}', destination, label, section)

figures = {
    'output/income_shock_reputation_20261027': ['reputation_by_initial_debt.png'],
    'output/income_shock_debt_comparison_20261027': ['income_shock_by_initial_debt.png', 'income_shock_impact_by_debt.png'],
    'output/income_shock_20261027': ['income_shock_comparison.png', 'income_shock_fiscal_detail.png'],
    'output/model_diagnostics_20261027': ['transition_comparison.png', 'long_run_support_and_conditional_spreads.png', 'state_and_measurement_implications.png']
}
for folder, names in figures.items():
    for name in names:
        origin, target = src / folder / name, site / 'assets/figures' / name
        shutil.copyfile(origin, target)
        provenance[str(target.relative_to(site))] = dict(source=f'{folder}/{name}', sha256=hashlib.sha256(target.read_bytes()).hexdigest())

for path in sorted((src / 'output/reproduced_slides').iterdir()):
    if path.suffix in {'.pdf', '.tex'}:
        copy_file(str(path.relative_to(src)), 'downloads/slide_' + path.name,
                  'Slide replication: ' + path.stem.replace('_', ' '), 'Slide replication')

variables = ['net_issuance_pct_reference', 'spread_quarterly_bp', 'primary_balance_pct_reference']
models = ['Ramsey', 'Markov', 'Reputation_p10', 'Reputation_p50', 'Reputation_p90']
def shock_data(path):
    rows = list(csv.DictReader(path.open()))
    data, debts = {}, {}
    for row in rows:
        d = str(int(float(row['target_debt_pct'])))
        actual = float(row['actual_debt_pct'])
        assert d not in debts or abs(debts[d] - actual) < 1e-9
        debts[d] = actual
        if row['variable'] not in variables:
            continue
        key = f"{d}|{row['model']}|{row['variable']}"
        data.setdefault(key, []).append([int(row['horizon']), float(row['response']), float(row['mcse'])])
    for d in debts:
        for m in models:
            for v in variables:
                values = data[f'{d}|{m}|{v}']
                values.sort()
                assert [x[0] for x in values] == list(range(41))
    assert len(debts) == 5
    return dict(data=data, debts=debts)

baseline_shock = shock_data(site / 'data/responses_all_debts_priors.csv')
figure_names = dict(reputation='reputation_by_initial_debt.png',
                    debt_paths='income_shock_by_initial_debt.png',
                    debt_impact='income_shock_impact_by_debt.png',
                    fiscal_detail='income_shock_fiscal_detail.png')
shock_cases = {'baseline': dict(**baseline_shock, label='Baseline', annual_beta=.90,
    quarterly_beta=.90**.25, response_file='data/responses_all_debts_priors.csv',
    figures={key: 'assets/figures/' + name for key, name in figure_names.items()})}
lower_path = args.lower_patience_dir
if lower_path is not None:
    lower_path = lower_path.resolve()
    metadata_origin = lower_path / 'experiment.toml'
    lower_run = public_metadata(tomllib.loads(metadata_origin.read_text()))
    assert abs(lower_run['annual_beta'] - .85) < 1e-12
    assert abs(lower_run['quarterly_beta'] - .85**.25) < 1e-12
    assert lower_run['equilibria_resolved'] is True
    assert lower_run['all_models_converged'] is True
    lower = shock_data(lower_path / 'responses_all_debts_priors.csv')
    assert lower['debts'] == baseline_shock['debts'], 'Patience cases must share starting debts'
    lower_figures = {}
    for name, label in [('responses_all_debts_priors.csv', 'Lower patience: all shock responses'),
                        ('checks.csv', 'Lower patience: numerical checks'),
                        ('verification.txt', 'Lower patience: verification summary'),
                        ('income_shock_comparison.pdf', 'Lower patience: three-model comparison')]:
        origin = lower_path / name
        if not origin.is_file():
            if name != 'responses_all_debts_priors.csv':
                continue
            raise FileNotFoundError(origin)
        relative = str(origin.relative_to(src))
        destination = ('data/' if name.endswith('.csv') else 'downloads/') + 'lower_patience_' + name
        copy_file(relative, destination, label, 'Lower patience · annual β 0.85')
    metadata_destination = 'data/lower_patience_experiment.json'
    metadata_target = site / metadata_destination
    metadata_target.write_text(json.dumps(lower_run, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    downloads.append(dict(label='Lower patience: parameters and solve diagnostics',
                          file=metadata_destination, kind='JSON', section='Lower patience · annual β 0.85'))
    provenance[metadata_destination] = dict(source=str(metadata_origin.relative_to(src)),
        source_sha256=hashlib.sha256(metadata_origin.read_bytes()).hexdigest(),
        sha256=hashlib.sha256(metadata_target.read_bytes()).hexdigest(),
        transformation='TOML converted to JSON; research paths made relative')
    for key, name in figure_names.items():
        for suffix in ['.png', '.pdf']:
            origin = lower_path / Path(name).with_suffix(suffix)
            if not origin.is_file():
                continue
            destination = ('assets/figures/' if suffix == '.png' else 'downloads/') + 'lower_patience_' + origin.name
            copy_file(str(origin.relative_to(src)), destination,
                      'Lower patience: ' + key.replace('_', ' '), 'Lower patience · annual β 0.85')
            if suffix == '.png':
                lower_figures[key] = destination
    shock_cases['lower'] = dict(**lower, label='Lower patience', annual_beta=.85,
        quarterly_beta=.85**.25, response_file='data/lower_patience_responses_all_debts_priors.csv',
        figures=lower_figures, metadata=lower_run)

moments = list(csv.DictReader((site / 'data/long_run_moments.csv').open()))
quantiles = list(csv.DictReader((site / 'data/long_run_ergodic_debt_quantiles.csv').open()))
long_run = []
for scenario, label in [('ramsey_d45_s11', 'Ramsey'), ('markov_d45_s11', 'Markov'),
    ('reputation_rational_d45_s11_p5', 'Reputation · strategic'), ('reputation_behavioral_d45_s11_p5', 'Reputation · committed')]:
    def metric(key):
        return float(next(x['mean'] for x in moments if x['scenario_id'] == scenario and x['window_start'] == '2001' and x['metric'] == key))
    def q(value):
        return float(next(x['debt_pct_annual_income'] for x in quantiles if x['scenario_id'] == scenario and float(x['quantile']) == value))
    long_run.append(dict(model=label, debt=metric('debt_pct_annual_income'), spread=metric('quarterly_spread_bps'), low90=q(.05), high90=q(.95)))

run = tomllib.loads((src / 'output/model_diagnostics_20261027/experiment.toml').read_text())
metadata = dict(date='2026-10-27', scope='Baseline diagnostics; patience variants are listed separately',
    julia_version=run['julia_version'], solution_sha256=run['source_sha256'],
    parameters=run['parameters'], rule_bstar=run['rule_bstar'], rule_lambda=run['rule_lambda'],
    implementation_scale=run['implementation_scale'], parameters_changed=False, equilibria_resolved=False,
    income_shock_percent=-3.360564197935123, paths_per_income_case=2000, income_response_quarters=41,
    finite_horizon_paths_per_type=500, finite_horizon_quarters=120, long_run_paths_per_case=32,
    long_run_quarters=4000, long_run_summary_window=[2001,4000], source_solution='output/ramsey.jld2',
    uncertainty='Monte Carlo standard errors describe simulation error, conditional on saved solutions and finite history pools.')
downloads.append(dict(label='Parameters, design and source checksum', file='data/experiment_metadata.json', kind='JSON', section='Methods'))
metadata['patience_cases'] = {key: dict(annual_beta=case['annual_beta'], quarterly_beta=case['quarterly_beta'])
                              for key, case in shock_cases.items()}
(site / 'data/experiment_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
bundle = dict(shock=baseline_shock, shock_cases=shock_cases, long_run=long_run, downloads=downloads, metadata=metadata)
(site / 'data/board-data.json').write_text(json.dumps(bundle, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
(site / 'data/provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
with zipfile.ZipFile(site / 'downloads/experiment-data.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted((site / 'data').iterdir()):
        if path.name != 'board-data.json':
            archive.write(path, 'data/' + path.name)
if args.plotly_js:
    shutil.copyfile(args.plotly_js, site / 'assets/plotly.min.js')
(site / '.nojekyll').touch()
print(f'Refreshed {sum(len(c["data"]) for c in shock_cases.values())} series across '
      f'{len(shock_cases)} patience cases, {len(downloads)} downloads, {len(long_run)} long-run summaries.')
