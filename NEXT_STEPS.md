# LandVerify: What We Do Next

## Current position

LandVerify is a working MVP. Users can create accounts, save documents, upload documents for checking, and receive a green **REAL DOCUMENT** or red **FAKE DOCUMENT** result when the uploaded file matches or differs from a saved copy.

The application is deployed with Docker and PostgreSQL, has a responsive interface, a help page, a land-search request form, pricing pages, and automated tests.

The result is a file-integrity check. It does **not** yet prove legal ownership, title validity, or government-issued authenticity.

## Priority plan

### Phase 1: Stabilize the MVP

**Goal:** Make the current system reliable for controlled pilot users.

- [ ] Test the complete user journey on Windows, macOS, and Linux.
- [ ] Test Chrome, Edge, Firefox, and Safari.
- [ ] Test desktop, tablet, and mobile layouts.
- [ ] Test account registration, login, logout, document saving, checking, and help.
- [ ] Test PDF, PNG, JPG, JPEG, and TXT uploads.
- [ ] Confirm files above 10 MB are rejected safely.
- [ ] Fix all high-priority errors found during user acceptance testing.
- [ ] Keep automatic approval disabled for real land documents unless an authorized owner explicitly accepts the risk.

**Done when:** Five pilot users can complete the main workflow without assistance and all automated tests pass.

### Phase 2: Secure document handling

**Goal:** Protect uploaded land documents and user information.

- [ ] Add malware scanning and quarantine before a document is accepted.
- [ ] Store files in private object storage or protected volumes.
- [ ] Add document retention and deletion rules.
- [ ] Add encrypted backups.
- [ ] Perform a restore drill and record the result.
- [ ] Add MFA or an approved enterprise identity provider.
- [ ] Review administrator, reviewer, verifier, and submitter permissions.
- [ ] Add monitoring, alerts, and rate limits for important operations.

**Done when:** A security review confirms that documents, accounts, and audit records are protected and recoverable.

### Phase 3: Official land-record integration

**Goal:** Add authoritative land information without inventing or overstating results.

- [ ] Identify the responsible government or authorized data owner.
- [ ] Obtain written permission and an integration agreement.
- [ ] Obtain official API or portal documentation.
- [ ] Obtain sandbox credentials and test data.
- [ ] Define allowed fields, such as title number, proprietor, tenure, area, caveats, mortgages, and pending instruments.
- [ ] Define API errors, unavailable-service behavior, timeouts, and audit requirements.
- [ ] Build an adapter behind a clear configuration boundary.
- [ ] Label official results separately from local file matching.
- [ ] Add source, timestamp, and reference information to every official result.

**Done when:** An authorized test query returns verified source data and the application never presents a local match as government confirmation.

### Phase 4: Payments and subscriptions

**Goal:** Turn the billing foundation into a real, trustworthy service.

- [ ] Register the business and merchant account.
- [ ] Select an approved payment provider that supports the target market.
- [ ] Obtain sandbox credentials.
- [ ] Implement hosted checkout or provider-approved payment collection.
- [ ] Implement signed webhook verification.
- [ ] Record successful, failed, cancelled, and refunded payments.
- [ ] Activate a subscription only after confirmed payment.
- [ ] Add invoices and receipts.
- [ ] Add renewal, expiry, cancellation, and refund handling.
- [ ] Never store card or mobile-money secrets in the application database.
- [ ] Test duplicate webhooks and interrupted payments.

**Done when:** A sandbox payment reliably changes the correct account plan and an unsuccessful payment never activates paid access.

### Phase 5: Reports and business operations

**Goal:** Provide useful paid services to individuals and organizations.

- [ ] Define exactly what each plan includes.
- [ ] Add downloadable verification reports.
- [ ] Add organization accounts and team members.
- [ ] Add usage limits and usage history.
- [ ] Add support contact details and response targets.
- [ ] Add organization billing and administrator controls.
- [ ] Define pricing, taxes, refunds, and terms of service.
- [ ] Create a privacy notice and document-handling policy.

**Done when:** A customer can understand the price, pay safely, use the promised features, download a report, and request support.

### Phase 6: Production approval

**Goal:** Launch responsibly.

- [ ] Complete privacy and legal review.
- [ ] Complete threat modeling.
- [ ] Complete an independent penetration test.
- [ ] Replace the local proof adapter with an approved production ledger or signed audit service, if required.
- [ ] Configure HTTPS and production domains.
- [ ] Configure centralized logs and alerting.
- [ ] Review backup and restore evidence.
- [ ] Create an incident-response plan.
- [ ] Create an access-review schedule.
- [ ] Run a limited pilot before public launch.

**Done when:** The accountable business and data owners approve the service for production use.

## What we should do first

1. Run structured pilot testing on multiple devices and browsers.
2. Decide whether records require human approval.
3. Begin the official data-access request.
4. Choose a payment provider and open a sandbox account.
5. Add malware scanning and backup/restore procedures.
6. Complete the privacy, legal, and security reviews.

## Important product rules

- A matching file means the bytes match a saved copy.
- A different file must not automatically be described as legally fraudulent.
- The application must not claim official ownership or title confirmation without an authorized official source.
- Payment must not be marked successful until the provider confirms it.
- Sensitive documents, passwords, API keys, and payment credentials must never be committed to GitHub.
