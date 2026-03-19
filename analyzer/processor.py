import pandas as pd
import re
import os
import sys
import warnings
import time

# Suppress harmless similarity warnings from small spacy models
warnings.filterwarnings("ignore", message=".*The model you're using has no word vectors loaded.*")

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

_groq_client = None

def _get_groq_client():
    """Lazily initialize the Groq client so env vars have time to be set."""
    global _groq_client
    if _groq_client is None and GROQ_AVAILABLE:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            try:
                _groq_client = groq.Groq(api_key=api_key)
            except Exception as e:
                print(f"Warning: Groq client not initialized ({e}).")
    return _groq_client

class DataProcessor:
    def __init__(self):
        self.groq_api_healthy = _get_groq_client() is not None

            
    def extract_skills(self, jobs: list[dict]) -> list[list[str]]:
        """Extract skills from a batch of jobs using Groq LLM (10 jobs at a time)."""
        all_skills = [[] for _ in range(len(jobs))]
        
        if not (self.groq_api_healthy and _get_groq_client()):
            return all_skills
            
        import json
        batch_size = 10
        client = _get_groq_client()
        
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i:i+batch_size]
            prompt_text = ""
            for idx, job in enumerate(batch):
                title = job.get('title', 'Unknown Role')
                company = job.get('company', 'Unknown')
                desc = job.get('description', '')
                if pd.isna(desc): desc = ""
                # Cap the description size heavily since context gets shared when batching
                short_text = desc[:1500] if len(desc) > 1500 else desc
                prompt_text += f"\n--- Job {idx} ---\nTitle: {title}\nCompany: {company}\nDescription: {short_text}\n"

            system_prompt = (
                "You are an expert technical data extraction tool. Your job is to extract technical skills, "
                "frameworks, and programming languages from the provided job descriptions.\n"
                "You must return ONLY a JSON object where the keys are the Job indices (e.g., \"0\", \"1\") "
                "and the values are arrays of strings representing the extracted tools. "
                "Do not include generic terms or soft skills, only specific technical tools like Python, AWS, React, SQL."
            )

            retry_count = 0
            max_retries = 3
            batch_success = False
            
            while retry_count < max_retries and not batch_success:
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt_text}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0,
                        max_tokens=1024
                    )
                    
                    llm_response = completion.choices[0].message.content
                    try:
                        parsed_json = json.loads(llm_response)
                        for idx_str, skills in parsed_json.items():
                            if idx_str.isdigit() and int(idx_str) < len(batch):
                                cleaned_for_job = []
                                if isinstance(skills, list):
                                    for s in skills:
                                        s_clean = str(s).strip().title()
                                        if len(s_clean) > 1:
                                            cleaned_for_job.append(s_clean)
                                    all_skills[i + int(idx_str)] = cleaned_for_job
                        batch_success = True
                    except json.JSONDecodeError:
                        print("Warning: Failed to parse Groq JSON response.")
                        break # Try next batch
                                
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "rate limit" in err_str:
                        print(f"\n[Groq API] Batch Rate Limit reached! Pausing for 60 seconds... (Attempt {retry_count + 1}/{max_retries})")
                        time.sleep(60)
                        retry_count += 1
                    else:
                        print(f"Groq API Error on batch {i//batch_size}: {e}")
                        break
                        
        return all_skills

    def extract_salary(self, text: str) -> dict:
        """Extract salary bounds from text using regex."""
        # This is a basic regex and might need refinement based on actual data
        # Looks for patterns like $100,000 - $150,000 or $100k-$150k
        
        salary_info = {
            "min_salary": None,
            "max_salary": None,
            "currency": "$",
            "period": "yearly"
        }
        
        if not text:
            return salary_info
            
        # Simplified regex for demo purposes
        # match $100k
        k_pattern = re.search(r'\$?(\d+)[kK]\s*-\s*\$?(\d+)[kK]', text)
        if k_pattern:
            salary_info["min_salary"] = int(k_pattern.group(1)) * 1000
            salary_info["max_salary"] = int(k_pattern.group(2)) * 1000
            if "hour" in text.lower() or "/hr" in text.lower():
                salary_info["period"] = "hourly"
            return salary_info
            
        # match $100,000
        full_pattern = re.search(r'\$?(\d{2,3}(?:,\d{3})+)\s*-\s*\$?(\d{2,3}(?:,\d{3})+)', text)
        if full_pattern:
            min_val = int(full_pattern.group(1).replace(',', ''))
            max_val = int(full_pattern.group(2).replace(',', ''))
            salary_info["min_salary"] = min_val
            salary_info["max_salary"] = max_val
            
            # Very basic heuristic for period
            if min_val < 500:
                salary_info["period"] = "hourly"
            return salary_info
            
        return salary_info

    def clean_and_normalize(self, jobs_data: list[dict]) -> pd.DataFrame:
        """Convert raw scraped jobs into a cleaned pandas DataFrame."""
        if not jobs_data:
            return pd.DataFrame()
            
        df = pd.DataFrame(jobs_data)
        
        # Extract skills (Batched extraction)
        # We pass the raw dict records so the extractor has access to title, company, and description
        df['skills'] = self.extract_skills(jobs_data)
        
        # Extract salary if not already provided cleanly
        if 'salary_raw' in df.columns:
            # Combine raw salary and description for better extraction
            text_for_salary = df['salary_raw'].fillna('') + " " + df['description'].fillna('')
            extracted_salaries = text_for_salary.apply(self.extract_salary)
        else:
            extracted_salaries = df['description'].fillna('').apply(self.extract_salary)
            
        df['min_salary'] = extracted_salaries.apply(lambda x: x['min_salary'])
        df['max_salary'] = extracted_salaries.apply(lambda x: x['max_salary'])
        df['salary_period'] = extracted_salaries.apply(lambda x: x['period'])
        
        # Calculate average salary for easier plotting
        df['avg_salary'] = df[['min_salary', 'max_salary']].mean(axis=1)
        
        # Clean company and title
        df['company'] = df['company'].str.strip()
        df['title'] = df['title'].str.strip()
        
        return df

if __name__ == "__main__":
    # Test
    processor = DataProcessor()
    sample_job = {
        "title": "Software Engineer", 
        "company": "Tech Corp", 
        "description": "We are looking for a Python and React developer. Salary: $120k - $150k per year. Must know SQL and Docker."
    }
    print("Skills:", processor.extract_skills([sample_job]))
    print("Salary:", processor.extract_salary(sample_job['description']))
