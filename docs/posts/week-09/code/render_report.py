"""Generate the finished blog and its tables from saved analysis outputs."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results'
s=json.loads((R/'summary.json').read_text())
d=json.loads((R/'class_diagnostic_summary.json').read_text())
f=pd.read_csv(R/'predictive_metrics.csv').set_index('model')
daily=pd.read_csv(R/'predictive_metrics_daily.csv').set_index('model')
m=pd.read_csv(R/'investment_metrics.csv')
annual=pd.read_csv(R/'calendar_year_returns.csv')
v=pd.read_csv(R/'validation.csv')
def pct(x): return f'{100*x:.1f}%'
def perf(name,cost=10): return m[(m.model==name)&(m.cost_bps==cost)].iloc[0]
def year(name,y): return annual[(annual.strategy==f'{name} | 10 bps')&(annual.year==y)].return_value.iloc[0]
def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,row))+' |' for row in rows])
pred_table=table(['Forecast','RMSE (pp)','MAE (pp)','Out-of-sample R²','Direction correct','Rank correlation'],
    [[name,f'{f.loc[name,"rmse_pp"]:.2f}',f'{f.loc[name,"mae_pp"]:.2f}',f'{f.loc[name,"r2_vs_mean"]:.3f}',
      pct(f.loc[name,'direction_accuracy']),f'{f.loc[name,"mean_rank_ic"]:.3f}' if name!='Historical mean' else 'Not applicable']
     for name in ['Original','Improved','Historical mean']])
investment_table=table(['Strategy','Final $1','CAGR','Annual volatility','Sharpe (zero rate)','Worst drawdown'],
    [[name,f'${perf(name).final_wealth:.3f}',pct(perf(name).cagr),pct(perf(name).annual_vol),
      f'{perf(name).sharpe_zero_rf:.2f}',pct(perf(name).max_drawdown)]
     for name in ['Original','Improved','Equal weight','SPY']])
cost_table=table(['Strategy','No costs','10 bps','25 bps'],
    [[name]+[pct(perf(name,c).cagr) for c in [0,10,25]] for name in ['Original','Improved','Equal weight','SPY']])
for name,text in [('predictive',pred_table),('investment',investment_table),('costs',cost_table)]:
    (R/f'{name}_table.md').write_text(text+'\n')
ci=s['uncertainty']['Historical mean']['95pct_block_bootstrap_interval']
ci_original=s['uncertainty']['Original']['95pct_block_bootstrap_interval']
params=s['chosen_parameters']
compact_table=table(["Strategy","Final $1","Annualized return"], [[name,f"${perf(name).final_wealth:.3f}",pct(perf(name).cagr)] for name in ["Original","Improved","Equal weight","SPY"]])
body=(ROOT/"code/blog_template.qmd").read_text()
replacements={"RETRIEVED":s["data"]["retrieved_utc"][:10],"ORIGINAL_RMSE":f"{f.loc["Original","rmse_pp"]:.2f}","IMPROVED_RMSE":f"{f.loc["Improved","rmse_pp"]:.2f}","MEAN_RMSE":f"{f.loc["Historical mean","rmse_pp"]:.2f}","COMPACT_TABLE":compact_table,"IMPROVED_VOL":pct(perf("Improved").annual_vol),"SPY_VOL":pct(perf("SPY").annual_vol),"YEAR2024":pct(year("Improved",2024)),"YEAR2025":pct(year("Improved",2025)),"HIGH_COST_CAGR":pct(perf("Improved",25).cagr)}
for key,value in replacements.items():
    body=body.replace("@"+key+"@",str(value))
(ROOT/'index.qmd').write_text(body)
(ROOT/'article.md').write_text(body.split('---',2)[2].lstrip())
print('Generated index.qmd, article.md and three results tables.')
