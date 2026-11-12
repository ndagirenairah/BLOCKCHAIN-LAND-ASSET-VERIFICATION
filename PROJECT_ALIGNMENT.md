# Project Title Alignment

## Project title

**Blockchain-Assisted Land & Asset Record Verification Tool**

## Honest current description

LandVerify is a working document-integrity verification MVP. It registers permitted files, calculates SHA-256 fingerprints, stores private file references and metadata, compares later uploads with registered fingerprints, records review and audit events, and creates local proof references.

It is **not yet** connected to a live blockchain, an official UgNLIS/government land-record API, or a real payment provider. It does not independently prove legal ownership or official authenticity.

## Four required functions

| Function | Current status | Evidence |
|---|---|---|
| Document registration | Working | Secure upload, unique `UG-REC-*` reference, SHA-256 hash, private storage, metadata |
| Document integrity verification | Working | Exact hash comparison, green REAL DOCUMENT, red FAKE DOCUMENT, record-not-found handling |
| Blockchain proof | Partial | Local deterministic `demo-ledger-*` proof and audit hash chain; no live ledger transaction |
| Official record and human review | Partial | Reviewer/administrator approval and reasons work; official registry integration is not connected |

## Requirements checklist

### 1. Make registration and SHA-256 verification reliable — **Complete for MVP**

- Registration requires a supported document.
- The server calculates the SHA-256 fingerprint.
- A unique record reference is generated.
- The document is stored outside the public static directory.
- Later uploads are compared with the registered fingerprint.
- Automated tests cover matching, changed files, missing files, unsupported files, and unknown references.

### 2. Integrate a real blockchain or permissioned-ledger test environment — **Not complete**

The current `ledger_record()` function is a local adapter. It creates a deterministic proof label but does not submit a transaction to a blockchain network.

To complete this requirement:

- Select an approved permissioned network or blockchain test environment.
- Obtain network access and test credentials.
- Define the transaction schema.
- Store only hashes and non-sensitive references.
- Submit registration and approved-review proofs.
- Save the real transaction ID and confirmation status.
- Add a read-back verification screen or service.
- Test failures, retries, duplicate submissions, and key rotation.

Until then, the project must describe the ledger component as **simulated/local**, not live blockchain.

### 3. Support land titles and another asset type — **Working MVP support**

The current record supports structured land fields and vehicle/logbook fields, with validation for key land and vehicle requirements.

To complete this requirement:

- Land fields include district, county, block, plot, tenure, title volume, and title folio.
- Vehicle/logbook fields include registration number, chassis/VIN, and engine number.
- Land records require district and tenure; vehicle records require a registration number.
- Keep sensitive identity details restricted by role.
- Show asset-specific details in the record and report.

### 4. Add reviewer approval and discrepancy reporting — **Mostly complete**

- Reviewer and administrator roles exist.
- Records can be approved, flagged, or rejected.
- Rejection and flagging require a reason.
- Finalized records cannot be reviewed again.
- Review events are stored.

Remaining work:

- Add a dedicated discrepancy report showing expected and submitted metadata.
- Require human approval for real records by default.
- Add reviewer assignment and escalation.

### 5. Provide a clear verification report — **Working MVP report**

Records now have a downloadable HTML evidence report.

The report should include:

- Record reference.
- Asset type.
- Verification date and time.
- Registered file fingerprint.
- Match result.
- Review status.
- Proof transaction reference, if a real ledger is connected.
- Source and limitation statement.

### 6. Plan official registry integration — **Planned**

The application must not invent government results. Official integration requires:

- Written authorization from the data owner.
- API or approved portal documentation.
- Sandbox access.
- Allowed-field and privacy rules.
- Error and unavailable-service behavior.
- Source, timestamp, and reference display.

Until this exists, LandVerify can only perform local file-integrity checks and controlled manual review.

## What can be demonstrated now

1. Register a fictional original land or asset document.
2. Show its generated record reference.
3. Upload the same file and show **REAL DOCUMENT**.
4. Upload an altered copy and show **FAKE DOCUMENT**.
5. Show reviewer approval and the local proof reference.
6. Explain that the proof reference is simulated until a real ledger is connected.

## What must not be claimed

- Do not claim that a local hash match proves legal ownership.
- Do not claim that `demo-ledger-*` is a blockchain transaction.
- Do not claim that the system is connected to UgNLIS.
- Do not call a first-time unregistered upload legally fake; it is only not authenticated against a saved record.
- Do not activate paid subscriptions until a payment provider confirms payment.

## Recommended implementation order

1. Replace the local ledger adapter with an approved test-ledger integration.
2. Add official registry integration only after authorization.
3. Add discrepancy comparison for submitted metadata.
4. Keep human review enabled for real records.
