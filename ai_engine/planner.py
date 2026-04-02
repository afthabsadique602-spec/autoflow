import json
import re
from .llm import call_llm
from .prompts import get_planner_prompt

def plan_tasks(user_input):
    """Parses user input into a JSON task list with robust extraction."""
    messages = get_planner_prompt(user_input)
    response = call_llm(messages, temp=0.1)
    
    # 1. Try Precise Extraction (Handle Markdown or extra text)
    try:
        # Extract the JSON block if wrapped in backticks
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            clean_json = match.group(0)
            return json.loads(clean_json)
        return json.loads(response)
    except:
        # 2. Additive Fallback Logic (detect ALL tasks in input)
        tasks = []
        explanation = "Detected intent: "
        
        low_input = user_input.lower()
        if any(word in low_input for word in ["clean", "fix", "duplicate", "missing"]):
            tasks.append("data_clean")
            explanation += "Cleaning, "
        if any(word in low_input for word in ["insight", "analyze", "trend", "report", "stats"]):
            tasks.append("data_insight")
            explanation += "Data Insight, "
        if any(word in low_input for word in ["summarize", "text", "document"]):
            tasks.append("text_summary")
            explanation += "Text Summary, "
            
        if not tasks:
            return {"tasks": [], "explanation": "Could not understand specific tasks."}
            
        return {
            "tasks": tasks, 
            "focus": "business" if "business" in low_input else "trends",
            "explanation": explanation.strip(", ")
        }
