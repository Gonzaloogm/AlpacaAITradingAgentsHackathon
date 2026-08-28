import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

export function useAgentStatus(pollInterval = 15000) {
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAccount = useCallback(async () => {
    const result = await apiClient.getAccount();
    if (result.success) {
      setAccount(result.data);
      setError(null);
    } else {
      setError(result.error);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchAccount();
    const id = setInterval(fetchAccount, pollInterval);
    return () => clearInterval(id);
  }, [fetchAccount, pollInterval]);

  return { account, loading, error, refetch: fetchAccount };
}
