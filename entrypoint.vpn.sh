#!/bin/bash
set -e

# Setup ExpressVPN with activation code
if [ ! -z "$EXPRESSVPN_ACTIVATION_CODE" ]; then
    expressvpn activate $EXPRESSVPN_ACTIVATION_CODE
fi

# Connect to ExpressVPN
expressvpn connect

# Keep the container running
tail -f /dev/null