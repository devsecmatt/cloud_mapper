"""CLI entry point for cloud-mapper."""

import click
from rich.console import Console

from cloud_mapper.config import ALL_SERVICES

console = Console()


@click.command()
@click.option(
    "--region",
    default="all",
    help="Comma-separated AWS regions or 'all'. [default: all]",
)
@click.option(
    "--services",
    default="all",
    help=f"Comma-separated services or 'all'. Available: {', '.join(ALL_SERVICES)}",
)
@click.option("--vpc", default=None, help="Filter to a specific VPC ID.")
@click.option(
    "--output",
    default="aws-architecture",
    help="Output file path (extension auto-added). [default: aws-architecture]",
)
@click.option(
    "--format",
    "output_format",
    default="png",
    type=click.Choice(["png", "svg", "pdf"]),
    help="Output format. [default: png]",
)
@click.option("--save-data", type=click.Path(), help="Save discovered resources to JSON.")
@click.option(
    "--from-data", type=click.Path(exists=True), help="Load resources from JSON (skip AWS scan)."
)
@click.option("--profile", default=None, help="AWS profile name from ~/.aws/credentials.")
@click.option("--verbose", is_flag=True, help="Enable verbose logging.")
def main(region, services, vpc, output, output_format, save_data, from_data, profile, verbose):
    """Discover AWS resources and generate an architecture diagram."""
    from cloud_mapper.discovery.coordinator import DiscoveryCoordinator
    from cloud_mapper.discovery.models import ResourceGraph
    from cloud_mapper.discovery.session import create_session, get_enabled_regions
    from cloud_mapper.diagram.renderer import DiagramRenderer
    from cloud_mapper.utils.logging import setup_logging

    setup_logging(verbose)

    # Parse services
    if services == "all":
        service_list = ALL_SERVICES
    else:
        service_list = [s.strip() for s in services.split(",")]
        invalid = set(service_list) - set(ALL_SERVICES)
        if invalid:
            raise click.BadParameter(f"Unknown services: {', '.join(invalid)}")

    # Load from cache or discover
    if from_data:
        console.print(f"[bold]Loading resources from {from_data}...[/bold]")
        graph = ResourceGraph.from_json_file(from_data)
        console.print(f"Loaded {len(graph.resources)} resources.")
    else:
        session = create_session(profile)

        # Parse regions
        if region == "all":
            regions = get_enabled_regions(session)
            console.print(f"[bold]Scanning {len(regions)} regions...[/bold]")
        else:
            regions = [r.strip() for r in region.split(",")]

        coordinator = DiscoveryCoordinator(session, regions, service_list)
        graph = coordinator.discover_all()

        console.print(f"\n[bold green]Discovered {len(graph.resources)} resources.[/bold green]")
        graph.print_summary(console)

    # Save data if requested
    if save_data:
        graph.to_json_file(save_data)
        console.print(f"[bold]Saved resource data to {save_data}[/bold]")

    # Filter by VPC if requested
    if vpc:
        graph = graph.filter_by_vpc(vpc)
        console.print(f"Filtered to VPC {vpc}: {len(graph.resources)} resources.")

    # Generate diagram
    console.print(f"\n[bold]Generating {output_format.upper()} diagram...[/bold]")
    renderer = DiagramRenderer(graph, output, output_format)
    output_path = renderer.render()
    console.print(f"[bold green]Diagram saved to {output_path}[/bold green]")
