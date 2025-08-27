import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from 'react-query';
import ExternalServiceKeys from '../ExternalServiceKeys';
import { externalServiceKeysAPI } from '../../services/api';

// Mock react-hot-toast specifically for this test
jest.mock('react-hot-toast', () => ({
  default: {
    success: jest.fn(),
    error: jest.fn(),
    loading: jest.fn()
  }
}));

// Mock the API
jest.mock('../../services/api', () => ({
  externalServiceKeysAPI: {
    getKeys: jest.fn(() => Promise.resolve({ 
      data: [], 
      status: 200, 
      statusText: 'OK', 
      headers: {}, 
      config: {} 
    })),
    createKey: jest.fn(),
    deleteKey: jest.fn(),
    testKey: jest.fn(),
    toggleKey: jest.fn()
  }
}));

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false }
    }
  });
  
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

const mockExternalServiceKeysAPI = externalServiceKeysAPI as jest.Mocked<typeof externalServiceKeysAPI>;

test('renders key management table', async () => {
  mockExternalServiceKeysAPI.getKeys.mockResolvedValueOnce({ 
    data: [], 
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);
  
  renderWithProviders(<ExternalServiceKeys />);
  
  await waitFor(() => {
    expect(screen.getByText('External Service Keys')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create new key/i })).toBeInTheDocument();
  });
});

test('shows create key dialog', async () => {
  mockExternalServiceKeysAPI.getKeys.mockResolvedValueOnce({ 
    data: [], 
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);
  
  renderWithProviders(<ExternalServiceKeys />);
  
  const createButton = await screen.findByRole('button', { name: /create new key/i });
  fireEvent.click(createButton);
  
  await waitFor(() => {
    expect(screen.getByLabelText(/service name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/api key/i)).toBeInTheDocument();
  });
});

test('handles successful key creation', async () => {
  mockExternalServiceKeysAPI.getKeys.mockResolvedValueOnce({ 
    data: [], 
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);
  mockExternalServiceKeysAPI.createKey.mockResolvedValueOnce({ 
    data: { id: 1, name: 'Test Key', service_name: 'Test Service' },
    status: 201, 
    statusText: 'Created', 
    headers: {}, 
    config: {} 
  } as any);

  renderWithProviders(<ExternalServiceKeys />);
  
  const createButton = await screen.findByRole('button', { name: /create new key/i });
  fireEvent.click(createButton);

  await waitFor(() => {
    fireEvent.change(screen.getByLabelText(/service name/i), { target: { value: 'Test Service' } });
    fireEvent.change(screen.getByLabelText(/api key/i), { target: { value: 'test_key' } });
  });
  
  const submitButton = screen.getByRole('button', { name: 'Create Key' });
  fireEvent.click(submitButton);

  await waitFor(() => {
    expect(mockExternalServiceKeysAPI.createKey).toHaveBeenCalled();
  });
});

test('displays test results', async () => {
  const mockKeys = [{
    id: 1,
    name: 'Test Key',
    service_name: 'Test Service',
    key_type: 'api_key',
    key_preview: 'sk-***',
    usage_context: 'header',
    is_active: true,
    usage_count: 0,
    created_at: '2023-01-01',
    updated_at: '2023-01-01'
  }];
  
  mockExternalServiceKeysAPI.getKeys.mockResolvedValueOnce({ 
    data: mockKeys,
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);
  mockExternalServiceKeysAPI.testKey.mockResolvedValueOnce({ 
    data: { success: true, message: 'Test Successful' },
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);

  renderWithProviders(<ExternalServiceKeys />);
  
  // Wait for keys to load and find test button
  await waitFor(() => {
    expect(screen.getByText('Test Service')).toBeInTheDocument();
  });
  
  const testButton = await screen.findByRole('button', { name: 'Test key' });
  fireEvent.click(testButton);
  
  // Verify test dialog opens
  expect(screen.getByText('Test External Service Key')).toBeInTheDocument();
});

test('confirms key deletion', async () => {
  const mockKeys = [{
    id: 1,
    name: 'Test Key',
    service_name: 'Test Service',
    key_type: 'api_key',
    key_preview: 'sk-***',
    usage_context: 'header',
    is_active: true,
    usage_count: 0,
    created_at: '2023-01-01',
    updated_at: '2023-01-01'
  }];
  
  // Mock getKeys to return the test data
  mockExternalServiceKeysAPI.getKeys.mockResolvedValueOnce({ 
    data: mockKeys,
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);
  
  // Mock deleteKey to resolve successfully
  mockExternalServiceKeysAPI.deleteKey.mockResolvedValueOnce({ 
    data: {},
    status: 200, 
    statusText: 'OK', 
    headers: {}, 
    config: {} 
  } as any);

  renderWithProviders(<ExternalServiceKeys />);
  
  // Wait for the component to load and keys to be displayed
  await waitFor(() => {
    expect(screen.getByText('Test Key')).toBeInTheDocument();
  });
  
  // Find and click the delete button
  const deleteButton = screen.getByRole('button', { name: 'Delete key' });
  fireEvent.click(deleteButton);
  
  // Wait for the async operation to complete
  await waitFor(() => {
    expect(mockExternalServiceKeysAPI.deleteKey).toHaveBeenCalledWith(1);
  });
});