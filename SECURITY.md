# Security policy

## Supported versions

Security fixes are applied to the latest published release. The current repository snapshot is an alpha MVP and may change incompatibly before 1.0.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, personal data, or a vulnerable production dataset. Use GitHub's private vulnerability reporting feature if it is enabled for the repository; otherwise contact the maintainers privately through the repository owner profile.

## Data handling notes

- DataGate does not make network requests during its commands.
- Profile and validation reports do not intentionally include raw cell values.
- Uniqueness validation temporarily writes values to a SQLite file under a temporary directory. Normal cleanup is not cryptographic secure erasure.
- Cleaning writes a new file and an audit sidecar; protect those files according to the sensitivity of the input.
- Local execution does not replace operating-system access control, encryption, backup, or retention controls.
