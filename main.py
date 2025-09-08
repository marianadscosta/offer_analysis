import config
from modules import  db, preprocessing, aggregations as agg, plots, outputs

def main():
    # -------------------------
    # Load raw data from Mongo
    # -------------------------
    df = db.load_data(
        start_date=config.START_DATE,
        end_date=config.END_DATE,
        line_ids=config.LINE_IDS
    )

    # -------------------------
    # Preprocess & join with daytypes
    # -------------------------
    df = preprocessing.prepare(df, config.DAYTYPE_FILE)

    # -------------------------
    # Aggregations
    # -------------------------
    df_monthly = agg.agg_monthly_summary(df)
    df_daytype_month_avg = agg.agg_daytype_monthly_avg(df)
    df_daytype_pivot = agg.agg_daytype_pivot(df_daytype_month_avg)
    df_totals = agg.agg_totals(df)
    df_daytype_total = agg.agg_daytype_total(df)
    df_daytype_date = agg.agg_daytype_date(df)
    df_lineid = agg.agg_lineid_summary(df)

    # -------------------------
    # Save Excel
    # -------------------------
    outputs.save_to_excel(
        config.OUTPUT_EXCEL,
        {
            "Daytype Averages Monthly": df_daytype_month_avg,
            "Daytype Averages Pivot": df_daytype_pivot,
            "Daytype Averages Total": df_daytype_total,
            "Daytype by Date": df_daytype_date,
            "Monthly Summary": df_monthly,
            "Totals": df_totals,
            "Rides per LineID": df_lineid,
        }
    )

    # -------------------------
    # Plots
    # -------------------------
    plots.plot_monthly_rides(df_monthly, config.OUTPUT_PLOT_RIDES)
    plots.plot_monthly_extensions(df_monthly, config.OUTPUT_PLOT_EXTENSIONS)
    plots.plot_daytype_bar(df_daytype_month_avg, config.OUTPUT_PLOT_DAYTYPE)

    print("✅ Analysis complete!")


if __name__ == "__main__":
    main()
