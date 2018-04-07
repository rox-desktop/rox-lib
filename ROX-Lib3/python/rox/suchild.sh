#!/bin/sh
message="$1"
roxlib_dir=`dirname "$0"`; export roxlib_dir
roxlib_python="$2"; export roxlib_python
roxlib_to_parent="$3"; export roxlib_to_parent
roxlib_from_parent="$4"; export roxlib_from_parent
root="$5"
echo "$message"
echo
echo "Enter $root's password:"
while true; do
  su "$root" -c 'nohup "$roxlib_python" "$roxlib_dir/suchild.py" $roxlib_to_parent $roxlib_from_parent >/dev/null &' && break
done
sleep 1
