"""CLI commands for LinuxWhisper."""

import click


@click.group()
@click.version_option(version="0.1.0", prog_name="linuxwhisper")
def cli():
    """LinuxWhisper - Linux desktop voice dictation tool."""
    pass
