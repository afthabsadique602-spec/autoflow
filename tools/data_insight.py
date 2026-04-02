import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import time
import pandas as pd
import numpy as np
import re
from collections import Counter

def generate_insights(df, get_ai_summary_fn=None):
    """Unified Smart Analysis Engine - Combines stats, quality, and AI insights."""
    try:
        # 1. Performance Optimization - Sampling for large datasets
        orig_rows = len(df)
        is_sampled = False
        if orig_rows > 5000:
            df_analysis = df.sample(5000, random_state=42).copy()
            is_sampled = True
        else:
            df_analysis = df.copy()
        
        # 2. Data Cleaning for Analysis
        df_analysis = df_analysis.dropna(how='all')
        df_analysis.columns = df_analysis.columns.astype(str).str.strip()
        
        # 3. Column Classification
        numeric_cols = df_analysis.select_dtypes(include=['number', 'float', 'int']).columns.tolist()
        categorical_cols = df_analysis.select_dtypes(include=['object', 'string', 'category']).columns.tolist()
        
        # Attempt to detect datetime columns
        datetime_cols = []
        for col in categorical_cols:
            try:
                if df_analysis[col].nunique() > 1: # Avoid constants
                    potential_dates = pd.to_datetime(df_analysis[col], errors='coerce')
                    if potential_dates.notnull().mean() > 0.8: # If 80% looks like dates
                        datetime_cols.append(col)
            except:
                pass

        # 4. Advanced Red Flags (Severity Levels)
        red_flags = []
        
        # Missing Values
        missing_pct = (df_analysis.isnull().sum().sum() / (df_analysis.size)) * 100 if df_analysis.size > 0 else 0
        if missing_pct > 40:
            red_flags.append({"msg": f"🔴 Critical: {missing_pct:.1f}% Data Missing", "severity": "critical"})
        elif missing_pct > 10:
            red_flags.append({"msg": f"🟡 Moderate: {missing_pct:.1f}% Data Missing", "severity": "moderate"})

        # Duplicates
        dupe_count = int(df_analysis.duplicated().sum())
        if dupe_count > 0:
            red_flags.append({"msg": f"🟡 {dupe_count} Duplicates Found", "severity": "moderate"})

        # 5. Core Statistics & Key Patterns
        insights = []
        overview = ""
        if numeric_cols:
            primary = numeric_cols[0]
            avg = df_analysis[primary].mean()
            overview = f"Strategic focus on '{primary}' reveals a baseline average of {avg:,.2f}. "
            
            # Trend Check (if dates)
            if datetime_cols:
                dt_col = datetime_cols[0]
                temp_df = df_analysis.copy()
                temp_df[dt_col] = pd.to_datetime(temp_df[dt_col], errors='coerce')
                temp_df = temp_df.sort_values(dt_col)
                # Check for growth/decline
                first_half = temp_df[primary].iloc[:len(temp_df)//2].mean()
                second_half = temp_df[primary].iloc[len(temp_df)//2:].mean()
                diff = ((second_half - first_half) / first_half) * 100 if first_half != 0 else 0
                if diff > 5:
                    insights.append(f"Growth Pattern: Values in '{primary}' increased by {diff:.1f}% over the analyzed timeline.")
                elif diff < -5:
                    insights.append(f"Decline Pattern: Values in '{primary}' dropped by {abs(diff):.1f}% recently.")
        else:
            overview = "Dataset consists primarily of categorical attributes. "

        # Categorical patterns
        for col in categorical_cols[:2]:
            if not df_analysis[col].empty:
                top = df_analysis[col].value_counts().idxmax()
                insights.append(f"Concentration: Segment '{top}' is the dominant category in '{col}'.")

        # 6. Hybrid Column Explorer (Pre-calculated for speed)
        col_explorer = []
        for col in df_analysis.columns:
            stats = {"name": col, "type": str(df_analysis[col].dtype), "missing": int(df_analysis[col].isnull().sum()), "unique": int(df_analysis[col].nunique())}
            if col in numeric_cols:
                stats.update({
                    "mean": f"{df_analysis[col].mean():.2f}",
                    "median": f"{df_analysis[col].median():.2f}",
                    "min": f"{df_analysis[col].min()}",
                    "max": f"{df_analysis[col].max()}",
                    "std": f"{df_analysis[col].std():.2f}"
                })
            else:
                top_v = df_analysis[col].value_counts().head(5).to_dict()
                stats["top_values"] = [{"label": str(k), "count": int(v)} for k,v in top_v.items()]
            col_explorer.append(stats)

        # 7. Visualization Synthesis
        charts = []
        if numeric_cols:
             charts.append(generate_custom_chart(df_analysis, numeric_cols[0], 'histogram'))
             if len(numeric_cols) > 1:
                charts.append(generate_custom_chart(df_analysis, numeric_cols[1], 'box'))
        elif categorical_cols:
             charts.append(generate_custom_chart(df_analysis, categorical_cols[0], 'pie'))

        # Correlations
        if len(numeric_cols) > 1:
            try:
                corr_matrix = df_analysis[numeric_cols].corr()
                sol = (corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
                      .stack()
                      .sort_values(ascending=False))
                if not sol.empty and sol.iloc[0] > 0.7:
                    c1, c2 = sol.index[0]
                    insights.append(f"Strong Correlation: '{c1}' and '{c2}' are highly linked ({sol.iloc[0]:.2f}).")
            except: pass

        # 8. AI Prompt Construction
        insights_md = f"### Executive Strategy\n{overview}\n\n"
        insights_md += "#### Key Patterns\n" + "\n".join([f"- {i}" for i in insights]) if insights else "#### Patterns\n- Standard distribution observed."
        
        # 9. Return Unified Payload
        return {
            "success": True,
            "stats": {"rows": orig_rows, "cols": len(df_analysis.columns), "sampled": is_sampled},
            "red_flags": red_flags,
            "insights_md": insights_md,
            "insights_list": insights,
            "column_details": col_explorer,
            "charts": charts,
            "preview": df_analysis.head(50).fillna("").astype(str).to_dict(orient="records"),
            "numeric_cols": numeric_cols,
            "categorical_cols": categorical_cols,
            "columns": df_analysis.columns.tolist()
        }
    except Exception as e:
        print(f"[ENGINE FAIL] {e}")
        return {
            "success": False,
            "error": str(e),
            "insights_md": "### ⚠️ Analysis Critical Error\nThe engine encountered a structural failure while processing this dataset.",
            "stats": {"rows": 0, "cols": 0},
            "red_flags": [{"msg": f"CRITICAL: {str(e)}", "severity": "critical"}],
            "charts": [],
            "preview": [],
            "columns": []
        }

def generate_custom_chart(df, col, chart_type='bar'):
    """Improved intelligent charting."""
    try:
        plt.figure(figsize=(10, 6))
        plt.style.use('dark_background')
        ax = plt.gca()
        ax.set_facecolor('#0f172a')
        plt.gcf().set_facecolor('#0f172a')
        
        if chart_type == 'histogram':
            plt.hist(df[col].dropna(), bins=20, color='#38bdf8', edgecolor='#0f172a', alpha=0.8)
            plt.ylabel("Frequency", color='#94a3b8')
        elif chart_type == 'box':
            plt.boxplot(df[col].dropna(), vert=False, patch_artist=True, 
                        boxprops=dict(facecolor='#818cf8', color='#818cf8'),
                        medianprops=dict(color='white'))
        elif chart_type == 'pie':
            df[col].value_counts().head(5).plot(kind='pie', autopct='%1.1f%%', colors=['#38bdf8', '#818cf8', '#2dd4bf', '#fb7185', '#f59e0b'])
            plt.ylabel("")
        else: # Bar
            df[col].value_counts().head(10).plot(kind='bar', color='#818cf8', alpha=0.9)
            plt.ylabel("Count", color='#94a3b8')
            plt.xticks(rotation=45, ha='right')

        plt.title(f"{col} Analysis", color='white', pad=20, fontsize=14, fontweight='bold')
        plt.grid(axis='y', linestyle='--', alpha=0.1)
        
        os.makedirs("static/charts", exist_ok=True)
        path = f"static/charts/insight_{int(time.time()*1000)}_{col.replace(' ', '_')}.png"
        plt.savefig(path, transparent=True, bbox_inches='tight')
        plt.close()
        return "/"+path
    except:
        return ""
