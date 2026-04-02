import pandas as pd
import copy
import numpy as np

def detect_cell_issues(df):
    """
    Perform a granular scan of every cell to identify specific violations.
    Returns a list of dicts: {row, column, issue, value}
    """
    issues_list = []
    
    # Identify column types once for performance
    # Detect duplicate rows (by full row equality) and record as issues
    duplicate_rows = df.duplicated(keep=False)
    duplicate_indices = df[duplicate_rows].index.tolist()
    for dup_idx in duplicate_indices:
        issues_list.append({
            "row": int(dup_idx) + 1,
            "column": "*",
            "issue": "Duplicate",
            "value": "Row duplicate"
        })
    col_types = {}
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            col_types[col] = "Numeric"
        elif "email" in col.lower():
            col_types[col] = "Email"
        else:
            col_types[col] = "Text"

    # Iterate through rows
    for i, row in df.iterrows():
        # Limit scanning to first 1000 rows for performance on large files
        if i >= 1000: break 
        
        for col in df.columns:
            val = row[col]
            issue_type = None
            
            # 1. Missing / Empty Check
            if pd.isna(val) or str(val).strip() == "" or str(val).lower() == "nan":
                issue_type = "Missing"
                val_str = "NaN"
            
            # 2. Type Specific Checks
            else:
                c_type = col_types.get(col)
                if c_type == "Numeric":
                    try:
                        float(val)
                    except:
                        issue_type = "Invalid Number"
                elif c_type == "Email":
                    if "@" not in str(val) or "." not in str(val):
                        issue_type = "Invalid Email"
                
                val_str = str(val)

            if issue_type:
                issues_list.append({
                    "row": int(i) + 1,
                    "column": col,
                    "issue": issue_type,
                    "value": val_str
                })
    
    return issues_list

def analyze_data(df):
    """
    Advanced data profiling for the Ultra Data Cleaner.
    """
    analysis = {
        "total_rows": int(df.shape[0]),
        "total_cols": int(df.shape[1]),
        "columns": [],
        "risks": [],
        "health_score": 0,
        "cell_issues": detect_cell_issues(df)
    }
    
    total_cells = df.size
    total_missing = len([i for i in analysis["cell_issues"] if i["issue"] == "Missing"])
    total_dupes = len([i for i in analysis["cell_issues"] if i["issue"] == "Duplicate"])
    # Existing risk calculations remain unchanged
    total_missing = len([i for i in analysis["cell_issues"] if i["issue"] == "Missing"])
    total_dupes = int(df.duplicated().sum())
    
    for col in df.columns:
        col_missing = int(df[col].isna().sum())
        col_unique = int(df[col].nunique())
        
        # Suggested Fix Logic
        col_type = "Numeric" if pd.api.types.is_numeric_dtype(df[col]) else "Text"
        if "email" in col.lower(): col_type = "Email"
        
        suggested_fix = "Fill with Mean" if col_missing > 0 and col_type == "Numeric" else ("Trim Whitespace" if col_type == "Text" else "None")

        # Column-specific summary issues
        col_issues = [i for i in analysis["cell_issues"] if i["column"] == col]
        summary_issues = []
        if col_issues:
            types = set([i["issue"] for i in col_issues])
            for t in types:
                count = len([i for i in col_issues if i["issue"] == t])
                summary_issues.append({"type": t, "count": count})

        analysis["columns"].append({
            "name": col,
            "type": col_type,
            "missing": col_missing,
            "unique": col_unique,
            "suggested_fix": suggested_fix,
            "issues": summary_issues
        })

    # Risk Detection
    if total_missing > 0:
        missing_pct = (total_missing / total_cells) * 100 if total_cells > 0 else 0
        level = "high" if missing_pct > 20 else "medium"
        analysis["risks"].append({
            "level": level,
            "message": f"{total_missing} granular cell issues detected ({int(missing_pct)}% impact)"
        })
        
    if total_dupes > 0:
        analysis["risks"].append({
            "level": "medium",
            "message": f"{total_dupes} duplicate rows detected"
        })

    # Health Score
    score = 100
    if total_cells > 0:
        score -= (total_missing / total_cells) * 60
    score -= (total_dupes / len(df) * 40) if len(df) > 0 else 0
    analysis["health_score"] = max(0, int(score))
    
    return analysis
