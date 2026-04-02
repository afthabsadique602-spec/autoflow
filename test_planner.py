import sys
import os
# Add the project root to sys.path
sys.path.append(os.getcwd())

from ai_engine.planner import plan_tasks

print("Testing 'Clean and Analyze'...")
res = plan_tasks("Clean my data and give me insights")
print(f"Detected Tasks: {res.get('tasks')}")
print(f"Explanation: {res.get('explanation')}")

if "data_clean" in res['tasks'] and "data_insight" in res['tasks']:
    print("SUCCESS: Multi-tasking detected.")
else:
    print("FAILURE: Only part of the task detected.")
