# Environment Schema

The benchmark reads configuration through `benchmarks/15turn/env_config.py`. Values may come from environment variables or from a local `.env` file.

This schema documents the private infrastructure required to reproduce the published run. The benchmark is not expected to run for OSS readers unless they have equivalent Azure AI Foundry, Azure OpenAI, Fabric, and Power BI dataset access.

## Required Variables

- `AZURE_ENDPOINT`: Azure OpenAI or Azure AI Services endpoint used by the judge and ContextForge provider.
- `DEPLOYMENT_NAME`: Model deployment name used for all benchmark LLM calls.
- `API_VERSION`: Azure OpenAI API version used by the OpenAI client.
- `FOUNDRY_PROJECT_ENDPOINT`: Foundry project endpoint used to create the Foundry Agent session.
- `FOUNDRY_AGENT_NAME`: Foundry Agent name under test.
- `FOUNDRY_AGENT_VERSION`: Foundry Agent version under test.
- `FABRIC_WORKSPACE_ID`: Fabric workspace ID containing the benchmark dataset.
- `DATASET_ID`: Power BI dataset ID used by the DAX executeQueries API.

## Notes

Do not commit real values. Use `benchmarks/15turn/.env.example` as a template and keep local `.env` files ignored. If adapting the benchmark to another dataset, update the DAX queries, dataset assumptions, and judge hints together so the scoring still reflects the data being queried.