import pandas as pd
import numpy as np

def clean_data(df, global_settings, column_settings):
    """
    Advanced data cleaning logic.
    - global_settings: dict { remove_duplicates: bool, trim_all: bool, fill_all: bool }
    - column_settings: dict { col_name: { fill: 'mean'|'mode'|'median'|'custom', custom_val: val, strip: bool, dropoutliers: bool } }
    """
    df_clean = df.copy()
    report = []
    
    # Pre-cleaning basic sanitizations to guarantee no internal server errors
    df_clean = df_clean.dropna(how='all')
    df_clean.columns = df_clean.columns.astype(str).str.strip()
    df_clean = df_clean.head(5000)
    
    # Strict datatype sanitization loop
    for col in df_clean.columns:
        try:
            df_clean[col] = pd.to_numeric(df_clean[col])
        except Exception:
            df_clean[col] = df_clean[col].astype(str)
    
    # 1. Global: Trim Whitespace (if requested globally or per column)
    if global_settings.get('trim_all'):
        cols_obj = df_clean.select_dtypes(['object']).columns
        for col in cols_obj:
            df_clean[col] = df_clean[col].astype(str).str.strip()
        report.append("Trimmed whitespace from all text columns.")
    else:
        for col, settings in column_settings.items():
            if settings.get('strip') and col in df_clean.columns:
                df_clean[col] = df_clean[col].astype(str).str.strip()
                report.append(f"Trimmed whitespace in '{col}'.")

    # 2. Global: Remove Duplicates
    if global_settings.get('remove_duplicates'):
        count = int(df_clean.duplicated().sum())
        df_clean = df_clean.drop_duplicates()
        report.append(f"Removed {count} duplicate row(s).")

    # 3. Column-Level: Handle Missing Values & Outliers
    for col, settings in column_settings.items():
        if col not in df_clean.columns: continue
        
        # Outlier Removal Safe IQR Calculation (User specified requirement)
        if settings.get('dropoutliers') and pd.api.types.is_numeric_dtype(df_clean[col]):
            try:
                q1 = df_clean[col].quantile(0.25)
                q3 = df_clean[col].quantile(0.75)
                iqr = q3 - q1
                count_before = len(df_clean)
                df_clean = df_clean[(df_clean[col] >= q1 - 1.5 * iqr) & (df_clean[col] <= q3 + 1.5 * iqr)]
                removed = count_before - len(df_clean)
                if removed > 0:
                    report.append(f"Removed {removed} outliers from '{col}' using IQR method.")
            except Exception:
                continue

        # Fill Missing
        fill_method = settings.get('fill')
        if fill_method and df_clean[col].isnull().any():
            if fill_method == 'mean' and pd.api.types.is_numeric_dtype(df_clean[col]):
                val = df_clean[col].mean()
                df_clean[col] = df_clean[col].fillna(val)
                report.append(f"Filled '{col}' missing values with Mean ({round(float(val), 2)}).")
            elif fill_method == 'median' and pd.api.types.is_numeric_dtype(df_clean[col]):
                val = df_clean[col].median()
                df_clean[col] = df_clean[col].fillna(val)
                report.append(f"Filled '{col}' missing values with Median ({round(float(val), 2)}).")
            elif fill_method == 'mode':
                modes = df_clean[col].mode()
                val = modes[0] if not modes.empty else "N/A"
                df_clean[col] = df_clean[col].fillna(val)
                report.append(f"Filled '{col}' missing values with Mode ({val}).")
            elif fill_method == 'custom':
                val = settings.get('custom_val', 'N/A')
                df_clean[col] = df_clean[col].fillna(val)
                report.append(f"Filled '{col}' missing values with custom value: {val}.")

    return df_clean, report
