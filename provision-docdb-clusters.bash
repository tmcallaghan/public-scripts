#! /bin/bash

#INSTANCETYPELIST="db.r8g.large db.r8g.xlarge db.r8g.2xlarge db.r8g.4xlarge db.r8g.8xlarge db.r8g.12xlarge db.r8g.16xlarge db.r8g.24xlarge db.r8g.48xlarge"
#INSTANCETYPELIST="db.r8g.48xlarge"
#INSTANCETYPELIST="db.r8g.24xlarge"
INSTANCETYPELIST="db.r8g.16xlarge"

for thisInstanceType in ${INSTANCETYPELIST}; do
    thisClusterName=$(echo "$thisInstanceType" | tr '.' '-')
    thisFullClusterName="tmcallag-${thisClusterName}"
    echo "$thisFullClusterName | $thisInstanceType"

    python3 docdb-admin.py --create-cluster -d ~/config/defaults.lycia --nrr 0 --it $thisInstanceType -i $thisFullClusterName
    #python3 docdb-admin.py --add-tag -d ~/config/defaults.lycia --tag-key max-age-in-days --tag-value 60 -i $thisFullClusterName
    python3 docdb-admin.py --delete-cluster -d ~/config/defaults.lycia -i $thisFullClusterName
done
