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
assert len(bundle['shock']['debts']) == 5
assert len(bundle['shock']['data']) == 75
for key, series in bundle['shock']['data'].items():
    assert [r[0] for r in series] == list(range(41)), key
    assert all(math.isfinite(x) for r in series for x in r), key
    assert all(r[2] >= 0 for r in series), key
for download in bundle['downloads']:
    target = (site / download['file']).resolve()
    assert target.is_relative_to(site.resolve()) and target.is_file(), download
    assert target.stat().st_size > 0, download
assert len(bundle['long_run']) == 4
assert bundle['metadata']['parameters_changed'] is False
assert bundle['metadata']['income_shock_percent'] < 0

rows = list(csv.DictReader((site / 'data/responses_all_debts_priors.csv').open()))
groups = {}
for row in rows:
    key = (row['model'], row['target_debt_pct'], row['horizon'])
    groups.setdefault(key, {})[row['variable']] = float(row['response'])
for key, g in groups.items():
    assert abs(g['consumption_pct_reference'] - g['income_pct_reference'] + g['primary_balance_pct_reference']) < 1e-10
    if key[2] == '0':
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
    if path.suffix in {'.json', '.csv', '.html', '.js', '.css', '.txt'}:
        text = path.read_text()
        for forbidden in ['/Users/', '/home/', 'dropbox.com', '127.0.0.1', 'gho_', 'github_pat_']:
            assert forbidden not in text, f'{forbidden} in {path.relative_to(site)}'
with zipfile.ZipFile(site / 'downloads/experiment-data.zip') as z:
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
    assert z.testzip() is None
print(f'Passed: 75 chart series, {len(groups)} scenario-horizon accounting checks, '
      f'{len(bundle["downloads"])} downloads, local links and public-package scan.')
