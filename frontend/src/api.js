const API_BASE = 'http://192.168.126.128:8000';

export async function getProjects() {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error(`Failed to fetch projects: ${res.statusText}`);
  return res.json();
}

export async function createProject(name) {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  if (!res.ok) throw new Error(`Failed to create project: ${res.statusText}`);
  return res.json();
}

export async function getTargets(projectId) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/targets`);
  if (!res.ok) throw new Error(`Failed to fetch targets: ${res.statusText}`);
  return res.json();
}

export async function createTarget(projectId, domain) {
  const res = await fetch(`${API_BASE}/projects/${projectId}/targets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ domain })
  });
  if (!res.ok) throw new Error(`Failed to create target: ${res.statusText}`);
  return res.json();
}

export async function scanTarget(targetId) {
  const res = await fetch(`${API_BASE}/targets/${targetId}/scan`, {
    method: 'POST'
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to scan target: ${res.statusText}`);
  }
  return res.json();
}

export async function getHosts(targetId) {
  const res = await fetch(`${API_BASE}/targets/${targetId}/hosts`);
  if (!res.ok) throw new Error(`Failed to fetch hosts: ${res.statusText}`);
  return res.json();
}
