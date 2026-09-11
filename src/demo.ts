import type { Incident, Status } from './types';
import fixture from './fixtures.json';
const KEY = 'threatlens-demo-v1';
export function initialIncidents(): Incident[] { return structuredClone(fixture) as Incident[]; }
export function loadDemo(): Incident[] {
  try { const value = JSON.parse(localStorage.getItem(KEY) || 'null'); if (Array.isArray(value) && value.every(i => i.id && i.status && Array.isArray(i.timeline))) return value; } catch { /* Reset corrupted browser-only data. */ }
  return initialIncidents();
}
export function persistDemo(items: Incident[]) { localStorage.setItem(KEY, JSON.stringify(items)); }
export function changeDemo(item: Incident, status: Status, note: string, version: number, now = new Date().toISOString()): Incident {
  if (version !== item.version) throw new Error('Incident changed; refresh and retry');
  if (status === 'RESOLVED' && !note.trim()) throw new Error('A resolution note is required');
  if (note.length > 2000) throw new Error('Notes may contain at most 2,000 characters');
  if (item.status === 'RESOLVED' && status === 'OPEN') throw new Error('Reopen as investigating first');
  return { ...item, status, version: version + 1, updatedAt: now, timeline: [...(item.timeline || []), { at: now, actor: 'local-demo-analyst', kind: 'ANALYST_UPDATE', text: note.trim() || `Status changed to ${status}`, status }] };
}
export function filterIncidents(items: Incident[], query: string, severity: string, status: string) {
  const term = query.toLowerCase().trim();
  return items.filter(i => (severity === 'ALL' || severity === i.severity) && (status === 'ALL' || status === i.status) && `${i.title} ${i.resource} ${i.category} ${i.id}`.toLowerCase().includes(term));
}
