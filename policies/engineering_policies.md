POLICY SEC-001: No hardcoded secrets
Passwords, API keys, tokens and private keys must never be written in source code.
They must be read from environment variables or a secrets manager.

POLICY SEC-002: Parameterized SQL only
SQL queries must use parameterized statements. Building queries with string
concatenation or f-strings with user input is forbidden.

POLICY SEC-003: No eval or exec
The use of eval(), exec() or compile() on dynamic input is forbidden.

POLICY LOG-001: No sensitive data in logs
Passwords, tokens, API keys and personal data must never be logged or printed.

POLICY ERR-001: No swallowed exceptions
Bare "except:" blocks and empty "except Exception: pass" handlers are forbidden.
Errors must be logged or re-raised.

POLICY NET-001: HTTP calls need timeouts
Every outgoing HTTP request must set an explicit timeout.