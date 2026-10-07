# Security Policy

## Supported versions

Only the latest release on PyPI receives security fixes. Upgrade to the newest
version before reporting an issue.

## Reporting a vulnerability

Please do not open a public issue for security problems.

Use GitHub's private vulnerability reporting for this repository:
<https://github.com/michaelrice/zendesk-mcp/security/advisories/new>

Include the version you tested, what the issue lets an attacker do, and how to
reproduce it. A patch with tests is welcome but not required.

You can expect an acknowledgement within a few days. Fixes are released as a new
version on PyPI together with a GitHub security advisory, and reporters are
credited unless they ask not to be.

## Scope

This server holds an OAuth token with read and write access to a Zendesk
account, and its tools act on arguments chosen by a language model that reads
customer-written ticket content. Reports about prompt-injection paths that lead
to token exposure, writes outside the attachment cache, or unintended Zendesk
changes are in scope.
