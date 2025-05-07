#! /bin/bash

instanceList="db.r6g.large db.r6g.xlarge db.r6g.2xlarge db.r6g.4xlarge db.r6g.8xlarge db.r6g.12xlarge db.r6g.16xlarge db.r6gd.large db.r6gd.xlarge db.r6gd.2xlarge db.r6gd.4xlarge db.r6gd.8xlarge db.r6gd.12xlarge db.r6gd.16xlarge"

for thisInstance in $instanceList; do
    thisInstanceDashes=`echo $thisInstance | tr '.' '-'`
    echo "$thisInstance | $thisInstanceDashes"
    python3 docdb-admin.py -d ~/config/prod-c.json -i $thisInstanceDashes --nrr 0 --create-cluster --it $thisInstance --pg tls-disabled-50 &
done

