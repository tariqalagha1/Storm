import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ChartBarIcon,
  KeyIcon,
  FolderIcon,
  CreditCardIcon,
  ArrowUpIcon,
  ArrowDownIcon,
} from '@heroicons/react/24/outline';
import { api } from '../services/api';
import { format } from 'date-fns';
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
} from 'recharts';
import AIInsights from '../components/AIInsights';

interface DashboardStats {
  total_projects: number;
  total_api_calls: number;
  active_api_keys: number;
  current_plan: string;
  monthly_usage: number;
  plan_limits: {
    api_calls: number;
    api_keys: number;
  };
}

interface UsageData {
  date: string;
  requests: number;
  errors: number;
  avg_response_time: number;
}

interface RecentProject {
  id: number;
  name: string;
  description: string;
  created_at: string;
  api_calls_count: number;
}

const Dashboard: React.FC = () => {
  const { data: stats, isLoading: statsLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const response = await api.get('/dashboard/stats');
      return response.data;
    },
  });

  const { data: usageData, isLoading: usageLoading } = useQuery<UsageData[]>({
    queryKey: ['dashboard-usage'],
    queryFn: async () => {
      const response = await api.get('/dashboard/usage');
      return response.data;
    },
  });

  const { data: recentProjects, isLoading: projectsLoading } = useQuery<RecentProject[]>({
    queryKey: ['recent-projects'],
    queryFn: async () => {
      const response = await api.get('/dashboard/projects/recent');
      return response.data;
    },
  });

  const getUsagePercentage = () => {
    if (!stats) return 0;
    return (stats.monthly_usage / stats.plan_limits.api_calls) * 100;
  };

  const getUsageColor = () => {
    const percentage = getUsagePercentage();
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 75) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    icon: React.ComponentType<any>;
    change?: { value: number; type: 'increase' | 'decrease' };
    color: string;
  }> = ({ title, value, icon: Icon, change, color }) => (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-5">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <Icon className={`h-6 w-6 ${color}`} aria-hidden="true" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-gray-500 truncate">{title}</dt>
              <dd className="flex items-baseline">
                <div className="text-2xl font-semibold text-gray-900">{value}</div>
                {change && (
                  <div
                    className={`ml-2 flex items-baseline text-sm font-semibold ${
                      change.type === 'increase' ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {change.type === 'increase' ? (
                      <ArrowUpIcon className="self-center flex-shrink-0 h-4 w-4" />
                    ) : (
                      <ArrowDownIcon className="self-center flex-shrink-0 h-4 w-4" />
                    )}
                    <span className="sr-only">
                      {change.type === 'increase' ? 'Increased' : 'Decreased'} by
                    </span>
                    {change.value}%
                  </div>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="md:flex md:items-center md:justify-between">
        <div className="flex-1 min-w-0">
          <h2 className="text-2xl font-bold leading-7 text-gray-900 sm:text-3xl sm:truncate">
            Dashboard
          </h2>
          <p className="mt-1 text-sm text-gray-500">
            Welcome back! Here's what's happening with your API usage.
          </p>
        </div>
        <div className="mt-4 flex md:mt-0 md:ml-4">
          <button
            type="button"
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Export Data
          </button>
          <button
            type="button"
            className="ml-3 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Create Project
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Projects"
          value={stats?.total_projects || 0}
          icon={FolderIcon}
          color="text-blue-600"
        />
        <StatCard
          title="API Calls This Month"
          value={stats?.monthly_usage?.toLocaleString() || 0}
          icon={ChartBarIcon}
          change={{ value: 12, type: 'increase' }}
          color="text-green-600"
        />
        <StatCard
          title="Active API Keys"
          value={stats?.active_api_keys || 0}
          icon={KeyIcon}
          color="text-purple-600"
        />
        <StatCard
          title="Current Plan"
          value={stats?.current_plan || 'Free'}
          icon={CreditCardIcon}
          color="text-yellow-600"
        />
      </div>

      {/* Usage Progress */}
      {stats && (
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Monthly Usage</h3>
            <div className="mt-2 max-w-xl text-sm text-gray-500">
              <p>
                You've used {stats.monthly_usage.toLocaleString()} of{' '}
                {stats.plan_limits.api_calls.toLocaleString()} API calls this month.
              </p>
            </div>
            <div className="mt-5">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Usage</span>
                <span className="font-medium text-gray-900">
                  {getUsagePercentage().toFixed(1)}%
                </span>
              </div>
              <div className="mt-1 relative">
                <div className="overflow-hidden h-2 text-xs flex rounded bg-gray-200">
                  <div
                    style={{ width: `${Math.min(getUsagePercentage(), 100)}%` }}
                    className={`shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center ${getUsageColor()}`}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Insights */}
      <AIInsights />

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Usage Chart */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <h3 className="text-lg leading-6 font-medium text-gray-900">API Usage Trend</h3>
            <div className="mt-5">
              {usageLoading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={usageData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
                    />
                    <Line
                      type="monotone"
                      dataKey="requests"
                      stroke="#3B82F6"
                      strokeWidth={2}
                      name="Requests"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>

        {/* Error Rate Chart */}
        <div className="bg-white overflow-hidden shadow rounded-lg">
          <div className="p-5">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Error Rate</h3>
            <div className="mt-5">
              {usageLoading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={usageData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tickFormatter={(value) => format(new Date(value), 'MMM dd')}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => format(new Date(value), 'MMM dd, yyyy')}
                    />
                    <Bar dataKey="errors" fill="#EF4444" name="Errors" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Projects */}
      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <div className="px-4 py-5 sm:px-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Recent Projects</h3>
          <p className="mt-1 max-w-2xl text-sm text-gray-500">
            Your most recently created projects and their usage.
          </p>
        </div>
        <ul className="divide-y divide-gray-200">
          {projectsLoading ? (
            <li className="px-4 py-4 flex items-center justify-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
            </li>
          ) : recentProjects && recentProjects.length > 0 ? (
            recentProjects.map((project: any) => (
              <li key={project.id}>
                <div className="px-4 py-4 flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <div className="h-10 w-10 rounded-lg bg-primary-100 flex items-center justify-center">
                        <FolderIcon className="h-6 w-6 text-primary-600" />
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">{project.name}</div>
                      <div className="text-sm text-gray-500">{project.description}</div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    <div className="text-sm text-gray-500">
                      {project.api_calls_count} calls
                    </div>
                    <div className="text-sm text-gray-500">
                      {format(new Date(project.created_at), 'MMM dd')}
                    </div>
                    <button className="text-primary-600 hover:text-primary-900 text-sm font-medium">
                      View
                    </button>
                  </div>
                </div>
              </li>
            ))
          ) : (
            <li className="px-4 py-4 text-center text-gray-500">
              No projects yet. Create your first project to get started!
            </li>
          )}
        </ul>
      </div>
    </div>
  );
};

export default Dashboard;