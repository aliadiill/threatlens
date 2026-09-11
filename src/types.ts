export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM';
export type Status = 'OPEN' | 'INVESTIGATING' | 'RESOLVED';
export interface TimelineEvent { at: string; kind: string; actor: string; text: string; status?: Status }
export interface Incident { id: string; eventId: string; title: string; severity: Severity; category: string; resource: string; actor: string; region: string; source: string; eventName: string; createdAt: string; updatedAt: string; status: Status; version: number; simulated: boolean; guidance: string; response: string; timeline?: TimelineEvent[] }
export interface Config { mode: 'demo' | 'live'; apiUrl: string; cognitoDomain: string; clientId: string; scope: string }
export interface Page { items: Incident[]; nextCursor: string | null }
