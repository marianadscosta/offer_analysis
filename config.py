# -------------------------
# Parameters & Paths
# -------------------------

START_DATE = "20240101"
END_DATE = "20250930"

DAYTYPE_FILE = "daytypes.csv"  # CSV: date, day_type

OUTPUT_EXCEL = "output.xlsx"
OUTPUT_PLOT_RIDES = "rides.png"
OUTPUT_PLOT_EXTENSIONS = "extensions.png"
OUTPUT_PLOT_DAYTYPE = "daytype_bar.png"

LINE_IDS = [
    3536, 3641, 4632, 3215, 3549, 3210, 3222, 3642, 3217, 3544,
    3203, 4730, 4642, 3625, 3635, 3205, 3626, 3206, 3218, 3213,
    3540, 3590, 3220, 3547, 3201, 3721, 3535, 3640, 3208, 3542,
    3209, 3543, 3204, 3605, 3216, 3223, 4643, 3650, 3211, 3545,
    3212, 3546, 3207, 3107, 4641, 3620, 3541, 3720, 3214, 3221,
    3548, 3202
]

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "your_db"
COLLECTION_NAME = "your_collection"
