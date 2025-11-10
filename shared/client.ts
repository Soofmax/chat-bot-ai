/**
 * Client TypeScript léger pour consommer l'API RAG
 * Nécessite les types générés: shared/api-types.ts (générés en CI)
 */

import type { paths } from "./api-types";

type ChatBody = paths["/v1/chat"]["post"]["requestBody"]["content"]["application/json"];
type ChatOK = paths["/v1/chat"]["post"]["responses"]["200"]["content"]["application/json"];
type ChatErr =
  | paths["/v1/chat"]["post"]["responses"]["400"]["content"]["application/json"]
  | paths["/v1/chat"]["post"]["responses"]["401"]["content"]["application/json"]
  | paths["/v1/chat"]["post"]["responses"]["403"]["content"]["application/json"]
  | paths["/v1/chat"]["post"]["responses"]["404"]["content"]["application/json"]
  | paths["/v1/chat"]["post"]["responses"]["429"]["content"]["application/json"]
  | paths["/v1/chat"]["post"]["responses"]["500"]["content"]["application/json"];

export interface ChatClientOptions {
  baseUrl: string;
  apiKey?: string;
}

export class ChatClient {
  private baseUrl: string;
  private apiKey?: string;

  constructor(opts: ChatClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/+$/, "");
    this.apiKey = opts.apiKey;
  }

  async chat(body: ChatBody): Promise<{ ok: boolean; status: number; data: ChatOK | ChatErr }> {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (this.apiKey) headers["Authorization"] = `Bearer ${this.apiKey}`;

    const res = await fetch(`${this.baseUrl}/v1/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const text = await res.text();
    let data: any;
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
    return { ok: res.ok, status: res.status, data };
  }
}