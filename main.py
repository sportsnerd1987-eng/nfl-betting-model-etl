import math
import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

SPREADSHEET_ID = "1TPsmpYjJbkD-SjynBGKUvbNnnU6fNz2r5CdPmPofm2M"
WRITE_URL = os.environ["APPS_SCRIPT_WEB_APP_URL"]
SHARED_SECRET = os.environ["ETL_SHARED_SECRET"]

now = datetime.now(ZoneInfo("America/Chicago"))
SEASON = now.year if now.month >= 7 else now.year - 1

TEAM_NAMES = {
    "ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens","BUF":"Buffalo Bills",
    "CAR":"Carolina Panthers","CHI":"Chicago Bears","CIN":"Cincinnati Bengals","CLE":"Cleveland Browns",
    "DAL":"Dallas Cowboys","DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers",
    "HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars","KC":"Kansas City Chiefs",
    "LA":"Los Angeles Rams","LAC":"Los Angeles Chargers","LV":"Las Vegas Raiders","MIA":"Miami Dolphins",
    "MIN":"Minnesota Vikings","NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants",
    "NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers","SEA":"Seattle Seahawks",
    "SF":"San Francisco 49ers","TB":"Tampa Bay Buccaneers","TEN":"Tennessee Titans","WAS":"Washington Commanders"
}

ESPN_IDS = {
    "ARI":22,"ATL":1,"BAL":33,"BUF":2,"CAR":29,"CHI":3,"CIN":4,"CLE":5,"DAL":6,"DEN":7,"DET":8,"GB":9,
    "HOU":34,"IND":11,"JAX":30,"KC":12,"LV":13,"LAC":24,"LA":14,"MIA":15,"MIN":16,"NE":17,"NO":18,
    "NYG":19,"NYJ":20,"PHI":21,"PIT":23,"SF":25,"SEA":26,"TB":27,"TEN":10,"WAS":28
}

def clean(v, d=None):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, np.integer):
        v = int(v)
    if isinstance(v, np.floating):
        v = float(v)
    return round(float(v), d) if d is not None else v

def collect(o, d):
    if isinstance(o, dict):
        n = o.get("name") or o.get("abbreviation") or o.get("displayName")
        raw = o.get("value", o.get("displayValue"))
        if n is not None and raw is not None:
            try:
                d[str(n)] = float(str(raw).replace(",", "").replace("%", ""))
            except Exception:
                pass
        for v in o.values():
            collect(v, d)
    elif isinstance(o, list):
        for v in o:
            collect(v, d)

def pick(d, names):
    for n in names:
        if n in d:
            return d[n]
    return np.nan

def json_safe(value):
    if value is None or value is pd.NA:
        return ""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return "" if np.isnan(value) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float) and math.isnan(value):
        return ""
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    return value

def rows(df, defense=False):
    x = df.copy()
    x["Tm"] = [TEAM_NAMES.get(i, i) for i in x.index]
    x = x.sort_values(
        ["PFPA", "Tm"],
        ascending=[True, True] if defense else [False, True]
    )

    z = []

    for rk, (a, r) in enumerate(x.iterrows(), 1):
        z.append([
            rk,
            TEAM_NAMES.get(a, a),
            int(r.G),
            int(round(r.PFPA)),
            int(round(r.YDS)),
            int(round(r.PLY)),
            clean(r.Y_P, 1),
            clean(r.TO),
            clean(r.FL),
            clean(r.get("total_first_downs", np.nan)),
            int(round(r.completions)),
            int(round(r.attempts)),
            int(round(r.PASS_NET_YDS)),
            int(round(r.passing_tds)),
            int(round(r.passing_interceptions)),
            clean(r.NY_A, 1),
            int(round(r.passing_first_downs)),
            int(round(r.carries)),
            int(round(r.rushing_yards)),
            int(round(r.rushing_tds)),
            clean(r.RY_A, 1),
            int(round(r.rushing_first_downs)),
            clean(r.get("penalties", np.nan)),
            clean(r.get("penalty_yards", np.nan)),
            clean(r.get("penalty_first_downs", np.nan)),
            clean(r.get("sc_pct", np.nan), 1),
            clean(r.get("to_pct", np.nan), 1),
            ""
        ])

    return z

