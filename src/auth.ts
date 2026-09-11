import type { Config } from './types';
let accessToken: string | null = null;
let expiresAt = 0;
const b64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
export function authenticated() { return !!accessToken && Date.now() < expiresAt; }
export function token() { if (!authenticated()) throw new Error('Sign in to continue. Your session may have expired.'); return accessToken!; }
export async function signIn(config: Config) {
  const verifier = b64(crypto.getRandomValues(new Uint8Array(48)));
  const state = b64(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem('tl-pkce', verifier); sessionStorage.setItem('tl-state', state);
  const challenge = b64(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
  const url = new URL('/oauth2/authorize', config.cognitoDomain);
  url.search = new URLSearchParams({ client_id: config.clientId, response_type: 'code', scope: config.scope, redirect_uri: window.location.origin + '/', state, code_challenge_method: 'S256', code_challenge: challenge }).toString();
  window.location.assign(url);
}
export async function completeSignIn(config: Config) {
  const params = new URLSearchParams(window.location.search);
  if (params.has('error')) { history.replaceState({}, '', '/'); throw new Error('Sign-in was not completed.'); }
  const code = params.get('code'); if (!code) return;
  const verifier = sessionStorage.getItem('tl-pkce');
  const state = sessionStorage.getItem('tl-state');
  sessionStorage.removeItem('tl-pkce'); sessionStorage.removeItem('tl-state');
  history.replaceState({}, '', '/');
  if (!verifier || !state || params.get('state') !== state) throw new Error('Sign-in state did not match. Start again.');
  const result = await fetch(new URL('/oauth2/token', config.cognitoDomain), { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ grant_type: 'authorization_code', client_id: config.clientId, code, redirect_uri: window.location.origin + '/', code_verifier: verifier }) });
  if (!result.ok) throw new Error('The sign-in code could not be exchanged.');
  const body = await result.json(); accessToken = body.access_token; expiresAt = Date.now() + Number(body.expires_in) * 1000;
}
export function signOut(config: Config) { accessToken = null; expiresAt = 0; const url = new URL('/logout', config.cognitoDomain); url.search = new URLSearchParams({ client_id: config.clientId, logout_uri: window.location.origin + '/' }).toString(); window.location.assign(url); }
