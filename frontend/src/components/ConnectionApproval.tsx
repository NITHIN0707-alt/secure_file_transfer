import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldX, Wifi, Clock3 } from 'lucide-react';
import { api, PendingConnectionRequest } from '../services/api';

export function ConnectionApproval() {
  const [requests, setRequests] = useState<PendingConnectionRequest[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const data = await api.getPendingConnectionRequests();
        if (active) setRequests(data);
      } catch { /* The dashboard remains usable if the control API is temporarily unavailable. */ }
    };
    void refresh();
    const timer = window.setInterval(refresh, 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  const decide = async (request: PendingConnectionRequest, decision: 'approved' | 'rejected') => {
    setBusy(request.request_id);
    try {
      await api.decideConnectionRequest(request.request_id, decision);
      setRequests(current => current.filter(item => item.request_id !== request.request_id));
    } catch (error) {
      window.alert(error instanceof Error ? error.message : 'Unable to process connection request');
      setRequests(current => current.filter(item => item.request_id !== request.request_id));
    } finally { setBusy(null); }
  };

  if (!requests.length) return null;
  const request = requests[0];
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="connection-approval-title">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#10101b] p-6 shadow-2xl">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400"><ShieldCheck size={25} /></div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-400">Security approval required</p>
        <h2 id="connection-approval-title" className="mt-2 text-xl font-semibold text-white">Incoming device connection</h2>
        <p className="mt-2 text-sm leading-6 text-zinc-400">A device is requesting a TCP session with this receiver. Review the network address before allowing it.</p>
        <div className="my-5 space-y-3 rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center gap-3"><Wifi size={17} className="text-zinc-400" /><div><p className="text-xs text-zinc-500">Network address</p><p className="font-mono text-sm text-white">{request.client_ip}</p></div></div>
          <div className="flex items-center gap-3"><ShieldX size={17} className="text-zinc-400" /><div><p className="text-xs text-zinc-500">Device identity</p><p className="text-sm text-white">Unverified — {request.device_name}</p></div></div>
          <div className="flex items-center gap-3"><Clock3 size={17} className="text-zinc-400" /><div><p className="text-xs text-zinc-500">Request expires in</p><p className="text-sm text-white">{request.expires_in}s</p></div></div>
        </div>
        <p className="mb-4 text-xs text-zinc-500">Only approve devices you recognize. Approval permits this connection to continue to the separate login step.</p>
        <div className="grid grid-cols-2 gap-3">
          <button disabled={busy === request.request_id} onClick={() => void decide(request, 'rejected')} className="rounded-xl border border-white/10 px-4 py-3 text-sm font-medium text-zinc-200 hover:bg-white/5 disabled:opacity-50">Reject</button>
          <button disabled={busy === request.request_id} onClick={() => void decide(request, 'approved')} className="rounded-xl bg-[#ff6321] px-4 py-3 text-sm font-semibold text-white hover:bg-[#ed5518] disabled:opacity-50">{busy === request.request_id ? 'Processing…' : 'Approve connection'}</button>
        </div>
        {requests.length > 1 && <p className="mt-3 text-center text-xs text-zinc-500">{requests.length - 1} more request(s) waiting</p>}
      </div>
    </div>
  );
}
