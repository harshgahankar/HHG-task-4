const API_BASE = '';

export async function fetchCases() {
  const res = await fetch(`${API_BASE}/api/cases`);
  if (!res.ok) throw new Error('Failed to fetch cases');
  return res.json();
}

export async function fetchCase(caseId) {
  const res = await fetch(`${API_BASE}/api/cases/${caseId}`);
  if (!res.ok) throw new Error('Case not found');
  return res.json();
}

export async function runInvestigation(caseId) {
  const res = await fetch(`${API_BASE}/api/investigate/${caseId}`, { method: 'POST' });
  if (!res.ok) throw new Error('Investigation failed');
  return res.json();
}

export async function runAllInvestigations() {
  const res = await fetch(`${API_BASE}/api/investigate-all`, { method: 'POST' });
  if (!res.ok) throw new Error('Batch investigation failed');
  return res.json();
}

export async function fetchSubgraph(txnId, hops = 2) {
  const res = await fetch(`${API_BASE}/api/graph/subgraph/${txnId}?hops=${hops}`);
  if (!res.ok) throw new Error('Subgraph fetch failed');
  return res.json();
}

export async function fetchGraphStats() {
  const res = await fetch(`${API_BASE}/api/graph/stats`);
  if (!res.ok) throw new Error('Stats fetch failed');
  return res.json();
}

export async function fetchSimilarCases(caseId) {
  const res = await fetch(`${API_BASE}/api/similar-cases/${caseId}`);
  if (!res.ok) throw new Error('Similar cases fetch failed');
  return res.json();
}

export async function fetchAuditLog(caseId = null) {
  const url = caseId ? `${API_BASE}/api/audit?case_id=${caseId}` : `${API_BASE}/api/audit`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Audit log fetch failed');
  return res.json();
}

export async function fetchPatterns() {
  const res = await fetch(`${API_BASE}/api/patterns`);
  if (!res.ok) throw new Error('Patterns fetch failed');
  return res.json();
}

export async function fetchClosedCases(pattern = null, outcome = null) {
  let url = `${API_BASE}/api/closed-cases?`;
  if (pattern) url += `pattern=${pattern}&`;
  if (outcome) url += `outcome=${outcome}&`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Closed cases fetch failed');
  return res.json();
}
