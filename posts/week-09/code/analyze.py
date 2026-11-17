"""Offline, reproducible model comparison and executable backtest.

Run after download_data.py. Outputs are generated, never manually transcribed.
"""
from pathlib import Path
import os, json, itertools, hashlib
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'results/.mplconfig'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from xgboost import XGBRegressor

RES = ROOT / 'results'
FIG = RES / 'figures'
SEED = 123
ORIGINAL = ['open','high','low','close','volume','adjusted','return','spy_ret',
            'mom_1m','mom_3m','mom_6m','vol_1m','ret_5d','excess_ret']
IMPROVED = ['momentum_5','momentum_21','momentum_63','momentum_126',
            'volatility_21','relative_21','excess_lag1']

def load_panel():
    path = ROOT / 'data/raw/prices.csv'
    meta = json.loads((ROOT / 'data/raw/metadata.json').read_text())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == meta['sha256']
    raw = pd.read_csv(path, parse_dates=['date']).sort_values(['symbol','date'])
    assert not raw.duplicated(['symbol','date']).any()
    assert (raw.adjusted > 0).all()
    spy = raw[raw.symbol == 'SPY'].set_index('date').adjusted
    calendar = spy.index
    frames = []
    for symbol, part in raw[raw.symbol != 'SPY'].groupby('symbol'):
        part = part.set_index('date').reindex(calendar)
        assert part.adjusted.notna().all(), f'Missing price: {symbol}'
        a = part.adjusted
        part['return'] = a.pct_change(fill_method=None)
        part['spy_ret'] = spy.pct_change(fill_method=None)
        for suffix, lag in [('1m',21),('3m',63),('6m',126)]:
            part['mom_'+suffix] = a.shift(lag) / a.shift(1) - 1
        part['vol_1m'] = part['return'].shift(1).rolling(22).std()
        part['ret_5d'] = a.shift(5) / a.shift(1) - 1
        part['excess_ret'] = part['return'] - part.spy_ret
        for lag in [5,21,63,126]:
            part[f'momentum_{lag}'] = a.shift(1) / a.shift(lag+1) - 1
        part['volatility_21'] = part['return'].shift(1).rolling(21).std()
        part['relative_21'] = part.momentum_21 - (spy.shift(1)/spy.shift(22)-1)
        part['excess_lag1'] = part.excess_ret.shift(1)
        part['target'] = a.shift(-20) / a.shift(-1) - 1
        part['entry_date'] = pd.Series(calendar, index=calendar).shift(-1)
        part['label_end'] = pd.Series(calendar, index=calendar).shift(-20)
        frames.append(part.reset_index())
    panel = pd.concat(frames, ignore_index=True)
    # Shared support eliminates feature-history differences in the comparison.
    panel = panel.dropna(subset=ORIGINAL+IMPROVED+['target','entry_date','label_end'])
    return raw, panel.sort_values(['date','symbol']), calendar, meta

def fit_model(frame, features, improved=None):
    params = dict(n_estimators=300, max_depth=5, learning_rate=.05,
                  min_child_weight=10, gamma=0, subsample=1, colsample_bytree=1,
                  reg_lambda=1, objective='reg:squarederror', tree_method='hist',
                  random_state=SEED, n_jobs=2, base_score=float(frame.target.mean()))
    if improved:
        params.update(improved)
    model = XGBRegressor(**params)
    model.fit(frame[features], frame.target)
    return model

