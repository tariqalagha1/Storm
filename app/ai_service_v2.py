from typing import List, Dict, Any, Optional, AsyncGenerator
import asyncio
import logging
from datetime import datetime, timedelta
import json
import uuid
from enum import Enum

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import tensorflow as tf
from tensorflow import keras
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import redis
from prometheus_client import Counter, Histogram, Gauge
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
from loguru import logger

from .models import Usage, APIKey, User, Project
from .config import settings
from .ai_service import AIService

# Prometheus metrics
api_requests_total = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
api_request_duration = Histogram('api_request_duration_seconds', 'API request duration')
active_users = Gauge('active_users_total', 'Number of active users')
ai_model_predictions = Counter('ai_model_predictions_total', 'Total AI model predictions', ['model_type'])

class ModelType(Enum):
    ANOMALY_DETECTION = "anomaly_detection"
    USAGE_PREDICTION = "usage_prediction"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    CUSTOM_ML = "custom_ml"

class AIMarketplaceService:
    """AI-as-a-Service marketplace for custom AI endpoints"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            decode_responses=True
        )
        self.available_models = {}
        self.custom_endpoints = {}
    
    async def register_ai_model(self, model_id: str, model_config: Dict[str, Any]) -> Dict[str, Any]:
        """Register a new AI model in the marketplace"""
        try:
            model_info = {
                "id": model_id,
                "name": model_config.get("name"),
                "description": model_config.get("description"),
                "model_type": model_config.get("type"),
                "pricing": model_config.get("pricing", {"per_request": 0.01}),
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "usage_count": 0,
                "rating": 0.0
            }
            
            # Store in Redis
            await self.redis_client.hset(f"ai_model:{model_id}", mapping=model_info)
            await self.redis_client.sadd("ai_models", model_id)
            
            self.available_models[model_id] = model_info
            
            return {
                "success": True,
                "model_id": model_id,
                "message": "AI model registered successfully"
            }
            
        except Exception as e:
            logger.error(f"Error registering AI model: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def create_custom_endpoint(self, user_id: int, endpoint_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a custom AI endpoint for a user"""
        try:
            endpoint_id = str(uuid.uuid4())
            endpoint_path = f"/api/ai/custom/{endpoint_id}"
            
            endpoint_info = {
                "id": endpoint_id,
                "user_id": user_id,
                "name": endpoint_config.get("name"),
                "description": endpoint_config.get("description"),
                "model_id": endpoint_config.get("model_id"),
                "path": endpoint_path,
                "created_at": datetime.now().isoformat(),
                "status": "active",
                "request_count": 0,
                "revenue_generated": 0.0
            }
            
            # Store endpoint info
            await self.redis_client.hset(f"custom_endpoint:{endpoint_id}", mapping=endpoint_info)
            await self.redis_client.sadd(f"user_endpoints:{user_id}", endpoint_id)
            
            self.custom_endpoints[endpoint_id] = endpoint_info
            
            return {
                "success": True,
                "endpoint_id": endpoint_id,
                "endpoint_path": endpoint_path,
                "message": "Custom AI endpoint created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating custom endpoint: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_marketplace_models(self) -> List[Dict[str, Any]]:
        """Get all available AI models in the marketplace"""
        try:
            model_ids = await self.redis_client.smembers("ai_models")
            models = []
            
            for model_id in model_ids:
                model_info = await self.redis_client.hgetall(f"ai_model:{model_id}")
                if model_info:
                    models.append(model_info)
            
            return models
            
        except Exception as e:
            logger.error(f"Error fetching marketplace models: {str(e)}")
            return []

class RealTimeMonitoringService:
    """Real-time monitoring and alerting service"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            decode_responses=True
        )
        self.alert_thresholds = {
            "error_rate": 5.0,  # 5%
            "response_time": 2000,  # 2 seconds
            "request_rate": 1000,  # requests per minute
            "anomaly_score": 0.8
        }
        self.active_alerts = {}
    
    async def process_real_time_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Process real-time metrics and trigger alerts if needed"""
        try:
            timestamp = datetime.now().isoformat()
            
            # Store metrics in Redis with TTL
            await self.redis_client.setex(
                f"metrics:{timestamp}",
                3600,  # 1 hour TTL
                json.dumps(metrics)
            )
            
            # Check for alert conditions
            alerts = await self._check_alert_conditions(metrics)
            
            # Update Prometheus metrics
            if 'endpoint' in metrics and 'method' in metrics and 'status_code' in metrics:
                api_requests_total.labels(
                    endpoint=metrics['endpoint'],
                    method=metrics['method'],
                    status=str(metrics['status_code'])
                ).inc()
            
            if 'response_time' in metrics:
                api_request_duration.observe(metrics['response_time'] / 1000)  # Convert to seconds
            
            return {
                "success": True,
                "alerts_triggered": len(alerts),
                "alerts": alerts,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error processing real-time metrics: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _check_alert_conditions(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any alert conditions are met"""
        alerts = []
        
        # Error rate alert
        if metrics.get('error_rate', 0) > self.alert_thresholds['error_rate']:
            alert = {
                "type": "error_rate",
                "severity": "high",
                "message": f"Error rate {metrics['error_rate']:.1f}% exceeds threshold {self.alert_thresholds['error_rate']}%",
                "timestamp": datetime.now().isoformat(),
                "value": metrics['error_rate'],
                "threshold": self.alert_thresholds['error_rate']
            }
            alerts.append(alert)
        
        # Response time alert
        if metrics.get('avg_response_time', 0) > self.alert_thresholds['response_time']:
            alert = {
                "type": "response_time",
                "severity": "medium",
                "message": f"Response time {metrics['avg_response_time']:.0f}ms exceeds threshold {self.alert_thresholds['response_time']}ms",
                "timestamp": datetime.now().isoformat(),
                "value": metrics['avg_response_time'],
                "threshold": self.alert_thresholds['response_time']
            }
            alerts.append(alert)
        
        return alerts
    
    async def get_real_time_dashboard_data(self) -> Dict[str, Any]:
        """Get real-time dashboard data"""
        try:
            # Get recent metrics from Redis
            current_time = datetime.now()
            metrics_keys = []
            
            # Get metrics from last 5 minutes
            for i in range(300):  # 5 minutes * 60 seconds
                timestamp = (current_time - timedelta(seconds=i)).isoformat()
                key = f"metrics:{timestamp}"
                if await self.redis_client.exists(key):
                    metrics_keys.append(key)
            
            # Aggregate metrics
            total_requests = 0
            total_errors = 0
            response_times = []
            
            for key in metrics_keys[:50]:  # Limit to last 50 data points
                metrics_data = await self.redis_client.get(key)
                if metrics_data:
                    metrics = json.loads(metrics_data)
                    total_requests += metrics.get('request_count', 0)
                    total_errors += metrics.get('error_count', 0)
                    if 'avg_response_time' in metrics:
                        response_times.append(metrics['avg_response_time'])
            
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            avg_response_time = np.mean(response_times) if response_times else 0
            
            return {
                "success": True,
                "data": {
                    "total_requests": total_requests,
                    "error_rate": error_rate,
                    "avg_response_time": avg_response_time,
                    "active_alerts": len(self.active_alerts),
                    "last_updated": current_time.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time dashboard data: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

class AdvancedAIService(AIService):
    """Advanced AI service with Phase 2 capabilities"""
    
    def __init__(self):
        super().__init__()
        self.marketplace = AIMarketplaceService()
        self.monitoring = RealTimeMonitoringService()
        self.custom_models = {}
        self.model_registry = {}
        
        # Initialize MLflow
        mlflow.set_tracking_uri(getattr(settings, 'MLFLOW_TRACKING_URI', 'sqlite:///mlflow.db'))
        
        # Initialize TensorFlow models
        self._init_deep_learning_models()
    
    def _init_deep_learning_models(self):
        """Initialize deep learning models for advanced analytics"""
        try:
            # LSTM model for time series prediction
            self.lstm_model = keras.Sequential([
                keras.layers.LSTM(50, return_sequences=True, input_shape=(10, 1)),
                keras.layers.LSTM(50, return_sequences=False),
                keras.layers.Dense(25),
                keras.layers.Dense(1)
            ])
            self.lstm_model.compile(optimizer='adam', loss='mean_squared_error')
            
            # Autoencoder for anomaly detection
            self.autoencoder = keras.Sequential([
                keras.layers.Dense(32, activation='relu', input_shape=(10,)),
                keras.layers.Dense(16, activation='relu'),
                keras.layers.Dense(8, activation='relu'),
                keras.layers.Dense(16, activation='relu'),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(10, activation='sigmoid')
            ])
            self.autoencoder.compile(optimizer='adam', loss='mse')
            
            logger.info("Deep learning models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing deep learning models: {str(e)}")
    
    async def train_custom_model(self, user_id: int, model_config: Dict[str, Any], training_data: pd.DataFrame) -> Dict[str, Any]:
        """Train a custom ML model for a user"""
        try:
            model_id = str(uuid.uuid4())
            model_type = model_config.get('type', 'regression')
            
            with mlflow.start_run(run_name=f"custom_model_{model_id}"):
                # Prepare data
                X = training_data.drop(columns=[model_config['target_column']])
                y = training_data[model_config['target_column']]
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                
                # Train model based on type
                if model_type == 'regression':
                    model = RandomForestRegressor(n_estimators=100, random_state=42)
                    model.fit(X_train, y_train)
                    
                    # Evaluate
                    y_pred = model.predict(X_test)
                    mse = mean_squared_error(y_test, y_pred)
                    r2 = r2_score(y_test, y_pred)
                    
                    # Log to MLflow
                    mlflow.log_param("model_type", "random_forest_regression")
                    mlflow.log_metric("mse", mse)
                    mlflow.log_metric("r2_score", r2)
                    mlflow.sklearn.log_model(model, "model")
                    
                    metrics = {"mse": mse, "r2_score": r2}
                    
                elif model_type == 'deep_learning':
                    # Use LSTM for time series or neural network for other tasks
                    model = keras.Sequential([
                        keras.layers.Dense(64, activation='relu', input_shape=(X_train.shape[1],)),
                        keras.layers.Dropout(0.2),
                        keras.layers.Dense(32, activation='relu'),
                        keras.layers.Dense(1)
                    ])
                    
                    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
                    history = model.fit(X_train, y_train, epochs=50, batch_size=32, validation_split=0.2, verbose=0)
                    
                    # Evaluate
                    loss, mae = model.evaluate(X_test, y_test, verbose=0)
                    
                    # Log to MLflow
                    mlflow.log_param("model_type", "neural_network")
                    mlflow.log_metric("loss", loss)
                    mlflow.log_metric("mae", mae)
                    mlflow.tensorflow.log_model(model, "model")
                    
                    metrics = {"loss": loss, "mae": mae}
                
                # Store model info
                model_info = {
                    "id": model_id,
                    "user_id": user_id,
                    "type": model_type,
                    "name": model_config.get('name', f'Custom Model {model_id[:8]}'),
                    "description": model_config.get('description', ''),
                    "metrics": metrics,
                    "created_at": datetime.now().isoformat(),
                    "status": "trained",
                    "mlflow_run_id": mlflow.active_run().info.run_id
                }
                
                self.custom_models[model_id] = {
                    "model": model,
                    "info": model_info,
                    "scaler": StandardScaler().fit(X_train) if model_type != 'deep_learning' else None
                }
                
                # Register in marketplace
                await self.marketplace.register_ai_model(model_id, {
                    "name": model_info['name'],
                    "description": model_info['description'],
                    "type": model_type,
                    "pricing": {"per_request": 0.05}  # Custom models cost more
                })
                
                return {
                    "success": True,
                    "model_id": model_id,
                    "metrics": metrics,
                    "message": "Custom model trained successfully"
                }
                
        except Exception as e:
            logger.error(f"Error training custom model: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_advanced_visualizations(self, data: pd.DataFrame, chart_type: str = "usage_trends") -> Dict[str, Any]:
        """Generate advanced interactive visualizations using Plotly"""
        try:
            if chart_type == "usage_trends":
                fig = px.line(
                    data, 
                    x='timestamp', 
                    y='request_count',
                    title='API Usage Trends Over Time',
                    labels={'request_count': 'Requests', 'timestamp': 'Time'}
                )
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Number of Requests",
                    hovermode='x unified'
                )
                
            elif chart_type == "error_analysis":
                error_data = data.groupby(['timestamp', 'status_code']).size().reset_index(name='count')
                fig = px.bar(
                    error_data,
                    x='timestamp',
                    y='count',
                    color='status_code',
                    title='Error Analysis by Status Code',
                    labels={'count': 'Number of Requests', 'timestamp': 'Time'}
                )
                
            elif chart_type == "performance_heatmap":
                # Create heatmap of response times by hour and day
                data['hour'] = pd.to_datetime(data['timestamp']).dt.hour
                data['day'] = pd.to_datetime(data['timestamp']).dt.day_name()
                
                heatmap_data = data.groupby(['day', 'hour'])['response_time'].mean().reset_index()
                heatmap_pivot = heatmap_data.pivot(index='day', columns='hour', values='response_time')
                
                fig = px.imshow(
                    heatmap_pivot,
                    title='Response Time Heatmap (by Day and Hour)',
                    labels={'color': 'Avg Response Time (ms)'},
                    aspect='auto'
                )
                
            elif chart_type == "anomaly_detection":
                # Scatter plot with anomalies highlighted
                fig = px.scatter(
                    data,
                    x='timestamp',
                    y='response_time',
                    color='is_anomaly',
                    title='Anomaly Detection in Response Times',
                    labels={'response_time': 'Response Time (ms)', 'timestamp': 'Time'}
                )
                
            # Convert to JSON for frontend
            chart_json = json.dumps(fig, cls=PlotlyJSONEncoder)
            
            return {
                "success": True,
                "chart_data": chart_json,
                "chart_type": chart_type,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating visualization: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def intelligent_auto_scaling(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Provide intelligent auto-scaling recommendations"""
        try:
            # Analyze current load
            current_rps = current_metrics.get('requests_per_second', 0)
            current_response_time = current_metrics.get('avg_response_time', 0)
            current_error_rate = current_metrics.get('error_rate', 0)
            current_cpu_usage = current_metrics.get('cpu_usage', 0)
            current_memory_usage = current_metrics.get('memory_usage', 0)
            
            recommendations = []
            
            # Scale up conditions
            if current_response_time > 1000 and current_cpu_usage > 80:
                recommendations.append({
                    "action": "scale_up",
                    "reason": "High response time and CPU usage",
                    "suggested_instances": min(10, int(current_cpu_usage / 50)),
                    "priority": "high"
                })
            
            if current_rps > 100 and current_memory_usage > 85:
                recommendations.append({
                    "action": "scale_up",
                    "reason": "High request rate and memory usage",
                    "suggested_instances": min(5, int(current_rps / 50)),
                    "priority": "medium"
                })
            
            # Scale down conditions
            if current_rps < 10 and current_cpu_usage < 20 and current_memory_usage < 30:
                recommendations.append({
                    "action": "scale_down",
                    "reason": "Low resource utilization",
                    "suggested_instances": -1,
                    "priority": "low"
                })
            
            # Optimization recommendations
            if current_error_rate > 5:
                recommendations.append({
                    "action": "optimize",
                    "reason": "High error rate detected",
                    "suggestion": "Review error logs and implement circuit breakers",
                    "priority": "high"
                })
            
            return {
                "success": True,
                "recommendations": recommendations,
                "current_metrics": current_metrics,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in intelligent auto-scaling: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def predictive_maintenance(self, system_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Predict potential system issues before they occur"""
        try:
            # Analyze trends in system metrics
            issues_predicted = []
            
            # CPU trend analysis
            cpu_trend = system_metrics.get('cpu_trend', [])
            if len(cpu_trend) >= 5:
                cpu_slope = np.polyfit(range(len(cpu_trend)), cpu_trend, 1)[0]
                if cpu_slope > 2:  # CPU increasing by 2% per time unit
                    issues_predicted.append({
                        "type": "cpu_overload",
                        "probability": min(0.9, cpu_slope / 10),
                        "estimated_time": "2-4 hours",
                        "recommendation": "Consider scaling up or optimizing CPU-intensive operations"
                    })
            
            # Memory trend analysis
            memory_trend = system_metrics.get('memory_trend', [])
            if len(memory_trend) >= 5:
                memory_slope = np.polyfit(range(len(memory_trend)), memory_trend, 1)[0]
                if memory_slope > 1.5:  # Memory increasing by 1.5% per time unit
                    issues_predicted.append({
                        "type": "memory_leak",
                        "probability": min(0.8, memory_slope / 8),
                        "estimated_time": "1-3 hours",
                        "recommendation": "Check for memory leaks and restart services if necessary"
                    })
            
            # Disk space analysis
            disk_usage = system_metrics.get('disk_usage', 0)
            if disk_usage > 85:
                issues_predicted.append({
                    "type": "disk_space",
                    "probability": (disk_usage - 85) / 15,
                    "estimated_time": "6-12 hours",
                    "recommendation": "Clean up logs and temporary files, or increase disk capacity"
                })
            
            return {
                "success": True,
                "issues_predicted": issues_predicted,
                "system_health_score": max(0, 100 - len(issues_predicted) * 20),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in predictive maintenance: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

# Global advanced AI service instance
advanced_ai_service = AdvancedAIService()