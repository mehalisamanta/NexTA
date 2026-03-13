import json
from backend.resume_analysis import ResumeAnalyzer

# Mock OpenAI client (replace with your real client if needed)
class MockClient:
    def __init__(self):
        pass

def mock_create_openai_completion(client, messages, model, temperature, max_tokens):
    """
    Mock AI response for testing.
    """
    # Example: resume missing email
    return type("Resp", (), {"choices": [type("C", (), {"message": type("M", (), {"content": json.dumps({
        "is_previous_employee": False,
        "nexturn_history_details": "None",
        "career_gaps": ["Gap between Jan 2020 - Aug 2020"],
        "technical_anomalies": ["Claimed 5 years experience in a 3-year-old tech"],
        "fake_indicators": ["Overlapping job dates in 2018"],
        "domain_knowledge": ["Python", "Data Science"],
        "missing_contact_info": ["email"],
        "summary": "Candidate has minor gaps and anomalies; missing email"
    })})})]})()

# Monkey patch your backend client call
import backend.resume_analysis as ra
ra.create_openai_completion = mock_create_openai_completion

# Initialize analyzer
analyzer = ResumeAnalyzer(client=MockClient())

# Test resume text
resume_text = """
John Doe
Phone: +1 234 567 8901
Experience:
Software Engineer at XYZ Corp (2015-2018)
Data Scientist at ABC Inc (2018-2022)
"""

# Run analysis
result = analyzer.analyze_resume(resume_text)
print("=== ANALYSIS RESULT ===")
print(json.dumps(result, indent=4))

# Optional: simple console rendering (instead of Streamlit)
def simple_render(analysis):
    def print_green(label, msg):
        print(f"[OK] {label}: {msg}")

    def print_yellow(label, items):
        print(f"[WARN] {label}:")
        for i, item in enumerate(items, 1):
            print(f"  {i}. {item}")

    # Work history
    if analysis.get("career_gaps"):
        print_yellow("Gaps in work history", analysis["career_gaps"])
    else:
        print_green("Work history", "No major gaps found")

    # Technical anomalies
    if analysis.get("technical_anomalies"):
        print_yellow("Things to double-check", analysis["technical_anomalies"])
    else:
        print_green("Experience details", "Everything looks consistent")

    # Fake indicators
    if analysis.get("fake_indicators"):
        print_yellow("Points that need a closer look", analysis["fake_indicators"])

    # Missing contact info
    missing_contact = analysis.get("missing_contact_info", [])
    if missing_contact:
        print_yellow("Missing Contact Information", missing_contact)
    else:
        print_green("Contact Information", "Phone number and email are present")

# Render in console
print("\n=== SIMPLE RENDER ===")
simple_render(result)