#!/bin/sh
echo hello
mkdir test
cd test
hostname > index.html
python3 -m http.server
