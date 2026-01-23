"""A Crossplane composition function."""

import importlib.util
import inspect
import types

import grpc
from crossplane.function import logging, response
from crossplane.function.proto.v1 import run_function_pb2 as fnv1
from crossplane.function.proto.v1 import run_function_pb2_grpc as grpcv1


class FunctionRunner(grpcv1.FunctionRunnerService):
    """A FunctionRunner handles gRPC RunFunctionRequests."""

    def __init__(self):
        """Create a new FunctionRunner."""
        self.log = logging.get_logger()

    async def RunFunction(
        self,
        req: fnv1.RunFunctionRequest,
        _: grpc.aio.ServicerContext,
    ) -> fnv1.RunFunctionResponse:
        """Run the function."""
        log = self.log.bind(tag=req.meta.tag)
        log.info("Running function")

        rsp = response.to(req)

        if req.input["script"] is None:
            response.fatal(rsp, "missing script")
            return rsp

        log.debug("Running script", script=req.input["script"])
        script = load_module("script", req.input["script"])

        has_compose = hasattr(script, "compose")
        has_operate = hasattr(script, "operate")

        match (has_compose, has_operate):
            case (True, True):
                msg = "script must define only one function: compose or operate"
                log.debug(msg)
                response.fatal(rsp, msg)
            case (True, False):
                log.debug("running composition function")
                if inspect.iscoroutinefunction(script.compose):
                    await script.compose(req, rsp)
                else:
                    script.compose(req, rsp)
            case (False, True):
                log.debug("running operation function")
                if inspect.iscoroutinefunction(script.operate):
                    await script.operate(req, rsp)
                else:
                    script.operate(req, rsp)
            case (False, False):
                msg = "script must define a compose or operate function"
                log.debug(msg)
                response.fatal(rsp, msg)

        return rsp


def load_module(name: str, source: str) -> types.ModuleType:
    """Load a Python module from the supplied string."""
    spec = importlib.util.spec_from_loader(name, loader=None)
    # This should never happen in practice, but it lets type checkers know that
    # spec won't be None when passed to module_from_spec.
    if spec is None:
        err = "cannot create module spec"
        raise RuntimeError(err)

    module = importlib.util.module_from_spec(spec)
    exec(source, module.__dict__)  # noqa: S102  # We intend to run arbitrary code.
    return module
