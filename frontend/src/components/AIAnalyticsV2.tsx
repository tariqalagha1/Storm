import React, { useState, useEffect, useRef } from 'react';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  CpuChipIcon,
  ArrowTrendingUpIcon,
  BoltIcon,
  CogIcon,
  ArrowUpTrayIcon,
  ArrowDownTrayIcon,
  PlayIcon,
  PauseIcon,
  ArrowPathIcon,
  EyeIcon,
  CurrencyDollarIcon,
  ServerIcon,
  ShieldCheckIcon,
  ClockIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';

interface RealTimeMetrics {
  total_requests: number;
  error_rate: number;
  avg_response_time: number;
  active_alerts: number;
  last_updated: string;
}

interface Alert {
  type: string;
  severity: string;
  message: string;
  timestamp: string;
  value: number;
  threshold: number;
}

interface MarketplaceModel {
  id: string;
  name: string;
  description: string;
  type: string;
  pricing: { per_request: number };
  rating: number;
  usage_count: number;
}

interface CustomModel {
  id: string;
  name: string;
  type: string;
  metrics: any;
  created_at: string;
  status: string;
}

interface AutoScalingRecommendation {
  action: string;
  reason: string;
  suggested_instances?: number;
  priority: string;
}

const AIAnalyticsV2: React.FC = () => {
  const [activeTab, setActiveTab] = useState('monitoring');
  const [realTimeData, setRealTimeData] = useState<RealTimeMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [marketplaceModels, setMarketplaceModels] = useState<MarketplaceModel[]>([]);
  const [customModels, setCustomModels] = useState<CustomModel[]>([]);
  const [autoScalingRecs, setAutoScalingRecs] = useState<AutoScalingRecommendation[]>([]);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket connection for real-time monitoring
  useEffect(() => {
    if (isMonitoring) {
      const ws = new WebSocket('ws://localhost:8000/api/ai/v2/ws/real-time-monitoring');
      wsRef.current = ws;

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.success && data.data) {
          setRealTimeData(data.data);
        }
        if (data.type === 'alert') {
          setAlerts(prev => [...prev, ...data.alerts]);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      return () => {
        ws.close();
      };
    }
  }, [isMonitoring]);

  // Fetch marketplace models
  const fetchMarketplaceModels = async () => {
    try {
      const response = await fetch('/api/ai/v2/marketplace/models', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setMarketplaceModels(data.models);
      }
    } catch (error) {
      console.error('Error fetching marketplace models:', error);
    }
  };

  // Fetch user's custom models
  const fetchCustomModels = async () => {
    try {
      const response = await fetch('/api/ai/v2/my-models', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setCustomModels(data.models);
      }
    } catch (error) {
      console.error('Error fetching custom models:', error);
    }
  };

  // Fetch auto-scaling recommendations
  const fetchAutoScalingRecs = async () => {
    try {
      const response = await fetch('/api/ai/v2/auto-scaling/recommendations', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setAutoScalingRecs(data.recommendations);
      }
    } catch (error) {
      console.error('Error fetching auto-scaling recommendations:', error);
    }
  };

  // Fetch visualization data
  const fetchVisualizationData = async (type: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/ai/v2/visualizations/${type}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      if (data.success) {
        setChartData(JSON.parse(data.chart_data));
      }
    } catch (error) {
      console.error('Error fetching visualization data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketplaceModels();
    fetchCustomModels();
    fetchAutoScalingRecs();
  }, []);

  const toggleMonitoring = () => {
    setIsMonitoring(!isMonitoring);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'low': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const TabButton = ({ id, label, icon: Icon, isActive, onClick }: any) => (
    <button
      onClick={() => onClick(id)}
      className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-colors ${
        isActive
          ? 'bg-blue-600 text-white'
          : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
      }`}
    >
      <Icon className="w-4 h-4" />
      <span>{label}</span>
    </button>
  );

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-gray-900">AI Analytics v2.0</h2>
          <p className="text-gray-600 mt-1">
            Advanced AI-powered analytics with real-time monitoring and intelligent automation
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 border border-blue-200">
            <SparklesIcon className="w-4 h-4 mr-1" />
            Phase 2 Active
          </span>
          <button
            onClick={toggleMonitoring}
            className={`inline-flex items-center px-4 py-2 rounded-lg font-medium transition-colors ${
              isMonitoring
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isMonitoring ? (
              <>
                <PauseIcon className="w-4 h-4 mr-2" />
                Stop Monitoring
              </>
            ) : (
              <>
                <PlayIcon className="w-4 h-4 mr-2" />
                Start Monitoring
              </>
            )}
          </button>
        </div>
      </div>

      {/* Real-time Status Bar */}
      {realTimeData && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
          <div className="p-6">
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{realTimeData.total_requests}</div>
                <div className="text-sm text-gray-600">Total Requests</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{realTimeData.error_rate.toFixed(1)}%</div>
                <div className="text-sm text-gray-600">Error Rate</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{realTimeData.avg_response_time.toFixed(0)}ms</div>
                <div className="text-sm text-gray-600">Avg Response Time</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{realTimeData.active_alerts}</div>
                <div className="text-sm text-gray-600">Active Alerts</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-1">
          <TabButton
            id="monitoring"
            label="Real-time"
            icon={ChartBarIcon}
            isActive={activeTab === 'monitoring'}
            onClick={setActiveTab}
          />
          <TabButton
            id="marketplace"
            label="AI Marketplace"
            icon={SparklesIcon}
            isActive={activeTab === 'marketplace'}
            onClick={setActiveTab}
          />
          <TabButton
            id="models"
            label="Custom Models"
            icon={CogIcon}
            isActive={activeTab === 'models'}
            onClick={setActiveTab}
          />
          <TabButton
            id="visualizations"
            label="Visualizations"
            icon={ArrowTrendingUpIcon}
            isActive={activeTab === 'visualizations'}
            onClick={setActiveTab}
          />
          <TabButton
            id="automation"
            label="Automation"
            icon={BoltIcon}
            isActive={activeTab === 'automation'}
            onClick={setActiveTab}
          />
          <TabButton
            id="pricing"
            label="Smart Pricing"
            icon={CurrencyDollarIcon}
            isActive={activeTab === 'pricing'}
            onClick={setActiveTab}
          />
        </nav>
      </div>

      {/* Tab Content */}
      <div className="mt-6">
        {/* Real-time Monitoring Tab */}
        {activeTab === 'monitoring' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Live Metrics */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                    <ChartBarIcon className="w-5 h-5" />
                    <span>Live Metrics</span>
                    {isMonitoring && (
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    )}
                  </h3>
                </div>
                <div className="p-6">
                  {realTimeData ? (
                    <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <span>Error Rate</span>
                        <div className="flex items-center space-x-2">
                          <div className="w-20 bg-gray-200 rounded-full h-2">
                            <div 
                              className="bg-blue-600 h-2 rounded-full" 
                              style={{ width: `${Math.min(realTimeData.error_rate, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium">{realTimeData.error_rate.toFixed(1)}%</span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span>Response Time</span>
                        <span className="text-sm font-medium">{realTimeData.avg_response_time.toFixed(0)}ms</span>
                      </div>
                      <div className="text-xs text-gray-500">
                        Last updated: {new Date(realTimeData.last_updated).toLocaleTimeString()}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      {isMonitoring ? 'Waiting for data...' : 'Start monitoring to see live metrics'}
                    </div>
                  )}
                </div>
              </div>

              {/* Active Alerts */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                    <ExclamationTriangleIcon className="w-5 h-5" />
                    <span>Active Alerts</span>
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {alerts.length}
                    </span>
                  </h3>
                </div>
                <div className="p-6">
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {alerts.length > 0 ? (
                      alerts.slice(-5).map((alert, index) => (
                        <div key={index} className="p-3 border border-orange-200 rounded-lg bg-orange-50">
                          <div className="flex justify-between items-start">
                            <div className="flex items-start space-x-2">
                              <ExclamationTriangleIcon className="h-4 w-4 text-orange-600 mt-0.5" />
                              <div>
                                <div className="font-medium text-gray-900">{alert.message}</div>
                                <div className="text-xs text-gray-500 mt-1">
                                  {new Date(alert.timestamp).toLocaleString()}
                                </div>
                              </div>
                            </div>
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                              {alert.severity}
                            </span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        No active alerts
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* AI Marketplace Tab */}
        {activeTab === 'marketplace' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {marketplaceModels.map((model) => (
                <div key={model.id} className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h3 className="text-lg font-semibold text-gray-900">{model.name}</h3>
                    <p className="text-sm text-gray-600 mt-1">{model.description}</p>
                  </div>
                  <div className="p-6">
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
                          {model.type}
                        </span>
                        <span className="text-sm font-medium">${model.pricing.per_request}/request</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Rating:</span>
                        <div className="flex items-center">
                          <span className="text-sm font-medium">{model.rating.toFixed(1)}</span>
                          <span className="text-yellow-500 ml-1">★</span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Usage:</span>
                        <span className="text-sm font-medium">{model.usage_count} requests</span>
                      </div>
                      <button className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                        Deploy Model
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Custom Models Tab */}
        {activeTab === 'models' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-semibold text-gray-900">Your Custom Models</h3>
              <button className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                <ArrowUpTrayIcon className="w-4 h-4 mr-2" />
                Train New Model
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {customModels.map((model) => (
                <div key={model.id} className="bg-white rounded-lg border border-gray-200 shadow-sm">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-semibold text-gray-900">{model.name}</h3>
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        model.status === 'trained' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {model.status}
                      </span>
                    </div>
                  </div>
                  <div className="p-6">
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm">Type:</span>
                        <span className="text-sm font-medium">{model.type}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm">Created:</span>
                        <span className="text-sm font-medium">
                          {new Date(model.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      {model.metrics && (
                        <div className="mt-3 p-2 bg-gray-50 rounded">
                          <div className="text-xs font-medium mb-1">Performance Metrics:</div>
                          {Object.entries(model.metrics).map(([key, value]) => (
                            <div key={key} className="flex justify-between text-xs">
                              <span>{key}:</span>
                              <span>{typeof value === 'number' ? value.toFixed(3) : String(value)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      <div className="flex space-x-2 mt-3">
                        <button className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                          <EyeIcon className="w-4 h-4 mr-1" />
                          View
                        </button>
                        <button className="flex-1 inline-flex items-center justify-center px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50">
                          <ArrowDownTrayIcon className="w-4 h-4 mr-1" />
                          Export
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Visualizations Tab */}
        {activeTab === 'visualizations' && (
          <div className="space-y-6">
            <div className="flex space-x-2 mb-4">
              <button 
                onClick={() => fetchVisualizationData('usage-trends')}
                disabled={loading}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                {loading ? (
                  <ArrowPathIcon className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <ArrowTrendingUpIcon className="w-4 h-4 mr-2" />
                )}
                Usage Trends
              </button>
              <button 
                onClick={() => fetchVisualizationData('performance-heatmap')}
                disabled={loading}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Performance Heatmap
              </button>
            </div>
            
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Advanced Analytics Visualization</h3>
              </div>
              <div className="p-6">
                {chartData ? (
                  <div className="h-96">
                    <div className="flex items-center justify-center h-full bg-gray-50 rounded">
                      <div className="text-center">
                        <ArrowTrendingUpIcon className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                        <p className="text-gray-600">Interactive Plotly Chart</p>
                        <p className="text-sm text-gray-500">Chart data loaded successfully</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-96 flex items-center justify-center bg-gray-50 rounded">
                    <div className="text-center">
                      <ArrowTrendingUpIcon className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                      <p className="text-gray-600">Select a visualization type to view charts</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Automation Tab */}
        {activeTab === 'automation' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Auto-scaling Recommendations */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                    <ServerIcon className="w-5 h-5" />
                    <span>Auto-scaling Recommendations</span>
                  </h3>
                </div>
                <div className="p-6">
                  <div className="space-y-3">
                    {autoScalingRecs.map((rec, index) => (
                      <div key={index} className="p-3 border border-gray-200 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium capitalize">{rec.action.replace('_', ' ')}</span>
                          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(rec.priority)}`}>
                            {rec.priority}
                          </span>
                        </div>
                        <p className="text-sm text-gray-600">{rec.reason}</p>
                        {rec.suggested_instances && (
                          <p className="text-sm font-medium mt-1">
                            Suggested instances: {rec.suggested_instances > 0 ? '+' : ''}{rec.suggested_instances}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Predictive Maintenance */}
              <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                    <ShieldCheckIcon className="w-5 h-5" />
                    <span>Predictive Maintenance</span>
                  </h3>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span>System Health Score</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div className="bg-green-600 h-2 rounded-full" style={{ width: '85%' }} />
                        </div>
                        <span className="text-sm font-medium">85%</span>
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="text-sm font-medium">Predicted Issues:</div>
                      <div className="p-2 bg-yellow-50 border border-yellow-200 rounded">
                        <div className="flex items-center space-x-2">
                          <ClockIcon className="w-4 h-4 text-yellow-600" />
                          <span className="text-sm">CPU usage trending up - potential overload in 2-4 hours</span>
                        </div>
                      </div>
                    </div>
                    
                    <button className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                      View Detailed Analysis
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Smart Pricing Tab */}
        {activeTab === 'pricing' && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
                  <CurrencyDollarIcon className="w-5 h-5" />
                  <span>AI-Powered Pricing Recommendations</span>
                </h3>
              </div>
              <div className="p-6">
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 p-4 bg-blue-50 rounded-lg">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">$127</div>
                      <div className="text-sm text-gray-600">Current Monthly Cost</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">$97</div>
                      <div className="text-sm text-gray-600">Optimized Cost</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">$30</div>
                      <div className="text-sm text-gray-600">Potential Savings</div>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Usage-based Optimization</span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Recommended
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">
                        Based on your usage patterns, switching to a usage-based plan could save $20/month.
                      </p>
                    </div>
                    
                    <div className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Premium SLA Tier</span>
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          Consider
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">
                        Your excellent performance metrics qualify you for premium SLA with 99.99% uptime guarantee.
                      </p>
                    </div>
                  </div>
                  
                  <button className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Apply Recommendations
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIAnalyticsV2;