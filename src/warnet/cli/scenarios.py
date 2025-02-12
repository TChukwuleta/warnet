import click
from typing import List
from rich import print
from rich.console import Console
from rich.table import Table


from warnet.cli.rpc import rpc_call


@click.group(name="scenarios")
def scenarios():
    """Scenario commands"""


@scenarios.command()
def list():
    """
    List available scenarios in the Warnet Test Framework
    """
    console = Console()
    result = rpc_call("scenarios_list", None)
    assert isinstance(result, List)

    # Create the table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Description")

    for scenario in result:
        table.add_row(scenario[0], scenario[1])
    console.print(table)


@scenarios.command(context_settings={"ignore_unknown_options": True})
@click.argument("scenario", type=str)
@click.argument("additional_args", nargs=-1, type=click.UNPROCESSED)
@click.option("--network", default="warnet", show_default=True)
def run(scenario, network, additional_args):
    """
    Run <scenario> from the Warnet Test Framework on <--network> with optional arguments
    """
    params = {
        "scenario": scenario,
        "additional_args": additional_args,
        "network": network,
    }
    print(rpc_call("scenarios_run", params))


@scenarios.command()
def active():
    """
    List running scenarios "name": "pid" pairs
    """
    console = Console()
    result = rpc_call("scenarios_list_running", {})
    assert isinstance(result, List), "Result is not a list"  # Make mypy happy again

    table = Table(show_header=True, header_style="bold")
    for key in result[0].keys():
        table.add_column(key.capitalize())

    for scenario in result:
        table.add_row(*[str(scenario[key]) for key in scenario])

    console.print(table)


@scenarios.command()
@click.argument("pid", type=int)
def stop(pid: int):
    """
    Stop scenario with PID <pid> from running
    """
    params = {"pid": pid}
    print(rpc_call("scenarios_stop", params))
