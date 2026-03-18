"""
utils/scoring.py
Candidate scoring utilities.

"""

import pandas as pd
from config.settings import COLUMN_DISPLAY_NAMES


def format_dataframe_for_display(df: pd.DataFrame, columns_to_display: list) -> pd.DataFrame:
    """
    Return a display-ready copy of df with only the requested columns,
    renamed using the COLUMN_DISPLAY_NAMES mapping from config/settings.py.
    """
    available = [c for c in columns_to_display if c in df.columns]
    display_df = df[available].copy()
    display_df = display_df.rename(columns=COLUMN_DISPLAY_NAMES)
    return display_df