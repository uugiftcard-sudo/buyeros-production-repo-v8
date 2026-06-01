"use client";

interface ApiConfigProps {
  apiState: { proxyUrl: string; apiKey: string };
  setApiState: (state: { proxyUrl: string; apiKey: string }) => void;
}

export function ApiConfig({ apiState, setApiState }: ApiConfigProps) {
  return (
    <div className="card">
      <h2>API Config</h2>
      <form className="flex gap-2">
        <input
          type="text"
          placeholder="Proxy URL"
          value={apiState.proxyUrl}
          onChange={(e) => setApiState({ ...apiState, proxyUrl: e.target.value })}
          className="border p-2 rounded"
        />
        <input
          type="password"
          placeholder="API Key"
          value={apiState.apiKey}
          onChange={(e) => setApiState({ ...apiState, apiKey: e.target.value })}
          className="border p-2 rounded"
        />
      </form>
    </div>
  );
}
