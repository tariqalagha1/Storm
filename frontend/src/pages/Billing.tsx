import React, { useState, useEffect } from 'react';
import { CreditCardIcon, DocumentTextIcon, CalendarIcon } from '@heroicons/react/24/outline';
import { useAuthStore } from '../store/authStore';

interface BillingInfo {
  currentPlan: string;
  billingCycle: string;
  nextBillingDate: string;
  currentUsage: number;
  planLimit: number;
  amount: number;
}

interface Invoice {
  id: string;
  date: string;
  amount: number;
  status: string;
  downloadUrl?: string;
}

const Billing: React.FC = () => {
  const [billingInfo, setBillingInfo] = useState<BillingInfo | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuthStore();

  useEffect(() => {
    // TODO: Fetch billing data from API
    // Mock data for now
    setTimeout(() => {
      setBillingInfo({
        currentPlan: 'Professional',
        billingCycle: 'Monthly',
        nextBillingDate: '2024-02-15',
        currentUsage: 7500,
        planLimit: 10000,
        amount: 29.99
      });
      setInvoices([
        {
          id: 'inv_001',
          date: '2024-01-15',
          amount: 29.99,
          status: 'Paid'
        },
        {
          id: 'inv_002',
          date: '2023-12-15',
          amount: 29.99,
          status: 'Paid'
        },
        {
          id: 'inv_003',
          date: '2023-11-15',
          amount: 29.99,
          status: 'Paid'
        }
      ]);
      setLoading(false);
    }, 1000);
  }, []);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getUsagePercentage = () => {
    if (!billingInfo) return 0;
    return (billingInfo.currentUsage / billingInfo.planLimit) * 100;
  };

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
        <h1 className="text-2xl font-semibold text-gray-900">Billing & Usage</h1>
        <p className="mt-2 text-sm text-gray-700">
          Manage your subscription and view billing history.
        </p>
      </div>

      {billingInfo && (
        <>
          {/* Current Plan */}
          <div className="bg-white shadow rounded-lg mb-8">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Current Plan
              </h3>
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <div className="text-sm font-medium text-gray-500">Plan</div>
                  <div className="mt-1 text-lg font-semibold text-gray-900">
                    {billingInfo.currentPlan}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Billing Cycle</div>
                  <div className="mt-1 text-lg font-semibold text-gray-900">
                    {billingInfo.billingCycle}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Next Billing Date</div>
                  <div className="mt-1 text-lg font-semibold text-gray-900">
                    {formatDate(billingInfo.nextBillingDate)}
                  </div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Amount</div>
                  <div className="mt-1 text-lg font-semibold text-gray-900">
                    ${billingInfo.amount}
                  </div>
                </div>
              </div>
              <div className="mt-6">
                <button className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 mr-3">
                  Upgrade Plan
                </button>
                <button className="bg-gray-200 text-gray-700 px-4 py-2 rounded-md text-sm font-medium hover:bg-gray-300">
                  Cancel Subscription
                </button>
              </div>
            </div>
          </div>

          {/* Usage */}
          <div className="bg-white shadow rounded-lg mb-8">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Current Usage
              </h3>
              <div className="mb-4">
                <div className="flex justify-between text-sm font-medium text-gray-700">
                  <span>API Requests</span>
                  <span>{billingInfo.currentUsage.toLocaleString()} / {billingInfo.planLimit.toLocaleString()}</span>
                </div>
                <div className="mt-2 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${Math.min(getUsagePercentage(), 100)}%` }}
                  ></div>
                </div>
                <div className="mt-2 text-sm text-gray-500">
                  {getUsagePercentage().toFixed(1)}% of monthly limit used
                </div>
              </div>
              {getUsagePercentage() > 80 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
                  <div className="text-sm text-yellow-800">
                    <strong>Warning:</strong> You're approaching your monthly limit. Consider upgrading your plan.
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Payment Method */}
          <div className="bg-white shadow rounded-lg mb-8">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Payment Method
              </h3>
              <div className="flex items-center">
                <CreditCardIcon className="h-8 w-8 text-gray-400 mr-3" />
                <div>
                  <div className="text-sm font-medium text-gray-900">•••• •••• •••• 4242</div>
                  <div className="text-sm text-gray-500">Expires 12/25</div>
                </div>
                <button className="ml-auto bg-gray-200 text-gray-700 px-3 py-1 rounded-md text-sm font-medium hover:bg-gray-300">
                  Update
                </button>
              </div>
            </div>
          </div>

          {/* Billing History */}
          <div className="bg-white shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
                Billing History
              </h3>
              <div className="overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Invoice
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Date
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Amount
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {invoices.map((invoice) => (
                      <tr key={invoice.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {invoice.id}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(invoice.date)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          ${invoice.amount}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                            invoice.status === 'Paid'
                              ? 'bg-green-100 text-green-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {invoice.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          <button className="text-blue-600 hover:text-blue-500">
                            <DocumentTextIcon className="h-4 w-4 inline mr-1" />
                            Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Billing;