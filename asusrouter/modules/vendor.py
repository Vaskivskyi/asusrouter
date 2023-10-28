"""Vendor module."""


def replace_vendor(vendor: str) -> str:
    """Replace vendor name."""

    # Check if vendor is any of `android-dhcp-XX` where XX is a version number
    if vendor.startswith("android-dhcp-"):
        # Get the version number
        version = vendor.replace("android-dhcp-", "")
        # Return the version number
        return f"Android {version}"

    match vendor:
        case "MSFT 5.0":
            return "Microsoft Corporation"

    return vendor
