# Security Policy

## Supported Versions
We provide security updates according to the following policy:

| Version | Supported |
| ------- | --------- |
| 2.x     | :white_check_mark: |
| 1.x     | :warning: Security fixes only |
| < 1.0   | :x: |

## Reporting a Vulnerability
Please report security issues **privately**.

- Primary contact: admin@ratchetsurgery.xyz
- Expected response time: **48 hours** for acknowledgment
- Encryption: Please request a PGP key or use a secure submission form (if available).

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

Please do **not** disclose the issue publicly until a patch is released and we have coordinated disclosure timing.

## Security Update Process
- We assess reports, reproduce the issue, and develop a fix.
- Patches are tested and released as quickly as possible, depending on severity.
- Security releases are announced via GitHub Security Advisories.
- For serious vulnerabilities, we will request a CVE where applicable.

## Security Best Practices (Users)
- Keep PivotStream updated.
- Review PivotStream configurations for sensitive paths.
- Do not commit `.env` files with credentials.
- Use virtual environments for local development.
- Verify the integrity of PivotStream downloads.

## Known Security Considerations
- Configuration files may contain file paths; treat them as sensitive if they expose system structure.

## Hall of Fame (Optional)
We appreciate and acknowledge security researchers who report vulnerabilities responsibly.
