from tools.data_cleaner import clean_data
from tools.data_insight import generate_insights
from tools.text_summary import summarize_text
from .llm import call_llm

def run_tasks(tasks, context, focus='business'):
    """the orchestrator that executes multiple tools and aggregates results."""
    results = {}
    
    # 1. Cleaning Task
    if "data_clean" in tasks:
        df = context.get("df")
        if df is not None:
            cleaned_df, report = clean_data(df, remove_duplicates=True, fill_missing=True)
            results["clean_report"] = report
            # Pass cleaned df to next tasks if any
            context["df"] = cleaned_df 
        else:
            results["clean_error"] = "No dataset found for cleaning."

    # 2. Insight Task
    if "data_insight" in tasks:
        df = context.get("df")
        if df is not None:
            # We pass a lambda for Groq summaries to keep tools decoupled
            get_ai_summary = lambda p: call_llm([{"role": "user", "content": p}])
            results["insights"] = generate_insights(df, focus=focus, get_ai_summary_fn=get_ai_summary)
        else:
            results["insight_error"] = "No dataset found for analysis."

    # 3. Summary Task
    if "text_summary" in tasks:
        source = context.get("text") or context.get("file_path")
        if source:
            get_ai_summary = lambda p: call_llm([{"role": "user", "content": p}])
            results["summary"] = summarize_text(source, get_ai_summary_fn=get_ai_summary)
        else:
            results["summary_error"] = "No text or document found to summarize."

    return results
