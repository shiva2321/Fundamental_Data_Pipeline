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

        # Get model from config, with fallback to default
        profile_settings = self.config.get('profile_settings', {})
        self.model = profile_settings.get('ai_model', 'llama3.2')

        self.ollama_available = self._check_ollama()
        
    def _check_ollama(self) -> bool:
        """Check if Ollama is running and available."""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info(f"Ollama is available at {self.ollama_url}")
                return True
            else:
                logger.warning(f"Ollama returned status code {response.status_code}, will use rule-based analysis")
                return False
        except requests.exceptions.ConnectionError:
            logger.warning("Ollama is not running on localhost:11434. Install and start Ollama or disable AI analysis. Using rule-based analysis.")
            return False
        except Exception as e:
            logger.warning(f"Ollama connection error: {e}. Will use rule-based analysis")
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
            # Check if the specific model is installed
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    model_names = [m.get('name', '').split(':')[0] for m in models]

                    if self.model not in model_names:
                        logger.warning(f"Model '{self.model}' not installed. Available models: {', '.join(model_names)}. Using rule-based analysis.")
                        return self._analyze_rule_based(profile)
            except Exception as e:
                logger.warning(f"Could not check installed models: {e}")

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
        material_events = profile.get('material_events', {})
        governance = profile.get('corporate_governance', {})
        insider_trading = profile.get('insider_trading', {})
        institutional = profile.get('institutional_ownership', {})

        # Calculate trends
        revenue_trend = self._calculate_trend(time_series.get('Revenues', {}))
        income_trend = self._calculate_trend(time_series.get('NetIncomeLoss', {}))
        
        # Create structured prompt
        prompt = self._create_analysis_prompt(
            company_info, latest_financials, ratios, growth_rates, health,
            revenue_trend, income_trend, material_events, governance,
            insider_trading, institutional
        )
        
        # Call Ollama API with increased timeout and retry logic
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "num_predict": 2048,  # Limit response length
                        "temperature": 0.7,
                        "top_p": 0.9
                    }
                },
                timeout=60  # 60 seconds timeout
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
                    logger.warning("Failed to parse LLM response as JSON, using rule-based analysis")
                    return self._analyze_rule_based(profile)
            else:
                logger.warning(f"Ollama API returned {response.status_code}. Model '{self.model}' may not be installed. Run: ollama pull {self.model}")
                return self._analyze_rule_based(profile)
                
        except requests.exceptions.ReadTimeout:
            # Timeout is expected for large models like mixtral
            logger.warning(f"Ollama request timed out after 60s for model {self.model} - using fallback analysis")
            return self._analyze_rule_based(profile)
        except Exception as e:
            logger.warning(f"Ollama request failed for model {self.model}: {str(e)[:100]} - using fallback analysis")
            return self._analyze_rule_based(profile)
    
    def _create_analysis_prompt(self, company_info, latest_financials, ratios, 
                                growth_rates, health, revenue_trend, income_trend,
                                material_events=None, governance=None,
                                insider_trading=None, institutional=None) -> str:
        """Create a comprehensive structured prompt for the LLM with all available data."""

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
        
        # Material events section
        events_section = ""
        if material_events and material_events.get('total_8k_count', 0) > 0:
            recent_count = material_events.get('recent_count', 0)
            total_count = material_events.get('total_8k_count', 0)
            risk_flags = material_events.get('risk_flags', [])
            positive_catalysts = material_events.get('positive_catalysts', [])
            avg_frequency = material_events.get('avg_events_per_quarter', 0)

            events_section = f"""
Material Events (8-K Filings):
- Total 8-K filings: {total_count}
- Recent events (90 days): {recent_count}
- Average per quarter: {avg_frequency}
- Risk flags: {', '.join(risk_flags[:3]) if risk_flags else 'None identified'}
- Positive catalysts: {', '.join(positive_catalysts[:3]) if positive_catalysts else 'None identified'}
"""

        # Corporate governance section
        governance_section = ""
        if governance and governance.get('total_proxy_count', 0) > 0:
            gov_score = governance.get('governance_score', 0)
            insights = governance.get('insights', [])
            proxy_count = governance.get('total_proxy_count', 0)

            governance_section = f"""
Corporate Governance (DEF 14A):
- Proxy statements filed: {proxy_count}
- Governance score: {gov_score}/100
- Key insights: {'; '.join(insights[:3]) if insights else 'Limited data'}
"""

        # Insider trading section with DETAILED DATA
        insider_section = ""
        if insider_trading and insider_trading.get('total_form4_count', 0) > 0:
            form4_count = insider_trading.get('total_form4_count', 0)
            recent_count = insider_trading.get('recent_count_90d', 0)
            sentiment = insider_trading.get('sentiment', 'Unknown')
            activity_level = insider_trading.get('activity_level', 'Unknown')
            insights = insider_trading.get('insights', [])

            # Add detailed transaction data if available
            detailed = insider_trading.get('detailed_analysis', {})
            if detailed.get('available'):
                net_value = detailed.get('net_value', 0)
                signal = detailed.get('overall_signal', 'Unknown')
                buy_sell_ratio = detailed.get('buy_sell_ratio', 0)

                insider_section = f"""
Insider Trading Activity (Form 4) - DETAILED ANALYSIS:
- Total Form 4 filings: {form4_count}
- Recent transactions (90 days): {recent_count}
- Activity level: {activity_level}
- **Net insider activity: {detailed.get('summary', 'N/A')}**
- **Overall signal: {signal}**
- **Buy/Sell ratio: {buy_sell_ratio:.2f}**
- Top buyers: {', '.join([f"{name} ({count} txns)" for name, count in detailed.get('top_buyers', [])[:3]])}
- Top sellers: {', '.join([f"{name} ({abs(count)} txns)" for name, count in detailed.get('top_sellers', [])[:3]])}
- Key insights: {'; '.join(insights[:3]) if insights else 'Limited data'}
"""
            else:
                insider_section = f"""
Insider Trading Activity (Form 4):
- Total Form 4 filings: {form4_count}
- Recent transactions (90 days): {recent_count}
- Activity level: {activity_level}
- Sentiment: {sentiment}
- Key insights: {'; '.join(insights[:3]) if insights else 'Limited data'}
"""

        # Institutional ownership section with DETAILED DATA
        institutional_section = ""

        # Initialize variables to avoid UnboundLocalError
        total_sc13 = 0
        activist_count = 0
        interest_level = "Unknown"

        if institutional:
            total_sc13 = institutional.get('total_sc13_count', 0)
            activist_count = institutional.get('activist_count', 0)
            interest_level = institutional.get('institutional_interest', 'Unknown')

        if total_sc13 > 0 and institutional:
            insights = institutional.get('insights', [])

            # Add detailed ownership data if available
            detailed = institutional.get('detailed_analysis', {})
            if detailed.get('available'):
                concentration = detailed.get('ownership_concentration', {})

                institutional_section = f"""
Institutional Ownership (SC 13D/G) - DETAILED ANALYSIS:
- Total SC 13 filings: {total_sc13}
- Activist investors (SC 13D): {activist_count}
- Institutional interest: {interest_level}
- **Ownership concentration: {concentration.get('concentration_level', 'Unknown')}**
- **Top shareholder: {detailed['largest_shareholders'][0]['investor_name']} ({detailed['largest_shareholders'][0]['ownership_percent']:.1f}%)** if detailed.get('largest_shareholders') else 'Unknown'
- **Top 3 own: {concentration.get('top_3', 0):.1f}%**
- Activist details: {'; '.join([f"{a['investor']} - {a['intent']}" for a in detailed.get('activist_details', [])[:2]])}
- Key insights: {'; '.join(insights[:3]) if insights else 'Limited data'}
"""
            else:
                institutional_section = f"""
Institutional Ownership (SC 13D/G):
- Total SC 13 filings: {total_sc13}
- Activist investors (SC 13D): {activist_count}
- Institutional interest: {interest_level}
- Key insights: {'; '.join(insights[:3]) if insights else 'Limited data'}
"""
        else:
            institutional_section = f"""
Institutional Ownership (SC 13D/G):
- Total SC 13 filings: 0
- Limited institutional data available
"""

        # Corporate governance section with DETAILED DATA
        governance_section = ""
        if governance and governance.get('total_proxy_count', 0) > 0:
            gov_score = governance.get('governance_score', 0)
            insights = governance.get('insights', [])
            proxy_count = governance.get('total_proxy_count', 0)

            # Add detailed compensation and board data if available
            detailed_comp = governance.get('detailed_compensation', {})
            detailed_board = governance.get('detailed_board', {})

            comp_info = ""
            if detailed_comp.get('available'):
                latest = detailed_comp.get('latest', {})
                trends = detailed_comp.get('trends', {})
                comp_info = f"""
- **CEO total compensation: ${latest.get('ceo_total_comp', 0):,.0f}**
- **Pay ratio (CEO/median): {latest.get('pay_ratio', 0):.0f}:1**
- **Compensation growth: {trends.get('ceo_comp_growth_percent', 0):.1f}%**
- Red flags: {'; '.join(detailed_comp.get('red_flags', [])[:2])}"""

            board_info = ""
            if detailed_board.get('available'):
                latest_board = detailed_board.get('latest_composition', {})
                board_info = f"""
- **Board size: {latest_board.get('total_directors', 0)} directors**
- **Independent: {latest_board.get('independent_directors', 0)} ({latest_board.get('independence_ratio', 0):.0%})**
- **Assessment: {detailed_board.get('governance_assessment', 'Unknown')}**"""

            governance_section = f"""
Corporate Governance (DEF 14A) - DETAILED ANALYSIS:
- Proxy statements filed: {proxy_count}
- Governance score: {gov_score}/100{comp_info}{board_info}
- Key insights: {'; '.join(insights[:3]) if insights else 'Limited data'}
"""

        prompt = f"""You are a financial analyst. Analyze this company's COMPLETE fundamental data including financial metrics, corporate events, governance, insider trading, and institutional ownership to provide comprehensive investment insights.

Company: {ticker} - {name}

=== FINANCIAL METRICS ===
- Revenue: ${revenue:,.0f} (Trend: {revenue_trend})
- Net Income: ${net_income:,.0f} (Trend: {income_trend})
- Total Assets: ${assets:,.0f}
- Return on Equity (ROE): {roe:.2%}
- Return on Assets (ROA): {roa:.2%}
- Debt to Equity: {de_ratio:.2f}
- Revenue Growth Rate: {rev_growth:.1f}%
- Overall Health Score: {health_score:.1f}/100
{events_section}{governance_section}{insider_section}{institutional_section}
=== ANALYSIS INSTRUCTIONS ===
Consider ALL available data when forming your investment thesis:
1. Financial performance and trends
2. Material events and their implications
3. Corporate governance quality
4. Insider sentiment and activity patterns
5. Institutional investor confidence
6. Risk factors from all sources
7. Catalysts and opportunities identified

Provide a comprehensive analysis in JSON format with these exact fields:

{{
  "investment_thesis": "2-3 sentence comprehensive summary considering ALL data sources",
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
  "risks": ["specific risk 1", "specific risk 2"],
  "governance_assessment": "Brief assessment of corporate governance quality",
  "insider_signals": "Brief assessment of insider trading signals",
  "institutional_signals": "Brief assessment of institutional investor signals"
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
