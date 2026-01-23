
from datetime import date, timedelta, datetime
from sqlalchemy import text
from database import SessionLocal
from model import Movie
from agent.state import OpsState
from agent.tools.booking_history_tool import get_daily_booking_series
from agent.tools.external_signals import fetch_all_external_signals, TrendAnalyzer, HolidayCalendar, get_trend_factor
import pandas as pd
import numpy as np
from typing import List, Dict
import warnings
warnings.filterwarnings('ignore')

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

FORECAST_DAYS = 7


class EnhancedMovieDemandForecaster:
    """Prophet forecaster with external signals"""
    
    def __init__(self, trend_data: Dict = None, holidays: List[Dict] = None):
        self.trend_data = trend_data or {}
        self.holidays = holidays or []
        self.models = {}
    
    def prepare_data_with_regressors(self, history_data: List[tuple], 
                                     movie_title: str) -> pd.DataFrame:
        """Prepare data with trend and holiday regressors"""
        
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
            trend_df['trend_score'] = trend_df['value'] / 100.0  # Normalize to 0-1
            
            df = df.merge(trend_df[['ds', 'trend_score']], on='ds', how='left')
            df['trend_score'] = df['trend_score'].fillna(0.5)  # Default if missing
        else:
            df['trend_score'] = 0.5
        
        # Add holiday indicator
        df['is_holiday'] = df['ds'].apply(
            lambda x: 1 if HolidayCalendar.is_holiday(x.strftime("%Y-%m-%d"), self.holidays) else 0
        )
        
        # Add holiday boost
        df['holiday_boost'] = df['ds'].apply(
            lambda x: HolidayCalendar.get_holiday_boost(x.strftime("%Y-%m-%d"), self.holidays)
        )
        
        return df
    
    def fit_predict_with_regressors(self, df: pd.DataFrame, periods: int,
                                    movie_title: str, competition: float) -> pd.DataFrame:
        """Fit Prophet with external regressors"""
        
        if len(df) < 7:
            return self._fallback_forecast(df, periods, movie_title, competition)
        
        # Configure Prophet with regressors
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
        
        # Add future trend scores
        future_start = df['ds'].max() + timedelta(days=1)
        future_dates = pd.date_range(start=future_start, periods=periods)
        
        # Extrapolate trend (use last 7 days average)
        recent_trend = df['trend_score'].tail(7).mean() if 'trend_score' in df.columns else 0.5
        future['trend_score'] = future['ds'].apply(
            lambda x: recent_trend if x >= future_start else 
            df[df['ds'] == x]['trend_score'].values[0] if x in df['ds'].values else recent_trend
        )
        
        # Add future holiday boost
        future['holiday_boost'] = future['ds'].apply(
            lambda x: HolidayCalendar.get_holiday_boost(x.strftime("%Y-%m-%d"), self.holidays)
        )
        
        # Predict
        forecast = model.predict(future)
        
        # Extract future predictions
        forecast = forecast.tail(periods)
        
        # Apply competition penalty
        forecast['yhat'] = forecast['yhat'] * (1 - competition * 0.3)
        forecast['yhat_lower'] = forecast['yhat_lower'] * (1 - competition * 0.3)
        forecast['yhat_upper'] = forecast['yhat_upper'] * (1 - competition * 0.3)
        
        # Ensure non-negative
        forecast['yhat'] = forecast['yhat'].clip(lower=1)
        forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=1)
        forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=1)
        
        return forecast
    
    def _fallback_forecast(self, df: pd.DataFrame, periods: int,
                          movie_title: str, competition: float) -> pd.DataFrame:
        """Deterministic fallback with external signals"""
        
        if len(df) == 0:
            base_demand = 30
        else:
            base_demand = df['y'].mean()
        
        # Get recent trend momentum
        movie_trends = self.trend_data.get(movie_title, [])
        trend_momentum = TrendAnalyzer.calculate_trend_momentum(movie_trends) if movie_trends else 1.0
        trend_factor = get_trend_factor(movie_title, self.trend_data)
        # Generate dates
        last_date = df['ds'].max() if len(df) > 0 else pd.Timestamp.now()
        future_dates = pd.date_range(start=last_date + timedelta(days=1), periods=periods)
        
        # Weekly pattern
        day_factors = {0: 0.85, 1: 0.85, 2: 0.9, 3: 0.9, 4: 1.1, 5: 1.2, 6: 1.15}
        
        predictions = []
        for i, future_date in enumerate(future_dates):
            day_factor = day_factors[future_date.dayofweek]
            growth_factor = 1 + (i * 0.02)
            
            # Apply holiday boost
            holiday_boost = HolidayCalendar.get_holiday_boost(
                future_date.strftime("%Y-%m-%d"), 
                self.holidays
            )
            
            pred = (base_demand * day_factor * growth_factor * 
                   trend_momentum * trend_factor * holiday_boost * (1 - competition * 0.3))
            pred = max(1, pred)
            
            predictions.append({
                'ds': future_date,
                'yhat': pred,
                'yhat_lower': pred * 0.7,
                'yhat_upper': pred * 1.3
            })
        
        return pd.DataFrame(predictions)
    
    def calculate_confidence(self, forecast_row: pd.Series, history_length: int,
                           competition: float) -> float:
        """Dynamic confidence"""
        
        pred_range = forecast_row['yhat_upper'] - forecast_row['yhat_lower']
        pred_value = forecast_row['yhat']
        
        if pred_value > 0:
            uncertainty = pred_range / pred_value
            interval_conf = 1 - min(uncertainty, 0.5)
        else:
            interval_conf = 0.5
        
        # History bonus
        if history_length >= 30:
            history_bonus = 0.2
        elif history_length >= 14:
            history_bonus = 0.1
        else:
            history_bonus = 0
        
        # Competition penalty
        competition_penalty = competition * 0.2
        
        confidence = interval_conf + history_bonus - competition_penalty
        
        return round(max(0.45, min(confidence, 0.92)), 2)


