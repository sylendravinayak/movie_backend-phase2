from datetime import date, timedelta, datetime
from sqlalchemy import text
from database import SessionLocal
from model import Movie,Screen
from agent.state import OpsState
from agent.tools.booking_history_tool import get_daily_booking_series
from agent.tools.external_signals import fetch_all_external_signals, TrendAnalyzer, HolidayCalendar, get_trend_factor
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import warnings
import os
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from typing import Literal
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

warnings.filterwarnings('ignore')
from prophet import Prophet


FORECAST_DAYS = 7

Multiplier = Annotated[float, Field(strict=True)]

class DemandMultiplierOutput(BaseModel):
    base_demand_multiplier: Annotated[float, Field(ge=0.7, le=1.3)]
    
    monday_multiplier: Annotated[float, Field(ge=0.7, le=1.0)]
    tuesday_multiplier: Annotated[float, Field(ge=0.7, le=1.0)]
    wednesday_multiplier: Annotated[float, Field(ge=0.7, le=1.0)]
    thursday_multiplier: Annotated[float, Field(ge=0.7, le=1.0)]
    
    friday_multiplier: Annotated[float, Field(ge=1.05, le=1.3)]
    saturday_multiplier: Annotated[float, Field(ge=1.1, le=1.35)]
    sunday_multiplier: Annotated[float, Field(ge=1.05, le=1.3)]
    
    daily_decay_rate: Annotated[float, Field(ge=0.0, le=0.10)]
    competition_adjustment: Annotated[float, Field(ge=0.0, le=0.30)]
    
    confidence: Annotated[int, Field(ge=1, le=10)]
    trend_direction: Literal["increasing", "stable", "decreasing"]
    
    key_drivers: List[str]
    risk_factors: List[str]

parser = PydanticOutputParser(pydantic_object=DemandMultiplierOutput)


