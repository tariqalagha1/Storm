import React, { useState, useEffect } from 'react';
import { ChartBarIcon, ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/outline';
import { useAuthStore } from '../store/authStore';

interface AnalyticsData {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  requestsToday: number;
  requestsThisWeek: number;
  requestsThisMonth: number;
}

const Analytics: React.FC = () => {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();

  useEffect(() => {
    // TODO: Fetch analytics data from API
    // Mock data for now
    setTimeout(() => {
      setAnalyticsData({
        totalRequests: 12543,
        successfulRequests: 11876,
        failedRequests: 667,
        averageResponseTime: 245,
        requestsToday: 156,
        requestsThisWeek: 1234,
        requestsThisMonth: 5678
      });
      setLoading(false);
    }, 1000);
  }, []);

  const calculateSuccessRate = () => {
    if (!analyticsData) return 0;
    return ((analyticsData.successfulRequests / analyticsData.totalRequests) * 100).toFixed(1);
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    change?: number;
    icon: React.ReactNode;
  }> = ({ title, value, change, icon }) => (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            {icon}
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">{value}</div>
                {change !== undefined && (
                  <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                    change >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {change >= 0 ? (
                      <ArrowUpIcon className="self-center flex-shrink-0 h-4 w-4 text-green-500" />
                    ) : (
                      <ArrowDownIcon className="self-center flex-shrink-0 h-4 w-4 text-red-500" />
                    )}
                    <span className="sr-only">{change >= 0 ? 'Increased' : 'Decreased'} by</span>
                    {Math.abs(change)}%
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Analytics</h1>
        <p className="mt-2 text-sm text-gray-700">
          Monitor your API usage and performance metrics.
        </p>
      </div>

      {analyticsData && (
        <>
          {/* Overview Stats */}
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            <StatCard
              title="Total Requests"
              value={analyticsData.totalRequests.toLocaleString()}
              change={12.5}
              icon={<ChartBarIcon className="h-8 w-8 text-blue-500" />}
            />
            <StatCard
              title="Success Rate"
              value={`${calculateSuccessRate()}%`}
              change={2.1}
              icon={<ChartBarIcon className="h-8 w-8 text-green-500" />}
            />
            <StatCard
              title="Failed Requests"
              value={analyticsData.failedRequests.toLocaleString()}
              change={-5.2}
              icon={<ChartBarIcon className="h-8 w-8 text-red-500" />}
            />
            <StatCard
              title="Avg Response Time"
              value={`${analyticsData.averageResponseTime}ms`}
              change={-8.1}
              icon={<ChartBarIcon className="h-8 w-8 text-yellow-500" />}
            />
          </div>

          {/* Time Period Stats */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Requests by Time Period
              </h3>
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
                <div className="text-center">
                  <div className="text-2xl font-semibold text-gray-900">
                    {analyticsData.requestsToday.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-500">Today</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-semibold text-gray-900">
                    {analyticsData.requestsThisWeek.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-500">This Week</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-semibold text-gray-900">
                    {analyticsData.requestsThisMonth.toLocaleString()}
                  </div>
                  <div className="text-sm text-gray-500">This Month</div>
                </div>
              </div>
            </div>
          </div>

          {/* Placeholder for Charts */}
          <div className="mt-8 bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Request Trends
              </h3>
              <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
                <div className="text-center">
                  <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">Charts Coming Soon</h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Interactive charts and graphs will be available here.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Analytics;