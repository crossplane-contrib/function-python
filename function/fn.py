"""A Crossplane composition function."""

import importlib.util
import inspect
import traceback
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
        log.debug("Running function")

        rsp = response.to(req)

        if "script" not in req.input or not req.input["script"]:
            response.fatal(rsp, "missing script in function input")
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
                try:
                    log.debug("running composition function")
                    if inspect.iscoroutinefunction(script.compose):
                        await script.compose(req, rsp)
                    else:
                        script.compose(req, rsp)
                except Exception as e:
                    msg = (
                        f"Exception: {type(e)}, "
                        f"traceback: {traceback.format_tb(e.__traceback__.tb_next)}"
                    )
                    log.debug(msg)
                    response.fatal(rsp, msg)

            case (False, True):
                log.debug("running operation function")
                try:
                    if inspect.iscoroutinefunction(script.operate):
                        await script.operate(req, rsp)
                    else:
                        script.operate(req, rsp)
                except Exception as e:
                    msg = (
                        f"Exception: {e}, "
                        f"traceback: {traceback.format_tb(e.__traceback__.tb_next)}"
                    )
                    log.debug(msg)
                    response.fatal(rsp, msg)

            case (False, False):
                msg = "script must define a compose or operate function"
                log.debug(msg)
                response.fatal(rsp, msg)
        log.debug(f"Response: {rsp}")
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
