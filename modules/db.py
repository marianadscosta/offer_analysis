from pymongo import MongoClient
import pandas as pd
import config


def load_data(start_date: str, end_date: str, line_ids: list[int] = None) -> pd.DataFrame:
    """
    Query MongoDB and return rides dataframe.

    Parameters
    ----------
    start_date : str (YYYYMMDD)
    end_date : str (YYYYMMDD)
    line_ids : list[int]
        Optional list of line_ids to filter.

    Returns
    -------
    pd.DataFrame
    """
    client = MongoClient(config.MONGO_URI)
    db = client[config.DB_NAME]
    collection = db[config.COLLECTION_NAME]

    match_stage = {
        "operational_date": {"$gte": start_date, "$lte": end_date}
    }
    if line_ids:
        match_stage["line_id"] = {"$in": line_ids}

    pipeline = [
        {"$match": match_stage},
        {
            "$group": {
                "_id": {
                    "operational_date": "$operational_date",
                    "agency_id": "$agency_id",
                    "line_id": "$line_id",
                    "hour": { "$hour": { "$toDate": "$start_time_scheduled" } },
                },
                "ride_count": {"$sum": 1},
                "extension_sum": {"$sum": "$extension_scheduled"},
            }
        },
        {"$sort": {"_id.operational_date": 1, "_id.agency_id": 1, "_id.line_id": 1, "_id.hour": 1}},
    ]

    results = list(collection.aggregate(pipeline))
    df = pd.DataFrame(results)
    
    
# Flatten _id fields
    df["operational_date"] = df["_id"].apply(lambda x: x["operational_date"])
    df["agency_id"] = df["_id"].apply(lambda x: x["agency_id"])
    df["line_id"] = df["_id"].apply(lambda x: x.get("line_id"))
    df["hour"] = df["_id"].apply(lambda x: x["hour"]) 
    df = df.drop(columns=["_id"])

    df.loc[(df["hour"] >= 4) & (df["hour"] < 6), "period_of_day"] = "4-6"
    df.loc[(df["hour"] >= 6) & (df["hour"] < 9), "period_of_day"] = "6-9"
    df.loc[(df["hour"] >= 9) & (df["hour"] < 13), "period_of_day"] = "9-13"
    df.loc[(df["hour"] >= 14) & (df["hour"] < 17), "period_of_day"] = "14-17"
    df.loc[(df["hour"] >= 17) & (df["hour"] < 20), "period_of_day"] = "17-20"
    df.loc[(df["hour"] >= 20) & (df["hour"] < 0), "period_of_day"] = "20-0"
    df.loc[(df["hour"] >= 0) & (df["hour"] < 4), "period_of_day"] = "0-4"
    
    return df

