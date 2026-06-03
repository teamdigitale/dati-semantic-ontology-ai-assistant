# coding: utf-8

import argparse
import asyncio
import logging
import os
import sys

from lightrag.utils import (
    logger as lrag_logger,
    setup_logger,
)
import uvicorn

from .rag import initialize_ontorag
from .gscape import write_gscape
from .utils import logger


def command_designer_generate(args: argparse.Namespace) -> None:
    """
    Perform a one-shot designer generation.
    """
    designer = None
    try:
        designer = asyncio.run(initialize_ontorag(working_dir=args.data_dir or "./lightrag_cache"))
        infile = sys.stdin if args.input == "-" else open(args.input)
        outfile = sys.stdout if args.output == "-" else open(args.output, "at")
        designer.insert(infile.read())
        outfile.write(write_gscape(asyncio.run(designer.chunk_entity_relation_graph.get_graph())).to_json())
    except Exception as e:
        logger.error("An error occurred", exc_info=e)
    finally:
        if designer:
            asyncio.run(designer.finalize_storages())


def command_server_run(args: argparse.Namespace) -> None:
    """
    Run the FastAPI ASGI server.
    """
    ########################################
    # SETUP ENV VARS
    # must be set before importing the app instance
    ##############################
    if args.data_dir:
        logger.info("Using working dir: %s", args.data_dir)
        os.environ["WORKING_DIR"] = args.data_dir
    # TODO: setup uvicorn logging
    ########################################
    # STARTUP FASTAPI
    ##############################
    from .server.main import app
    if args.mount:
        os.putenv("ROOT_PATH", args.mount)
    uvicorn.run(
        app="ai_assistant.server.main:app",
        host=args.bind,
        port=args.port,
        reload=args.reload,
        root_path=args.root_path,
        # workers=None,
        # proxy_headers=None,
        # log_config=None,
    )


def main(args: list[str] = None) -> int:
    """
    CLI entry point.
    """
    parser = argparse.ArgumentParser(
        prog="ai_assistant",
        description="Ontology assistant using generative AI",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Produce verbose output. Multiple occurrences increase verbosity.",
    )
    parser.add_argument(
        "-L", "--log", type=str,
        help="Log to the given output file.",
    )
    # TODO: add lightrag and llm config options
    subparsers = parser.add_subparsers(required=True, help="sub-command help")

    ############################################################
    # designer subcommands
    ########################################

    designer = subparsers.add_parser("designer", help="Designer-related commands.")
    designer_subparsers = designer.add_subparsers(
        required=True,
        help="Designer-related sub-commands",
    )

    ########################################
    # designer generate command
    ####################

    generate = designer_subparsers.add_parser(
        "generate",
        help="Generate gscape diagram for the given request.",
    )
    generate.add_argument(
        "-i", "--input", type=str, default="-",
        help="The input request file to process (defaults to stdin).",
    )
    generate.add_argument(
        "-o", "--output", type=str, default="-",
        help="The output file to save the generated gscape (defaults to stdout).",
    )
    generate.add_argument(
        "-d", "--data-dir", type=str, default=None,
        help="Directory where cache and temporary files are stored.",
    )
    generate.set_defaults(func=command_designer_generate)

    ############################################################
    # server subcommands
    ########################################

    server = subparsers.add_parser("server", help="FastAPI server-related commands.")
    server_subparsers = server.add_subparsers(
        required=True,
        help="FastAPI server-related sub-commands",
    )

    ########################################
    # server run command
    ####################

    run = server_subparsers.add_parser(
        "run",
        help="Run the ASGI API server.",
    )
    run.add_argument(
        "-b", "--bind", type=str, default="127.0.0.1",
        help="Listening address to bind the server to (defaults to loopback).",
    )
    run.add_argument(
        "-p", "--port", type=int, default=8200,
        help="Port to listen on (defaults to 8200).",
    )
    run.add_argument(
        "-d", "--data-dir", type=str, default=None,
        help="Directory where cache and temporary files are stored.",
    )
    run.add_argument(
        "-r", "--reload", action="store_true", default=False,
        help="Start the server in development mode.",
    )
    run.add_argument(
        "-m", "--mount", type=str, default="",
        help="The path to mount the main router to (defaults to /).",
    )
    run.add_argument(
        "-P", "--root-path", type=str, default="",
        help="The root path that is used to serve the API from (defaults to /).",
    )
    run.set_defaults(func=command_server_run)

    options = parser.parse_args(args if args else sys.argv[1:])
    level = logging.getLevelName(logging.INFO if options.verbose <= 1 else logging.DEBUG)
    if options.log:
        setup_logger(logger_name=logger.name, level=level, log_file_path=options.log)
        setup_logger(logger_name=lrag_logger.name, level=level, log_file_path=options.log)
    else:
        setup_logger(logger_name=logger.name, level=level, enable_file_logging=False)
        setup_logger(logger_name=lrag_logger.name, level=level, enable_file_logging=False)
    options.func(options)
    return 0
