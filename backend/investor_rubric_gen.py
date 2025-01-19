import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import logging
from datetime import datetime
import json
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Dict, List
import os
from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

class ThemeAnalysis(BaseModel):
    themes: List[str] = Field(description="List of identified investment themes")
    importance_scores: Dict[str, float] = Field(description="Importance score for each theme")
    key_insights: List[str] = Field(description="Key insights extracted from the content")

class A16ZInvestmentResearcher:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.logger = self._setup_logging()
        self._setup_langchain()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.getLogger('A16ZResearcher')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def _setup_langchain(self):
        """Setup LangChain components"""
        self.theme_parser = PydanticOutputParser(pydantic_object=ThemeAnalysis)
        
        self.analysis_prompt = PromptTemplate(
            template="""You are an expert investment analyst focusing on a16z's investment patterns.
            Analyze the following content and identify key investment themes, their importance, and key insights.
            
            Content: {content}
            
            Extract themes and insights that reflect a16z's investment thesis and preferences.
            {format_instructions}
            """,
            input_variables=["content"],
            partial_variables={"format_instructions": self.theme_parser.get_format_instructions()}
        )

        # Create chain using new syntax
        self.analysis_chain = self.analysis_prompt | self.llm | self.theme_parser

    async def gather_investment_thesis(self) -> List[Dict[str, Any]]:
        """Gather investment thesis data from a16z website"""
        self.logger.info("Gathering investment thesis data...")
        thesis_data = []

        try:
            news_url = "https://a16z.com/news-content/"
            response = requests.get(news_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            articles = soup.find_all('a', href=True)
            article_links = [a['href'] for a in articles if 'a16z.com' in a.get('href', '')]
            
            for link in article_links[:10]:
                try:
                    article_response = requests.get(link, headers=self.headers)
                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    
                    title = article_soup.find('h1').text.strip() if article_soup.find('h1') else ""
                    content = ""
                    
                    content_div = article_soup.find('article') or article_soup.find('div', class_='post-content')
                    if content_div:
                        paragraphs = content_div.find_all('p')
                        content = ' '.join([p.text.strip() for p in paragraphs])
                    
                    if content:
                        analysis = self.analysis_chain.invoke({"content": content})
                        
                        thesis_data.append({
                            'source': 'article',
                            'url': link,
                            'title': title,
                            'analysis': analysis.dict()
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error processing article {link}: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Error scraping news page: {str(e)}")

        return thesis_data

    async def analyze_portfolio_companies(self) -> List[Dict[str, Any]]:
        """Analyze portfolio companies and their success patterns"""
        self.logger.info("Analyzing portfolio companies...")
        portfolio_data = []

        try:
            portfolio_url = "https://a16z.com/portfolio/"
            response = requests.get(portfolio_url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            companies = soup.find_all('div', class_='portfolio-item')
            
            for company in companies:
                try:
                    name = company.find('h3').text.strip() if company.find('h3') else ""
                    description = company.find('p').text.strip() if company.find('p') else ""
                    
                    if description:
                        analysis = self.analysis_chain.invoke({"content": description})
                        
                        portfolio_data.append({
                            'name': name,
                            'description': description,
                            'analysis': analysis.dict()
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error analyzing company {name}: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Error analyzing portfolio companies: {str(e)}")

        return portfolio_data

class RubricGenerator:
    def __init__(self):
        self.logger = logging.getLogger('RubricGenerator')
        self.llm = ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self._setup_chain()

    def _setup_chain(self):
        """Setup the rubric generation chain"""
        rubric_prompt = PromptTemplate(
            template="""Based on the following research data from a16z's investment patterns, 
            generate a detailed investment evaluation rubric with weights and criteria.

            Research Data:
            {research_data}

            Generate a rubric that includes:
            1. Main evaluation categories with weights (must sum to 1.0)
            2. Description for each category
            3. Subcriteria for each category with weights
            4. Specific evaluation points for each subcriteria

            The output must be valid JSON and follow this structure:
            {{
                "technical_innovation": {{
                    "weight": 0.3,
                    "description": "Evaluation of technical innovation and differentiation",
                    "subcriteria": {{
                        "core_technology": {{
                            "weight": 0.4,
                            "description": "Assessment of the fundamental technology",
                            "evaluation_points": [
                                "Novel technical approach",
                                "Technical complexity",
                                "Implementation feasibility"
                            ]
                        }}
                    }}
                }}
            }}
            """,
            input_variables=["research_data"]
        )

        # Create chain using new syntax with JSON parser
        self.json_parser = JsonOutputParser()
        self.rubric_chain = (
            RunnablePassthrough() | 
            rubric_prompt | 
            self.llm | 
            self.json_parser
        )

    def synthesize_rubric(self, research_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate investment rubric from research data"""
        self.logger.info("Synthesizing investment rubric...")

        try:
            # Generate rubric using new invoke syntax
            rubric = self.rubric_chain.invoke({"research_data": json.dumps(research_data, indent=2)})
            return self._normalize_weights(rubric)
        except Exception as e:
            self.logger.error(f"Error generating rubric: {str(e)}")
            return None

    def _normalize_weights(self, rubric: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure weights sum to 1.0 at each level"""
        if not isinstance(rubric, dict):
            return rubric

        # If this level has weights, normalize them
        weights = []
        for key, value in rubric.items():
            if isinstance(value, dict) and 'weight' in value:
                weights.append((key, value['weight']))

        if weights:
            total = sum(w[1] for w in weights)
            if total != 0:
                for key, _ in weights:
                    rubric[key]['weight'] = rubric[key]['weight'] / total

        # Recurse into nested dictionaries
        for key, value in rubric.items():
            if isinstance(value, dict):
                rubric[key] = self._normalize_weights(value)

        return rubric

async def main():
    # Initialize researcher and generator
    researcher = A16ZInvestmentResearcher()
    generator = RubricGenerator()
    
    # Gather research data
    thesis_data = await researcher.gather_investment_thesis()
    portfolio_data = await researcher.analyze_portfolio_companies()
    
    # Combine research data
    research_data = {
        'thesis_data': thesis_data,
        'portfolio_data': portfolio_data
    }
    
    # Generate rubric
    rubric = generator.synthesize_rubric(research_data)
    
    if rubric:
        # Output results
        print("\nGenerated Investment Evaluation Rubric:")
        print(json.dumps(rubric, indent=2))
        
        # Save rubric to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f'a16z_rubric_{timestamp}.json', 'w') as f:
            json.dump(rubric, f, indent=2)
    else:
        print("Failed to generate rubric")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())