class GroqLLMForecaster:
    """Enhanced LLM-based time series forecasting using Groq"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Groq API key"""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            print("Warning: GROQ_API_KEY not found. LLM forecasting will fail.")
    
    def create_multiplier_based_prompt(self, history_data: List[tuple], 
                                   movie_title: str,
                                   forecast_horizon: int,
                                   context: Dict,
                                   prophet_baseline: Optional[float] = None) -> str:
        
        # Calculate historical baseline (CRITICAL ANCHOR)
        if history_data:
            recent_values = [float(row[1]) for row in history_data[-14:]]
            window = recent_values[-14:]
            low, high = np.percentile(window, [15, 85])
            trimmed = [v for v in window if low <= v <= high]
            historical_baseline = np.mean(trimmed)
            historical_std = np.std(recent_values)
            
            # Show trend within history
            if len(recent_values) >= 14:
                recent_7 = np.mean(recent_values[-7:])
                previous_7 = np.mean(recent_values[-14:-7])
                observed_momentum = recent_7 / previous_7 if previous_7 > 0 else 1.0
            else:
                observed_momentum = 1.0
        else:
            historical_baseline = None
            historical_std = None
            observed_momentum = 1.0
        
        # Build patches (for pattern recognition only)
        patches = []
        if history_data:
            values = [float(row[1]) for row in history_data[-21:]]
            for i in range(len(values) - 2):
                patch = values[i:i+3]
                trend = "↑" if patch[2] > patch[0] else "↓" if patch[2] < patch[0] else "→"
                patches.append(f"  [{patch[0]:.0f}, {patch[1]:.0f}, {patch[2]:.0f}] {trend}")
        
        patches_text = "\n".join(reversed(patches[-15:])) if patches else "No history"
        
        # Context
        trend_info = context.get('trend_factor', 1.0)
        competition = context.get('competition_pressure', 0.5)
        
        # Add Prophet baseline info if available
        prophet_info = ""
        if prophet_baseline is not None:
            prophet_info = f"\n## PROPHET ML BASELINE\n- Prophet predicted average: {prophet_baseline:.1f} seats/day\n- Use this as additional signal for calibration\n"
        
        prompt = f"""## SYSTEM
You are a multiplier-calibration expert for time-series forecasting. 
You output ONLY adjustment multipliers, NOT absolute demand numbers.

## CRITICAL CONSTRAINT
You must NEVER output seat counts, fill rates, or absolute demand.
Output ONLY multipliers relative to the historical baseline.

## MOVIE: {movie_title}

## HISTORICAL BASELINE (ANCHOR POINT)
{'- Recent 7-day average: ' + f'{historical_baseline:.1f} seats/day' if historical_baseline else '- NO HISTORY: New release'}
{'- Volatility (std dev): ' + f'{historical_std:.1f}' if historical_std else ''}
{'- Observed momentum (last 7d / prev 7d): ' + f'{observed_momentum:.2f}x' if historical_baseline else ''}
{prophet_info}
## RECENT PATTERNS (for pattern recognition only)
{patches_text}

## EXTERNAL SIGNALS
- Trend factor: {trend_info:.2f} ({'high buzz' if trend_info > 1.2 else 'moderate' if trend_info > 0.95 else 'weak'})
- Market pressure: {competition:.2f} ({self._interpret_pressure(competition)})
- Holidays in period: {', '.join([h['date'] for h in context.get('holidays', [])[:3]]) or 'None'}

## YOUR TASK
Based on patterns, Prophet ML signal, and external data, output multipliers that will adjust the historical baseline.

**YOU MUST OUTPUT EXACTLY THIS JSON STRUCTURE:**
{{
"base_demand_multiplier": 0.XX,
"monday_multiplier": 0.XX,
"tuesday_multiplier": 0.XX,
"wednesday_multiplier": 0.XX,
"thursday_multiplier": 0.XX,
"friday_multiplier": 1.XX,
"saturday_multiplier": 1.XX,
"sunday_multiplier": 1.XX,
"daily_decay_rate": 0.0X,
"competition_adjustment": 0.XX,
"confidence": X,
"trend_direction": "increasing|stable|decreasing",
"key_drivers": ["driver1", "driver2", "driver3"],
"risk_factors": ["risk1", "risk2"]
}}

Return ONLY the JSON object. No markdown, no explanations, no seat counts.
{parser.get_format_instructions()}
"""
        
        return prompt

    def _interpret_pressure(self, pressure: float) -> str:
        """Interpret competition pressure as market crowding"""
        if pressure >= 0.7:
            return "very high market pressure (crowded)"
        elif pressure >= 0.5:
            return "high market pressure"
        elif pressure >= 0.3:
            return "moderate market pressure"
        else:
            return "low market pressure (favorable)"
    
    def _interpret_trend(self, trend_factor: float) -> str:
        """Interpret trend factor"""
        if trend_factor >= 1.3:
            return "Very High buzz/interest"
        elif trend_factor >= 1.15:
            return "High buzz/interest"
        elif trend_factor >= 1.05:
            return "Moderate positive buzz"
        elif trend_factor >= 0.95:
            return "Neutral buzz"
        elif trend_factor >= 0.85:
            return "Moderate negative buzz"
        else:
            return "Low interest/declining buzz"
    
    def create_cold_start_prompt(self, movie_title: str, 
                                 forecast_horizon: int,
                                 context: Dict) -> str:
        """Create enhanced prompt for new movies"""
        
        trend_info = context.get('trend_factor', 1.0)
        holiday_dates = [h['date'] for h in context.get('holidays', [])[:5]]
        physical_cap = context.get('physical_cap', 1000)
        num_competing_movies = context.get('num_movies', 3)
        competition = context.get('competition_pressure', 0.5)
        
        prompt = f"""## System
You are an expert in predicting opening week performance for new movie releases. You use market signals and industry benchmarks to forecast realistic attendance patterns.

## Context
**New Movie Release**: {movie_title}
**Forecast Period**: Opening week ({forecast_horizon} days) starting {context.get('start_date', 'tomorrow')}
**Status**: NO HISTORICAL DATA - Cold start prediction based on market signals

## Market Intelligence
- **Pre-release Buzz (Trend Factor)**: {trend_info:.2f}
  → {self._interpret_trend(trend_info)}
  
- **Competitive Landscape**: 
  * Number of competing movies: {num_competing_movies}
  * Market pressure: {competition:.2f}
  * {self._interpret_pressure(competition)}
  
- **Theater Capacity**: {physical_cap} seats/day maximum
- **Holiday Influence**: {', '.join(holiday_dates) if holiday_dates else 'No holidays in opening week'}

Return ONLY the JSON object.{parser.get_format_instructions()}
"""
        
        return prompt
    
    def call_groq_api(self, prompt: str, retry_count: int = 2) -> Dict:
        """Call Groq API with retry logic and better error handling"""
        
        llm = ChatGroq(
            api_key=self.api_key,
            model="llama-3.3-70b-versatile",
            temperature=0.2
        )
       
        messages = [
            {"role": "system", "content": "You are a professional time-series forecasting expert. You ALWAYS respond with valid JSON only, never with markdown or explanatory text."},
            HumanMessage(content=prompt)
        ]
            
        try:
            res = llm.invoke(messages)
            parsed = parser.parse(res.content)
        except Exception as e:
            return {"error": f"LLM invocation failed: {str(e)}"}        
        
        return {
            "base_demand_multiplier": parsed.base_demand_multiplier,
            "monday_multiplier": parsed.monday_multiplier,
            "tuesday_multiplier": parsed.tuesday_multiplier,
            "wednesday_multiplier": parsed.wednesday_multiplier,
            "thursday_multiplier": parsed.thursday_multiplier,
            "friday_multiplier": parsed.friday_multiplier,
            "saturday_multiplier": parsed.saturday_multiplier,
            "sunday_multiplier": parsed.sunday_multiplier,
            "daily_decay_rate": parsed.daily_decay_rate,
            "competition_adjustment": parsed.competition_adjustment,
            "confidence": parsed.confidence / 10.0,
            "trend_direction": parsed.trend_direction,
            "key_drivers": parsed.key_drivers,
            "risk_factors": parsed.risk_factors,
            "method": "groq_llm_multiplier"
        }
    
    def forecast(self, history_data: List[tuple],
                movie_title: str,
                forecast_horizon: int,
                context: Dict,
                prophet_baseline: Optional[float] = None) -> Dict:
        """Execute LLM-based forecast with enhanced context"""
        
        # Choose prompt based on data availability
        if history_data and len(history_data) >= 7:
            prompt = self.create_multiplier_based_prompt(
                history_data, movie_title, forecast_horizon, context, prophet_baseline
            )
        else:
            prompt = self.create_cold_start_prompt(
                movie_title, forecast_horizon, context
            )
        
        return self.call_groq_api(prompt)


