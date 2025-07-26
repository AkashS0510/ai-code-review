from models.models import Results
from langchain_openai import AzureChatOpenAI
import os
import json

llm = AzureChatOpenAI(
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    temperature=0,
).with_structured_output(Results)




def ai_code_review(input_data: dict) -> dict:
    """
    Analyze the PR and code based on the provided criteria.

    Args:
        input_data (dict): Input data containing PR details and code files.

    Returns:
        dict: Structured results of the code review.
    """
    if not input_data.get("code_changes"):
        raise ValueError("No code_changes found in the input data.")

    # Prepare the prompt with the input data
    prompt = f"""
You are an expert Pull request Reviewer. Analyze the PR and code based on the following criteria:

- Code style and formatting issues
- Potential bugs or errors  
- Performance improvements
- Best practices

Make sure to analyze and look into all the files in the PR and include the review results of all files in the output.

For each file, identify specific issues with line numbers (if available from the diff) and provide concrete suggestions.

PR Information:
Title: {input_data.get('pr_info', {}).get('title', 'N/A')}
Description: {input_data.get('pr_info', {}).get('description', 'N/A')}

Files to review: {len(input_data.get('code_changes', []))} files

Code Changes:
{json.dumps(input_data.get('code_changes', []), indent=2)}

Return the results in the following structured format:
- files: array of file objects with name and issues
- summary: object with total_files, total_issues(MAKE SURE YOU COUNT IT PROPERLY OR ELSE WILL BE PUNISHED SEVERELY), and critical_issues counts

Each issue should have:
- type: "bug", "style", "performance", "security", or "best_practice"
- line: line number (if identifiable from diff)
- description: clear description of the issue
- suggestion: actionable suggestion to fix the issue

Consider "bug" and "security" issues as critical.
"""

    # Invoke the LLM with the prepared prompt
    result = llm.invoke(
        [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "Please analyze this PR and provide a comprehensive code review in the specified format.",
            },
        ]
    )

    final_result = result.model_dump()

    final_result["summary"] = {
        "total_files": len(result.files),
        "total_issues": sum(len(file.issues) for file in result.files),
        "critical_issues": sum(
            1
            for file in result.files
            for issue in file.issues
            if issue.type in ["bug", "security"]
        ),
    }
    return final_result