def tune(panel):
    rows = []
    grid = [dict(max_depth=d, min_child_weight=w, n_estimators=n,
                 learning_rate=.03, subsample=.8, reg_lambda=10)
            for d,w,n in itertools.product([1,2],[30,100],[100,300])]
    folds = [('2023-04-01','2023-07-01'),('2023-07-01','2023-10-01'),
             ('2023-10-01','2024-01-01')]
    for i, params in enumerate(grid):
        for start, end in folds:
            train = panel[panel.label_end < start]
            valid = panel[(panel.date >= start) & (panel.date < end) & (panel.label_end < end)]
            assert train.label_end.max() < valid.date.min()
            model = fit_model(train, IMPROVED, params)
            pred = model.predict(valid[IMPROVED])
            rows.append(dict(candidate=i, fold=start, train_n=len(train), valid_n=len(valid),
                             mse=float(np.mean((valid.target-pred)**2)), **params))
        print('Validated candidate', i, flush=True)
    results = pd.DataFrame(rows)
    results.to_csv(RES / 'validation.csv', index=False)
    best = int(results.groupby('candidate').mse.mean().idxmin())
    return grid[best], best

def forecast_scores(preds, label):
    rows=[]
    for name in ['Original','Improved','Historical mean','Original unpurged diagnostic']:
        error = preds[name]-preds.target
        rank = []
        if name != 'Historical mean':
            for _, g in preds.groupby('date'):
                if g[name].nunique() > 1:
                    rank.append(spearmanr(g[name],g.target).statistic)
        mse = np.mean(error**2)
        base_mse = np.mean((preds['Historical mean']-preds.target)**2)
        rows.append(dict(model=name, sample=label, observations=len(preds), dates=preds.date.nunique(),
                         rmse_pp=np.sqrt(mse)*100, mae_pp=np.abs(error).mean()*100,
                         r2_vs_mean=1-mse/base_mse,
                         direction_accuracy=np.mean((preds[name]>0)==(preds.target>0)),
                         mean_rank_ic=np.mean(rank) if rank else np.nan))
    return pd.DataFrame(rows)

def block_interval(values, block=3, draws=5000):
    """Circular block bootstrap of date-level mean loss differences."""
    rng=np.random.default_rng(SEED)
    a=np.asarray(values); n=len(a)
    starts=rng.integers(0,n,size=(draws,int(np.ceil(n/block))))
    indices=((starts[:,:,None]+np.arange(block))%n).reshape(draws,-1)[:,:n]
    return np.quantile(a[indices].mean(axis=1),[.025,.975]).tolist()

