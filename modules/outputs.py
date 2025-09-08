import pandas as pd


def save_to_excel(path: str, sheets: dict[str, pd.DataFrame]) -> None:
    """
    Save multiple dataframes to Excel file with nice formatting.

    Parameters
    ----------
    path : str
        Output Excel path.
    sheets : dict
        {sheet_name: dataframe}
    """
    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)

            # Formatting
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)  # freeze header row
            worksheet.set_column(0, len(df.columns) - 1, 15)

    print(f"✅ Excel saved to {path}")