def summary(rows_):
    a = pd.DataFrame(rows_)

    av = [""] * 28
    tot = [""] * 28
    pg = [""] * 28

    av[1] = "Avg Team"
    tot[1] = "League Total"
    pg[1] = "Avg Tm/G"

    g = pd.to_numeric(a[2], errors="coerce").sum()

    for c in [
        3,4,5,7,8,9,10,11,12,13,14,16,17,18,19,21,22,23,24
    ]:
        v = pd.to_numeric(a[c], errors="coerce")

        if v.notna().any():
            s = v.sum()
            tot[c] = round(s, 1)
            av[c] = round(s / 32, 1)
            pg[c] = round(s / g, 1) if g else ""

    y = pd.to_numeric(a[4], errors="coerce").sum()
    p = pd.to_numeric(a[5], errors="coerce").sum()

    av[6] = tot[6] = pg[6] = round(y / p, 1) if p else ""

    av[15] = tot[15] = pg[15] = ""

    ya = pd.to_numeric(a[18], errors="coerce").sum()
    at = pd.to_numeric(a[17], errors="coerce").sum()

    av[20] = tot[20] = pg[20] = round(ya / at, 1) if at else ""

    for c in [25, 26]:
        v = pd.to_numeric(a[c], errors="coerce")

        if v.notna().any():
            av[c] = tot[c] = pg[c] = round(v.mean(), 1)

    return [av, tot, pg]

