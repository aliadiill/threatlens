import { describe, expect, it } from 'vitest';
import { initialIncidents, changeDemo, filterIncidents } from './demo';
describe('analyst demo workflow', () => {
  it('has ten deterministic findings across five categories', () => { const items = initialIncidents(); expect(items).toHaveLength(10); expect(new Set(items.map(i => i.category)).size).toBe(5); expect(items.every(i => i.simulated)).toBe(true); });
  it('combines search, severity and status filters', () => { const items = initialIncidents(); expect(filterIncidents(items, 'administrator', 'HIGH', 'OPEN')).toHaveLength(2); expect(filterIncidents(items, 'administrator', 'CRITICAL', 'OPEN')).toHaveLength(0); });
  it('keeps prior timeline and appends a resolution note', () => { const item = initialIncidents()[0]; const changed = changeDemo(item, 'RESOLVED', 'Approved lab activity', 1, '2026-01-16T00:00:00Z'); expect(changed.version).toBe(2); expect(changed.timeline).toHaveLength(2); expect(item.timeline).toHaveLength(1); expect(changed.status).toBe('RESOLVED'); });
  it('rejects stale writes', () => expect(() => changeDemo(initialIncidents()[0], 'OPEN', '', 4)).toThrow('refresh'));
  it('requires explanation for resolution', () => expect(() => changeDemo(initialIncidents()[0], 'RESOLVED', ' ', 1)).toThrow('resolution note'));
  it('requires reopening through investigation', () => { const item = changeDemo(initialIncidents()[0], 'RESOLVED', 'Verified', 1); expect(() => changeDemo(item, 'OPEN', '', 2)).toThrow('investigating'); });
  it('bounds note length', () => expect(() => changeDemo(initialIncidents()[0], 'OPEN', 'x'.repeat(2001), 1)).toThrow('2,000'));
});
