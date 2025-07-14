# Firebolt Fivetran Connector

A custom Fivetran connector for syncing data from Firebolt databases to your destination data warehouse using the Fivetran Connector SDK.

## Prerequisites

Before using this connector, you need:

### Fivetran Account
- An active Fivetran account with access to the Fivetran REST API
- A Fivetran account on Free, Standard, Enterprise, or Business Critical plan

### API Key Generation
You'll need to generate a Fivetran API key to deploy and manage your connector:

1. Log into your Fivetran dashboard
2. Click your user name in the top right corner
3. Click **API Key**
4. Click **Generate API key**
5. Save both the API key and secret securely - you'll need them for deployment

For detailed instructions, see the [Fivetran Scoped API Key documentation](https://fivetran.com/docs/rest-api/getting-started#scopedapikey).

### Development Environment
- Python 3.9, 3.10, 3.11, or 3.12
- Operating system:
  - Windows: 10 or later (64-bit only)
  - macOS: 13 (Ventura) or later (Apple Silicon [arm64] or Intel [x86_64])
  - Linux: Distributions such as Ubuntu 20.04 or later, Debian 10 or later, or Amazon Linux 2 or later (arm64 or x86_64)

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/firebolt-db/firebolt-fivetran-connector.git
cd firebolt-fivetran-connector
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
pip install fivetran_connector_sdk
```

### 3. Set up configuration file

Create a `configuration.json` file in the project root with your Firebolt connection details:

```json
{
  "client_id": "YOUR_FIREBOLT_CLIENT_ID",
  "client_secret": "YOUR_FIREBOLT_CLIENT_SECRET", 
  "database": "YOUR_FIREBOLT_DATABASE",
  "engine_name": "YOUR_FIREBOLT_ENGINE_NAME",
  "account_name": "YOUR_FIREBOLT_ACCOUNT_NAME"
}
```

**Important:** Never commit the `configuration.json` file to version control as it contains sensitive credentials. The file is already included in `.gitignore`.

### 4. Test locally (optional)

Before deploying, you can test the connector locally:

```bash
python connector.py
```

This will run the connector in debug mode using your configuration file.

### 5. Deploy to Fivetran

Deploy your connector to Fivetran using the Fivetran CLI:

```bash
fivetran deploy
```

Follow the prompts to:
- Authenticate with your Fivetran API key and secret
- Configure your connector settings
- Deploy the connector to your Fivetran account

Once deployed, you can set up and schedule your connector through the Fivetran dashboard.

## Configuration parameters

The connector requires the following configuration parameters:

- `client_id`: Your Firebolt service account client ID
- `client_secret`: Your Firebolt service account client secret
- `database`: The name of your Firebolt database
- `engine_name`: The name of your Firebolt engine
- `account_name`: Your Firebolt account name

To obtain these credentials:
- `client_id` and `client_secret` are from your Firebolt service account. Follow the [Manage service accounts](https://docs.firebolt.io/guides/managing-your-organization/service-accounts) guide to create one.
- `database` and `engine_name` are the Firebolt database and engine you want to sync data from.
- `account_name` is your Firebolt account identifier. Learn more in the [Managing accounts](https://docs.firebolt.io/guides/managing-your-organization/managing-accounts) guide.

These parameters are validated by the `validate_configuration()` function in `connector.py` (lines 47-61).

## Features

- **Incremental sync**: Supports incremental data updates using state management
- **Schema definition**: Automatically defines table schemas for your destination
- **Error handling**: Robust error handling with detailed logging
- **Checkpointing**: Regular state checkpointing to ensure reliable sync resumption

## Further reading

For more information about setting up and managing your Fivetran pipeline:

- [Fivetran Connector SDK Setup Guide](https://fivetran.com/docs/connector-sdk/setup-guide) - Complete setup instructions for custom connectors
- [Fivetran Connector SDK Technical Reference](https://fivetran.com/docs/connector-sdk/technical-reference) - Detailed API reference and methods
- [Fivetran Connector SDK Best Practices](https://fivetran.com/docs/connector-sdk/best-practices) - Performance optimization and development guidelines
- [Fivetran REST API Documentation](https://fivetran.com/docs/rest-api) - API reference for managing connectors programmatically
- [Fivetran Connector SDK Examples](https://fivetran.com/docs/connector-sdk/examples) - Additional connector examples and patterns
- [Fivetran Connector SDK Troubleshooting](https://fivetran.com/docs/connector-sdk/troubleshooting) - Common issues and solutions