def main():
    print("NFL season:", SEASON)

    weekly = pd.read_csv(
        f"https://github.com/nflverse/nflverse-data/releases/download/"
        f"stats_team/stats_team_week_{SEASON}.csv"
    )

    weekly = weekly[
        (weekly.season == SEASON) &
        (weekly.season_type == "REG")
    ].copy()

    req = [
        "week","team","opponent_team","completions","attempts",
        "passing_yards","passing_tds","passing_interceptions",
        "sacks_suffered","sack_yards_lost","passing_first_downs",
        "carries","rushing_yards","rushing_tds","rushing_first_downs"
    ]

    missing = [c for c in req if c not in weekly.columns]

    if missing:
        raise RuntimeError("Missing nflverse fields: " + str(missing))

    if weekly.team.nunique() != 32:
        raise RuntimeError(
            f"Expected 32 teams, found {weekly.team.nunique()}"
        )

    print("Loaded", len(weekly), "team-week records")

    games = pd.read_csv(
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        low_memory=False
    )

    games = games[
        (games.season == SEASON) &
        (games.game_type == "REG") &
        games.home_score.notna() &
        games.away_score.notna()
    ].copy()

    sr = []

    for _, g in games.iterrows():
        sr += [
            {
                "week": int(g.week),
                "team": g.home_team,
                "points": float(g.home_score)
            },
            {
                "week": int(g.week),
                "team": g.away_team,
                "points": float(g.away_score)
            }
        ]

    scores = pd.DataFrame(sr)

    print("Completed games:", len(games))

    e = {}

    for abbr, tid in ESPN_IDS.items():

        u = (
            f"https://sports.core.api.espn.com/v2/sports/football/"
            f"leagues/nfl/seasons/{SEASON}/types/2/teams/{tid}/statistics"
        )

        try:
            r = requests.get(u, timeout=30)
            r.raise_for_status()

            f = {}
            collect(r.json(), f)

            e[abbr] = {
                "total_first_downs":
                    pick(f, ["firstDowns", "totalFirstDowns"]),
                "penalty_first_downs":
                    pick(f, ["firstDownsPenalty", "penaltyFirstDowns"]),
                "penalties":
                    pick(f, ["totalPenalties", "penalties"]),
                "penalty_yards":
                    pick(f, ["totalPenaltyYards", "penaltyYards"])
            }

        except Exception as exc:

            print("ESPN warning", abbr, exc)

            e[abbr] = {
                "total_first_downs": np.nan,
                "penalty_first_downs": np.nan,
                "penalties": np.nan,
                "penalty_yards": np.nan
            }

    espn = pd.DataFrame.from_dict(e, orient="index")

    p = f"/tmp/play_by_play_{SEASON}.parquet"

    u = (
        f"https://github.com/nflverse/nflverse-data/releases/download/"
        f"pbp/play_by_play_{SEASON}.parquet"
    )

    with requests.get(u, stream=True, timeout=180) as r:

        r.raise_for_status()

        with open(p, "wb") as f:

            for chunk in r.iter_content(1024 * 1024):

                if chunk:
                    f.write(chunk)

    cols = [
        "game_id","season_type","posteam","defteam",
        "fixed_drive","fixed_drive_result","interception",
        "fumble_lost","first_down_penalty","penalty_team",
        "penalty_yards"
    ]

    pbp = pd.read_parquet(p, columns=cols)

    pbp = pbp[
        pbp.season_type == "REG"
    ].copy()

    dr = (
        pbp
        .dropna(
            subset=[
                "game_id",
                "posteam",
                "defteam",
                "fixed_drive"
            ]
        )
        .sort_values(
            ["game_id", "fixed_drive"]
        )
        .groupby(
            [
                "game_id",
                "fixed_drive",
                "posteam",
                "defteam"
            ],
            as_index=False
        )
        .agg(
            fixed_drive_result=("fixed_drive_result", "last"),
            interception=("interception", "max"),
            fumble_lost=("fumble_lost", "max")
        )
    )

    dr["scored"] = dr.fixed_drive_result.isin(
        ["Touchdown", "Field goal"]
    )

    dr["turnover"] = (
        dr.interception.fillna(0).eq(1) |
        dr.fumble_lost.fillna(0).eq(1)
    )

    od = dr.groupby("posteam").agg(
        drives=("game_id", "size"),
        scores=("scored", "sum"),
        turnovers=("turnover", "sum")
    )

    od["sc_pct"] = 100 * od.scores / od.drives
    od["to_pct"] = 100 * od.turnovers / od.drives

    dd = dr.groupby("defteam").agg(
        drives=("game_id", "size"),
        scores=("scored", "sum"),
        turnovers=("turnover", "sum")
    )

    dd["sc_pct"] = 100 * dd.scores / dd.drives
    dd["to_pct"] = 100 * dd.turnovers / dd.drives

    pbp["first_down_penalty"] = pd.to_numeric(
        pbp["first_down_penalty"],
        errors="coerce"
    ).fillna(0)

    pbp["penalty_yards"] = pd.to_numeric(
        pbp["penalty_yards"],
        errors="coerce"
    ).fillna(0)

    opp_pen = pbp[
        pbp["posteam"].notna() &
        (pbp["penalty_team"] == pbp["posteam"])
    ].copy()

    def_pen = opp_pen.groupby("defteam").agg(
        penalties=("game_id", "size"),
        penalty_yards=("penalty_yards", "sum")
    )

    pen_first = (
        pbp[
            pbp["defteam"].notna() &
            (pbp["first_down_penalty"] == 1)
        ]
        .groupby("defteam")["first_down_penalty"]
        .sum()
    )

    fcols = [
        c for c in [
            "sack_fumbles_lost",
            "rushing_fumbles_lost",
            "receiving_fumbles_lost"
        ]
        if c in weekly.columns
    ]

    agg = {
        "completions":"sum",
        "attempts":"sum",
        "passing_yards":"sum",
        "passing_tds":"sum",
        "passing_interceptions":"sum",
        "sacks_suffered":"sum",
        "sack_yards_lost":"sum",
        "passing_first_downs":"sum",
        "carries":"sum",
        "rushing_yards":"sum",
        "rushing_tds":"sum",
        "rushing_first_downs":"sum"
    }

    for c in fcols:
        agg[c] = "sum"

    def derive(df, key, pts):

        x = df.groupby(key).agg(agg)

        x["G"] = df.groupby(key).size()

        x["PFPA"] = pts.reindex(x.index).fillna(0)

        if len(fcols) == 3:

            x["FL"] = x[fcols].sum(axis=1)
            x["TO"] = x.passing_interceptions + x.FL

        else:

            x["FL"] = np.nan
            x["TO"] = np.nan

        x["PASS_NET_YDS"] = (
            x.passing_yards -
            x.sack_yards_lost
        )

        x["YDS"] = (
            x.PASS_NET_YDS +
            x.rushing_yards
        )

        x["PLY"] = (
            x.attempts +
            x.sacks_suffered +
            x.carries
        )

        x["Y_P"] = (
            x.YDS /
            x.PLY
        )

        x["NY_A"] = (
            x.PASS_NET_YDS /
            (
                x.attempts +
                x.sacks_suffered
            )
        )

        x["RY_A"] = (
            x.rushing_yards /
            x.carries
        )

        return x

    pts = scores.groupby("team").points.sum()

    off = (
        derive(
            weekly,
            "team",
            pts
        )
        .join(
            espn,
            how="left"
        )
        .join(
            od[
                [
                    "sc_pct",
                    "to_pct"
                ]
            ],
            how="left"
        )
    )

    wd = weekly.copy()

    wd["defense_team"] = wd.opponent_team

    sl = (
        scores
        .set_index(
            [
                "week",
                "team"
            ]
        )
        .points
    )

    wd["opp_points"] = [
        sl.get(
            (
                int(w),
                t
            ),
            np.nan
        )
        for w, t
        in zip(
            wd.week,
            wd.team
        )
    ]

    dpts = (
        wd
        .groupby(
            "defense_team"
        )
        .opp_points
        .sum()
    )

    deff = (
        derive(
            wd,
            "defense_team",
            dpts
        )
        .join(
            dd[
                [
                    "sc_pct",
                    "to_pct"
                ]
            ],
            how="left"
        )
    )

    deff["penalty_first_downs"] = (
        pen_first
        .reindex(
            deff.index
        )
        .fillna(0)
    )

    deff["total_first_downs"] = (
        deff["passing_first_downs"] +
        deff["rushing_first_downs"] +
        deff["penalty_first_downs"]
    )

    deff["penalties"] = (
        def_pen["penalties"]
        .reindex(
            deff.index
        )
        .fillna(0)
    )

    deff["penalty_yards"] = (
        def_pen["penalty_yards"]
        .reindex(
            deff.index
        )
        .fillna(0)
    )

    check_cols = [
        "total_first_downs",
        "penalties",
        "penalty_yards",
        "penalty_first_downs"
    ]

    missing_counts = (
        deff[
            check_cols
        ]
        .isna()
        .sum()
    )

    if int(
        missing_counts.sum()
    ) != 0:

        raise RuntimeError(
            f"Missing defensive derived fields: "
            f"{missing_counts.to_dict()}"
        )

    off_rows = rows(off)

    def_rows = rows(
        deff,
        True
    )

    if not (
        len(off_rows) == 32 and
        len(def_rows) == 32 and
        len(
            set(
                r[1]
                for r
                in off_rows
            )
        ) == 32 and
        len(
            set(
                r[1]
                for r
                in def_rows
            )
        ) == 32
    ):

        raise RuntimeError(
            "32-team validation failed"
        )

    off_sum = summary(off_rows)

    def_sum = summary(def_rows)

    payload = {
        "secret": SHARED_SECRET,
        "spreadsheetId": SPREADSHEET_ID,
        "data": [
            {
                "range":
                    "Offense!B4:AC18",
                "values":
                    off_rows[:15]
            },
            {
                "range":
                    "Offense!B21:AC37",
                "values":
                    off_rows[15:]
            },
            {
                "range":
                    "Offense!B38:AC40",
                "values":
                    off_sum
            },
            {
                "range":
                    "Defense!B4:AC18",
                "values":
                    def_rows[:15]
            },
            {
                "range":
                    "Defense!B21:AC37",
                "values":
                    def_rows[15:]
            },
            {
                "range":
                    "Defense!B38:AC40",
                "values":
                    def_sum
            }
        ]
    }

    response = requests.post(
        WRITE_URL,
        json=json_safe(payload),
        timeout=90
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):

        raise RuntimeError(
            f"Apps Script write failed: "
            f"{result}"
        )

    print(
        "WRITE COMPLETE for season",
        SEASON
    )

if __name__ == "__main__":
    main()
