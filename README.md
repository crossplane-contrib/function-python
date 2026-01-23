# function-python

[![CI](https://github.com/crossplane-contrib/function-python/actions/workflows/ci.yml/badge.svg)](https://github.com/crossplane-contrib/function-python/actions/workflows/ci.yml)

A Crossplane function that lets you compose resources and run operational tasks using Python.

## Composition Functions

To compose resources, provide a Python script that defines a `compose` function with this signature:

```python
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

def compose(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse)
```

`function-python` passes the `compose` function a request and a response. It
pre-populates the response with the results of any previous functions in the
pipeline. The `compose` function should modify the response (`rsp`), for example
to add composed resources.

The [`RunFunctionRequest` and `RunFunctionResponse` types][buf-types] provided
by this SDK are generated from a proto3 protocol buffer schema. Their fields
behave similarly to built-in Python types like lists and dictionaries, but there
are some differences. Read the [generated code documentation][python-protobuf]
to familiarize yourself with the the differences.

Your script has access to [function-sdk-python] as the `crossplane.function`
module. For example you can `import crossplane.function.resource`. It also has
access to the full Python standard library - use it with care.

```yaml
apiVersion: apiextensions.crossplane.io/v1
kind: Composition
metadata:
  name: compose-a-resource-with-python
spec:
  compositeTypeRef:
    apiVersion: example.crossplane.io/v1
    kind: XR
  mode: Pipeline
  pipeline:
  - step: compose-a-resource-with-python
    functionRef:
      name: function-python
    input:
      apiVersion: python.fn.crossplane.io/v1beta1
      kind: Script
      script: |
        from crossplane.function.proto.v1 import run_function_pb2 as fnv1

        def compose(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
            rsp.desired.resources["bucket"].resource.update({
                "apiVersion": "s3.aws.upbound.io/v1beta2",
                "kind": "Bucket",
                "spec": {
                    "forProvider": {
                        "region": req.observed.composite.resource["spec"]["region"]
                    }
                },
            })
            rsp.desired.resources["bucket"].ready = True
```

## Operations Functions (Alpha)

`function-python` also supports Crossplane Operations, which are one-time operational tasks that run to completion (like Kubernetes Jobs). For operations, provide a Python script that defines an `operate` function with this signature:

```python
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

def operate(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    # Your operational logic here

    # Set output for operation monitoring
    rsp.output["result"] = "success"
    rsp.output["message"] = "Operation completed successfully"
```

### Operation Example

```yaml
apiVersion: ops.crossplane.io/v1alpha1
kind: Operation
metadata:
  name: check-cert-expiry
spec:
  template:
    spec:
      pipeline:
      - step: check-certificate
        functionRef:
          name: function-python
        input:
          apiVersion: python.fn.crossplane.io/v1beta1
          kind: Script
          script: |
            from crossplane.function.proto.v1 import run_function_pb2 as fnv1
            import datetime

            def operate(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
                # Example: Check certificate expiration
                # In real use, you'd retrieve and validate actual certificates

                # Set operation output
                rsp.output["check_time"] = datetime.datetime.now().isoformat()
                rsp.output["status"] = "healthy"
                rsp.output["message"] = "Certificate expiry check completed"
```

For more complex operations, see the [operation examples](example/operation/).

## Async Functions

`function-python` supports async functions for compositions and operations.  Use `async def compose()`
and `async def operate()` to define async functions.  `async` should be used if the script/function
is making network or other potentially blocking IO calls `async`.  This allows
`function-python` to serve multiple requests concurrently without blocking.

## Usage Notes

`function-python` is best for very simple cases. If writing Python inline of
YAML becomes unwieldy, consider building a Python function using
[function-template-python].

[function-sdk-python]: https://github.com/crossplane/function-sdk-python
[buf-types]: https://buf.build/crossplane/crossplane/docs/main:apiextensions.fn.proto.v1
[python-protobuf]: https://protobuf.dev/reference/python/python-generated/
[function-template-python]: https://github.com/crossplane/function-template-python
