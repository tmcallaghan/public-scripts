#! /bin/bash

# make sure user passed elastic cluster identifier
if [ $# -ne 1 ] ; then
    echo "1 argument required: <elastic-cluster-identifier>"
    exit 1
fi

DDB_DB_CLUSTER_IDENTIFIER=$1

clusterInfo=$(aws docdb-elastic list-clusters --query clusters[?clusterName==\`$DDB_DB_CLUSTER_IDENTIFIER\`].clusterArn)

#echo $clusterInfo

clusterArn=`echo $clusterInfo | jq -c ".[0]" | tr -d '"'`

#echo $clusterArn

echo "... deleting elastic cluster $DDB_DB_CLUSTER_IDENTIFIER"

clusterDeleteInfo=`aws docdb-elastic delete-cluster --cluster-arn $clusterArn`

#echo $clusterDeleteInfo

