"""Build SQLite tables, match generations with SQL, estimate IGE and save results."""

from pathlib import Path
import sqlite3, json
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
D = BASE / "data"
R = BASE / "results"
R.mkdir(exist_ok=True)
# CPI-U is the mean of all twelve non-seasonally-adjusted monthly observations.
obs = []
for f in sorted(D.glob("cpi_????_????.json")):
    j = json.loads(f.read_text())
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(f)
    for x in j["Results"]["series"][0]["data"]:
        if x["period"] in [f"M{i:02}" for i in range(1, 13)]:
            obs.append((int(x["year"]), x["period"], float(x["value"])))
cpi = pd.DataFrame(obs, columns=["year", "month", "cpi"]).drop_duplicates(
    ["year", "month"]
)
assert cpi.groupby("year").size().eq(12).all()
cpi = cpi.groupby("year").cpi.mean()
cpi.to_csv(D / "cpi_annual.csv")
# Load the compact public extracts and create one ID table per generation.
m = pd.read_csv(D / "mother_selected.csv")
c = pd.read_csv(D / "child_selected.csv")
assert not m.R0000100.duplicated().any() and not c.C0000100.duplicated().any()
db = D / "analysis.sqlite"
if db.exists():
    db.unlink()  # Rebuild this generated cache, never the source files.
con = sqlite3.connect(db)
parents = m.rename(
    columns={"R0000100": "mother_id", "R0000500": "birth_year", "R0214800": "sex"}
)[["mother_id", "birth_year", "sex"]].copy()
parents.birth_year += 1900
parents.to_sql("mothers", con, index=False, if_exists="replace")
children = c.rename(
    columns={"C0000100": "child_id", "C0000200": "mother_id", "C0005700": "birth_year"}
)[["child_id", "mother_id", "birth_year"]]
children.to_sql("children", con, index=False, if_exists="replace")
# Keep reported zeros; convert every negative special code to missing, never to zero.
long = []
for cohort, frame, idcol, birthcol in [
    ("mother", m, "R0000100", "R0000500"),
    ("child", c, "C0000100", "C0005700"),
]:
    v = pd.read_csv(D / f"{cohort}_variables.csv")
    for w in v.query("kind=='wage'").itertuples():
        if cohort == "mother" and not 1988 <= w.survey_year <= 2008:
            continue
        year = pd.Series(w.survey_year - 1, index=frame.index)
        if cohort == "mother" and w.survey_year == 2008:
            year = frame.T1200702 - 1
        if cohort == "child" and w.survey_year >= 2014:
            year = (
                frame[
                    v.query(
                        "kind=='interview_year' and survey_year==@w.survey_year"
                    ).variable.iloc[0]
                ]
                - 1
            )
        birth = frame[birthcol] + (1900 if cohort == "mother" else 0)
        wage = frame[w.variable]
        valid = (wage >= 0) & (year >= 1987) & (year <= 2019)
        assert not (
            (wage >= 0) & ~valid
        ).any(), "Valid income without known reference year"
        a = pd.DataFrame(
            {
                "person_id": frame[idcol],
                "survey_year": w.survey_year,
                "year": year,
                "age": year - birth,
                "wage_nominal": wage,
            }
        )[valid].copy()
        a["wage_real"] = a.wage_nominal * cpi.loc[2018] / a.year.map(cpi)
        assert a.wage_real.notna().all()
        a["cohort"] = cohort
        long.append(a)
