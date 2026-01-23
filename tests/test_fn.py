import dataclasses
import unittest

from crossplane.function import logging, resource
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from google.protobuf import duration_pb2 as durationpb
from google.protobuf import json_format
from google.protobuf import struct_pb2 as structpb

from function import fn

composition_script = """
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

def compose(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    rsp.desired.resources["bucket"].resource.update({
        "apiVersion": "s3.aws.upbound.io/v1beta2",
        "kind": "Bucket",
        "spec": {
            "forProvider": {
                "region": "us-east-1"
            }
        },
    })
"""

async_composition_script = """
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

async def compose(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    rsp.desired.resources["bucket"].resource.update({
        "apiVersion": "s3.aws.upbound.io/v1beta2",
        "kind": "Bucket",
        "spec": {
            "forProvider": {
                "region": "us-east-1"
            }
        },
    })
"""

operation_script = """
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

def operate(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    # Set output for operation monitoring
    rsp.output["result"] = "success"
    rsp.output["message"] = "Operation completed successfully"
"""

async_operation_script = """
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

async def operate(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    # Set output for operation monitoring
    rsp.output["result"] = "success"
    rsp.output["message"] = "Operation completed successfully"
"""

both_functions_script = """
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

def compose(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    pass

def operate(req: fnv1.RunFunctionRequest, rsp: fnv1.RunFunctionResponse):
    pass
"""

no_function_script = """
from crossplane.function.proto.v1 import run_function_pb2 as fnv1

def some_other_function():
    pass
"""


class TestFunctionRunner(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # Allow larger diffs, since we diff large strings of JSON.
        self.maxDiff = 2000

        logging.configure(level=logging.Level.DISABLED)

    async def test_run_function(self) -> None:
        @dataclasses.dataclass
        class TestCase:
            reason: str
            req: fnv1.RunFunctionRequest
            want: fnv1.RunFunctionResponse

        cases = [
            TestCase(
                reason="Function should run composition scripts with compose().",
                req=fnv1.RunFunctionRequest(
                    input=resource.dict_to_struct({"script": composition_script}),
                ),
                want=fnv1.RunFunctionResponse(
                    meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
                    desired=fnv1.State(
                        resources={
                            "bucket": fnv1.Resource(
                                resource=resource.dict_to_struct(
                                    {
                                        "apiVersion": "s3.aws.upbound.io/v1beta2",
                                        "kind": "Bucket",
                                        "spec": {
                                            "forProvider": {"region": "us-east-1"}
                                        },
                                    }
                                )
                            )
                        }
                    ),
                    context=structpb.Struct(),
                ),
            ),
            TestCase(
                reason="Function should run async composition scripts with await.",
                req=fnv1.RunFunctionRequest(
                    input=resource.dict_to_struct({"script": async_composition_script}),
                ),
                want=fnv1.RunFunctionResponse(
                    meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
                    desired=fnv1.State(
                        resources={
                            "bucket": fnv1.Resource(
                                resource=resource.dict_to_struct(
                                    {
                                        "apiVersion": "s3.aws.upbound.io/v1beta2",
                                        "kind": "Bucket",
                                        "spec": {
                                            "forProvider": {"region": "us-east-1"}
                                        },
                                    }
                                )
                            )
                        }
                    ),
                    context=structpb.Struct(),
                ),
            ),
        ]

        runner = fn.FunctionRunner()

        for case in cases:
            got = await runner.RunFunction(case.req, None)
            self.assertEqual(
                json_format.MessageToDict(case.want),
                json_format.MessageToDict(got),
                "-want, +got",
            )

    async def test_run_operation(self) -> None:
        @dataclasses.dataclass
        class TestCase:
            reason: str
            req: fnv1.RunFunctionRequest
            want: fnv1.RunFunctionResponse

        cases = [
            TestCase(
                reason="Function should run operation scripts with operate().",
                req=fnv1.RunFunctionRequest(
                    input=resource.dict_to_struct({"script": operation_script}),
                ),
                want=fnv1.RunFunctionResponse(
                    meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
                    desired=fnv1.State(),
                    context=structpb.Struct(),
                    output=resource.dict_to_struct(
                        {
                            "result": "success",
                            "message": "Operation completed successfully",
                        }
                    ),
                ),
            ),
            TestCase(
                reason="Function should run async operation scripts with await.",
                req=fnv1.RunFunctionRequest(
                    input=resource.dict_to_struct({"script": async_operation_script}),
                ),
                want=fnv1.RunFunctionResponse(
                    meta=fnv1.ResponseMeta(ttl=durationpb.Duration(seconds=60)),
                    desired=fnv1.State(),
                    context=structpb.Struct(),
                    output=resource.dict_to_struct(
                        {
                            "result": "success",
                            "message": "Operation completed successfully",
                        }
                    ),
                ),
            ),
        ]

        runner = fn.FunctionRunner()

        for case in cases:
            got = await runner.RunFunction(case.req, None)
            self.assertEqual(
                json_format.MessageToDict(case.want),
                json_format.MessageToDict(got),
                "-want, +got",
            )

    async def test_error_both_functions(self) -> None:
        """Test that having both compose and operate functions returns an error."""
        runner = fn.FunctionRunner()
        script = both_functions_script
        req = fnv1.RunFunctionRequest(input=resource.dict_to_struct({"script": script}))

        got = await runner.RunFunction(req, None)

        # Should have a fatal error
        self.assertEqual(len(got.results), 1)
        self.assertEqual(got.results[0].severity, fnv1.Severity.SEVERITY_FATAL)
        self.assertIn("only one function: compose or operate", got.results[0].message)

    async def test_error_no_functions(self) -> None:
        """Test that having neither compose nor operate functions returns an error."""
        runner = fn.FunctionRunner()
        script = no_function_script
        req = fnv1.RunFunctionRequest(input=resource.dict_to_struct({"script": script}))

        got = await runner.RunFunction(req, None)

        # Should have a fatal error
        self.assertEqual(len(got.results), 1)
        self.assertEqual(got.results[0].severity, fnv1.Severity.SEVERITY_FATAL)
        self.assertIn("compose or operate function", got.results[0].message)


if __name__ == "__main__":
    unittest.main()
