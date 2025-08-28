import os
import yaml
from datetime import datetime
from llm import LogAnalyzer

# Load config from openai-costs.yaml
with open("openai-costs.yaml", "r") as f:
    cost_config = yaml.safe_load(f)

# Load prompt and logs
with open("prompt.md", "r") as f:
    prompt_md = f.read()
with open("logs.md", "r") as f:
    logs_md = f.read()

# Compose config for LogAnalyzer
config = {
    "agent": {
        "name": "LogAI",
        "tag": "banking-logs",
        "model": "gpt-5-nano"
    },

    "system_prompt": prompt_md,
    "user_prompt": "Analyse the following logs:\n\n" + logs_md
}

# Get OpenAI API key from environment variable
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable not set.")

# Now create analyzer and run analysis
analyzer = LogAnalyzer(config, openai_api_key, debug=True)
system_prompt, user_prompt = analyzer.create_prompts(logs_md)
result, usage = analyzer.analyze_logs(system_prompt, user_prompt)

# Debug: Check what we got back
print(f"DEBUG: result type: {type(result)}, length: {len(result) if result else 0}")
print(f"DEBUG: usage type: {type(usage)}, value: {usage}")

# Generate report filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
model_name = config['agent']['model'].replace('/', '-').replace(':', '-')  # Sanitize model name for filename
report_filename = f"{model_name}-{timestamp}.md"

# Create full report content
if usage and isinstance(usage, dict):
    report_content = f"""# Log Analysis Report

**Model:** {usage.get('model', 'Unknown')}  
**Generated:** {usage.get('timestamp', 'Unknown')}  
**Cost:** ${usage.get('cost_usd') or 0:.4f}

## Analysis Result

{result}

## Usage Statistics

- **Model:** {usage.get('model', 'Unknown')}
- **Prompt tokens:** {usage.get('prompt_tokens', 0):,}
- **Completion tokens:** {usage.get('completion_tokens', 0):,}
- **Total tokens:** {usage.get('total_tokens', 0):,}
- **Response time:** {usage.get('response_time_seconds', 0)}s
- **Attempts:** {usage.get('attempts', 0)}
- **Cost:** ${usage.get('cost_usd') or 0:.4f}

## Cost Breakdown

- **Input tokens:** {usage.get('prompt_tokens', 0):,} × rate = ${(usage.get('prompt_tokens', 0) / 1_000_000) * 0.40:.4f}
- **Output tokens:** {usage.get('completion_tokens', 0):,} × rate = ${(usage.get('completion_tokens', 0) / 1_000_000) * 1.60:.4f}
- **Total cost:** ${usage.get('cost_usd') or 0:.4f}
"""
else:
    report_content = f"""# Log Analysis Report

**Model:** Unknown  
**Generated:** {datetime.now().isoformat()}  
**Cost:** $0.0000

## Analysis Result

{result}

## Usage Statistics

No usage statistics available.
"""

# Save report to file
with open(report_filename, 'w') as f:
    f.write(report_content)

print("=== ANALYSIS RESULT ===\n")
print(result)
print("\n=== USAGE STATISTICS ===\n")

if usage and isinstance(usage, dict):
    for key, value in usage.items():
        if key == 'cost_usd' and value is not None:
            print(f"{key}: ${value:.4f}")
        else:
            print(f"{key}: {value}")

    # Print cost breakdown if available
    if usage.get('cost_usd') is not None:
        print(f"\n=== COST BREAKDOWN ===")
        print(f"Input tokens: {usage.get('prompt_tokens', 0):,} × rate = ${(usage.get('prompt_tokens', 0) / 1_000_000) * 0.40:.4f}")
        print(f"Output tokens: {usage.get('completion_tokens', 0):,} × rate = ${(usage.get('completion_tokens', 0) / 1_000_000) * 1.60:.4f}")
        print(f"Total cost: ${usage.get('cost_usd') or 0:.4f}")
else:
    print("No usage statistics available.")

print(f"\nReport saved as: {report_filename}")
