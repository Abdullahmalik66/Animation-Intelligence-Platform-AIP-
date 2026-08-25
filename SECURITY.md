# Security Policy

## Reporting a Vulnerability

If you find a security issue in this repository — in the skill content, examples, or documentation — please report it privately.

**Do not open a public GitHub issue for security vulnerabilities.**

Email: security@your-org.com (update this with your actual contact)

We will respond within 5 business days.

---

## Security Rules in This Repository

All skill files and examples in this repository follow these security rules:

### Never

- Run remote scripts as part of animation setup
- Load animation assets from untrusted external URLs
- Inject SVG content without sanitization
- Expose API keys, tokens, or secrets in animation configuration
- Install packages from unverified sources

### Always

- Load Lottie JSON and Rive files from your own origin
- Sanitize SVG with DOMPurify before DOM injection
- Use Subresource Integrity (SRI) for CDN script tags
- Treat all user input as untrusted
- Pin dependency versions in `package.json`

---

## Scope

This security policy covers:

- ✅ Security guidance in skill files (`skills/`)
- ✅ Code examples in `examples/`
- ✅ Documentation in `docs/` and `references/`

This policy does not cover:

- ❌ Third-party animation libraries (report to their respective maintainers)
- ❌ User implementations based on these skills
