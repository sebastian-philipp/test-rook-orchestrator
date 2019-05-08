#!/bin/sh

while ! nc -z "$1" 22 ; do sleep 1 ; done