long = pd.concat(long, ignore_index=True)
assert not long.duplicated(
    ["cohort", "person_id", "year"]
).any(), "Duplicate reference year"
long.to_sql("earnings", con, index=False, if_exists="replace")
# SQL links each child to a mother and computes the two earnings averages.
con.executescript(
    """
CREATE INDEX IF NOT EXISTS person_idx ON earnings(cohort,person_id,age);
DROP TABLE IF EXISTS matched;
CREATE TABLE matched AS
SELECT c.child_id,c.mother_id,c.birth_year AS child_birth_year,m.birth_year AS mother_birth_year
FROM children c JOIN mothers m ON c.mother_id=m.mother_id WHERE m.sex=2;
DROP TABLE IF EXISTS mother_avg;
CREATE TABLE mother_avg AS
SELECT person_id AS mother_id,AVG(wage_real) AS mother_mean,COUNT(*) AS mother_n
FROM earnings WHERE cohort='mother' AND age BETWEEN 30 AND 44
GROUP BY person_id HAVING COUNT(*)>=3 AND AVG(wage_real)>0;
DROP TABLE IF EXISTS child_avg;
CREATE TABLE child_avg AS
SELECT person_id AS child_id,AVG(wage_real) AS child_mean,COUNT(*) AS child_n
FROM earnings WHERE cohort='child' AND age BETWEEN 25 AND 34
GROUP BY person_id HAVING COUNT(*)>=3 AND AVG(wage_real)>0;
"""
)


# Choose the valid observation nearest target age BEFORE excluding zero earnings.
# Earlier reference year wins ties; never search for the largest income or a positive substitute.
def nearest(name, cohort, lo, hi, target):
    con.executescript(
        f"""DROP TABLE IF EXISTS {name}; CREATE TABLE {name} AS
 SELECT person_id,wage_real,age,year FROM
 (SELECT *,ROW_NUMBER() OVER(PARTITION BY person_id ORDER BY ABS(age-{target}),year) AS rn
 FROM earnings WHERE cohort='{cohort}' AND age BETWEEN {lo} AND {hi}) WHERE rn=1;"""
    )


nearest("mother_single", "mother", 30, 44, 37)
nearest("child_single", "child", 25, 34, 30)
nearest("child_young", "child", 25, 29, 27)
nearest("child_older", "child", 35, 39, 37)
# Build fixed paired samples so each comparison changes the measure, not the people.
main0 = pd.read_sql_query(
    """SELECT p.*,ma.*,ca.*,ms.wage_real AS mother_one,cs.wage_real AS child_one,
ms.age AS mother_age,cs.age AS child_age
FROM matched p JOIN mother_avg ma USING(mother_id) JOIN child_avg ca USING(child_id)
JOIN mother_single ms ON ms.person_id=p.mother_id JOIN child_single cs ON cs.person_id=p.child_id""",
    con,
)
main0 = main0.loc[:, ~main0.columns.duplicated()]
main = main0.query("mother_one>0 and child_one>0").copy()
life0 = pd.read_sql_query(
    """SELECT p.*,ma.mother_mean,ma.mother_n,y.wage_real AS young,o.wage_real AS older,
y.age AS young_age,o.age AS older_age,y.year AS young_year,o.year AS older_year
FROM matched p JOIN mother_avg ma USING(mother_id)
JOIN child_young y ON y.person_id=p.child_id JOIN child_older o ON o.person_id=p.child_id""",
    con,
)
life = life0.query("young>0 and older>0").copy()
main.to_csv(D / "matched_averaging.csv", index=False)
life.to_csv(D / "matched_lifecycle.csv", index=False)


# OLS log-log slope with mother-clustered sandwich uncertainty (CR1 correction).
def estimate(frame, x, y, key):
    X = np.column_stack([np.ones(len(frame)), np.log(frame[x])])
    Y = np.log(frame[y].to_numpy())
    inv = np.linalg.inv(X.T @ X)
    b = inv @ X.T @ Y
    residual = Y - X @ b
    score = (
        pd.DataFrame(X * residual[:, None]).groupby(frame.mother_id.to_numpy()).sum()
    )
    g = len(score)
    n = len(frame)
    factor = g / (g - 1) * (n - 1) / (n - 2)
    influence = score.to_numpy() @ inv[:, 1] * np.sqrt(factor)
    se = np.sqrt(influence @ influence)
    return dict(
        model=key,
        beta=b[1],
        se=se,
        lower=b[1] - 1.96 * se,
        upper=b[1] + 1.96 * se,
        n=n,
        mothers=g,
    ), pd.Series(influence, index=score.index)


rows = []
infl = {}
for frame, x, y, key in [
    (main, "mother_one", "child_one", "single"),
    (main, "mother_mean", "child_mean", "average"),
    (life, "mother_mean", "young", "young"),
    (life, "mother_mean", "older", "older"),
]:
    row, inf = estimate(frame, x, y, key)
    rows.append(row)
    infl[key] = inf
