# daemon (zitles-agent)

Small local app the user installs. Proxies scraping traffic through their residential IP so county portals don't trigger captchas on cloud datacenter IPs.

Responsibilities:
- Outbound WebSocket to the tunnel coordinator (no port forwarding needed)
- Local SOCKS5 server that the tunnel routes traffic through
- Captcha detection + local browser popup for user to solve
- Status tray UI (online/offline, bandwidth used, jobs in flight)

v1 target: macOS only, internal users.

Not implemented yet — placeholder. Phase 5 in the build order; earlier phases use `chisel` as a stand-in.
