import pandas as pd
import itertools
from collections import Counter

class MetricsAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        
    def get_most_demanded_skills(self, top_n: int = 20) -> pd.DataFrame:
        """Calculate the most frequently mentioned skills/tools."""
        if self.df.empty or 'skills' not in self.df.columns:
            return pd.DataFrame()
            
        all_skills = list(itertools.chain.from_iterable(self.df['skills']))
        skill_counts = Counter(all_skills)
        
        top_skills = skill_counts.most_common(top_n)
        res_df = pd.DataFrame(top_skills, columns=['Skill', 'Count'])
        return res_df

    def get_skill_cooccurrence(self, top_n: int = 15) -> pd.DataFrame:
        """Calculate which skills appear together most often."""
        if self.df.empty or 'skills' not in self.df.columns:
            return pd.DataFrame()
            
        cooccurrences = Counter()
        for skills_list in self.df['skills']:
            # Sort to ensure (A, B) and (B, A) are treated as the same pair
            sorted_skills = sorted(skills_list)
            for pair in itertools.combinations(sorted_skills, 2):
                cooccurrences[pair] += 1
                
        if not cooccurrences:
            return pd.DataFrame()
            
        top_pairs = cooccurrences.most_common(top_n)
        
        # Flatten into a dataframe format suitable for Plotly networks or heatmaps
        data = []
        for (skill1, skill2), count in top_pairs:
            data.append({"Skill 1": skill1, "Skill 2": skill2, "Co-occurrence": count})
            
        return pd.DataFrame(data)

    def get_salary_vs_skills(self) -> pd.DataFrame:
        """Calculate the average salary associated with each skill."""
        if self.df.empty or 'skills' not in self.df.columns or 'avg_salary' not in self.df.columns:
            return pd.DataFrame()
            
        # Explode the dataframe so each skill has its own row with the salary
        exploded_df = self.df[['skills', 'avg_salary']].explode('skills')
        exploded_df.dropna(subset=['avg_salary', 'skills'], inplace=True)
        
        if exploded_df.empty:
            return pd.DataFrame()
            
        # Group by skill and calculate average salary and count
        salary_by_skill = exploded_df.groupby('skills').agg(
            Average_Salary=('avg_salary', 'mean'),
            Count=('avg_salary', 'count')
        ).reset_index()
        
        # Filter for skills that have a dataset count > 0 (allowing single occurrences for small scrapes)
        salary_by_skill = salary_by_skill[salary_by_skill['Count'] > 0]
        salary_by_skill = salary_by_skill.sort_values(by='Average_Salary', ascending=False)
        
        return salary_by_skill

    def get_demand_growth(self) -> pd.DataFrame:
        """Placeholder for time-series growth if date data was available."""
        # Note: We didn't scrape post dates for speed in the current version,
        # but this is where the logic would go.
        pass
        
    def get_top_hiring_companies(self, top_n: int = 10) -> pd.DataFrame:
        """Calculate which companies are hiring the most for this role."""
        if self.df.empty or 'company' not in self.df.columns:
            return pd.DataFrame()
            
        # Filter out "Unknown" companies
        valid_companies = self.df[self.df['company'] != 'Unknown']
        company_counts = valid_companies['company'].value_counts().head(top_n).reset_index()
        company_counts.columns = ['Company', 'Job Postings']
        return company_counts
