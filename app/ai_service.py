from typing import List, Dict, Any, Optional
import asyncio
import logging
from datetime import datetime, timedelta
import json

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .models import Usage, APIKey, User, Project
from .config import settings

logger = logging.getLogger(__name__)

class AIService:
    """AI-powered analytics and insights service for Storm platform"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=getattr(settings, 'OPENAI_API_KEY', None)
        )
        self.anomaly_detector = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42
        )
        self.scaler = StandardScaler()
        self._model_trained = False
    
    async def analyze_api_usage(self, db: Session, user_id: int, days: int = 7) -> Dict[str, Any]:
        """Analyze API usage patterns and detect anomalies"""
        try:
            # Get usage data for the specified period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            usage_data = db.query(Usage).filter(
                Usage.user_id == user_id,
                Usage.timestamp >= start_date,
                Usage.timestamp <= end_date
            ).all()
            
            if not usage_data:
                return {
                    "status": "no_data",
                    "message": "No usage data available for analysis",
                    "anomalies": [],
                    "insights": []
                }
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame([
                {
                    "timestamp": usage.timestamp,
                    "endpoint": usage.endpoint,
                    "method": usage.method,
                    "status_code": usage.status_code,
                    "response_time": float(usage.response_time or 0),
                    "hour": usage.timestamp.hour,
                    "day_of_week": usage.timestamp.weekday()
                }
                for usage in usage_data
            ])
            
            # Detect anomalies
            anomalies = await self._detect_anomalies(df)
            
            # Generate insights
            insights = await self._generate_usage_insights(df)
            
            return {
                "status": "success",
                "total_requests": len(df),
                "anomalies": anomalies,
                "insights": insights,
                "analysis_period": f"{days} days",
                "avg_response_time": df["response_time"].mean(),
                "error_rate": len(df[df["status_code"] >= 400]) / len(df) * 100
            }
            
        except Exception as e:
            logger.error(f"Error analyzing API usage: {str(e)}")
            return {
                "status": "error",
                "message": f"Analysis failed: {str(e)}",
                "anomalies": [],
                "insights": []
            }
    
    async def _detect_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in API usage patterns"""
        if len(df) < 10:  # Need minimum data for anomaly detection
            return []
        
        try:
            # Prepare features for anomaly detection
            features = df[[
                "response_time", "status_code", "hour", "day_of_week"
            ]].copy()
            
            # Handle missing values
            features = features.fillna(0)
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features)
            
            # Detect anomalies
            anomaly_labels = self.anomaly_detector.fit_predict(features_scaled)
            
            # Get anomalous records
            anomalies = []
            for idx, label in enumerate(anomaly_labels):
                if label == -1:  # Anomaly detected
                    anomaly_record = df.iloc[idx]
                    anomalies.append({
                        "timestamp": anomaly_record["timestamp"].isoformat(),
                        "endpoint": anomaly_record["endpoint"],
                        "method": anomaly_record["method"],
                        "status_code": int(anomaly_record["status_code"]),
                        "response_time": float(anomaly_record["response_time"]),
                        "anomaly_type": self._classify_anomaly(anomaly_record),
                        "severity": self._calculate_anomaly_severity(anomaly_record, df)
                    })
            
            return anomalies[:10]  # Return top 10 anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {str(e)}")
            return []
    
    def _classify_anomaly(self, record: pd.Series) -> str:
        """Classify the type of anomaly"""
        if record["status_code"] >= 500:
            return "server_error"
        elif record["status_code"] >= 400:
            return "client_error"
        elif record["response_time"] > 5000:  # > 5 seconds
            return "slow_response"
        elif record["hour"] < 6 or record["hour"] > 22:
            return "unusual_time"
        else:
            return "pattern_deviation"
    
    def _calculate_anomaly_severity(self, record: pd.Series, df: pd.DataFrame) -> str:
        """Calculate severity of anomaly"""
        response_time_percentile = (df["response_time"] < record["response_time"]).mean()
        
        if record["status_code"] >= 500 or response_time_percentile > 0.95:
            return "high"
        elif record["status_code"] >= 400 or response_time_percentile > 0.8:
            return "medium"
        else:
            return "low"
    
    async def _generate_usage_insights(self, df: pd.DataFrame) -> List[str]:
        """Generate human-readable insights from usage data"""
        insights = []
        
        try:
            # Peak usage hours
            hourly_usage = df.groupby("hour").size()
            peak_hour = hourly_usage.idxmax()
            insights.append(f"Peak usage occurs at {peak_hour}:00 with {hourly_usage.max()} requests")
            
            # Most used endpoints
            endpoint_usage = df.groupby("endpoint").size().sort_values(ascending=False)
            if len(endpoint_usage) > 0:
                top_endpoint = endpoint_usage.index[0]
                insights.append(f"Most popular endpoint: {top_endpoint} ({endpoint_usage.iloc[0]} requests)")
            
            # Error rate analysis
            error_rate = len(df[df["status_code"] >= 400]) / len(df) * 100
            if error_rate > 5:
                insights.append(f"High error rate detected: {error_rate:.1f}% (consider investigation)")
            elif error_rate < 1:
                insights.append(f"Excellent API reliability: {error_rate:.1f}% error rate")
            
            # Response time analysis
            avg_response_time = df["response_time"].mean()
            if avg_response_time > 1000:
                insights.append(f"Average response time is high: {avg_response_time:.0f}ms (consider optimization)")
            elif avg_response_time < 200:
                insights.append(f"Excellent performance: {avg_response_time:.0f}ms average response time")
            
            # Usage patterns
            weekend_usage = df[df["day_of_week"].isin([5, 6])]
            weekday_usage = df[~df["day_of_week"].isin([5, 6])]
            
            if len(weekend_usage) > 0 and len(weekday_usage) > 0:
                weekend_avg = len(weekend_usage) / 2  # 2 weekend days
                weekday_avg = len(weekday_usage) / 5  # 5 weekdays
                
                if weekend_avg > weekday_avg * 1.2:
                    insights.append("Higher usage on weekends - consider weekend-specific scaling")
                elif weekday_avg > weekend_avg * 2:
                    insights.append("Business-hours focused usage pattern detected")
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return ["Unable to generate insights due to data processing error"]
    
    async def generate_ai_insights(self, usage_data: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI-powered insights using OpenAI"""
        if not self.openai_client.api_key:
            return {
                "status": "error",
                "message": "OpenAI API key not configured",
                "insights": []
            }
        
        try:
            # Prepare context for AI analysis
            context = {
                "total_requests": usage_data.get("total_requests", 0),
                "error_rate": usage_data.get("error_rate", 0),
                "avg_response_time": usage_data.get("avg_response_time", 0),
                "anomalies_count": len(usage_data.get("anomalies", [])),
                "user_plan": user_context.get("subscription_plan", "free"),
                "api_keys_count": user_context.get("api_keys_count", 0)
            }
            
            prompt = f"""
            Analyze the following API usage data and provide actionable insights:
            
            Usage Summary:
            - Total Requests: {context['total_requests']}
            - Error Rate: {context['error_rate']:.1f}%
            - Average Response Time: {context['avg_response_time']:.0f}ms
            - Anomalies Detected: {context['anomalies_count']}
            - User Plan: {context['user_plan']}
            - Active API Keys: {context['api_keys_count']}
            
            Please provide:
            1. Performance assessment (1-2 sentences)
            2. Specific recommendations for improvement (2-3 actionable items)
            3. Potential issues to monitor (1-2 items)
            
            Keep the response concise and actionable for a technical user.
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert API performance analyst. Provide clear, actionable insights based on usage data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            ai_insights = response.choices[0].message.content.strip()
            
            return {
                "status": "success",
                "ai_insights": ai_insights,
                "model_used": "gpt-3.5-turbo",
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to generate AI insights: {str(e)}",
                "ai_insights": ""
            }
    
    async def predict_usage_trends(self, db: Session, user_id: int, days_ahead: int = 7) -> Dict[str, Any]:
        """Predict future usage trends based on historical data"""
        try:
            # Get historical data (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            usage_data = db.query(
                func.date(Usage.timestamp).label('date'),
                func.count(Usage.id).label('request_count')
            ).filter(
                Usage.user_id == user_id,
                Usage.timestamp >= start_date,
                Usage.timestamp <= end_date
            ).group_by(
                func.date(Usage.timestamp)
            ).all()
            
            if len(usage_data) < 7:  # Need at least a week of data
                return {
                    "status": "insufficient_data",
                    "message": "Need at least 7 days of historical data for predictions",
                    "predictions": []
                }
            
            # Simple trend analysis (can be enhanced with more sophisticated models)
            df = pd.DataFrame(usage_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculate moving average and trend
            df['moving_avg'] = df['request_count'].rolling(window=7, min_periods=1).mean()
            recent_avg = df['moving_avg'].tail(7).mean()
            
            # Simple linear trend
            x = np.arange(len(df))
            y = df['request_count'].values
            trend = np.polyfit(x, y, 1)[0]  # Linear trend coefficient
            
            # Generate predictions
            predictions = []
            for i in range(days_ahead):
                predicted_date = end_date + timedelta(days=i+1)
                predicted_count = max(0, int(recent_avg + trend * i))
                
                predictions.append({
                    "date": predicted_date.strftime("%Y-%m-%d"),
                    "predicted_requests": predicted_count,
                    "confidence": "medium" if len(df) > 14 else "low"
                })
            
            return {
                "status": "success",
                "predictions": predictions,
                "trend_direction": "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable",
                "historical_average": int(recent_avg),
                "data_points_used": len(df)
            }
            
        except Exception as e:
            logger.error(f"Error predicting usage trends: {str(e)}")
            return {
                "status": "error",
                "message": f"Prediction failed: {str(e)}",
                "predictions": []
            }

# Global AI service instance
ai_service = AIService()