import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getTargets, createTarget, scanTarget } from '../api';

export default function Targets() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const projectName = location.state?.projectName || `PROJECT_${projectId}`;

  const [targets, setTargets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [newDomain, setNewDomain] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  
  // Track scanning state per target ID
  const [scanningTargets, setScanningTargets] = useState({});
  // Track scan results/errors per target ID
  const [scanResults, setScanResults] = useState({});

  useEffect(() => {
    fetchTargets();
  }, [projectId]);

  async function fetchTargets() {
    setLoading(true);
    setError(null);
    try {
      const data = await getTargets(projectId);
      setTargets(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!newDomain.trim()) return;

    setIsCreating(true);
    try {
      await createTarget(projectId, newDomain);
      setNewDomain('');
      await fetchTargets();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsCreating(false);
    }
  }

  async function handleScan(targetId) {
    setScanningTargets(prev => ({ ...prev, [targetId]: true }));
    setScanResults(prev => {
      const newRes = { ...prev };
      delete newRes[targetId]; // clear previous result/error
      return newRes;
    });

    try {
      const summary = await scanTarget(targetId);
      setScanResults(prev => ({
        ...prev,
        [targetId]: { success: true, data: summary }
      }));
    } catch (err) {
      setScanResults(prev => ({
        ...prev,
        [targetId]: { success: false, error: err.message }
      }));
    } finally {
      setScanningTargets(prev => ({ ...prev, [targetId]: false }));
    }
  }

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '40px 20px' }}>
      
      <div style={{ marginBottom: '20px', fontFamily: 'var(--font-mono)' }}>
        <button 
          onClick={() => navigate('/')}
          style={{ padding: '6px 12px', fontSize: '0.8em' }}
        >
          &lt; BACK_TO_PROJECTS
        </button>
      </div>

      <h1 style={{ borderBottom: '1px solid var(--accent-transparent)', paddingBottom: '10px', marginBottom: '30px' }}>
        [&gt;] {projectName.toUpperCase()}::TARGETS
      </h1>
      
      {error && (
        <div className="alert-error">
          <span>[ERR]</span> {error}
        </div>
      )}

      <div className="panel" style={{ marginBottom: '30px' }}>
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: '15px' }}>
          <input
            type="text"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="ENTER_TARGET_DOMAIN (e.g. acme.com)"
            disabled={isCreating}
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={isCreating || !newDomain.trim()}>
            {isCreating ? 'ADDING_TARGET...' : 'ADD_TARGET'}
          </button>
        </form>
      </div>

      <div className="panel">
        {loading && targets.length === 0 ? (
          <div className="loading-text">[ FETCHING_TARGETS... ]</div>
        ) : targets.length === 0 ? (
          <div className="empty-state">
            [ NO_TARGETS_FOUND ]<br/>
            AWAITING_INPUT
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>ID</th>
                <th>DOMAIN</th>
                <th style={{ width: '200px' }}>ADDED_AT</th>
                <th style={{ width: '250px' }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {targets.map(t => {
                const isScanning = scanningTargets[t.id];
                const result = scanResults[t.id];

                return (
                  <tr key={t.id}>
                    <td>#{t.id}</td>
                    <td style={{ color: 'var(--accent-color)' }}>{t.domain}</td>
                    <td>{new Date(t.added_at).toLocaleString()}</td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <button 
                          onClick={() => handleScan(t.id)} 
                          disabled={isScanning}
                          style={{ width: 'fit-content' }}
                        >
                          {isScanning ? 'SCANNING...' : 'RUN_RECON'}
                        </button>

                        {/* Inline status reporting */}
                        {result && result.success && (
                          <div style={{ fontSize: '0.8em', color: 'var(--accent-color)' }}>
                            [SUCCESS] Found:{result.data.hosts_found} (New:{result.data.hosts_new} Upd:{result.data.hosts_updated})
                          </div>
                        )}
                        {result && !result.success && (
                          <div className="alert-error" style={{ margin: 0, padding: '6px', fontSize: '0.8em' }}>
                            [ERR] {result.error}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
