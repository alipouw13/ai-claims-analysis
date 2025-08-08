export interface StartResponse {
  id: string; // durable instance id
  statusQueryGetUri?: string;
  sendEventPostUri?: string;
}

const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export async function startIngestion(document: {
  content: string; // base64
  content_type: string;
  filename: string;
  metadata?: Record<string, any>;
}) {
  const res = await fetch(`${baseUrl}/workflows/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document }),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as StartResponse;
}

export async function startQA(payload: any) {
  const res = await fetch(`${baseUrl}/workflows/qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as StartResponse;
}

export async function getStatus(instanceId: string) {
  const res = await fetch(`${baseUrl}/workflows/status?instance_id=${encodeURIComponent(instanceId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}


