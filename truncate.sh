#!/bin/bash -

cd $(dirname $0)

day0=$(date +%Y%m%d)
day1=$(date -d yesterday +%Y%m%d)
day2=$(date -d '2 days ago' +%Y%m%d)

for i in $(find videos/*/*/0/ videos/*/*/1/ -name *.mp4 -type f -size +1)
do
    day=$(basename $(dirname $(dirname $i)))
    if [[ "$day" = "$day0" || "$day" = "$day1" || "$day" = "$day2" ]]
    then
        continue
    fi

    : >$i
done
