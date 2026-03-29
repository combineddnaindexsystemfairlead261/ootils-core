# Security Policy

## Supported Versions

Ootils is currently in pre-release (concept / white paper phase). No production releases exist yet.

| Version | Supported |
|---------|-----------|
| pre-release | architecture review only |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues privately:
1. Go to the [Security tab](../../security) of this repository
2. Click "Report a vulnerability"
3. Provide a clear description, steps to reproduce, and potential impact

We will acknowledge receipt within 72 hours and provide a timeline for resolution.

## Security Considerations for a Planning Engine

Ootils handles supply chain data that may include:
- Customer order information
- Supplier contracts and pricing
- Production capacity and schedules
- Inventory positions

Any implementation should apply appropriate access controls at the API layer. The core engine itself does not handle authentication — that is the responsibility of the deployment layer.

We will publish security guidelines as part of the V1 deployment documentation.
