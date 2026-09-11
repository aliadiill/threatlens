import { token } from "./auth";
import type { Config, Incident, Page, Status } from "./types";
export async function request<T>(
  config: Config,
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(config.apiUrl + path, {
    ...init,
    headers: {
      "content-type": "application/json",
      Authorization: `Bearer ${token()}`,
      ...init?.headers,
    },
  });
  const data = await response.json();
  if (!response.ok)
    throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
export const list = (c: Config, cursor?: string) =>
  request<Page>(
    c,
    "/incidents" + (cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""),
  );
export const detail = (c: Config, id: string) =>
  request<Incident>(c, `/incidents/${id}`);
export const update = (c: Config, i: Incident, status: Status, note: string) =>
  request<Incident>(c, `/incidents/${i.id}`, {
    method: "PATCH",
    body: JSON.stringify({ version: i.version, status, note }),
  });