def backtest(raw, scheduled, calendar):
    prices=raw.pivot(index='date',columns='symbol',values='adjusted').sort_index()
    stocks=[s for s in prices.columns if s!='SPY']
    assets=stocks+['SPY']
    periods=[]; weights=[]
    methods=['Original','Improved','Equal weight','SPY']
    cost_levels=[0,.001,.0025]
    paths={}; metrics=[]
    # Each signal is 19 sessions after the preceding signal. Entry t+1, exit t+20.
    groups=list(scheduled.groupby('date'))
    for method in methods:
        portfolio_weights=[]
        for signal, g in groups:
            w=pd.Series(0.,index=assets)
            if method=='SPY': w['SPY']=1
            elif method=='Equal weight': w.loc[stocks]=1/len(stocks)
            else:
                chosen=g.sort_values([method,'symbol'],ascending=[False,True]).head(10)
                positive=chosen[method].clip(lower=0).to_numpy(dtype=float)
                w.loc[chosen.symbol]=positive/positive.sum() if positive.sum()>0 else 1/len(chosen)
            assert np.isclose(w.sum(),1) and (w>=0).all()
            portfolio_weights.append(w)
            for symbol,value in w[w>0].items():
                weights.append(dict(model=method,date=signal,symbol=symbol,weight=value))
        for cost in cost_levels:
            wealth=1.; drift=pd.Series(0.,index=assets); traded_total=0.; values={}
            for k, ((signal,g),w) in enumerate(zip(groups,portfolio_weights)):
                entry=g.entry_date.iloc[0]; end=g.label_end.iloc[0]
                segment=prices.loc[entry:end,assets]
                if k: assert entry == groups[k-1][1].label_end.iloc[0]
                before=wealth
                # Exact self-financing transaction cost: v = 1 - c*sum(|v*w-drift|).
                factor=1.
                for _ in range(30): factor=1-cost*float((factor*w-drift).abs().sum())
                traded=float((factor*w-drift).abs().sum())
                traded_total+=traded
                wealth*=factor
                relatives=segment/segment.iloc[0]
                trajectory=relatives.mul(w,axis=1).sum(axis=1)
                values.update((date,float(wealth*v)) for date,v in trajectory.items())
                gross=float(trajectory.iloc[-1])
                wealth*=gross
                drift=w*relatives.iloc[-1]/gross
                if k==len(groups)-1:
                    wealth*=1-cost
                    values[end]=wealth
                    traded_total+=1
                periods.append(dict(model=method,cost_bps=cost*10000,signal=signal,
                                    entry=entry,exit=end,period_return=wealth/before-1,
                                    traded_fraction=traded))
            path=pd.Series(values).sort_index()
            # Include entry fee and final sale in daily risk/return accounting.
            daily=path.pct_change(fill_method=None)
            daily.iloc[0]=path.iloc[0]-1
            years=(path.index[-1]-path.index[0]).days/365.25
            running=np.maximum.accumulate(np.r_[1,path.to_numpy()])[1:]
            metrics.append(dict(model=method,cost_bps=cost*10000,final_wealth=wealth,
                                total_return=wealth-1,cagr=wealth**(1/years)-1,
                                annual_vol=daily.std()*np.sqrt(252),
                                sharpe_zero_rf=daily.mean()/daily.std()*np.sqrt(252),
                                max_drawdown=float((path/running-1).min()),
                                annual_traded_notional=traded_total/years,
                                start=str(path.index[0].date()),end=str(path.index[-1].date())))
            paths[f'{method} | {int(cost*10000)} bps']=path
    pd.DataFrame(weights).to_csv(RES/'portfolio_weights.csv',index=False)
    pd.DataFrame(periods).to_csv(RES/'holding_period_returns.csv',index=False)
    allpaths=pd.DataFrame(paths)
    allpaths.index.name='date'; allpaths.to_csv(RES/'daily_wealth.csv')
    performance=pd.DataFrame(metrics); performance.to_csv(RES/'investment_metrics.csv',index=False)
    annual=[]
    for name,path in paths.items():
        rets=path.pct_change(); rets.iloc[0]=path.iloc[0]-1
        for year,g in rets.groupby(rets.index.year):
            annual.append(dict(strategy=name,year=year,return_value=float((1+g).prod()-1)))
    pd.DataFrame(annual).to_csv(RES/'calendar_year_returns.csv',index=False)
    return performance,allpaths

def plots(scores,performance,paths):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.dpi':150})
    colors=['#42566e','#007f82','#bd8738','#7b548f']
    fig,ax=plt.subplots(figsize=(9,5))
    for name,color in zip(['Original','Improved','Equal weight','SPY'],colors):
        ax.plot(paths.index,paths[f'{name} | 10 bps'],label=name,color=color,lw=2)
    ax.set(title='Could the forecasts grow an investment?',ylabel='Value of $1 (after 10 bps per dollar traded)',xlabel='Date')
    ax.legend(frameon=False,ncol=2); ax.grid(alpha=.15)
    fig.tight_layout(); fig.savefig(FIG/'wealth.png'); plt.close(fig)
    s=scores[scores.model!='Original unpurged diagnostic']
    fig,ax=plt.subplots(figsize=(8,4.5))
    bars=ax.bar(s.model,s.rmse_pp,color=[colors[0],colors[1],'#a7adb4'])
    ax.bar_label(bars,fmt='%.2f',padding=4)
    ax.set(ylabel='RMSE (percentage points; lower is better)',title='Accuracy on unseen 19-trading-day returns')
    ax.set_ylim(0,s.rmse_pp.max()*1.2)
    fig.tight_layout(); fig.savefig(FIG/'forecast_error.png'); plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,3.4))
    for y,start,end,text,color in [(2,'2022-07-01','2023-12-31','Training / expanding validation',colors[0]),
                                  (1,'2023-04-01','2023-12-31','2023 validation',colors[1]),
                                  (0,'2024-01-01','2025-12-31','Untouched final test',colors[2])]:
        ax.barh(y,(pd.Timestamp(end)-pd.Timestamp(start)).days,left=pd.Timestamp(start),height=.55,color=color)
        ax.text(pd.Timestamp(start)+pd.Timedelta(days=12),y,text,va='center',color='white',fontsize=9)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6)); ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.set_yticks([]); ax.set_title('Choose the model before measuring test performance')
    fig.autofmt_xdate(); fig.tight_layout(); fig.savefig(FIG/'timeline.png'); plt.close(fig)

