# Security Policy

## Supported Versions

We release patches for security vulnerabilities. The following versions are currently being supported with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

The security of our users is a top priority. If you have discovered a security vulnerability in Modbus Web Server, we appreciate your help in disclosing it to us in a responsible manner.

### Please do the following:

1. **Do not** open a public issue on GitHub
2. Email your findings to the project maintainers (create a security advisory on GitHub)
3. Include as much information as possible:
   - Type of vulnerability
   - Full paths of source files related to the vulnerability
   - Location of affected source code (tag/branch/commit or direct URL)
   - Step-by-step instructions to reproduce the issue
   - Proof-of-concept or exploit code (if possible)
   - Impact of the issue, including how an attacker might exploit it

### What to expect:

- **Initial Response**: We will acknowledge your email within 48 hours
- **Status Updates**: We will send you regular updates about our progress
- **Fix Timeline**: We aim to release a fix within 30 days for critical vulnerabilities
- **Credit**: We will credit you for the discovery when we publish the fix (unless you prefer to remain anonymous)

## Security Best Practices

When deploying Modbus Web Server, please follow these security recommendations:

### Production Deployment

- **Never use DEBUG=True** in production environments
- **Change the SECRET_KEY** from the default value
- Use **HTTPS** for all web traffic
- Configure **ALLOWED_HOSTS** appropriately
- Enable **CSRF protection** (enabled by default)
- Use **secure cookies** (SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)

### Database Security

- Use **strong database passwords**
- Restrict database access to localhost when possible
- Regularly backup your database
- Keep database software updated

### Network Security

- **Isolate Modbus networks** from the internet
- Use **firewalls** to restrict access to the application
- Consider using **VPN** for remote access
- Implement **network segmentation** between IT and OT networks
- Use **strong authentication** for Modbus devices

### Application Security

- Keep Python and all dependencies **up to date**
- Use a **reverse proxy** (nginx/Apache) in production
- Implement **rate limiting** for API endpoints
- Enable **logging and monitoring** for suspicious activity
- Use **environment variables** for sensitive configuration
- Regularly review and update **user permissions**

### Redis Security

- **Bind Redis** to localhost only
- Set a **strong Redis password** (requirepass)
- Disable dangerous commands if not needed
- Keep Redis updated to the latest version

### Modbus Security Considerations

Modbus protocol has limited built-in security features:

- Modbus RTU/TCP does **not provide encryption** by default
- Implement security at the **network layer** (VPN, firewalls)
- Use **authentication** at the application level
- Monitor for **unusual Modbus traffic patterns**
- Consider using **Modbus over TLS** when available
- Limit **write access** to registers based on user roles

### Docker Security

If using Docker deployment:

- Run containers as **non-root users**
- Use **official base images** only
- Keep Docker and images **updated**
- Scan images for **vulnerabilities**
- Use **secrets management** for sensitive data
- Limit container **resource usage**

## Security Updates

Security updates will be announced through:

- GitHub Security Advisories
- Release notes
- Repository README updates

We recommend:

- **Subscribe** to repository notifications
- **Review** release notes before updating
- **Test** updates in a development environment first
- Keep your installation **up to date**

## Known Security Considerations

### Modbus Protocol Limitations

- Modbus RTU/TCP lacks built-in authentication and encryption
- Commands can be intercepted or modified on the network
- Unauthorized access to Modbus devices can cause physical damage
- Always implement additional security layers

### WebSocket Connections

- WebSocket connections should be secured with WSS (WebSocket Secure)
- Implement proper authentication before establishing WebSocket connections
- Validate all incoming WebSocket messages

### API Security

- API endpoints are protected by Django REST Framework authentication
- Use token-based authentication for external integrations
- Implement rate limiting to prevent abuse
- Validate and sanitize all input data

## Compliance

This application handles industrial control system data. Ensure compliance with:

- Relevant data protection regulations (GDPR, etc.)
- Industry-specific standards (IEC 62443, NIST, etc.)
- Local and national security requirements
- Organizational security policies

## Third-Party Dependencies

We regularly monitor our dependencies for security vulnerabilities using:

- GitHub Dependabot alerts
- PyPI vulnerability database
- Security advisories from package maintainers

## Disclosure Policy

- We follow **coordinated vulnerability disclosure**
- Security issues will be patched before public disclosure
- We will credit researchers who report vulnerabilities responsibly
- Public disclosure will include fix details and affected versions

## Contact

For security-related questions or concerns, please create a GitHub Security Advisory or contact the maintainers through GitHub.

Thank you for helping keep Modbus Web Server and its users safe!
