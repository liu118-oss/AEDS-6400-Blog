"""Independent numerical checks and diagnostic reconstruction of class bookkeeping."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results'
p=pd.read_csv(R/'predictions.csv',parse_dates=['date','entry_date','label_end'])
prices=pd.read_csv(ROOT/'data/raw/prices.csv',parse_dates=['date']).pivot(index='date',columns='symbol',values='adjusted')
w=pd.read_csv(R/'portfolio_weights.csv',parse_dates=['date'])
h=pd.read_csv(R/'holding_period_returns.csv',parse_dates=['signal','entry','exit'])
m=pd.read_csv(R/'investment_metrics.csv')
checks=[]
for row in h[h.cost_bps==0].itertuples():
    weights=w[(w.model==row.model)&(w.date==row.signal)].set_index('symbol').weight
    expected=float(((prices.loc[row.exit,weights.index]/prices.loc[row.entry,weights.index]-1)*weights).sum())
    assert np.isclose(expected,row.period_return,atol=1e-10)
checks.append('All gross holding returns equal independently calculated weighted adjusted-price returns.')
for model,g in m.groupby('model'):
    assert g.sort_values('cost_bps').final_wealth.is_monotonic_decreasing
checks.append('Increasing costs weakly reduces ending wealth for every strategy.')
spy=m[(m.model=='SPY')&(m.cost_bps==0)].iloc[0]
assert np.isclose(spy.final_wealth,prices.loc[spy.end,'SPY']/prices.loc[spy.start,'SPY'])
checks.append('Gross SPY wealth equals direct adjusted-price buy-and-hold ratio.')
assert np.allclose(w.groupby(['model','date']).weight.sum(),1)
checks.append('Every portfolio is fully invested without leverage.')

# Literal original weighting behavior: scalar R ifelse returns only its first value;
# grouped mutate then recycles it. These are diagnostics, not investable results.
p['month']=p.date.dt.to_period('M').astype(str)
monthly=[]
for month,g in p.groupby('month'):
    g=g[g.date==g.date.min()].sort_values('Original unpurged diagnostic',ascending=False).head(10)
    z=g['Original unpurged diagnostic'].clip(lower=0)
    scalar=1/len(g) if z.sum()==0 else float(z.iloc[0]/z.sum())
    monthly.append(dict(month=month,signal=g.date.iloc[0],sum_weights=len(g)*scalar,
                        literal_return=float(scalar*g.target.sum()),
                        normalized_return=float((g.target*(z/z.sum() if z.sum()>0 else 1/len(g))).sum())))
diagnostic=pd.DataFrame(monthly)
diagnostic.to_csv(R/'class_bookkeeping_diagnostic.csv',index=False)
diagnostic_summary={'note':'Python reimplementation of R bookkeeping using reimplemented unpurged model; not an exact R rerun.',
                    'min_sum_weights':float(diagnostic.sum_weights.min()),
                    'max_sum_weights':float(diagnostic.sum_weights.max()),
                    'literal_reported_sharpe_wrong_252':float(diagnostic.literal_return.mean()/diagnostic.literal_return.std()*np.sqrt(252)),
                    'literal_pseudo_terminal_wealth':float((1+diagnostic.literal_return).prod()),
                    'warning':'Invalid as investment evidence: implicit leverage, unmatched holding windows and wrong annualization.'}
(R/'class_diagnostic_summary.json').write_text(json.dumps(diagnostic_summary,indent=2))

# Concentration and contribution: describe outcomes without selecting a new strategy.
contributions=[]
for row in h[(h.cost_bps==0)&h.model.isin(['Original','Improved'])].itertuples():
    weights=w[(w.model==row.model)&(w.date==row.signal)].set_index('symbol').weight
    ret=prices.loc[row.exit,weights.index]/prices.loc[row.entry,weights.index]-1
    for s in weights.index:
        contributions.append(dict(model=row.model,symbol=s,signal=row.signal,
                                  weight=weights[s],contribution=weights[s]*ret[s]))
c=pd.DataFrame(contributions)
summary=c.groupby(['model','symbol']).agg(selections=('signal','size'),
    mean_selected_weight=('weight','mean'),sum_period_contribution=('contribution','sum')).reset_index()
summary.sort_values(['model','sum_period_contribution'],ascending=[True,False]).to_csv(R/'stock_contributions.csv',index=False)
(R/'independent_verification.txt').write_text('\n'.join('PASS: '+x for x in checks)+'\n')
print('\n'.join(checks)); print(json.dumps(diagnostic_summary,indent=2))
