# Security and private playlists

Do not put a real IPTV playlist, provider URL, username, password, bearer token,
or generated configuration ZIP in a GitHub issue. Redact complete query strings
and URL path tokens from logs before sharing them.

The control page is designed for a trusted home network or personal phone
hotspot. It is PIN-protected but does not provide TLS. Do not port-forward it,
place it directly on the public internet, or use the same PIN as another
account.

For a security report, open a GitHub security advisory for the repository rather
than a public issue.
