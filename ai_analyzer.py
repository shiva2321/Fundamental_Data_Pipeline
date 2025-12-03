"""
Enhanced AI Analyzer with Ollama LLM Integration.
Provides advanced AI-powered insights using local LLM models.
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)


class OllamaAIAnalyzer:
    """
    AI-powered analyzer using Ollama for company fundamental data.
    Falls back to rule-based analysis if Ollama is unavailable.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.ollama_url = "http://localhost:11434/api/generate"
        self.model = "llama3.2"  # Default model
        self.ollama_available = self._check_ollama()
        
    def _check_ollama(self) -> bool:
        """Check if Ollama is running and available."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            logger.warning("Ollama not available, will use rule-based analysis")
            return False
    
    def analyze_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a company profile and generate insights.
        
        Args:
            profile: Company profile data
            
        Returns:
            Analysis results with insights, predictions, and recommendations
        """
        if self.ollama_available:
            try:
                return self._analyze_with_ollama(profile)
            except Exception as e:
                logger.exception("Ollama analysis failed, falling back to rule-based")
                return self._analyze_rule_based(profile)
        else:
            return self._analyze_rule_based(profile)
    
    def _analyze_with_ollama(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Use Ollama LLM for advanced analysis."""
        # Extract key data
        company_info = profile.get('company_info', {})
        latest_financials = profile.get('latest_financials', {})
        ratios = profile.get('financial_ratios', {})
        growth_rates = profile.get('growth_rates', {})
        health = profile.get('health_indicators', {})
        time_series = profile.get('financial_time_series', {})
        
        # Calculate trends
        revenue_trend = self._calculate_trend(time_series.get('Revenues', {}))
        income_trend = self._calculate_trend(time_series.get('NetIncomeLoss', {}))
        
        # Create structured prompt
        prompt = self._create_analysis_prompt(
            company_info, latest_financials, ratios, growth_rates, health,
            revenue_trend, income_trend
        )
        
        # Call Ollama API
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                llm_response = result.get('response', '{}')
                
                # Parse LLM response
                try:
                    analysis = json.loads(llm_response)
                    analysis['provider'] = 'ollama'
                    analysis['model'] = self.model
                    analysis['generated_at'] = datetime.utcnow().isoformat()
                    return analysis
                except json.JSONDecodeError:
                    logger.warning("Failed to parse LLM response as JSON")
                    return self._analyze_rule_based(profile)
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._analyze_rule_based(profile)
                
        except Exception as e:
            logger.exception("Ollama request failed")
            return self._analyze_rule_based(profile)
    
    def _create_analysis_prompt(self, company_info, latest_financials, ratios, 
                                growth_rates, health, revenue_trend, income_trend) -> str:
        """Create a structured prompt for the LLM."""
        
        # Extract key metrics
        ticker = company_info.get('ticker', 'N/A')
        name = company_info.get('name', 'Unknown')
        
        revenue = latest_financials.get('Revenues', 0)
        assets = latest_financials.get('Assets', 0)
        net_income = latest_financials.get('NetIncomeLoss', 0)
        
        roe = ratios.get('return_on_equity', 0)
        roa = ratios.get('return_on_assets', 0)
        de_ratio = ratios.get('debt_to_equity', 0)
        
        rev_growth = growth_rates.get('Revenues', {}).get('avg_growth_rate', 0)
        health_score = health.get('overall_health_score', 0)
        
        prompt = f"""You are a financial analyst. Analyze this company's fundamental data and provide investment insights.

Company: {ticker} - {name}

Financial Metrics:
- Revenue: ${revenue:,.0f} (Trend: {revenue_trend})
- Net Income: ${net_income:,.0f} (Trend: {income_trend})
- Total Assets: ${assets:,.0f}
- Return on Equity (ROE): {roe:.2%}
- Return on Assets (ROA): {roa:.2%}
- Debt to Equity: {de_ratio:.2f}
- Revenue Growth Rate: {rev_growth:.1f}%
- Overall Health Score: {health_score:.1f}/100

Provide a comprehensive analysis in JSON format with these exact fields:

{{
  "investment_thesis": "2-3 sentence summary of investment case",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
  "growth_prediction": {{
    "1yr": {{"revenue": X.X, "earnings": X.X}},
    "3yr": {{"revenue": X.X, "earnings": X.X}},
    "5yr": {{"revenue": X.X, "earnings": X.X}}
  }},
  "risk_level": "Low|Medium|High",
  "recommendation": "Strong Buy|Buy|Hold|Sell|Strong Sell",
  "confidence": 0.XX,
  "key_assumptions": ["assumption 1", "assumption 2", "assumption 3"],
  "catalysts": ["potential catalyst 1", "potential catalyst 2"],
  "risks": ["specific risk 1", "specific risk 2"]
}}

Respond ONLY with valid JSON, no additional text."""

        return prompt
    
    def _calculate_trend(self, time_series: Dict[str, float]) -> str:
        """Calculate trend from time series data."""
        if not time_series or len(time_series) < 2:
            return "insufficient data"
        
        dates = sorted(time_series.keys())
        values = [time_series[d] for d in dates]
        
        # Simple trend: compare recent vs older
        if len(values) >= 3:
            recent_avg = sum(values[-3:]) / 3
            older_avg = sum(values[:3]) / 3
            
            if recent_avg > older_avg * 1.1:
                return "accelerating"
            elif recent_avg > older_avg * 1.02:
                return "growing"
            elif recent_avg > older_avg * 0.98:
                return "stable"
            else:
                return "declining"
        
        return "stable"
    
    def _analyze_rule_based(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Rule-based analysis as fallback."""
        company_info = profile.get('company_info', {})
        latest_financials = profile.get('latest_financials', {})
        ratios = profile.get('financial_ratios', {})
        growth_rates = profile.get('growth_rates', {})
        health = profile.get('health_indicators', {})
        
        # Extract key metrics
        roe = ratios.get('return_on_equity', 0)
        roa = ratios.get('return_on_assets', 0)
        debt_to_equity = ratios.get('debt_to_equity', 0)
        health_score = health.get('overall_health_score', 50)
        
        # Calculate revenue growth
        revenue_growth = 0
        if 'Revenues' in growth_rates:
            revenue_growth = growth_rates['Revenues'].get('avg_growth_rate', 0)
        
        # Determine strengths
        strengths = []
        if health_score >= 70:
            strengths.append("Strong overall financial health")
        if roe > 0.15:
            strengths.append(f"High return on equity ({roe:.1%})")
        if revenue_growth > 10:
            strengths.append(f"Strong revenue growth ({revenue_growth:.1f}%)")
        if debt_to_equity < 1:
            strengths.append("Conservative debt levels")
        if not strengths:
            strengths.append("Stable operations")
        
        # Determine weaknesses
        weaknesses = []
        if health_score < 50:
            weaknesses.append("Poor overall financial health")
        if roe < 0.05:
            weaknesses.append("Low return on equity")
        if revenue_growth < 0:
            weaknesses.append("Declining revenue")
        if debt_to_equity > 2:
            weaknesses.append("High debt burden")
        if not weaknesses:
            weaknesses.append("Limited growth momentum")
        
        # Growth predictions
        base_growth = max(0, revenue_growth)
        predictions = {
            '1yr': {'revenue': base_growth * 0.8, 'earnings': base_growth * 1.2},
            '3yr': {'revenue': base_growth * 0.7, 'earnings': base_growth * 1.0},
            '5yr': {'revenue': base_growth * 0.6, 'earnings': base_growth * 0.9}
        }
        
        # Risk assessment
        risk_score = 0
        if debt_to_equity > 2: risk_score += 2
        if health_score < 50: risk_score += 2
        if revenue_growth < 0: risk_score += 1
        
        risk_level = 'Low' if risk_score <= 1 else 'Medium' if risk_score <= 3 else 'High'
        
        # Recommendation
        score = 0
        if health_score >= 70: score += 2
        if roe > 0.15: score += 2
        if revenue_growth > 10: score += 2
        if debt_to_equity < 1: score += 1
        if revenue_growth < 0: score -= 2
        if health_score < 50: score -= 2
        
        if score >= 5:
            recommendation = "Strong Buy"
        elif score >= 3:
            recommendation = "Buy"
        elif score >= 0:
            recommendation = "Hold"
        elif score >= -2:
            recommendation = "Sell"
        else:
            recommendation = "Strong Sell"
        
        return {
            'investment_thesis': f"Company shows {recommendation.lower()} characteristics based on fundamental analysis.",
            'strengths': strengths[:3],
            'weaknesses': weaknesses[:3],
            'growth_prediction': predictions,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'confidence': 0.65,  # Lower confidence for rule-based
            'key_assumptions': [
                "Historical trends continue",
                "No major market disruptions",
                "Current management strategy maintained"
            ],
            'catalysts': ["Improved operational efficiency", "Market expansion"],
            'risks': ["Economic downturn", "Competitive pressure"],
            'generated_at': datetime.utcnow().isoformat(),
            'provider': 'rule_based'
        }


# Maintain backward compatibility
AIAnalyzer = OllamaAIAnalyzer
