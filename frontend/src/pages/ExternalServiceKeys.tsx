import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  Tooltip,
  CircularProgress,

  InputAdornment,
  Grid,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Science as TestIcon,
  ContentCopy as CopyIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { externalServiceKeysAPI } from '../services/api';
import toast from 'react-hot-toast';

interface ExternalServiceKey {
  id: number;
  name: string;
  service_name: string;
  key_type: string;
  key_preview: string;
  description?: string;
  usage_context: string;
  header_name?: string;
  query_param_name?: string;
  prefix?: string;
  is_active: boolean;
  last_used?: string;
  usage_count: number;
  project_id?: number;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

interface CreateKeyData {
  name: string;
  service_name: string;
  key_type: string;
  api_key: string;
  description: string;
  usage_context: string;
  header_name: string;
  query_param_name: string;
  prefix: string;
  expires_at: string;
}

const ExternalServiceKeys: React.FC = () => {
  const [keys, setKeys] = useState<ExternalServiceKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [selectedKey, setSelectedKey] = useState<ExternalServiceKey | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);

  const [createData, setCreateData] = useState<CreateKeyData>({
    name: '',
    service_name: '',
    key_type: 'api_key',
    api_key: '',
    description: '',
    usage_context: 'header',
    header_name: '',
    query_param_name: '',
    prefix: '',
    expires_at: '',
  });

