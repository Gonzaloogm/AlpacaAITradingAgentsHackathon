import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

export function useAgentStatus(pollInterval = 5000) {
  const [account, setAccount] = useState(null);
  const [agentState, setAgentState] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAll = useCallback(async () => {
    try {
      const [accRes, stateRes, healthRes] = await Promise.all([
        apiClient.getAccount(),
        apiClient.getAgentState(),
        apiClient.getHealth(),
      ]);

      if (accRes.success) setAccount(accRes.data);
      if (stateRes.success) setAgentState(stateRes.data);
      if (healthRes.success) setHealth(healthRes.data);

      setError(null);
    } catch (err) {
      setError(err.message || 'Error fetching agent status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, pollInterval);
    return () => clearInterval(id);
  }, [fetchAll, pollInterval]);

  return { account, agentState, health, loading, error, refetch: fetchAll };
}
