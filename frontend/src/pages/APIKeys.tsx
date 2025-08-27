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
  Alert,
  Tooltip,
  CircularProgress,
  InputAdornment,
  Grid,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  ContentCopy as CopyIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { dashboardAPI } from '../services/api';
import toast from 'react-hot-toast';

interface APIKey {
  id: number;
  name: string;
  key_preview: string;
  project_id?: number;
  is_active: boolean;
  last_used?: string;
  usage_count: number;
  created_at: string;
  expires_at?: string;
}

interface CreateKeyData {
  name: string;
  project_id?: number;
}

const APIKeys: React.FC = () => {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [showFullKey, setShowFullKey] = useState<{ [key: number]: boolean }>({});

  const [createData, setCreateData] = useState<CreateKeyData>({
    name: '',
    project_id: undefined,
  });

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const response = await dashboardAPI.getAPIKeys();
      setKeys(response.data);
    } catch (error) {
      toast.error('Failed to fetch API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async () => {
    try {
      await dashboardAPI.createAPIKey(createData);
      toast.success('API key created successfully');
      setCreateDialogOpen(false);
      setCreateData({ name: '', project_id: undefined });
      fetchKeys();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to create API key');
    }
  };

  const handleDeleteKey = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this API key?')) {
      try {
        await dashboardAPI.deleteAPIKey(id);
        toast.success('API key deleted successfully');
        fetchKeys();
      } catch (error) {
        toast.error('Failed to delete API key');
      }
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const toggleKeyVisibility = (keyId: number) => {
    setShowFullKey(prev => ({
      ...prev,
      [keyId]: !prev[keyId]
    }));
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
          API Keys
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
        API keys allow you to authenticate requests to the Storm API. Keep your keys secure and never share them publicly.
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
                    <TableCell>Key</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Usage Count</TableCell>
                    <TableCell>Last Used</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {keys.map((key) => (
                    <TableRow key={key.id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {key.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body2" fontFamily="monospace">
                            {showFullKey[key.id] ? key.key_preview : key.key_preview}
                          </Typography>
                          <Tooltip title="Copy key">
                            <IconButton
                              size="small"
                              onClick={() => copyToClipboard(key.key_preview)}
                            >
                              <CopyIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={showFullKey[key.id] ? "Hide key" : "Show key"}>
                            <IconButton
                              size="small"
                              onClick={() => toggleKeyVisibility(key.id)}
                            >
                              {showFullKey[key.id] ? <VisibilityOffIcon fontSize="small" /> : <VisibilityIcon fontSize="small" />}
                            </IconButton>
                          </Tooltip>
                        </Box>
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
                        {key.last_used ? new Date(key.last_used).toLocaleDateString() : 'Never'}
                      </TableCell>
                      <TableCell>{new Date(key.created_at).toLocaleDateString()}</TableCell>
                      <TableCell>
                        <Tooltip title="Delete key">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleDeleteKey(key.id)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                  {keys.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={7} align="center">
                        <Typography color="text.secondary">
                          No API keys found. Create your first key to get started.
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
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New API Key</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid size={12}>
              <TextField
                fullWidth
                label="Key Name"
                value={createData.name}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCreateData({ ...createData, name: e.target.value })}
                required
                placeholder="e.g., Production API Key"
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleCreateKey} variant="contained" disabled={!createData.name}>
            Create Key
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default APIKeys;