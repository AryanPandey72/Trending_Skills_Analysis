import asyncio
import json
import os

try:
    import groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

class AmbitionBoxScraper:
    def __init__(self, groq_api_key: str = None):
        self.base_url = "https://www.ambitionbox.com/salaries"
        self.groq_client = None
        
        key = groq_api_key or os.environ.get("GROQ_API_KEY")
        if key and GROQ_AVAILABLE:
            try:
                self.groq_client = groq.Groq(api_key=key)
            except Exception as e:
                print(f"Groq init error: {e}")

    async def get_salaries_batch(self, job_title: str, companies: list) -> dict:
        """Fetch average salary data for multiple companies using LLM estimation."""
        results = {}
        if not companies:
            return results
            
        valid_companies = [c for c in companies if c and c.lower() != "unknown"]
        if not valid_companies:
            return results
        
        if self.groq_client:
            system_prompt = (
                "You are an expert compensation analyst. "
                "Estimate the average yearly salary in INR for the given role at the listed companies. "
                "Return ONLY a valid JSON object mapping the exact company name provided to the integer salary value. "
                "Do not use thousands separators in the integer. Provide realistic estimates based on market data."
            )
            prompt_text = f"Role: {job_title}. Companies: {', '.join(valid_companies)}"
            
            try:
                completion = await asyncio.to_thread(
                    self.groq_client.chat.completions.create,
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_text}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0
                )
                
                response_content = completion.choices[0].message.content
                parsed_json = json.loads(response_content)
                
                for comp, sal in parsed_json.items():
                    if isinstance(sal, (int, float)):
                        results[comp] = int(sal)
                        
            except Exception as e:
                print(f"Salary AI Estimation Error: {e}")
                
        return results

async def test_scraper():
    scraper = AmbitionBoxScraper()
    sals = await scraper.get_salaries_batch("Data Scientist", ["TCS", "Google", "Amazon"])
    print(sals)

if __name__ == "__main__":
    asyncio.run(test_scraper())
