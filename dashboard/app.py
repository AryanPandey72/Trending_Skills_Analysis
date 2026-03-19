import streamlit as st
import pandas as pd
import asyncio
import sys
import os
import plotly.express as px
import plotly.graph_objects as go
import itertools

# Load secrets - try Streamlit secrets first, then .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _get_secret(key):
    try:
        return st.secrets[key]
    except Exception:
        return os.environ.get(key)

_groq_key = _get_secret("GROQ_API_KEY")
_adzuna_app_id = _get_secret("ADZUNA_APP_ID")
_adzuna_api_key = _get_secret("ADZUNA_API_KEY")

# Add parent dir to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scrapers.adzuna import AdzunaScraper
from scrapers.ambitionbox import AmbitionBoxScraper
from analyzer.processor import DataProcessor
from analyzer.metrics import MetricsAnalyzer

# Streamlit config
st.set_page_config(
    page_title="Job Market Intelligence Analyzer",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark/Rich mode concepts)
st.markdown("""
<style>
    .main {
        background-color: #0E1117;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 24px;
        border: none;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #45a049;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
    }
    h1, h2, h3 {
        color: #E0E0E0;
        font-family: 'Inter', sans-serif;
    }
    .metric-card {
        background: linear-gradient(145deg, #1A1F2B, #222938);
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Main Title
st.title("Job Market Intelligence Analyzer")
st.markdown("Analyze skill demand, salaries, and tool trends for any specific job role.")

# --- Sidebar Inputs ---
st.sidebar.header("Search Configuration")

POPULAR_JOB_TITLES = [
    "Software Engineer",
    "Senior Software Engineer",
    "Frontend Developer",
    "Backend Developer",
    "Full Stack Developer",
    "Data Scientist",
    "Senior Data Scientist",
    "Data Analyst",
    "Data Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "DevOps Engineer",
    "Cloud Architect",
    "Product Manager",
    "Technical Product Manager",
    "Business Analyst",
    "Business Development Associate",
    "UI/UX Designer",
    "Systems Administrator",
    "Database Administrator",
    "Cybersecurity Analyst",
    "QA Engineer",
    "Mobile Developer",
    "iOS Developer",
    "Android Developer"
]

job_title = st.sidebar.selectbox("Select or Type a Job Title", options=POPULAR_JOB_TITLES, index=5)

with st.sidebar.expander("Advanced Settings"):
    max_jobs = st.slider("Max Job Posts to Fetch", min_value=10, max_value=200, value=50)
    country = st.selectbox("Country", list(AdzunaScraper.COUNTRY_CODES.keys()), index=0)
    country_code = AdzunaScraper.COUNTRY_CODES[country]

# Initialize processors
processor = DataProcessor(groq_api_key=_groq_key)
if not processor.groq_api_healthy:
    st.sidebar.warning("⚠️ Groq API key not found. Skills & salary analysis disabled.")

# Async scraping wrapper
async def run_adzuna(job: str, max_n: int, cc: str):
    scraper = AdzunaScraper(app_id=_adzuna_app_id, app_key=_adzuna_api_key, country=cc)
    return await scraper.get_jobs(job, max_n)

async def fetch_company_salaries(job_title: str, companies: list) -> dict:
    try:
        abs_scraper = AmbitionBoxScraper(groq_api_key=_groq_key)
        return await abs_scraper.get_salaries_batch(job_title, companies)
    except Exception as e:
        print(f"Failed to fetch company salaries: {e}")
        return {}

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        st.error(f"Error: {e}")
        return []
    finally:
        loop.close()


# State management to prevent rerunning scraper on UI interaction
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

analyze_btn = st.sidebar.button("Run Analysis 🚀")

if analyze_btn:
    if not job_title:
        st.warning("Please enter a job title.")
    else:
        # Run Scrapers
        with st.spinner(f"Fetching jobs from Adzuna ({country})..."):
            raw_jobs = run_async(run_adzuna(job_title, max_jobs, country_code))
        
        if not raw_jobs:
            st.error("Scraping failed or no jobs found. Try adjusting the search query.")
        else:
            with st.spinner("Processing Data and Extracting Skills..."):
                # Clean Data
                cleaned_df = processor.clean_and_normalize(raw_jobs)
                st.session_state.df = cleaned_df
                
            with st.spinner("Fetching Market Salary Data..."):
                # Extract unique companies from jobs
                unique_companies = cleaned_df['company'].dropna().unique().tolist()
                top_companies = [c for c in unique_companies if isinstance(c, str) and c.lower() != 'unknown'][:15]
                
                # Fetch company-specific salaries via Groq AI
                company_salaries = run_async(fetch_company_salaries(job_title, top_companies))
                
                # Map these salaries back into the dataframe to replace sparse scraped salaries
                def map_salary(row):
                    comp = row['company']
                    if comp in company_salaries and company_salaries[comp]:
                        return company_salaries[comp]
                    return row['avg_salary']
                    
                cleaned_df['avg_salary'] = cleaned_df.apply(map_salary, axis=1)
                st.session_state.df = cleaned_df
                
                # Calculate a general market average for the top metric card
                st.session_state.market_salary = None
                if company_salaries:
                    valid_sals = [s for s in company_salaries.values() if s]
                    if valid_sals:
                        st.session_state.market_salary = {'avg_salary': sum(valid_sals) / len(valid_sals)}
                
            st.success(f"Analysis complete! Processed {len(cleaned_df)} job postings and fetched salaries for {len(company_salaries)} companies.")


df = st.session_state.df

if not df.empty:
    analyzer = MetricsAnalyzer(df)
    
    # --- Top Metrics Row ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>Total Analyzed</h3><h1>{len(df)}</h1><p>Job Postings</p></div>', unsafe_allow_html=True)
    with col2:
        top_skill = list(itertools.chain.from_iterable(df['skills'].dropna()))
        from collections import Counter
        most_common = Counter(top_skill).most_common(1)
        top = most_common[0][0] if most_common else "N/A"
        st.markdown(f'<div class="metric-card"><h3>Top Skill</h3><h2 style="color:#00D2FF;">{top}</h2><p>Most Demanded</p></div>', unsafe_allow_html=True)
    with col3:
        market_salary = st.session_state.get('market_salary')
        if market_salary and market_salary.get('avg_salary'):
            sal_text = f"₹{market_salary['avg_salary']/100000:.1f}L"
            subtext = "Avg Yearly (AmbitionBox)"
        else:
            # Fallback to scraped if available
            avg_yearly = df[df['salary_period'] == 'yearly']['avg_salary'].mean()
            sal_text = f"${avg_yearly:,.0f}" if pd.notna(avg_yearly) else "N/A"
            subtext = "Average Yearly"
            
        st.markdown(f'<div class="metric-card"><h3>Avg Salary</h3><h2 style="color:#00D2FF;">{sal_text}</h2><p>{subtext}</p></div>', unsafe_allow_html=True)
    with col4:
        top_companies = analyzer.get_top_hiring_companies(1)
        top_company = top_companies.iloc[0]['Company'] if not top_companies.empty else "N/A"
        st.markdown(f'<div class="metric-card"><h3>Top Hirer</h3><h3 style="color:#00D2FF;">{top_company}</h3><p>Company</p></div>', unsafe_allow_html=True)
        
    st.markdown("---")
    
    # --- Charts Row 1 ---
    row1_c1, row1_c2 = st.columns(2)
    
    with row1_c1:
        st.subheader("1) Most Demanded Tools & Skills")
        skills_df = analyzer.get_most_demanded_skills(20)
        if not skills_df.empty:
            fig1 = px.bar(skills_df, x='Count', y='Skill', orientation='h',
                          title=f"Top 20 Skills for {job_title}",
                          color='Count', color_continuous_scale=px.colors.sequential.Teal)
            fig1.update_layout(
                yaxis={'categoryorder':'total ascending', 'dtick': 1}, 
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No skills could be extracted for this query.")
            
    with row1_c2:
        st.subheader("2) Salary vs Skills Correlation")
        salary_skills_df = analyzer.get_salary_vs_skills()
        if not salary_skills_df.empty:
            # Drop very small samples to remove noise
            # If length is 1, size parameter causes plotly to render the bubble weirdly, so we handle it
            if len(salary_skills_df) == 1:
                fig2 = px.scatter(salary_skills_df.head(15), x='Average_Salary', y='skills', 
                                  color='Average_Salary',
                                  title="Average Salary Associated With Skill",
                                  labels={'skills': 'Skill'},
                                  color_continuous_scale=px.colors.sequential.Plasma)
                fig2.update_traces(marker=dict(size=20))
            else:
                fig2 = px.scatter(salary_skills_df.head(15), x='Average_Salary', y='skills', 
                                  size='Count', color='Average_Salary',
                                  title="Average Salary Associated With Skill",
                                  labels={'skills': 'Skill'},
                                  color_continuous_scale=px.colors.sequential.Plasma)
            fig2.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
            st.caption("This chart maps the average salary found in job postings that specifically mention these skills. (Note: Many job postings omit salary data).")
        else:
            st.info("Insufficient salary data extracted to perform correlation.")

    # --- Charts Row 2 ---
    st.markdown("---")
    row2_c1, row2_c2 = st.columns(2)
    
    with row2_c1:
        st.subheader("3) Skill Co-occurrence (Heatmap)")
        co_df = analyzer.get_skill_cooccurrence(15)
        if not co_df.empty:
            # Pivot the dataframe for a heatmap
            heatmap_data = co_df.pivot(index='Skill 1', columns='Skill 2', values='Co-occurrence').fillna(0)
            fig_hm = px.imshow(heatmap_data, 
                               labels=dict(color="Occurrences"),
                               title="Skill Co-occurrence Heatmap",
                               color_continuous_scale="Viridis",
                               aspect="auto")
            fig_hm.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Not enough co-occurrence data found.")
            
    with row2_c2:
        st.subheader("4) Top Hiring Companies")
        companies_df = analyzer.get_top_hiring_companies(10)
        if not companies_df.empty:
            fig3 = px.pie(companies_df, values='Job Postings', names='Company',
                          title="Distribution of Jobs by Company",
                          hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig3.update_traces(textposition='inside', textinfo='percent+label')
            fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No company data extracted.")
            
    # --- Raw Data ---
    with st.expander("View Cleaned Raw Data"):
        st.dataframe(df.drop(columns=['description'], errors='ignore'))
        
else:
    # Empty State Page
    st.markdown("""
        <div style="text-align: center; margin-top: 100px; color: #7f8c8d;">
            <h1>👆 Start a search using the sidebar on the left</h1>
            <p>The system will dynamically scrape, analyze, and render charts based on live job market data.</p>
        </div>
    """, unsafe_allow_html=True)
