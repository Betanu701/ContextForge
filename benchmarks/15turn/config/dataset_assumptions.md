# Dataset Assumptions

The benchmark assumes a CMS Medicare Part D prescribing dataset exposed through Microsoft Fabric and the Power BI executeQueries API.

## Expected Data Shape

The script expects data that can answer questions over:

- Drug name and drug class
- Provider name and provider specialty
- Geography, including state and city
- Calendar year
- Claim totals
- Drug cost totals

## Expected Schema Concepts

The benchmark script references these logical tables and dimensions:

- A drug cost fact table
- A drug dimension
- A provider dimension
- A geography dimension
- A year dimension

## Query Expectations

Queries are expected to support:

- Filtering by state and city
- Filtering by provider type
- Filtering by year
- Matching drug classes through generic-name patterns
- Aggregating total claims and total drug cost
- Returning ranked top-N results

The fixed conversation depends on drug-class patterns such as quinolones, ACE inhibitors, statins, ARBs, and beta blockers.