import React, { useState } from 'react';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { useAuthStore } from '../store/authStore';

interface PricingPlan {
  id: string;
  name: string;
  price: number;
  interval: string;
  description: string;
  features: string[];
  limitations: string[];
  popular?: boolean;
  buttonText: string;
  buttonVariant: 'primary' | 'secondary' | 'outline';
}

const Pricing: React.FC = () => {
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');
  const { user, isAuthenticated } = useAuthStore();

  const plans: PricingPlan[] = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      interval: 'month',
      description: 'Perfect for getting started',
      features: [
        '1,000 API requests per month',
        'Basic analytics',
        'Email support',
        'Standard rate limits',
        'Community access'
      ],
      limitations: [
        'Limited to 1,000 requests/month',
        'Basic support only',
        'No priority processing'
      ],
      buttonText: 'Get Started',
      buttonVariant: 'outline'
    },
    {
      id: 'professional',
      name: 'Professional',
      price: billingInterval === 'monthly' ? 29 : 290,
      interval: billingInterval === 'monthly' ? 'month' : 'year',
      description: 'For growing businesses',
      features: [
        '10,000 API requests per month',
        'Advanced analytics & insights',
        'Priority email support',
        'Higher rate limits',
        'Custom integrations',
        'Team collaboration (up to 5 users)',
        'API key management',
        'Webhook support'
      ],
      limitations: [],
      popular: true,
      buttonText: isAuthenticated ? 'Upgrade Now' : 'Start Free Trial',
      buttonVariant: 'primary'
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: billingInterval === 'monthly' ? 99 : 990,
      interval: billingInterval === 'monthly' ? 'month' : 'year',
      description: 'For large-scale operations',
      features: [
        'Unlimited API requests',
        'Real-time analytics & reporting',
        '24/7 phone & email support',
        'No rate limits',
        'Custom integrations & APIs',
        'Unlimited team members',
        'Advanced security features',
        'SLA guarantee',
        'Dedicated account manager',
        'Custom deployment options'
      ],
      limitations: [],
      buttonText: 'Contact Sales',
      buttonVariant: 'secondary'
    }
  ];

  const handlePlanSelect = (planId: string) => {
    if (planId === 'free') {
      // Handle free plan signup
      console.log('Selecting free plan');
    } else if (planId === 'enterprise') {
      // Handle enterprise contact
      console.log('Contacting sales for enterprise');
    } else {
      // Handle paid plan upgrade
      console.log(`Upgrading to ${planId}`);
    }
  };

  const getYearlyDiscount = (monthlyPrice: number) => {
    const yearlyPrice = monthlyPrice * 10; // 2 months free
    const savings = (monthlyPrice * 12) - yearlyPrice;
    return Math.round((savings / (monthlyPrice * 12)) * 100);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Simple, Transparent Pricing
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Choose the perfect plan for your needs. Upgrade or downgrade at any time.
        </p>
        
        {/* Billing Toggle */}
        <div className="flex items-center justify-center mb-8">
          <span className={`mr-3 ${billingInterval === 'monthly' ? 'text-gray-900' : 'text-gray-500'}`}>
            Monthly
          </span>
          <button
            onClick={() => setBillingInterval(billingInterval === 'monthly' ? 'yearly' : 'monthly')}
            className="relative inline-flex h-6 w-11 items-center rounded-full bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                billingInterval === 'yearly' ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          <span className={`ml-3 ${billingInterval === 'yearly' ? 'text-gray-900' : 'text-gray-500'}`}>
            Yearly
            <span className="ml-1 text-green-600 text-sm font-medium">
              (Save up to 17%)
            </span>
          </span>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative rounded-2xl border-2 p-8 shadow-lg ${
              plan.popular
                ? 'border-blue-500 ring-2 ring-blue-500 ring-opacity-50'
                : 'border-gray-200'
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                <span className="bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-medium">
                  Most Popular
                </span>
              </div>
            )}
            
            <div className="text-center">
              <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
              <p className="text-gray-600 mb-6">{plan.description}</p>
              
              <div className="mb-6">
                <span className="text-4xl font-bold text-gray-900">
                  ${plan.price}
                </span>
                <span className="text-gray-600 ml-1">/{plan.interval}</span>
                {billingInterval === 'yearly' && plan.price > 0 && (
                  <div className="text-sm text-green-600 mt-1">
                    Save {getYearlyDiscount(plan.price / 10)}% annually
                  </div>
                )}
              </div>
              
              <button
                onClick={() => handlePlanSelect(plan.id)}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-colors ${
                  plan.buttonVariant === 'primary'
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : plan.buttonVariant === 'secondary'
                    ? 'bg-gray-900 text-white hover:bg-gray-800'
                    : 'bg-white text-gray-900 border-2 border-gray-300 hover:border-gray-400'
                }`}
              >
                {plan.buttonText}
              </button>
            </div>
            
            <div className="mt-8">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">Features included:</h4>
              <ul className="space-y-3">
                {plan.features.map((feature, index) => (
                  <li key={index} className="flex items-start">
                    <CheckIcon className="h-5 w-5 text-green-500 mr-3 mt-0.5 flex-shrink-0" />
                    <span className="text-gray-700">{feature}</span>
                  </li>
                ))}
              </ul>
              
              {plan.limitations.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Limitations:</h4>
                  <ul className="space-y-3">
                    {plan.limitations.map((limitation, index) => (
                      <li key={index} className="flex items-start">
                        <XMarkIcon className="h-5 w-5 text-red-500 mr-3 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-700">{limitation}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* FAQ Section */}
      <div className="mt-16">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
          Frequently Asked Questions
        </h2>
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Can I change my plan at any time?
            </h3>
            <p className="text-gray-600">
              Yes, you can upgrade or downgrade your plan at any time. Changes will be reflected in your next billing cycle.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              What happens if I exceed my API limits?
            </h3>
            <p className="text-gray-600">
              If you exceed your monthly API limits, your requests will be throttled. You can upgrade your plan for higher limits.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Do you offer refunds?
            </h3>
            <p className="text-gray-600">
              We offer a 30-day money-back guarantee for all paid plans. Contact support for refund requests.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Is there a free trial?
            </h3>
            <p className="text-gray-600">
              Yes, all new users start with our free plan. You can upgrade to a paid plan at any time to access more features.
            </p>
          </div>
        </div>
      </div>

      {/* Contact Section */}
      <div className="mt-16 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Need a custom solution?
        </h2>
        <p className="text-gray-600 mb-6">
          Contact our sales team to discuss enterprise pricing and custom features.
        </p>
        <button className="bg-blue-600 text-white px-8 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors">
          Contact Sales
        </button>
      </div>
    </div>
  );
};

export default Pricing;