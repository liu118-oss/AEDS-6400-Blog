"""Download the fixed historical Yahoo Finance snapshot; never silently overwrite it."""
from pathlib import Path
import re, json, hashlib, datetime
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/raw/prices.csv'
yf.set_tz_cache_location(str(ROOT / 'data/.yfinance_cache'))
source = (ROOT / 'reference/original_class_model.R').read_text()
universe = re.findall(r'"([A-Z]+)"', source.split('tickers <- c(')[1].split('\n)')[0])
if OUT.exists():
    raise SystemExit('Snapshot exists. Use it; move it explicitly to download a different vintage.')
rows = []
for symbol in universe + ['SPY']:
    frame = yf.download(symbol, start='2022-01-01', end='2026-01-01',
                        auto_adjust=False, actions=False, progress=False, threads=False)
    if frame.empty:
        raise RuntimeError(f'No data for {symbol}; refusing to silently change the universe.')
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.rename(columns={'Open':'open','High':'high','Low':'low',
                                  'Close':'close','Adj Close':'adjusted','Volume':'volume'})
    frame.index.name = 'date'
    frame = frame.reset_index()
    frame['symbol'] = symbol
    rows.append(frame[['date','symbol','open','high','low','close','volume','adjusted']])
    print(symbol, len(frame), flush=True)
data = pd.concat(rows, ignore_index=True).sort_values(['symbol','date'])
data.to_csv(OUT, index=False)
metadata = {'provider':'Yahoo Finance via yfinance', 'requested_start':'2022-01-01',
            'requested_end_exclusive':'2026-01-01', 'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'symbols':universe, 'stock_count':len(universe), 'rows':len(data),
            'first_date':str(data.date.min()), 'last_date':str(data.date.max()),
            'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest()}
(ROOT / 'data/raw/metadata.json').write_text(json.dumps(metadata, indent=2))
