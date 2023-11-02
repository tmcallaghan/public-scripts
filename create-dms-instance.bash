#! /bin/bash

echo $#

# make sure user passed correct number of parameters
if [ $# -ne 6 ] ; then
    echo "6 arguments required: <instance-identifier> <instance-class> <engine-version> <allocated-storage-gb> <subnet-group> <security-group>"
    exit 1
fi

DMS_INSTANCE_IDENTIFIER=$1
DMS_INSTANCE_CLASS=$2
DMS_ENGINE_VERSION=$3
DMS_ALLOCATED_STORAGE=$4
DMS_SUBNET_GROUP=$5
DMS_SECURITY_GROUP=$6


include --no-multi-az

# number of seconds to wait before looking for progress
sleepSeconds=5

# bash stuff
# check if not set or empty
#   : "${BATCHNUM:?Variable not set or empty}"
# use default value if not set or empty
#   : "${BATCHNUM:=3}"


# create the instance

echo "... creating cluster $DMS_CLUSTER_IDENTIFIER"

instanceCreateInfo=`aws dms create-replication-instance \
  --replication-instance-identifier $DMS_INSTANCE_IDENTIFIER \
  --replication-instance-class $DMS_INSTANCE_CLASS \
  --engine-version $DMS_ENGINE_VERSION \
  --allocated-storage $DMS_ALLOCATED_STORAGE \
  --replication-subnet-group-identifier $DMS_SUBNET_GROUP \
  --vpc-security-group-ids "$DMS_SECURITY_GROUP" \
  --no-multi-az \
  --no-auto-minor-version-upgrade`

echo $instanceCreateInfo

#dbClusterArn=`echo $clusterCreateInfo | jq -r '.DBCluster.DBClusterArn'`

# watch for cluster to be "available"

T="$(date +%s)"

instanceStatus='unknown'

exit 1

while true ; do
    clusterInfo=`aws docdb describe-db-clusters --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER`

    clusterStatus=`echo $clusterInfo | jq -r '.DBClusters[0].Status'`

    T2="$(($(date +%s)-T))"

    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
    echo "$thisDuration | waiting for cluster creation to complete"

    if [[ "$clusterStatus" == "available" ]] ; then
        break
    fi

    sleep $sleepSeconds
done

