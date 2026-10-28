"""Check portable links, chart coverage, accounting and the curated public package."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import csv
import json
import math
import zipfile

site = Path(__file__).resolve().parents[1] / 'site'
bundle = json.loads((site / 'data/board-data.json').read_text())
cases = bundle.get('shock_cases', {'baseline': bundle['shock']})
assert cases['baseline']['data'] == bundle['shock']['data']
assert cases['baseline']['debts'] == bundle['shock']['debts']
for name, case in cases.items():
    assert len(case['debts']) == 5
    assert len(case['data']) == 75
    assert case['debts'] == bundle['shock']['debts']
    for key, series in case['data'].items():
        assert [r[0] for r in series] == list(range(41)), (name, key)
        assert all(math.isfinite(x) for r in series for x in r), (name, key)
        assert all(r[2] >= 0 for r in series), (name, key)
    if 'annual_beta' in case:
        assert abs(case['quarterly_beta']**4 - case['annual_beta']) < 1e-12
    for figure in case.get('figures', {}).values():
        assert (site / figure).is_file(), (name, figure)
if 'lower' in cases:
    assert cases['lower']['annual_beta'] == .85
    assert cases['lower']['metadata']['equilibria_resolved'] is True
    assert cases['lower']['metadata']['all_models_converged'] is True
    assert cases['lower']['data'] != cases['baseline']['data']
implementation = json.loads((site / 'data/implementation-shock.json').read_text())
assert len(implementation['responses']) == 52
for key, values in implementation['responses'].items():
    assert [row[0] for row in values] == list(range(41)), key
    for h, response, mcse, baseline, shock in values:
        assert all(math.isfinite(x) for x in [response, mcse, baseline, shock])
        assert mcse >= 0 and abs(shock - baseline - response) < 1e-10
for impact in implementation['impacts']:
    total = impact['debt_first_component_bp'] + impact['learning_at_new_debt_component_bp']
    assert abs(total - impact['total_spread_response_bp']) < 1e-10
for case in implementation['patience_cases']:
    predictive_case = 'lower_patience' if case == 'lower' else case
    for offset in [-.05, .05]:
        for tolerance in [.025, .05, .1]:
            forecasts = [r for r in implementation['predictive'] if r['patience'] == predictive_case
                         and r['observation_offset_from_strategic_target'] == offset
                         and r['illustrative_tolerance'] == tolerance]
            assert sorted(r['horizon'] for r in forecasts) == [1,2,3,4]
            for r in forecasts:
                zero = next(z for z in implementation['predictive'] if z['patience'] == predictive_case
                            and z['observation_offset_from_strategic_target'] == 0
                            and z['illustrative_tolerance'] == tolerance and z['horizon'] == r['horizon'])
                assert abs(r['probability_any_excess_through_horizon']
                           - r['probability_any_excess_change_from_zero']
                           - zero['probability_any_excess_through_horizon']) < 1e-12
all_downloads = bundle['downloads'] + implementation['downloads']
for download in all_downloads:
    target = (site / download['file']).resolve()
    assert target.is_relative_to(site.resolve()) and target.is_file(), download
    assert target.stat().st_size > 0, download
assert len(bundle['long_run']) == 4
assert bundle['metadata']['parameters_changed'] is False
assert bundle['metadata']['income_shock_percent'] < 0

groups = {}
for name, case in cases.items():
    rows = list(csv.DictReader((site / case.get('response_file', 'data/responses_all_debts_priors.csv')).open()))
    for row in rows:
        key = (name, row['model'], row['target_debt_pct'], row['horizon'])
        groups.setdefault(key, {})[row['variable']] = float(row['response'])
for key, g in groups.items():
    assert abs(g['consumption_pct_reference'] - g['income_pct_reference'] + g['primary_balance_pct_reference']) < 1e-10
    if key[3] == '0':
        assert abs(g['primary_balance_pct_reference'] + g['cash_financing_pct_reference']) < 1e-10
        assert abs(g['income_pct_reference'] + 3.360564197935123) < 1e-10

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for k, value in attrs:
            if k not in {'href', 'src'} or not value or value.startswith('#'):
                continue
            url = urlsplit(value)
            if url.scheme or url.netloc:
                continue
            path = (site / unquote(url.path)).resolve()
            assert path.is_relative_to(site.resolve()) and path.is_file(), value

Links().feed((site / 'index.html').read_text())
for path in site.rglob('*'):
    if not path.is_file() or path.name in {'plotly.min.js', 'plotly.min.js.LICENSE.txt'}:
        continue
    if path.suffix in {'.json', '.csv', '.html', '.js', '.css', '.txt', '.toml'}:
        text = path.read_text()
        for forbidden in ['/Users/', '/home/', 'dropbox.com', '127.0.0.1', 'gho_', 'github_pat_']:
            assert forbidden not in text, f'{forbidden} in {path.relative_to(site)}'
with zipfile.ZipFile(site / 'downloads/experiment-data.zip') as z:
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
    assert z.testzip() is None
    for download in implementation['downloads']:
        if download['file'].startswith('data/'):
            assert z.read(download['file']) == (site / download['file']).read_bytes()
print(f'Passed: {sum(len(c["data"]) for c in cases.values())} chart series across {len(cases)} patience cases, {len(groups)} scenario-horizon accounting checks, '
      f'52 implementation response series, 72 predictive forecasts, {len(all_downloads)} downloads, local links and public-package scan.')