class HybridProphetLLMForecaster:
    """Hybrid forecaster combining Prophet ML and LLM intelligence"""
    
    def __init__(self, trend_data: Dict = None, holidays: List[Dict] = None):
        self.trend_data = trend_data or {}
        self.holidays = holidays or []
        self.llm_forecaster = GroqLLMForecaster()
    
    def prepare_prophet_data(self, history_data: List[tuple], movie_title: str) -> pd.DataFrame:
        """Prepare data with trend and holiday regressors for Prophet"""
        
        if not history_data:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(history_data, columns=['ds', 'y'])
        df['ds'] = pd.to_datetime(df['ds'])
        
        # Remove zeros and outliers
        df = df[df['y'] > 0]
        
        # Cap outliers
        if len(df) > 10:
            upper_bound = df['y'].quantile(0.99)
            df['y'] = df['y'].clip(upper=upper_bound)
        
        # Add trend regressor
        movie_trends = self.trend_data.get(movie_title, [])
        if movie_trends:
            trend_df = pd.DataFrame(movie_trends)
            trend_df['ds'] = pd.to_datetime(trend_df['date'])
            trend_df['trend_score'] = trend_df['value'] / 100.0
            
            df = df.merge(trend_df[['ds', 'trend_score']], on='ds', how='left')
            df['trend_score'] = df['trend_score'].fillna(0.5)
        else:
            df['trend_score'] = 0.5
        
        # Add holiday boost
        df['holiday_boost'] = df['ds'].apply(
            lambda x: HolidayCalendar.get_holiday_boost(x.strftime("%Y-%m-%d"), self.holidays)
        )
        
        return df
    
    def run_prophet_forecast(self, df: pd.DataFrame, periods: int, 
                            movie_title: str, competition: float,
                            daily_physical_cap: int) -> Optional[pd.DataFrame]:
        """Run Prophet forecast and return predictions"""
        
        if len(df) < 7:
            return None
        
        try:
            # Configure Prophet
            model = Prophet(
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=False,
                interval_width=0.80
            )
            
            # Add regressors
            if 'trend_score' in df.columns:
                model.add_regressor('trend_score', standardize=True)
            
            if 'holiday_boost' in df.columns:
                model.add_regressor('holiday_boost', standardize=True)
            
            # Fit model
            model.fit(df)
            
            # Generate future dates with regressors
            future = model.make_future_dataframe(periods=periods)
            
            # Add future regressors
            future_start = df['ds'].max() + timedelta(days=1)
            recent_trend = df['trend_score'].tail(7).mean() if 'trend_score' in df.columns else 0.5
            
            future['trend_score'] = future['ds'].apply(
                lambda x: recent_trend if x >= future_start else 
                df[df['ds'] == x]['trend_score'].values[0] if x in df['ds'].values else recent_trend
            )
            
            future['holiday_boost'] = future['ds'].apply(
                lambda x: HolidayCalendar.get_holiday_boost(x.strftime("%Y-%m-%d"), self.holidays)
            )
            
            # Predict
            forecast = model.predict(future)
            forecast = forecast.tail(periods)
            
            # Apply competition and capacity constraints
            forecast['yhat'] = forecast['yhat'] * (1 - competition * 0.3)
            forecast['yhat'] = forecast['yhat'].clip(lower=1, upper=daily_physical_cap * 0.95)
            forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=1)
            forecast['yhat_upper'] = forecast['yhat_upper'].clip(upper=daily_physical_cap * 0.95)
            
            return forecast
            
        except Exception as e:
            print(f"Prophet forecast failed for {movie_title}: {str(e)}")
            return None
    
    def hybrid_forecast(self, history_data: List[tuple], 
                       movie_title: str,
                       periods: int,
                       competition_pressure: float,
                       daily_physical_cap: int,
                       start_date: date,
                       velocity: float) -> pd.DataFrame:
        """
        HYBRID APPROACH: Combine Prophet ML predictions with LLM adjustments
        
        Strategy:
        1. Run Prophet to get ML-based baseline
        2. Feed Prophet results to LLM for intelligent adjustments
        3. Blend both predictions with confidence weighting
        """
        
        # 1. CALCULATE HISTORICAL BASELINE
        if history_data and len(history_data) >= 7:
            recent_values = [float(r[1]) for r in history_data[-14:]]
            baseline_window = recent_values[-7:]
            historical_baseline = np.median(baseline_window)
            
            if len(recent_values) >= 14:
                recent_avg = np.mean(recent_values[-7:])
                past_avg = np.mean(recent_values[-14:-7])
                observed_velocity = recent_avg / max(past_avg, 1)
            else:
                observed_velocity = 1.0
                
            historical_floor = int(np.percentile(recent_values[-7:], 25))
            
        else:
            trend_factor = get_trend_factor(movie_title, self.trend_data)
            estimated_fill = 0.25 + min((trend_factor - 1.0) * 0.15, 0.20)
            historical_baseline = daily_physical_cap * np.clip(estimated_fill, 0.20, 0.45)
            observed_velocity = 1.0
            historical_floor = int(daily_physical_cap * 0.15)
        
        # 2. RUN PROPHET FORECAST (if enough data)
        prophet_forecast = None
        prophet_baseline = None
        prophet_weight = 0.0
        
        if history_data and len(history_data) >= 7:
            df = self.prepare_prophet_data(history_data, movie_title)
            if not df.empty:
                prophet_forecast = self.run_prophet_forecast(
                    df, periods, movie_title, competition_pressure, daily_physical_cap
                )
                
                if prophet_forecast is not None:
                    prophet_baseline = prophet_forecast['yhat'].mean()
                    # Prophet gets more weight with more data
                    data_quality = min(len(df) / 30.0, 1.0)
                    prophet_weight = 0.4 * data_quality  # Max 40% weight
                    print(f"Prophet baseline for {movie_title}: {prophet_baseline:.1f}, weight: {prophet_weight:.2f}")
        
        # 3. BUILD CONTEXT FOR LLM (include Prophet signal)
        context = {
            'trend_factor': get_trend_factor(movie_title, self.trend_data),
            'holidays': self.holidays,
            'competition_pressure': competition_pressure,
            'physical_cap': daily_physical_cap,
            'start_date': str(start_date),
            'velocity': velocity,
            'num_movies': 3
        }
        
        # 4. CALL LLM WITH PROPHET BASELINE
        llm_result = self.llm_forecaster.forecast(
            history_data, movie_title, periods, context, prophet_baseline
        )
        
        # 5. HANDLE LLM ERRORS
        if 'error' in llm_result:
            print(f"LLM error for {movie_title}: {llm_result['error']}")
            # Fallback to Prophet-only if available
            if prophet_forecast is not None:
                return self._format_prophet_only(prophet_forecast, historical_baseline, historical_floor, daily_physical_cap, llm_result)
            else:
                return self._fallback_forecast(history_data, periods, movie_title, 
                                              competition_pressure, daily_physical_cap, start_date)
        
        # 6. EXTRACT LLM MULTIPLIERS
        base_mult = llm_result.get('base_demand_multiplier', 1.0)
        weekday_mults = {
            0: llm_result.get('monday_multiplier', 0.85),
            1: llm_result.get('tuesday_multiplier', 0.85),
            2: llm_result.get('wednesday_multiplier', 0.88),
            3: llm_result.get('thursday_multiplier', 0.90),
            4: llm_result.get('friday_multiplier', 1.15),
            5: llm_result.get('saturday_multiplier', 1.25),
            6: llm_result.get('sunday_multiplier', 1.18)
        }
        daily_decay = np.clip(llm_result.get('daily_decay_rate', 0.03), 0.0, 0.10)
        comp_adjustment = np.clip(llm_result.get('competition_adjustment', 0.0), 0.0, 0.30)
        
        velocity_multiplier = np.clip(velocity, 0.85, 1.25)
        
        # 7. CALCULATE HYBRID FORECASTS
        future_dates = pd.date_range(start=start_date, periods=periods)
        forecast_data = []
        
        for i, future_date in enumerate(future_dates):
            # ===== LLM-BASED PREDICTION =====
            demand_llm = historical_baseline
            demand_llm *= base_mult
            demand_llm *= weekday_mults[future_date.dayofweek]
            demand_llm *= velocity_multiplier
            
            if future_date.weekday() < 4:
                dampened_decay = (1.0 - daily_decay) ** (i ** 0.7)
                demand_llm *= dampened_decay
            
            holiday_boost = HolidayCalendar.get_holiday_boost(
                future_date.strftime("%Y-%m-%d"), 
                self.holidays
            )
            demand_llm *= holiday_boost
            
            # ===== PROPHET-BASED PREDICTION =====
            if prophet_forecast is not None and i < len(prophet_forecast):
                demand_prophet = prophet_forecast.iloc[i]['yhat']
            else:
                demand_prophet = demand_llm  # Fallback to LLM
            
            # ===== HYBRID BLEND =====
            # Weighted average: more weight to LLM for interpretability
            llm_weight = 1.0 - prophet_weight
            demand_hybrid = (demand_llm * llm_weight) + (demand_prophet * prophet_weight)
            
            # Apply constraints
            demand_hybrid = int(round(demand_hybrid))
            demand_hybrid = min(demand_hybrid, int(daily_physical_cap * 0.95))
            demand_hybrid = max(demand_hybrid, historical_floor)
            
            # Calculate bounds
            if history_data and len(history_data) >= 7:
                recent_values = [float(r[1]) for r in history_data[-14:]]
                volatility = np.std(recent_values[-7:]) / max(historical_baseline, 1)
            else:
                volatility = 0.25
            
            uncertainty_range = np.clip(0.15 + volatility, 0.15, 0.35)
            lower = int(demand_hybrid * (1 - uncertainty_range))
            upper = int(demand_hybrid * (1 + uncertainty_range))
            
            forecast_data.append({
                'ds': future_date,
                'yhat': demand_hybrid,
                'yhat_lower': max(lower, historical_floor),
                'yhat_upper': min(upper, int(daily_physical_cap * 0.95)),
                
                # Store components for analysis
                'baseline': historical_baseline,
                'demand_llm': int(demand_llm),
                'demand_prophet': int(demand_prophet) if prophet_forecast is not None else None,
                'prophet_weight': prophet_weight,
                'llm_weight': llm_weight,
                
                # LLM metadata
                'llm_confidence': llm_result.get('confidence', 0.5) if i == 0 else None,
                'llm_trend_direction': llm_result.get('trend_direction', 'stable') if i == 0 else None,
                'llm_risk_factors': llm_result.get('risk_factors', []) if i == 0 else None,
            })
        
        return pd.DataFrame(forecast_data)
    
    def _format_prophet_only(self, prophet_forecast: pd.DataFrame, 
                            historical_baseline: float,
                            historical_floor: int,
                            daily_physical_cap: int,
                            llm_result: Dict) -> pd.DataFrame:
        """Format Prophet-only forecast when LLM fails"""
        
        forecast_data = []
        for i, row in prophet_forecast.iterrows():
            forecast_data.append({
                'ds': row['ds'],
                'yhat': int(row['yhat']),
                'yhat_lower': max(int(row['yhat_lower']), historical_floor),
                'yhat_upper': min(int(row['yhat_upper']), int(daily_physical_cap * 0.95)),
                'baseline': historical_baseline,
                'demand_llm': None,
                'demand_prophet': int(row['yhat']),
                'prophet_weight': 1.0,
                'llm_weight': 0.0,
            })
        
        return pd.DataFrame(forecast_data)
    
    def _fallback_forecast(self, history_data: List[tuple], periods: int,
                          movie_title: str, market_pressure: float,
                          daily_physical_cap: int, start_date: date) -> pd.DataFrame:
        """Deterministic fallback when both Prophet and LLM fail"""
        
        if not history_data:
            trend_factor = get_trend_factor(movie_title, self.trend_data)
            base_fill_rate = 0.30 + min((trend_factor - 1.0) * 0.20, 0.15)
            base_fill_rate = np.clip(base_fill_rate, 0.25, 0.50)
            base_demand = int(daily_physical_cap * base_fill_rate)
        else:
            values = [float(row[1]) for row in history_data]
            base_demand = max(int(np.mean(values[-14:])), int(daily_physical_cap * 0.15))
        
        movie_trends = self.trend_data.get(movie_title, [])
        trend_momentum = TrendAnalyzer.calculate_trend_momentum(movie_trends) if movie_trends else 1.0
        trend_factor = get_trend_factor(movie_title, self.trend_data)
        
        future_dates = pd.date_range(start=start_date, periods=periods)
        day_factors = {0: 0.80, 1: 0.82, 2: 0.88, 3: 0.90, 4: 1.15, 5: 1.25, 6: 1.18}
        
        predictions = []
        for i, future_date in enumerate(future_dates):
            day_factor = day_factors[future_date.dayofweek]
            
            if trend_momentum > 1.05:
                time_factor = 1 + (i * 0.03)
            elif trend_momentum < 0.95:
                time_factor = max(0.85, 1 - (i * 0.04))
            else:
                time_factor = 1
            
            holiday_boost = HolidayCalendar.get_holiday_boost(
                future_date.strftime("%Y-%m-%d"), 
                self.holidays
            )
            
            total_market_penalty = np.clip(market_pressure, 0.0, 0.60)
            market_factor = np.exp(-0.5 * total_market_penalty)
            
            pred = (base_demand * day_factor * time_factor * 
                   trend_momentum * trend_factor * holiday_boost * market_factor)
            pred = max(int(daily_physical_cap * 0.10), int(pred))
            pred = min(pred, int(daily_physical_cap * 0.90))
            
            predictions.append({
                'ds': future_date,
                'yhat': pred,
                'yhat_lower': int(pred * 0.70),
                'yhat_upper': int(pred * 1.30)
            })
        
        return pd.DataFrame(predictions)
    
    def calculate_confidence(self, forecast_row: pd.Series, history_length: int,
                            competition_pressure: float, 
                            weekly_pattern_strength: float = 0.5) -> float:
        
        base = 0.40
        history_score = 0.20 * min(history_length / 30.0, 1.0)
        competition_score = 0.20 * (1.0 - competition_pressure)
        pattern_score = 0.20 * weekly_pattern_strength
        
        confidence = base + history_score + competition_score + pattern_score
        
        # Boost confidence if hybrid (Prophet + LLM)
        if 'prophet_weight' in forecast_row and forecast_row['prophet_weight'] > 0:
            hybrid_bonus = 0.10 * forecast_row['prophet_weight']
            confidence += hybrid_bonus
        
        confidence = np.clip(confidence, 0.50, 0.95)
        
        if 'llm_confidence' in forecast_row and pd.notna(forecast_row['llm_confidence']):
            llm_conf = float(forecast_row['llm_confidence'])
            llm_adjustment = (llm_conf - 0.7) * 0.10
            confidence += np.clip(llm_adjustment, -0.05, 0.05)
            confidence = np.clip(confidence, 0.50, 0.95)
        
        return round(confidence, 2)


