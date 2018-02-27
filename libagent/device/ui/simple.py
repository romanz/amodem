"""Simple, cross-platform UI for entering a PIN/passhprase."""
import sys

import pymsgbox

sys.stdout.write(pymsgbox.password(sys.stdin.read()))