  const [testData, setTestData] = useState({
    test_endpoint: '',
    test_method: 'GET',
    additional_headers: '',
    test_payload: '',
  });

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const response = await externalServiceKeysAPI.getKeys();
      setKeys(response.data);
    } catch (error) {
      toast.error('Failed to fetch external service keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    try {
      await externalServiceKeysAPI.createKey(createData);
      toast.success('External service key created successfully');
      setCreateDialogOpen(false);
      setCreateData({
        name: '',
        service_name: '',
        key_type: 'api_key',
        api_key: '',
        description: '',
        usage_context: 'header',
        header_name: '',
        query_param_name: '',
        prefix: '',
        expires_at: '',
      });
      fetchKeys();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create external service key');
    }
  };

  const handleDeleteKey = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this external service key?')) {
      try {
        await externalServiceKeysAPI.deleteKey(id);
        toast.success('External service key deleted successfully');
        fetchKeys();
      } catch (error) {
        toast.error('Failed to delete external service key');
      }
    }
  };

  const handleToggleKey = async (id: number) => {
    try {
      await externalServiceKeysAPI.toggleKey(id);
      toast.success('External service key status updated');
      fetchKeys();
    } catch (error) {
      toast.error('Failed to update external service key status');
    }
  };

  const handleTestKey = async () => {
    if (!selectedKey) return;

    try {
      setTesting(true);
      const additionalHeaders = testData.additional_headers
        ? JSON.parse(testData.additional_headers)
        : {};
      const testPayload = testData.test_payload
        ? JSON.parse(testData.test_payload)
        : undefined;

      const response = await externalServiceKeysAPI.testKey(selectedKey.id, {
        test_endpoint: testData.test_endpoint,
        test_method: testData.test_method,
        additional_headers: additionalHeaders,
        test_payload: testPayload,
      });

      setTestResult(response.data);
      toast.success('Key test completed');
    } catch (error: any) {
      setTestResult({
        success: false,
        error: error.response?.data?.detail || 'Test failed',
      });
      toast.error('Key test failed');
    } finally {
      setTesting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const getStatusColor = (isActive: boolean, expiresAt?: string) => {
    if (!isActive) return 'error';
    if (expiresAt && new Date(expiresAt) < new Date()) return 'warning';
    return 'success';
  };

  const getStatusText = (isActive: boolean, expiresAt?: string) => {
    if (!isActive) return 'Inactive';
    if (expiresAt && new Date(expiresAt) < new Date()) return 'Expired';
    return 'Active';
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          External Service Keys
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create New Key
        </Button>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Securely store and manage API keys for external services. Keys are encrypted and can be reused in HTTP requests.
      </Alert>

      <Card>
        <CardContent>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Service</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Key Preview</TableCell>
                    <TableCell>Usage Context</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Usage Count</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {keys.map((key) => (
                    <TableRow key={key.id}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {key.name}
                          </Typography>
                          {key.description && (
                            <Typography variant="caption" color="text.secondary">
                              {key.description}
                            </Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>{key.service_name}</TableCell>
                      <TableCell>
                        <Chip label={key.key_type} size="small" />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" fontFamily="monospace">
                            {key.key_preview}
                          </Typography>
                          <Tooltip title="Copy key preview">
                            <IconButton
                              size="small"
                              onClick={() => copyToClipboard(key.key_preview)}
                            >
                              <CopyIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={key.usage_context}
                          size="small"
                          variant="outlined"
                        />
                        {key.header_name && (
                          <Typography variant="caption" display="block">
                            Header: {key.header_name}
                          </Typography>
                        )}
                        {key.query_param_name && (
                          <Typography variant="caption" display="block">
                            Query: {key.query_param_name}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={getStatusText(key.is_active, key.expires_at)}
                          color={getStatusColor(key.is_active, key.expires_at) as any}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{key.usage_count}</TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Tooltip title="Test key">
                            <IconButton
                              size="small"
                              onClick={() => {
                                setSelectedKey(key);
                                setTestDialogOpen(true);
                                setTestResult(null);
                              }}
                            >
                              <TestIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Edit key">
                            <IconButton
                              size="small"
                              onClick={() => {
                                setSelectedKey(key);
                                setEditDialogOpen(true);
                              }}
                            >
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete key">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteKey(key.id)}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <FormControlLabel
                            control={
                              <Switch
                                checked={key.is_active}
                                onChange={() => handleToggleKey(key.id)}
                                size="small"
                              />
                            }
                            label=""
                            sx={{ m: 0 }}
                          />
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                  {keys.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={8} align="center">
                        <Typography color="text.secondary">
                          No external service keys found. Create your first key to get started.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Create Key Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New External Service Key</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Key Name"
                value={createData.name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, name: e.target.value })}
                required
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Service Name"
                value={createData.service_name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, service_name: e.target.value })}
                required
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Key Type</InputLabel>
                <Select
                  value={createData.key_type}
                  onChange={(e: any) => setCreateData({ ...createData, key_type: e.target.value })}
                  label="Key Type"
                >
                  <MenuItem value="api_key">API Key</MenuItem>
                  <MenuItem value="bearer_token">Bearer Token</MenuItem>
                  <MenuItem value="basic_auth">Basic Auth</MenuItem>
                  <MenuItem value="custom">Custom</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Usage Context</InputLabel>
                <Select
                  value={createData.usage_context}
                  onChange={(e: any) => setCreateData({ ...createData, usage_context: e.target.value })}
                  label="Usage Context"
                >
                  <MenuItem value="header">HTTP Header</MenuItem>
                  <MenuItem value="query_param">Query Parameter</MenuItem>
                  <MenuItem value="body">Request Body</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth
                label="API Key"
                type={showApiKey ? 'text' : 'password'}
                value={createData.api_key}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, api_key: e.target.value })}
                required
                InputProps={{
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowApiKey(!showApiKey)}
                        edge="end"
                      >
                        {showApiKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth
                label="Description"
                value={createData.description}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, description: e.target.value })}
                multiline
                rows={2}
              />
            </Grid>
            {createData.usage_context === 'header' && (
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Header Name"
                  value={createData.header_name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, header_name: e.target.value })}
                  placeholder="e.g., X-API-Key, Authorization"
                />
              </Grid>
            )}
            {createData.usage_context === 'query_param' && (
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Query Parameter Name"
                  value={createData.query_param_name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, query_param_name: e.target.value })}
                  placeholder="e.g., api_key, token"
                />
              </Grid>
            )}
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Key Prefix"
                value={createData.prefix}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, prefix: e.target.value })}
                placeholder="e.g., Bearer, API"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Expires At"
                type="datetime-local"
                value={createData.expires_at}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, expires_at: e.target.value })}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateKey} variant="contained">
            Create Key
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Key Dialog */}
      <Dialog open={testDialogOpen} onClose={() => setTestDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Test External Service Key</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={12}>
              <TextField
                fullWidth
                label="Test Endpoint URL"
                value={testData.test_endpoint}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTestData({ ...testData, test_endpoint: e.target.value })}
                required
                placeholder="https://api.example.com/test"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>HTTP Method</InputLabel>
                <Select
                  value={testData.test_method}
                  onChange={(e: any) => setTestData({ ...testData, test_method: e.target.value })}
                  label="HTTP Method"
                >
                  <MenuItem value="GET">GET</MenuItem>
                  <MenuItem value="POST">POST</MenuItem>
                  <MenuItem value="PUT">PUT</MenuItem>
                  <MenuItem value="DELETE">DELETE</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth
                label="Additional Headers (JSON)"
                value={testData.additional_headers}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTestData({ ...testData, additional_headers: e.target.value })}
                multiline
                rows={3}
                placeholder='{"Content-Type": "application/json"}'
              />
            </Grid>
            <Grid size={12}>
              <TextField
                fullWidth
                label="Test Payload (JSON)"
                value={testData.test_payload}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTestData({ ...testData, test_payload: e.target.value })}
                multiline
                rows={3}
                placeholder='{"test": "data"}'
              />
            </Grid>
            {testResult && (
              <Grid size={12}>
                <Alert
                  severity={testResult.success ? 'success' : 'error'}
                  icon={testResult.success ? <CheckIcon /> : <ErrorIcon />}
                >
                  <Typography variant="body2">
                    {testResult.success ? 'Test successful!' : `Test failed: ${testResult.error}`}
                  </Typography>
                  {testResult.response_data && (
                    <Box sx={{ mt: 1 }}>
                      <Typography variant="caption">Response:</Typography>
                      <pre style={{ fontSize: '12px', marginTop: '4px' }}>
                        {JSON.stringify(testResult.response_data, null, 2)}
                      </pre>
                    </Box>
                  )}
                </Alert>
              </Grid>
            )}
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTestDialogOpen(false)}>Close</Button>
          <Button
            onClick={handleTestKey}
            variant="contained"
            disabled={testing || !testData.test_endpoint}
            startIcon={testing ? <CircularProgress size={16} /> : <TestIcon />}
          >
            {testing ? 'Testing...' : 'Test Key'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExternalServiceKeys;