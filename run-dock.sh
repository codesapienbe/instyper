#!/bin/bash

docker run --rm -it \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ~/.Xauthority:/home/appuser/.Xauthority \
  -e DISPLAY \
  --device /dev/snd \
  instyper
