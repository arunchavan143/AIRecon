import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getProjects, createProject } from '../api';

export default function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  async function fetchProjects() {
    setLoading(true);
    setError(null);
    try {
      const data = await getProjects();
      setProjects(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!newProjectName.trim()) return;

    setIsCreating(true);
    try {
      await createProject(newProjectName);
      setNewProjectName('');
      await fetchProjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '40px 20px' }}>
      <h1 style={{ borderBottom: '1px solid var(--accent-transparent)', paddingBottom: '10px', marginBottom: '30px' }}>
        [&gt;] AI_RECON::PROJECTS
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
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            placeholder="ENTER_NEW_PROJECT_NAME"
            disabled={isCreating}
            style={{ flex: 1 }}
          />
          <button type="submit" disabled={isCreating || !newProjectName.trim()}>
            {isCreating ? 'INITIALIZING...' : 'INITIALIZE'}
          </button>
        </form>
      </div>

      <div className="panel">
        {loading && projects.length === 0 ? (
          <div className="loading-text">[ LOADING_PROJECTS... ]</div>
        ) : projects.length === 0 ? (
          <div className="empty-state">
            [ NO_PROJECTS_FOUND ]<br/>
            AWAITING_INITIALIZATION
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>ID</th>
                <th>PROJECT_NAME</th>
                <th style={{ width: '250px' }}>CREATED_AT</th>
              </tr>
            </thead>
            <tbody>
              {projects.map(p => (
                <tr 
                  key={p.id} 
                  onClick={() => navigate(`/projects/${p.id}/targets`, { state: { projectName: p.name } })}
                  style={{ cursor: 'pointer' }}
                  title="VIEW_TARGETS"
                >
                  <td>#{p.id}</td>
                  <td style={{ color: 'var(--accent-color)' }}>{p.name}</td>
                  <td>{new Date(p.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
