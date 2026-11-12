# LandVerify

## Panel Presentation

### A simple system for checking land-document integrity

**Presenter:** Nairah  
**Project:** LandVerify  
**Current stage:** Working document-integrity MVP / controlled pilot

---

## Slide 1: Title

### LandVerify

**Checking whether a land document matches a trusted saved copy**

**Opening statement**

> Land disputes and altered documents can cause financial loss, delays, and conflict. LandVerify helps users check whether a document is exactly the same as a trusted copy saved in the system.

**Speaker note**

Do not begin by claiming that the system proves legal ownership. Explain that it currently checks document integrity and is designed to connect to authoritative land services in a later phase.

---

## Slide 2: The problem

- Land documents may be lost, altered, or replaced.
- A small change to an area, name, date, or plot number can be difficult to notice.
- Manual comparison is slow and unreliable.
- Users need a simple way to check whether a file has changed.
- Official land ownership still requires an authorized land registry or issuing office.

**Say this**

> Our first problem is not trying to replace the government registry. Our first problem is detecting whether the digital document being checked is the same document that was previously trusted and registered.

---

## Slide 3: Our solution

LandVerify provides:

1. Account registration and secure sign-in.
2. Registration of a trusted document.
3. A unique record number.
4. A secure SHA-256 document fingerprint.
5. Upload and comparison of another copy.
6. A simple result:
   - Green: **REAL DOCUMENT**
   - Red: **FAKE DOCUMENT**
7. Audit records for important actions.

**Plain-language explanation**

> The system does not guess. It compares the uploaded file with the saved file fingerprint.

---

## Slide 4: How it works

```text
Trusted document
       |
       v
SHA-256 fingerprint
       |
       v
Private database record
       |
       v
User uploads a document to check
       |
       v
Fingerprint comparison
       |
   +---+---+
   |       |
  Same   Different
   |       |
 REAL    FAKE
```

**Technical explanation**

- SHA-256 produces a fingerprint from the exact file bytes.
- Changing one character or one pixel changes the fingerprint.
- The original file is stored in protected private storage.
- The fingerprint is stored with the record metadata.
- The comparison does not expose the document publicly.

---

## Slide 5: Where blockchain fits

### Current implementation

- SHA-256 document fingerprints.
- Hash-chained application audit entries.
- Local proof references for approval and review events.
- No personal document contents are written to a public blockchain.

### Honest current status

> LandVerify is blockchain-ready, but it is not connected to a real blockchain network yet.

### Future production option

With written authorization, we can connect an approved permissioned ledger and store only:

- Document fingerprint.
- Record reference.
- Event type.
- Timestamp.
- Transaction reference.

**Important**

The blockchain would prove that a recorded fingerprint and event existed. It would not by itself prove legal ownership.

---

## Slide 6: User experience

### A new user can:

1. Open **Get help**.
2. Create an account.
3. Choose **Add a record**.
4. Upload the trusted document.
5. Choose **Check your document**.
6. Upload the document to check.
7. Read the green or red result.

### Design choices

- Simple words instead of technical terms.
- Optional record number.
- Required document upload.
- Clear red and green result cards.
- Land image background.
- Responsive layout for computers, tablets, and phones.

---

## Slide 7: Demonstration

### Live demonstration script

#### Part 1: Save the original

1. Open `http://127.0.0.1:8000`.
2. Select **Sign in**.
3. Create or use a submitter account.
4. Select **Add a record**.
5. Upload the original test document.
6. Show the generated record number.

#### Part 2: Check the original

1. Select **Check your document**.
2. Upload the same original document.
3. Show the green **REAL DOCUMENT** result.

#### Part 3: Check the altered copy

1. Upload the modified test document.
2. Show the red **FAKE DOCUMENT** result.
3. Explain that the file differs from the saved copy.

**Demo warning**

Use fictional test documents only. Do not upload real personal land documents during a public presentation.

---

## Slide 8: Security and responsible use

Current protections include:

- Password hashing.
- CSRF protection.
- Login-attempt throttling.
- Private upload storage.
- File type and size checks.
- Security response headers.
- PostgreSQL support.
- Docker deployment.
- Audit events and hash-chain verification.
- Automated regression tests.

Before public production use, we still need:

- Malware scanning.
- MFA or enterprise identity.
- Encrypted backups and restore drills.
- Monitoring and alerting.
- Independent penetration testing.
- Privacy and legal review.

---

## Slide 9: Business model

### Basic plan

- Free document matching.

### Individual plan

- Monthly subscription.
- More saved records and reports.

### Professional plan

- For land agents, surveyors, and legal professionals.

### Organization plan

- Shared workspaces and institution support.

**Current status**

> The pricing and subscription foundation exists, but real payment collection is not connected yet. A payment provider, merchant account, sandbox testing, webhooks, receipts, and refund handling are still required.

---

## Slide 10: What the system does not claim

LandVerify does not currently:

- Prove legal ownership.
- Replace Uganda's official land registry.
- Confirm that a person is the lawful owner.
- Confirm that an issuing office created a document.
- Connect to an official land-record API.
- Process real subscription payments.
- Use a live public or permissioned blockchain.

**Say this clearly**

> A green result means the file matches the trusted copy saved in LandVerify. It is not a legal ownership certificate.

---

## Slide 11: Roadmap

### Immediate

- Pilot testing on different devices and browsers.
- Decide when human approval is required.
- Add malware scanning.
- Add backups and restore testing.

### Integration

- Obtain authorized official land-record API access.
- Define official data fields and error handling.
- Build an API adapter.
- Connect an approved payment provider.

### Production

- Complete privacy, legal, and security reviews.
- Add MFA, monitoring, and incident response.
- Complete penetration testing.
- Run a limited pilot.
- Launch only after accountable approval.

---

## Slide 12: Closing

### LandVerify turns document checking into a simple, traceable process.

**The value**

- Detects changed digital copies.
- Creates a clear record of document events.
- Makes checking simple for ordinary users.
- Provides a foundation for official integrations.

**Closing statement**

> We have built the working foundation. The next step is not to pretend that local matching is official ownership verification. The next step is to connect authorized official data, secure the service for real users, and validate it through a controlled pilot.

---

## Panel questions and answers

### Is this a real blockchain system?

Not yet. The application uses SHA-256 fingerprints, a local audit hash chain, and a local proof adapter. A real permissioned-ledger connection requires an approved network, credentials, schema, and authorization.

### Can a green result prove that someone owns land?

No. It proves that the uploaded file matches the saved copy. Legal ownership requires an authorized official land-record source and the required legal checks.

### What happens if a document is changed?

The fingerprint changes. The system shows the red **FAKE DOCUMENT** result because the file no longer matches the saved copy. A reviewer or issuing authority should investigate the reason.

### Why not put the whole document on a blockchain?

Documents may contain private personal information. We keep the document in protected storage and use a fingerprint or proof reference instead.

### How will the project make money?

Basic matching can remain free. Paid individual, professional, and organization plans can provide additional records, reports, team features, and support. Real payments require a provider integration.

### What makes the project different?

It combines simple document matching, user-friendly results, audit history, controlled access, and a path toward authorized official integration without falsely claiming legal authority.

### What is the current limitation?

The most important limitation is that the system is not connected to an official land registry or live blockchain. It is a working MVP for controlled testing and document-integrity checks.

## Presentation checklist

- [ ] Start the Docker application before the panel.
- [ ] Check `http://127.0.0.1:8000/healthz`.
- [ ] Prepare one fictional original document.
- [ ] Prepare one fictional changed copy.
- [ ] Confirm the original produces green **REAL DOCUMENT**.
- [ ] Confirm the changed copy produces red **FAKE DOCUMENT**.
- [ ] Do not use real personal documents.
- [ ] Do not claim live blockchain or official ownership integration.
- [ ] Keep the presentation between 8 and 12 minutes.
