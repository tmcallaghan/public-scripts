#! /bin/bash

# make sure user passed correct number of parameters
if [ $# -ne 4 ] ; then
    echo "4 arguments required: <global-cluster-identifier> <source-db-cluster-identifier> <remote-region> <remote-cluster-identifier>"
    exit 1
fi

DDB_GLOBAL_CLUSTER_IDENTIFIER=$1
DDB_SOURCE_DB_CLUSTER_IDENTIFIER=$2
DDB_REMOTE_REGION=$3
DDB_REMOTE_CLUSTER_IDENTIFIER=$4

DDB_ENGINE="docdb"

# number of seconds to wait before looking for progress
sleepSeconds=5

# ---------------------------------------------------
# create the global cluster

echo "... creating global cluster $DDB_GLOBAL_CLUSTER_IDENTIFIER"

globalClusterCreateInfo=`aws docdb create-global-cluster \
  --global-cluster-identifier $DDB_GLOBAL_CLUSTER_IDENTIFIER \
  --source-db-cluster-identifier $DDB_SOURCE_DB_CLUSTER_IDENTIFIER`

globalClusterArn=`echo $globalClusterCreateInfo | jq -r '.GlobalCluster.GlobalClusterArn'`

echo "... created global cluster, ARN = $globalClusterArn"

# ---------------------------------------------------
# watch for global cluster to be "available"

T="$(date +%s)"

globalClusterStatus='unknown'

while true ; do
    globalClusterInfo=`aws docdb describe-global-clusters --global-cluster-identifier $DDB_GLOBAL_CLUSTER_IDENTIFIER`
    globalClusterStatus=`echo $globalClusterInfo | jq -r '.GlobalClusters[0].Status'`

    T2="$(($(date +%s)-T))"

    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
    echo "$thisDuration | waiting for global cluster creation to complete"

    if [[ "$globalClusterStatus" == "available" ]] ; then
        break
    fi

    sleep $sleepSeconds
done

# ---------------------------------------------------
# create cluster in remote region

echo "... creating cluster in remote region"

clusterCreateInfo=`aws docdb create-db-cluster \
  --db-cluster-identifier $DDB_REMOTE_CLUSTER_IDENTIFIER \
  --global-cluster-identifier $DDB_GLOBAL_CLUSTER_IDENTIFIER \
  --region $DDB_REMOTE_REGION \
  --engine $DDB_ENGINE \
  --no-storage-encrypted`

# ---------------------------------------------------
# wait for cluster to be available

echo "... waiting for remote region cluster to be available"

dbClusterArn=`echo $clusterCreateInfo | jq -r '.DBCluster.DBClusterArn'`

T="$(date +%s)"

clusterStatus='unknown'

while true ; do
    clusterInfo=`aws docdb describe-db-clusters --db-cluster-identifier $dbClusterArn --region $DDB_REMOTE_REGION`
    clusterStatus=`echo $clusterInfo | jq -r '.DBClusters[0].Status'`

    T2="$(($(date +%s)-T))"

    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
    echo "$thisDuration | waiting for remote region cluster to be available"

    if [[ "$clusterStatus" == "available" ]] ; then
        break
    fi

    sleep $sleepSeconds
done