def demand_forecast_node(state: OpsState):
    """Enhanced forecasting with external signals"""
    
    db = SessionLocal()
    
    # Get movies
    movies_q = db.query(Movie)
    if state.get("movies"):
        movies_q = movies_q.filter(Movie.title.in_(state["movies"]))
    movies = movies_q.all()
    
    if not movies:
        db.close()
        return state
    
    titles = [m.title for m in movies]
    external_data = fetch_all_external_signals(titles)
    
    forecaster = EnhancedMovieDemandForecaster(
        trend_data=external_data["trends"],
        holidays=external_data["holidays"]
    )
    
    # Calculate physical capacity
    total_seats = db.execute(text("SELECT COUNT(*) FROM seats")).scalar() or 1
    avg_shows_per_day = float(db.execute(text("""
        SELECT COALESCE(COUNT(*) / 7.0, 1)
        FROM shows
        WHERE show_date >= CURRENT_DATE - INTERVAL '7 day'
    """)).scalar() or 1)
    
    daily_physical_cap = int(total_seats * avg_shows_per_day * 1.2)
    
    # Calculate competition
    movie_totals = {}
    for m in movies:
        raw = get_daily_booking_series(m.movie_id, 30, db)
        total = sum(float(r[1]) for r in raw if r and len(r) >= 2) if raw else 1
        movie_totals[m.movie_id] = float(total)
    
    total_market = float(sum(movie_totals.values())) or 1.0
    
    # Generate forecasts
    start_date = date.today() + timedelta(days=1)
    forecasts = []
    
    for movie in movies:
        raw_history = get_daily_booking_series(movie.movie_id, 60, db)
        
        if not raw_history:
            # New movie baseline
            avg_demand = total_market / len(movies) / 30 if len(movies) > 0 else 30
            for i in range(FORECAST_DAYS):
                forecast_date = start_date + timedelta(days=i)
                day_multiplier = [0.95, 1.0, 1.05, 1.08, 1.12, 1.18, 1.22][i]
                
                holiday_boost = HolidayCalendar.get_holiday_boost(
                    str(forecast_date),
                    external_data["holidays"]
                )
                trend_factor = get_trend_factor(movie.title, external_data["trends"])
                forecasts.append({
                    "movie_id": movie.movie_id,
                    "movie": movie.title,
                    "date": str(forecast_date),
                    "movie_day_demand": int(avg_demand * day_multiplier * holiday_boost*trend_factor),
                    "velocity": 1.0,
                    "competition": round(1.0 / len(movies), 3),
                    "physical_cap": daily_physical_cap,
                    "confidence": 0.55,
                    "forecast_method": "new_movie_baseline",
                    "holiday_boost": holiday_boost
                })
            continue
        
        df = forecaster.prepare_data_with_regressors(raw_history, movie.title)
        
        if df.empty:
            continue
        
        competition = movie_totals[movie.movie_id] / total_market
        
        # Generate ML forecast
        if PROPHET_AVAILABLE and len(df) >= 7:
            forecast_df = forecaster.fit_predict_with_regressors(
                df, FORECAST_DAYS, movie.title, competition
            )
            method = "prophet_ml_enhanced"
        else:
            forecast_df = forecaster._fallback_forecast(
                df, FORECAST_DAYS, movie.title, competition
            )
            method = "deterministic_enhanced"
        
        # Convert to output
        for idx, row in forecast_df.iterrows():
            forecast_date = row['ds'].date()
            demand = int(round(row['yhat']))
            demand = min(demand, daily_physical_cap)
            demand = max(demand, 1)
            
            # Velocity
            recent_avg = df['y'].tail(7).mean()
            past_avg = df['y'].head(len(df) - 7).mean() if len(df) > 14 else recent_avg
            velocity = round(recent_avg / max(past_avg, 1), 2)
            velocity = max(0.5, min(velocity, 2.0))
            
            # Confidence
            confidence = forecaster.calculate_confidence(row, len(df), competition)
            
            # Holiday boost
            holiday_boost = HolidayCalendar.get_holiday_boost(
                str(forecast_date),
                external_data["holidays"]
            )
            
            forecasts.append({
                "movie_id": movie.movie_id,
                "movie": movie.title,
                "date": str(forecast_date),
                "movie_day_demand": demand,
                "velocity": velocity,
                "competition": round(competition, 3),
                "physical_cap": daily_physical_cap,
                "confidence": confidence,
                "forecast_method": method,
                "prediction_lower": int(row['yhat_lower']),
                "prediction_upper": int(row['yhat_upper']),
                "holiday_boost": round(holiday_boost, 2),
                "is_holiday": holiday_boost > 1.0
            })
    
    db.close()
    
    state.setdefault("result", {})
    state["result"]["forecast"] = forecasts
    state["forecast_scope"] = "movie_day"
    state["external_signals"] = external_data
    
    ml_count = sum(1 for f in forecasts if "prophet" in f.get("forecast_method", ""))
    holiday_count = sum(1 for f in forecasts if f.get("is_holiday", False))
    
    state["output"] = (
        f"Enhanced ML Forecast: {ml_count} Prophet + external signals, "
        f"{len(forecasts)-ml_count} deterministic. "
        f"{holiday_count} holiday dates detected."
    )
    
    return state