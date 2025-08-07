# Operations Example

This example demonstrates using function-python with Crossplane Operations to
check SSL certificate expiry for websites referenced in Kubernetes Ingress
resources.

## Files

- `operation.yaml` - The Operation that checks certificate expiry
- `functions.yaml` - Function definition for local development
- `ingress.yaml` - Sample Ingress resource to check
- `rbac.yaml` - RBAC permissions for Operations to access Ingress resources
- `README.md` - This file

## Testing

Since Operations are runtime-only (they can't be statically rendered), you can
test this example locally using the new `crossplane alpha render op` command.

### Prerequisites

1. Run the function in development mode:
   ```bash
   hatch run development
   ```

2. In another terminal, render the operation:
   ```bash
   crossplane alpha render op operation.yaml functions.yaml --required-resources . -r
   ```

The `-r` flag includes function results in the output, and
`--required-resources .` tells the command to use the ingress.yaml file in this
directory as the required resource.

## What it does

The Operation:

1. **Reads the Ingress** resource specified in `requirements.requiredResources`
2. **Extracts the hostname** from the Ingress rules (`google.com` in this
   example)
3. **Fetches the SSL certificate** for that hostname
4. **Calculates expiry information** (days until expiration)
5. **Annotates the Ingress** with certificate monitoring annotations
6. **Returns status information** in the Operation's output field

This pattern is useful for:
- Certificate monitoring and alerting
- Compliance checking
- Automated certificate renewal workflows
- Integration with monitoring tools that read annotations

## Function Details

The operation function (`operate()`) demonstrates key Operations patterns:

- **Required Resources**: Accessing pre-populated resources via
  `request.get_required_resources(req, "ingress")`
- **Resource Updates**: Using `rsp.desired.resources` to update existing
  resources
- **Operation Output**: Using `rsp.output.update()` for monitoring data
- **Server-side Apply**: Crossplane applies the changes with force ownership