res = pd.DataFrame(rows)
res.to_csv(R / "estimates.csv", index=False)
# Preserve the shared-family dependence when comparing two estimated slopes.
diffs = []
for a, b in [("single", "average"), ("young", "older")]:
    delta = (
        res.set_index("model").loc[b, "beta"] - res.set_index("model").loc[a, "beta"]
    )
    se = np.sqrt(((infl[b] - infl[a]) ** 2).sum())
    diffs.append(
        dict(
            comparison=b + " minus " + a,
            difference=delta,
            se=se,
            lower=delta - 1.96 * se,
            upper=delta + 1.96 * se,
        )
    )
pd.DataFrame(diffs).to_csv(R / "differences.csv", index=False)
# Save sample counts and diagnostics for the article and replication checks.
flow = [
    ("Children in source file", len(c)),
    (
        "Matched to a mother",
        pd.read_sql_query("SELECT COUNT(*) AS n FROM matched", con).n[0],
    ),
    ("Both generations have 3+ valid years and positive means", len(main0)),
    ("Averaging comparison: positive selected single years", len(main)),
    ("Age comparison: both age windows and positive maternal mean", len(life0)),
    ("Age comparison: positive selected earnings at both ages", len(life)),
]
pd.DataFrame(flow, columns=["stage", "children"]).to_csv(
    R / "sample_flow.csv", index=False
)
checks = {
    "unique_child_ids": bool(not c.C0000100.duplicated().any()),
    "all_children_matched": int(
        pd.read_sql_query("SELECT COUNT(*) n FROM matched", con).n[0]
    )
    == len(c),
    "no_duplicate_income_years": True,
    "main_median_mother_years": float(main.mother_n.median()),
    "main_median_child_years": float(main.child_n.median()),
    "life_mean_young_age": float(life.young_age.mean()),
    "life_mean_older_age": float(life.older_age.mean()),
    "life_birth_min": int(life.child_birth_year.min()),
    "life_birth_max": int(life.child_birth_year.max()),
    "life_median_maternal_birth_age": float(
        (life.child_birth_year - life.mother_birth_year).median()
    ),
    "zero_earnings_retained_in_averages": int(long.wage_nominal.eq(0).sum()),
}
(R / "checks.json").write_text(json.dumps(checks, indent=2))
# Independent checks on the substantive joins, averages and fitted slopes.
assert main.child_id.is_unique and life.child_id.is_unique
assert main.mother_age.between(30, 44).all() and main.child_age.between(25, 34).all()
assert life.young_age.between(25, 29).all() and life.older_age.between(35, 39).all()
manual = (
    long.query("cohort=='mother' and 30<=age<=44").groupby("person_id").wage_real.mean()
)
assert np.allclose(main.mother_mean, main.mother_id.map(manual))
manual_c = (
    long.query("cohort=='child' and 25<=age<=34").groupby("person_id").wage_real.mean()
)
assert np.allclose(main.child_mean, main.child_id.map(manual_c))
for frame, x, y, key in [
    (main, "mother_one", "child_one", "single"),
    (main, "mother_mean", "child_mean", "average"),
    (life, "mother_mean", "young", "young"),
    (life, "mother_mean", "older", "older"),
]:
    X = np.column_stack([np.ones(len(frame)), np.log(frame[x])])
    independent = np.linalg.lstsq(X, np.log(frame[y]), rcond=None)[0][1]
    assert np.isclose(independent, res.set_index("model").loc[key, "beta"])
assert all(
    checks[k]
    for k in ["unique_child_ids", "all_children_matched", "no_duplicate_income_years"]
)
(R / "validation.txt").write_text(
    "PASS: unique IDs, complete maternal join, unique income reference years, known CPI, common paired samples, age windows, independent means, independent OLS.\n"
)
pd.DataFrame(list(checks.items()), columns=["metric", "value"]).to_csv(
    R / "metrics.csv", index=False
)
print(res.to_string(index=False))
print(pd.DataFrame(diffs).to_string(index=False))
con.close()
