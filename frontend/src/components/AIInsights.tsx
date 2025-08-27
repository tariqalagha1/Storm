import React, { useState, useEffect } from 'react';
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  LightBulbIcon,
  CpuChipIcon,
  ArrowTrendingUpIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';
import { api } from '../services/api';

interface Anomaly {
  timestamp: string;
  endpoint: string;
  method: string;
  status_code: number;
  response_time: number;
  anomaly_type: string;
  severity: 'low' | 'medium' | 'high';
}

interface AIInsightsData {
  usage_summary: {
    total_requests: number;
    error_rate: number;
    avg_response_time: number;
    anomalies_detected: number;
  };
  ai_insights: {
    ai_insights: string;
    status: string;
  };
}

interface Recommendation {
  type: string;
  priority: 'low' | 'medium' | 'high';
  title: string;
  description: string;
  action: string;
}

const AIInsights: React.FC = () => {
  const [insights, setInsights] = useState<AIInsightsData | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'insights' | 'anomalies' | 'recommendations'>('insights');

  useEffect(() => {
    fetchAIData();
  }, []);

  const fetchAIData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch AI insights
      const [insightsResponse, anomaliesResponse, recommendationsResponse] = await Promise.all([
        api.get('/ai/ai-insights?days=7'),
        api.get('/ai/anomalies?days=7'),
        api.get('/ai/smart-recommendations'),
      ]);

      setInsights(insightsResponse.data.data || insightsResponse.data);
      setAnomalies(anomaliesResponse.data.data?.anomalies || anomaliesResponse.data.anomalies || []);
      setRecommendations(recommendationsResponse.data.data?.recommendations || recommendationsResponse.data.recommendations || []);
    } catch (err: any) {
      console.error('Error fetching AI data:', err);
      setError(err.response?.data?.detail || 'Failed to load AI insights');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'medium':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'low':
        return 'text-green-600 bg-green-50 border-green-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPriorityIcon = (priority: string) => {
    switch (priority) {
      case 'high':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
      case 'medium':
        return <LightBulbIcon className="h-5 w-5 text-yellow-500" />;
      case 'low':
        return <ShieldCheckIcon className="h-5 w-5 text-green-500" />;
      default:
        return <CpuChipIcon className="h-5 w-5 text-gray-500" />;
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            <div className="h-4 bg-gray-200 rounded w-4/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="text-center">
          <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-red-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">AI Insights Unavailable</h3>
          <p className="mt-1 text-sm text-gray-500">{error}</p>
          <button
            onClick={fetchAIData}
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <CpuChipIcon className="h-6 w-6 text-primary-600 mr-2" />
            <h3 className="text-lg font-medium text-gray-900">AI-Powered Insights</h3>
          </div>
          <button
            onClick={fetchAIData}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Refresh
          </button>
        </div>

        {/* Tabs */}
        <div className="mt-4">
          <nav className="flex space-x-8">
            {[
              { key: 'insights', label: 'AI Insights', icon: ChartBarIcon },
              { key: 'anomalies', label: 'Anomalies', icon: ExclamationTriangleIcon },
              { key: 'recommendations', label: 'Recommendations', icon: LightBulbIcon },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setSelectedTab(key as any)}
                className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                  selectedTab === key
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4 mr-2" />
                {label}
                {key === 'anomalies' && anomalies.length > 0 && (
                  <span className="ml-2 bg-red-100 text-red-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                    {anomalies.length}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="p-6">
        {selectedTab === 'insights' && (
          <div className="space-y-6">
            {/* Usage Summary */}
            {insights?.usage_summary && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {insights.usage_summary.total_requests.toLocaleString()}
                  </div>
                  <div className="text-sm text-blue-600">Total Requests</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {insights.usage_summary.error_rate.toFixed(1)}%
                  </div>
                  <div className="text-sm text-green-600">Error Rate</div>
                </div>
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">
                    {Math.round(insights.usage_summary.avg_response_time)}ms
                  </div>
                  <div className="text-sm text-yellow-600">Avg Response Time</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {insights.usage_summary.anomalies_detected}
                  </div>
                  <div className="text-sm text-purple-600">Anomalies Detected</div>
                </div>
              </div>
            )}

            {/* AI Generated Insights */}
            {insights?.ai_insights?.ai_insights && (
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-200">
                <div className="flex items-start">
                  <CpuChipIcon className="h-6 w-6 text-blue-600 mr-3 mt-1 flex-shrink-0" />
                  <div>
                    <h4 className="text-lg font-medium text-gray-900 mb-2">AI Analysis</h4>
                    <div className="text-gray-700 whitespace-pre-line">
                      {insights.ai_insights.ai_insights}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {selectedTab === 'anomalies' && (
          <div className="space-y-4">
            {anomalies.length === 0 ? (
              <div className="text-center py-8">
                <ShieldCheckIcon className="mx-auto h-12 w-12 text-green-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No Anomalies Detected</h3>
                <p className="mt-1 text-sm text-gray-500">Your API usage patterns look normal.</p>
              </div>
            ) : (
              anomalies.map((anomaly, index) => (
                <div
                  key={index}
                  className={`p-4 rounded-lg border ${getSeverityColor(anomaly.severity)}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <span className="text-sm font-medium capitalize">
                          {anomaly.anomaly_type.replace('_', ' ')}
                        </span>
                        <span className={`ml-2 px-2 py-1 text-xs font-medium rounded-full ${
                          anomaly.severity === 'high' ? 'bg-red-100 text-red-800' :
                          anomaly.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {anomaly.severity}
                        </span>
                      </div>
                      <div className="mt-1 text-sm">
                        <span className="font-medium">{anomaly.method}</span> {anomaly.endpoint}
                      </div>
                      <div className="mt-1 text-xs text-gray-600">
                        Status: {anomaly.status_code} | Response Time: {anomaly.response_time}ms |
                        {' '}{new Date(anomaly.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {selectedTab === 'recommendations' && (
          <div className="space-y-4">
            {recommendations.length === 0 ? (
              <div className="text-center py-8">
                <LightBulbIcon className="mx-auto h-12 w-12 text-yellow-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No Recommendations</h3>
                <p className="mt-1 text-sm text-gray-500">Your API is performing optimally.</p>
              </div>
            ) : (
              recommendations.map((rec, index) => (
                <div key={index} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="flex items-start">
                    <div className="flex-shrink-0 mr-3 mt-1">
                      {getPriorityIcon(rec.priority)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h4 className="text-sm font-medium text-gray-900">{rec.title}</h4>
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          rec.priority === 'high' ? 'bg-red-100 text-red-800' :
                          rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {rec.priority} priority
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-gray-600">{rec.description}</p>
                      <div className="mt-2 text-sm font-medium text-primary-600">
                        💡 {rec.action}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AIInsights;