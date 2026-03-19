import pandas as pd
from analyzer.processor import DataProcessor
from analyzer.metrics import MetricsAnalyzer

def test_pipeline():
    print("Testing Pipeline...")
    dummy_data = [
        {"platform": "LinkedIn", "title": "Data Scientist", "company": "Tech Corp", "description": "Need Python, SQL, and Pandas. Salary is $120k - $150k.", "salary_raw": ""},
        {"platform": "Indeed", "title": "Data Analyst", "company": "Data Inc", "description": "Looking for SQL, Tableau, and a bit of Python.", "salary_raw": "$90,000 - $110,000"},
        {"platform": "LinkedIn", "title": "Senior DS", "company": "AI Space", "description": "Expert in Python, PyTorch, Deep Learning, and SQL.", "salary_raw": ""},
    ]
    
    processor = DataProcessor()
    df = processor.clean_and_normalize(dummy_data)
    
    print("--- Cleaned DataFrame ---")
    print(df[['title', 'skills', 'avg_salary']])
    
    analyzer = MetricsAnalyzer(df)
    
    print("\n--- Top Skills ---")
    print(analyzer.get_most_demanded_skills(5))
    
    print("\n--- Co-occurrence ---")
    print(analyzer.get_skill_cooccurrence(5))
    
    print("\n--- Salary vs Skills ---")
    print(analyzer.get_salary_vs_skills())
    
test_pipeline()
