#!/bin/sh
rm rox/*.pyc
pychecker --no-miximport  --no-argsused --classdoc rox/*.py | gvim -
