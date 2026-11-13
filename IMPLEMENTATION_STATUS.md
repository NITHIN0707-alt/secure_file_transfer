# ATP implementation status — receiver approval milestone

## Implemented in this revision
- Per-TCP-connection, single-use approval requests with a 30-second expiry.
- Receiver dashboard modal with peer IP, unverified identity label, approve and reject actions.
- Loopback-only approval API endpoints.
- TCP sessions are not allowed to process protocol messages until approval.
- X25519 key exchange now produces `KEY_EXCHANGED`, not `AUTHENTICATED`.
- Upload, chunk, resume, completion and download paths require both approval and successful login.
- Bundled TCP sender authenticates before upload, resume and download.
- Tests cover approval, rejection, expiry, protocol/crypto and TCP transfer/resume paths.

## Verification performed
- `python -m compileall -q backend` — passed.
- `python -m pytest backend/tests/test_connection_approval.py backend/tests/test_tcp_transfer.py backend/tests/test_resumable.py backend/tests/test_protocol.py backend/tests/test_crypto.py -q` — 16 passed.
- Frontend build was attempted but could not complete because the frontend dependencies are not installed in this environment (`vite/client` and `node` type definitions unavailable). Run `cd frontend && npm install && npm run build` on the development machine.

## Not yet production-ready
- Device name/type and IP are metadata, not cryptographically verified identity.
- No Ed25519 signed handshake transcript or pinned server identity yet; active MITM protection is not established.
- The project still needs administrator web authentication, Argon2id/bcrypt password hashing, secure secret configuration, and broader authorization/replay/ownership tests.
- Approval API is intentionally restricted to loopback; open the dashboard on the receiver using `http://localhost:8000`.
