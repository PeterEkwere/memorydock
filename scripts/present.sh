#!/bin/sh
set -eu
echo 'MemoryDock: open http://127.0.0.1:7777 in your browser.'
echo 'Keep this terminal open. Press Ctrl+C when finished.'
exec ssh -o BatchMode=yes -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -L 127.0.0.1:7777:127.0.0.1:7777 forefada-live