def demand_forecast_node(state: OpsState):
    """Hybrid Prophet + LLM forecasting with constraint awareness"""
    forecast_days=state['forecast_days']
    db = SessionLocal()
    
    try:
        # Get movies
        movies_q = db.query(Movie)
        if state.get("movies"):
            movies_q = movies_q.filter(Movie.title.in_(state["movies"]))
        movies = movies_q.all()
        if not movies:
            return state
    
        titles = [m.title for m in movies]
        external_data = fetch_all_external_signals(titles)
        
        # Initialize HYBRID forecaster
        forecaster = HybridProphetLLMForecaster(
            trend_data=external_data["trends"],
            holidays=external_data["holidays"]
        )
        
        # Calculate physical capacity
        total_seats = db.execute(text("SELECT COUNT(*) FROM seats")).scalar() or 1000
        avg_shows_per_day = float(db.execute(text("""
            SELECT COALESCE(COUNT(*) / 7.0, 3)
            FROM shows
            WHERE show_date >= CURRENT_DATE - INTERVAL '7 day'
        """)).scalar() or 3)
        
        daily_physical_cap = int(total_seats * avg_shows_per_day * 1.2)
        requested_movies = set(state.get("movies") or [])
        max_screen_capacity = max(
    db.execute(
        text("SELECT COUNT(*) FROM seats WHERE screen_id = :sid"),
        {"sid": screen.screen_id}
    ).scalar() or 100
    for screen in db.query(Screen).filter(Screen.is_available == True).all()
)      

        # Calculate competition pressure
        movie_totals = {}
        for m in movies:
            if requested_movies and m.title not in requested_movies:
                continue
            raw = get_daily_booking_series(m.movie_id, 30, db)
            total = sum(float(r[1]) for r in raw if r and len(r) >= 2) if raw else 1
            movie_totals[m.movie_id] = float(total)
        
        total_market = float(sum(movie_totals.values())) or 1.0
        
        market_pressure = {}
        for movie_id, total in movie_totals.items():
            market_share = total / max(total_market, 1)
            pressure = 1.0 - market_share
            pressure = 0.15 + (pressure * 0.60)
            market_pressure[movie_id] = np.clip(pressure, 0.15, 0.75)
        
        # Generate forecasts
        start_date = date.today() + timedelta(days=1)
        forecasts = []
        
        for movie in movies:
            if requested_movies and movie.title not in requested_movies:
                continue
            
            raw_history = get_daily_booking_series(movie.movie_id, 60, db)
            pressure = market_pressure.get(movie.movie_id, 0.5)
            
            # Calculate velocity
            if raw_history and len(raw_history) >= 14:
                values = [float(r[1]) for r in raw_history]
                recent_avg = np.mean(values[-7:])
                past_avg = np.mean(values[-14:-7])
                velocity = recent_avg / max(past_avg, 1)
                velocity = np.clip(velocity, 0.70, 1.30)
            else:
                velocity = 1.0
            
            if not raw_history:
                # Cold start for new movies
                trend_factor = get_trend_factor(movie.title, external_data["trends"])
                base_fill_ratio = 0.30 + min((trend_factor - 1.0) * 0.25, 0.15)
                base_fill_ratio = np.clip(base_fill_ratio, 0.25, 0.50)

                for i in range(forecast_days):
                    forecast_date = start_date + timedelta(days=i)
                    dow = forecast_date.weekday()
                    day_multiplier = {0: 0.95, 1: 0.92, 2: 0.90, 3: 0.92, 4: 1.20, 5: 1.30, 6: 1.22}[dow]
                    decay_factor = max(0.75, 1 - 0.05 * i)
                    holiday_boost = HolidayCalendar.get_holiday_boost(str(forecast_date), external_data["holidays"])
                    
                    demand = daily_physical_cap * base_fill_ratio * day_multiplier * decay_factor * holiday_boost
                    demand = min(demand, daily_physical_cap * 0.95)
                    demand = max(daily_physical_cap * 0.15, int(demand))
                    
                    confidence = min(0.60 + (trend_factor - 1.0) * 0.25, 0.85)
                    
                    forecasts.append({
                        "movie_id": movie.movie_id,
                        "movie": movie.title,
                        "date": str(forecast_date),
                        "movie_day_demand": int(demand),
                        "velocity": 1.0,
                        "market_pressure": round(pressure, 3),
                        "physical_cap": daily_physical_cap,
                        "confidence": round(confidence, 2),
                        "forecast_method": "cold_start_enhanced",
                        "holiday_boost": round(holiday_boost, 2),
                        "trend_factor": round(trend_factor, 2),
                        "is_holiday": holiday_boost > 1.0
                    })
                
                continue
            
            forecast_df = forecaster.hybrid_forecast(
                raw_history, movie.title, forecast_days, 
                pressure, daily_physical_cap, start_date, velocity
            )
            
            if 'prophet_weight' in forecast_df.columns and forecast_df['prophet_weight'].iloc[0] > 0:
                method = "hybrid_prophet_llm"
            elif 'llm_confidence' in forecast_df.columns and pd.notna(forecast_df['llm_confidence'].iloc[0]):
                method = "llm_only"
            else:
                method = "deterministic_fallback"
            
            # Convert to output
            for idx, row in forecast_df.iterrows():
                forecast_date = row['ds'].date()
                demand = int(round(row['yhat']))
                demand = min(demand, int(daily_physical_cap * 0.95))
                
                confidence = forecaster.calculate_confidence(row, len(raw_history), pressure)
                if method == "deterministic_fallback":
                    confidence *= 0.85
                
                holiday_boost = HolidayCalendar.get_holiday_boost(str(forecast_date), external_data["holidays"])
                
                forecast_item = {
                    "movie_id": movie.movie_id,
                    "movie": movie.title,
                    "date": str(forecast_date),
                    "movie_day_demand": demand,
                    "velocity": round(velocity, 3),
                    "market_pressure": round(pressure, 3),
                    "physical_cap": daily_physical_cap,
                    "confidence": round(confidence, 2),
                    "forecast_method": method,
                    "prediction_lower": int(row['yhat_lower']),
                    "prediction_upper": int(row['yhat_upper']),
                    "holiday_boost": round(holiday_boost, 2),
                    "is_holiday": holiday_boost > 1.0
                }
                
                # Add hybrid metadata
                if idx == 0:
                    if pd.notna(row.get('llm_trend_direction')):
                        forecast_item['llm_trend_direction'] = row['llm_trend_direction']
                    if 'prophet_weight' in row:
                        forecast_item['prophet_contribution'] = round(row['prophet_weight'], 2)
                
                forecasts.append(forecast_item)
        
        state.setdefault("result", {})
        state["result"]["forecast"] = forecasts
        state["forecast_scope"] = "movie_day"
        state["external_signals"] = external_data
        
        hybrid_count = sum(1 for f in forecasts if f.get("forecast_method") == "hybrid_prophet_llm")
        llm_count = sum(1 for f in forecasts if f.get("forecast_method") == "llm_only")
        avg_confidence = np.mean([f['confidence'] for f in forecasts]) if forecasts else 0
        
        state["output"] = (
            f"Hybrid Forecast: {hybrid_count} Prophet+LLM hybrid, "
            f"{llm_count} LLM-only, "
            f"{len(forecasts)-hybrid_count-llm_count} fallback. "
            f"Avg confidence: {avg_confidence:.2f}"
        )
        
    except Exception as e:
        state["error"] = f"Demand forecast node failed: {str(e)}"
        
    finally:
        db.close()

    return state