def main():
    raw,panel,calendar,meta=load_panel()
    best,candidate=tune(panel)
    train=panel[panel.label_end < '2024-01-01']
    test=panel[panel.date >= '2024-01-01'].copy()
    unpurged=panel[panel.date < '2024-01-01']
    assert train.label_end.max()<test.date.min()
    for name,features,params,training in [('Original',ORIGINAL,None,train),
                                         ('Improved',IMPROVED,best,train),
                                         ('Original unpurged diagnostic',ORIGINAL,None,unpurged)]:
        model=fit_model(training,features,params)
        test[name]=model.predict(test[features])
        model.save_model(RES/(name.lower().replace(' ','_')+'.json'))
    test['Historical mean']=train.target.mean()
    first=calendar.get_loc(test.date.min())
    signal_dates=calendar[first:len(calendar)-20:19]
    scheduled=test[test.date.isin(signal_dates)].copy()
    assert scheduled.groupby('date').size().eq(meta['stock_count']).all()
    assert len(scheduled)>0
    # Identity check: target is the exact adjusted-price holding return.
    prices=raw.pivot(index='date',columns='symbol',values='adjusted')
    for row in scheduled.itertuples():
        assert np.isclose(row.target,prices.loc[row.label_end,row.symbol]/prices.loc[row.entry_date,row.symbol]-1)
    test[['date','symbol','entry_date','label_end','target','Original','Improved','Historical mean',
          'Original unpurged diagnostic']].to_csv(RES/'predictions.csv',index=False)
    scores=forecast_scores(scheduled,'nonoverlapping signals')
    scores.to_csv(RES/'predictive_metrics.csv',index=False)
    forecast_scores(test,'all daily signals; overlapping labels').to_csv(RES/'predictive_metrics_daily.csv',index=False)
    uncertainty={}
    for other in ['Original','Historical mean']:
        loss=((scheduled.Improved-scheduled.target)**2-(scheduled[other]-scheduled.target)**2)
        date_loss=loss.groupby(scheduled.date).mean()
        uncertainty[other]={'mean_mse_difference':float(date_loss.mean()),
                            '95pct_block_bootstrap_interval':block_interval(date_loss)}
    performance,paths=backtest(raw,scheduled,calendar)
    plots(scores,performance,paths)
    summary=dict(data=meta,chosen_candidate=candidate,chosen_parameters=best,
                 training_rows=len(train),test_rows=len(test),scheduled_rows=len(scheduled),
                 signal_count=len(signal_dates),first_train_signal=str(train.date.min().date()),
                 last_train_signal=str(train.date.max().date()),
                 purged_rows=len(unpurged)-len(train),training_mean=float(train.target.mean()),
                 uncertainty=uncertainty)
    (RES/'summary.json').write_text(json.dumps(summary,indent=2))
    (RES/'verification.txt').write_text('PASS: snapshot hash; unique dates/symbols; positive prices; full common calendar;\n'
        'purged training and validation label boundaries; equal test universe; target/holding return identity;\n'
        'long-only weights sum to one; consecutive holdings share execution dates.\n')
    print(scores.to_string(index=False)); print(performance.to_string(index=False)); print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
