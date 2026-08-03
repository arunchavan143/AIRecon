import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { getHosts } from '../api';

export default function Hosts() {
  const { targetId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const targetDomain = location.state?.targetDomain || `TARGET_${targetId}`;
  const projectId = location.state?.projectId;

  const [hosts, setHosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filters
  const [aliveOnly, setAliveOnly] = useState(false);
  const [techFilter, setTechFilter] = useState('');

  useEffect(() => {
    fetchHosts();
  }, [targetId]);

  async function fetchHosts() {
    setLoading(true);
    setError(null);
    try {
      const data = await getHosts(targetId);
      setHosts(data);
    } catch (err) {
      setError(err.message === 'Failed to fetch' 
        ? 'BACKEND_UNREACHABLE - check that the API server is running' 
        : err.message);
    } finally {
      setLoading(false);
    }
  }

  const filteredHosts = hosts.filter(h => {
    if (aliveOnly && !h.alive) return false;
    if (techFilter.trim()) {
      const match = techFilter.toLowerCase();
      const hasTech = h.tech_stack && h.tech_stack.some(t => t.toLowerCase().includes(match));
      if (!hasTech) return false;
    }
    return true;
  });

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px' }}>
      
      <div style={{ marginBottom: '20px', fontFamily: 'var(--font-mono)' }}>
        <button 
          onClick={() => {
            if (projectId) {
              navigate(`/projects/${projectId}/targets`, { state: { projectName: location.state?.projectName } });
            } else {
              navigate('/');
            }
          }}
          style={{ padding: '6px 12px', fontSize: '0.8em' }}
        >
          &lt; BACK_TO_TARGETS
        </button>
      </div>

      <h1 style={{ borderBottom: '1px solid var(--accent-transparent)', paddingBottom: '10px', marginBottom: '30px' }}>
        [&gt;] {targetDomain.toUpperCase()}::HOSTS
      </h1>
      
      {error && (
        <div className="alert-error">
          <span>[ERR]</span> {error}
        </div>
      )}

      {/* Filter Bar */}
      <div className="panel" style={{ marginBottom: '30px', display: 'flex', gap: '20px', alignItems: 'center' }}>
        <div style={{ fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input 
            type="checkbox" 
            id="aliveFilter"
            checked={aliveOnly}
            onChange={(e) => setAliveOnly(e.target.checked)}
            style={{ width: '16px', height: '16px', accentColor: 'var(--accent-color)' }}
          />
          <label htmlFor="aliveFilter" style={{ cursor: 'pointer', color: aliveOnly ? 'var(--accent-color)' : 'var(--text-main)' }}>
            ALIVE_ONLY
          </label>
        </div>
        
        <div style={{ flex: 1, display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>TECH_FILTER:</span>
          <input
            type="text"
            value={techFilter}
            onChange={(e) => setTechFilter(e.target.value)}
            placeholder="e.g. nginx, php, react"
            style={{ flex: 1, maxWidth: '300px' }}
          />
        </div>
        
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9em', color: 'var(--text-muted)' }}>
          SHOWING: {filteredHosts.length} / {hosts.length}
        </div>
      </div>

      <div className="panel">
        {loading && hosts.length === 0 ? (
          <div className="loading-text">[ FETCHING_HOSTS... ]</div>
        ) : hosts.length === 0 ? (
          <div className="empty-state">
            [ NO_HOSTS_FOUND ]<br/>
            RUN_RECON_FROM_TARGETS_PAGE
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>HOSTNAME</th>
                  <th>IP</th>
                  <th>STATUS</th>
                  <th>TITLE</th>
                  <th>TECH_STACK</th>
                  <th>SERVER</th>
                  <th>ALIVE</th>
                </tr>
              </thead>
              <tbody>
                {filteredHosts.map(h => (
                  <tr key={h.id}>
                    <td style={{ color: 'var(--accent-color)', fontWeight: 'bold' }}>{h.hostname}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{h.ip || '-'}</td>
                    <td>
                      {h.status_code ? (
                        <span style={{ 
                          color: h.status_code >= 200 && h.status_code < 400 ? 'var(--accent-color)' : 
                                 h.status_code >= 400 ? 'var(--error-color)' : 'var(--text-main)'
                        }}>
                          {h.status_code}
                        </span>
                      ) : '-'}
                    </td>
                    <td style={{ maxWidth: '200px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={h.title}>
                      {h.title || '-'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {h.tech_stack && h.tech_stack.length > 0 ? h.tech_stack.map(tech => (
                          <span 
                            key={tech}
                            style={{ 
                              fontSize: '0.75em', 
                              padding: '2px 6px', 
                              backgroundColor: 'var(--accent-transparent)', 
                              border: '1px solid var(--accent-transparent)',
                              borderRadius: '3px',
                              color: 'var(--text-main)',
                              whiteSpace: 'nowrap'
                            }}
                          >
                            {tech}
                          </span>
                        )) : '-'}
                      </div>
                    </td>
                    <td style={{ fontSize: '0.9em' }}>{h.server || '-'}</td>
                    <td>
                      {/* Intentional: alive means the host responded, regardless of HTTP status code */}
                      {h.alive ? (
                        <span style={{ color: 'var(--accent-color)', fontWeight: 'bold' }}>● YES</span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>○ NO</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredHosts.length === 0 && hosts.length > 0 && (
              <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                [ NO_MATCHES_FOR_CURRENT_FILTERS ]
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
