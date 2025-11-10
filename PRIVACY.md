# Privacy Policy (GDPR)

This project may process limited business contact information within client JSON files (e.g., phone numbers, email addresses, URLs). Deployers must ensure compliance with GDPR and applicable laws.

## Data Processed

- Contact details provided by the client organization (business context).
- Public references and testimonials.
- No end-user personal data is collected by the API unless provided in the question payload.

## Purposes

- Provide automated, professional responses oriented to client services.
- Facilitate contacting the client’s team via recommended channels.

## Storage and Retention

- Client data is stored in repository files for configuration purposes.
- Runtime vector stores (Chroma) may persist derived embeddings.
- Define retention policies for logs and vector stores in production.

## Data Subject Rights

- Right of access, rectification, erasure, and restriction applies to any personal data processed.
- Contact: [replace with your DPO or privacy contact]

## Security

- API key authentication (optional but recommended).
- Input validation and path containment to avoid unauthorized data access.
- CORS restrictions and security headers.

## International Transfers

- Ensure hosting provider and data storage comply with applicable transfer rules.

## Updates

This policy may be updated. Deployers must adapt it to their specific organization and legal context.