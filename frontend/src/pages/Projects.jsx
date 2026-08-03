import { useState, useEffect } from 'react';
import { getProjects, createProject } from '../api';

export default function Projects() {
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
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>AIRecon Projects</h1>
      
      {error && (
        <div style={{ color: 'red', marginBottom: '20px', padding: '10px', border: '1px solid red' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      <form onSubmit={handleCreate} style={{ marginBottom: '30px' }}>
        <input
          type="text"
          value={newProjectName}
          onChange={(e) => setNewProjectName(e.target.value)}
          placeholder="New project name..."
          disabled={isCreating}
          style={{ padding: '8px', marginRight: '10px' }}
        />
        <button type="submit" disabled={isCreating || !newProjectName.trim()} style={{ padding: '8px' }}>
          {isCreating ? 'Creating...' : 'Create Project'}
        </button>
      </form>

      {loading && projects.length === 0 ? (
        <p>Loading projects...</p>
      ) : projects.length === 0 ? (
        <p>No projects found. Create one above!</p>
      ) : (
        <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #ccc' }}>
              <th style={{ padding: '10px 0' }}>ID</th>
              <th>Name</th>
              <th>Created At</th>
            </tr>
          </thead>
          <tbody>
            {projects.map(p => (
              <tr key={p.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '10px 0' }}>{p.id}</td>
                <td>{p.name}</td>
                <td>{new Date(p.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
