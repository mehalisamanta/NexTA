import os
import sys

# Ensure the project root is in the path so 'backend' can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.ppt_generator import generate_candidate_ppt

candidate_data = {
    # Slide 1: Profile
    "FULL_NAME": "John Michael Doe",
    "CURRENT_ROLE": "Senior Data Engineer & Cloud Architect",
    "PROFESSIONAL_SUMMARY": (
        "Versatile Data Engineer with over 8 years of experience in architecting "
        "large-scale data systems. Expert in AWS ecosystem, real-time stream processing, "
        "and optimizing multi-terabyte data warehouses for Fortune 500 clients."
    ),
    "EDUCATION_DETAILS": "Master of Science in Data Science - Stanford University (2017)\nB.Tech in CS - IIT Delhi (2015)",
    "TECHNICAL_SKILLS": "Python, PySpark, AWS (Glue, Lambda, Redshift), Kafka, Snowflake, Airflow, Terraform, Docker",

    # Slide 2: Project 1
    "PROJECT1_NAME": "Global Data Lake Migration",
    "DURATION_PROJECT1": "Jan 2022 – Present",
    "ROLE_PROJECT1": "Principal Architect",
    "Project1_Description": "Leading the migration of 500TB of on-premise Hadoop data to a centralized AWS S3 Data Lake.",
    "project1_bullets": [
        "Architected serverless ETL framework using AWS Glue and Step Functions",
        "Implemented Delta Lake for ACID transactions on S3",
        "Reduced annual infrastructure costs by $1.2M",
        "Established CI/CD pipelines for data infrastructure using Terraform"
    ],

    # Slide 3: Project 2
    "PROJECT2_NAME": "High-Frequency Trading Pipeline",
    "DURATION_PROJECT2": "Mar 2020 – Dec 2021",
    "ROLE_PROJECT2": "Senior Data Engineer",
    "Project2_Description": "Developed a low-latency streaming platform for real-time transaction analysis.",
    "project2_bullets": [
        "Built Kafka-Streams application processing 1M events per second",
        "Integrated Kinesis Firehose for cold storage archival",
        "Achieved sub-50ms end-to-end latency for fraud triggers"
    ],

    # Slide 4: Project 3
    "PROJECT3_NAME": "Healthcare Analytics Platform",
    "DURATION_PROJECT3": "June 2018 – Feb 2020",
    "ROLE_PROJECT3": "Data Engineer",
    "Project3_Description": "Centralized patient record system across 50+ hospital branches for predictive diagnostics.",
    "project3_bullets": [
        "Normalized heterogeneous data sources into a unified FHIR format",
        "Developed Airflow DAGs for daily batch synchronization",
        "Supported data scientists in deploying HIPAA-compliant ML models"
    ],

    # Slide 5: Project 4 (Testing Long Text & Auto-fit)
    "PROJECT4_NAME": "Legacy ERP Optimization Project",
    "DURATION_PROJECT4": "Aug 2017 – May 2018",
    "ROLE_PROJECT4": "Junior Data Engineer",
    "Project4_Description": (
        "This project involved a massive overhaul of an aging ERP system. It required "
        "extensive manual mapping of ancient database schemas to modern relational "
        "structures to ensure zero data loss during the transition to the cloud."
    ),
    "project4_bullets": [
        "Reverse-engineered undocumented SQL Server stored procedures",
        "Wrote 200+ Python scripts for automated data cleaning and deduplication",
        "Improved query response times by 80% through index optimization",
        "Collaborated with cross-functional teams to define data governance policies",
        "Created comprehensive technical documentation for the new schema architecture"
    ]
}

def main():
    print("⏳ Generating Extended PPT...")
    try:
        ppt_bytes = generate_candidate_ppt(candidate_data)
        
        if ppt_bytes:
            output_path = "test_candidate_output_full.pptx"
            with open(output_path, "wb") as f:
                f.write(ppt_bytes)
            print(f"✅ Success! File saved as: {output_path}")
        else:
            print("❌ The function returned None/Empty.")
            
    except Exception as e:
        print(f"❌ CRASHED with error: {e}")
        import traceback
        traceback.print_exc() # This will show exactly which line in backend failed
if __name__ == "__main__":
    main()