from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP, in-memory. There's no auth yet (see ARCHITECTURE.md "Known gaps"),
# so IP is the only real client boundary available right now. In-memory
# storage is fine for a single backend instance; a multi-instance deploy
# would need a shared store (e.g. Redis) so limits are enforced across
# instances, not per-instance.
# key_style="endpoint": slowapi's default buckets by the literal resolved URL
# path (e.g. "/attempts/256/answer"), so every distinct attempt_id would get
# its own bucket and never accumulate a count. "endpoint" buckets by the view
# function instead, which is what you want for any route with a path param.
limiter = Limiter(key_func=get_remote_address, key_style="endpoint")
