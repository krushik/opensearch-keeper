# opensearch-keeper

A command-line tool for managing OpenSearch index templates.

## Features

- List templates from OpenSearch
- Save templates from OpenSearch to local YAML files
- Publish templates from local files to OpenSearch
- Support for multiple environments (qa, prod, etc.)
- Support for AWS SigV4 authentication
- Support for SOCKS5 proxy
- Pattern matching for template selection

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/krushik/opensearch-keeper.git
   cd opensearch-keeper
   ```

2. Create a virtual environment, install dependencies, activate:
   ```bash
   uv sync
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package:
   ```bash
   pip install -e .
   ```

## Configuration

Create a configuration file named `config.yaml` in one of the following locations:
- Current directory (`./config.yaml`)
- User's home directory (`~/.opensearch-keeper/config.yaml`)
- System-wide configuration (`/etc/opensearch-keeper/config.yaml`)

Example configuration:

```yaml
environments:
  qa:
    host: opensearch-qa.example.com
    port: 443
    use_ssl: true
    verify_certs: true
    # Uncomment to use AWS SigV4 authentication
    # aws_auth:
    #   region: us-east-1
    #   service: es
    # Uncomment to use SOCKS5 proxy
    # proxy:
    #   host: proxy.example.com
    #   port: 1080
    #   username: proxy_user  # Optional
    #   password: proxy_pass  # Optional

  prod:
    host: opensearch-prod.example.com
    port: 443
    use_ssl: true
    verify_certs: true

# Templates directory where templates will be saved
templates_dir: ./templates

# Patterns to ignore when listing or saving templates
ignore_patterns:
  - ".opendistro_security"
  - ".kibana*"
  - ".apm*"
  - ".monitoring*"
```

## Usage

### List Available Environments

```bash
opensearch-keeper environments
```

### List Templates

```bash
opensearch-keeper list --env qa
```

List templates matching a pattern:

```bash
opensearch-keeper list --env qa --pattern "my-template*"
```

Change output format:

```bash
opensearch-keeper list --env qa --format json
```

### Save Templates

Save all templates to local files:

```bash
opensearch-keeper save --env qa
```

Save templates matching a pattern:

```bash
opensearch-keeper save --env qa --pattern "my-template*"
```

### Publish Templates

Publish all templates from local files to OpenSearch:

```bash
opensearch-keeper publish --env qa
```

Publish templates matching a pattern:

```bash
opensearch-keeper publish --env qa --pattern "my-template*"
```

### Delete a Template

```bash
opensearch-keeper delete --env qa my-template
```

## Development

### Running Tests

```bash
pytest
```

### Building the Package

```bash
uv build
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
