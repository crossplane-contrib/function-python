"""The composition function's main CLI."""

import click
from crossplane.function import logging, runtime

from function import fn


@click.command()
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="Emit debug logs.",
)
@click.option(
    "--address",
    default="0.0.0.0:9443",
    show_default=True,
    help="Address at which to listen for gRPC connections",
)
@click.option(
    "--tls-certs-dir",
    help="Serve using mTLS certificates.",
    envvar="TLS_SERVER_CERTS_DIR",
)
@click.option(
    "--insecure",
    is_flag=True,
    help=(
        "Run without mTLS credentials. "
        "If you supply this flag --tls-certs-dir will be ignored."
    ),
)
@click.option(
    "--max-recv-message-size",
    default=4,
    show_default=True,
    type=click.INT,
    help=("Maximum size of received messages in MB."),
)
@click.option(
    "--max-send-message-size",
    default=4,
    show_default=True,
    type=click.INT,
    help=("Maximum size of sent messages in MB."),
)
def cli(
    debug: bool,  # noqa:FBT001
    address: str,
    tls_certs_dir: str,
    insecure: bool,  # noqa:FBT001
    max_recv_message_size: int,
    max_send_message_size: int,
) -> None:  # We only expect callers via the CLI.
    """A Crossplane composition function."""
    try:
        level = logging.Level.INFO
        if debug:
            level = logging.Level.DEBUG
        logging.configure(level=level)
        runtime.serve(
            fn.FunctionRunner(),
            address,
            creds=runtime.load_credentials(tls_certs_dir),
            insecure=insecure,
            options=[
                (
                    "grpc.max_receive_message_length",
                    1024 * 1024 * max_recv_message_size,
                ),
                (
                    "grpc.max_send_message_length",
                    1024 * 1024 * max_send_message_size,
                ),
            ],
        )
    except Exception as e:
        click.echo(f"Cannot run function: {e}")


if __name__ == "__main__":
    cli()
