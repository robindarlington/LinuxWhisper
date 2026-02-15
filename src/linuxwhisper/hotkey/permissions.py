"""Permission checking for input device access."""
import os
import grp


def check_input_permissions() -> bool:
    """Check if current user has permission to access input devices.

    Returns:
        True if user is root or in the 'input' group, False otherwise.
    """
    # Root always has access
    if os.geteuid() == 0:
        return True

    try:
        # Get the input group GID
        input_gid = grp.getgrnam('input').gr_gid

        # Check if input GID is in user's groups
        return input_gid in os.getgroups()
    except KeyError:
        # 'input' group doesn't exist on this system
        return False


def get_permission_instructions() -> str:
    """Get instructions for adding user to input group.

    Returns:
        Multi-line string with setup instructions.
    """
    return """Add your user to the input group: sudo usermod -aG input $USER
Log out and back in for changes to take effect."""
