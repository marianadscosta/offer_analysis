import pandas as pd


def aggregate(df: pd.DataFrame, group_fields: list[str], metrics: dict) -> pd.DataFrame:
    """
    Generic aggregation function.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    group_fields : list[str]
        Columns to group by.
    metrics : dict
        Dictionary of columns and aggregation functions. 
        Example: {"ride_count": "sum", "extensions_k": "sum"}

    Returns
    -------
    pd.DataFrame
        Aggregated dataframe.
    """
    missing = [col for col in metrics.keys() if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataframe: {missing}")

    return df.groupby(group_fields, as_index=False).agg(metrics)


def agg_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly rides and extensions per agency."""
    return aggregate(df, ["month", "agency_id"], {
        "ride_count": "sum",
        "extensions_k": "sum"
    })


def agg_daytype_monthly_avg(df: pd.DataFrame) -> pd.DataFrame:
    """Average rides per day_type per month and agency."""
    totals = aggregate(df, ["month", "agency_id", "day_type"], {
        "ride_count": "sum"
    })
    day_counts = df.groupby(["month", "agency_id", "day_type"], as_index=False).agg(
        n_days=("operational_date", "nunique")
    )
    merged = totals.merge(day_counts, on=["month", "agency_id", "day_type"])
    merged["avg_rides_per_day"] = merged["ride_count"] / merged["n_days"]
    return merged


def agg_daytype_pivot(df_daytype_month_avg: pd.DataFrame) -> pd.DataFrame:
    """Pivot table of avg rides per day_type by month."""
    return df_daytype_month_avg.pivot_table(
        index=["agency_id", "day_type"],
        columns="month",
        values="avg_rides_per_day",
        aggfunc="first"
    ).reset_index()


def agg_totals(df: pd.DataFrame) -> pd.DataFrame:
    """Total rides per agency (whole period)."""
    return aggregate(df, ["agency_id"], {
        "ride_count": "sum"
    }).rename(columns={"ride_count": "total_rides"})


def agg_daytype_total(df: pd.DataFrame) -> pd.DataFrame:
    """Average rides per day_type per agency (whole period)."""
    totals = df.groupby(["agency_id", "day_type"], as_index=False).agg(
        total_rides=("ride_count", "sum"),
        n_days=("operational_date", "nunique")
    )
    totals["avg_rides_per_day"] = totals["total_rides"] / totals["n_days"]
    return totals


def agg_daytype_date(df: pd.DataFrame) -> pd.DataFrame:
    """Daily breakdown by day_type."""
    return df.groupby(["operational_date", "agency_id", "day_type"], as_index=False).agg(
        rides=("ride_count", "sum")
    )


def agg_lineid_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Rides and extensions per line_id (whole period)."""
    return df.groupby(["agency_id", "line_id"], as_index=False).agg(
        total_rides=("ride_count", "sum"),
        total_extensions=("extension_sum", "sum")
    )
