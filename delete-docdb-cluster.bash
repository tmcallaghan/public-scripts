#! /bin/bash

# make sure user passed cluster identifier
if [ $# -ne 1 ] ; then
    echo "1 argument required: <cluster-identifier>"
    exit 1
fi

DDB_DB_CLUSTER_IDENTIFIER=$1

clusterInfo=`aws docdb describe-db-clusters \
    --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER \
    --query 'DBClusters[*].[DBClusterIdentifier,DBClusterMembers[*].DBInstanceIdentifier]'
	`

#echo $clusterInfo

COUNTER=0
while [  $COUNTER -lt 16 ]; do
	thisInstance=`echo $clusterInfo | jq -c ".[][1][${COUNTER}]" | tr -d '"'`
    if [ "$thisInstance" = "null" ]; then
		# no more instances, exit loop
        COUNTER=16
	else
		# delete the instance
		echo "... deleting instance $thisInstance"
        instanceInfo=`aws docdb delete-db-instance \
                        --db-instance-identifier $thisInstance`
    fi
    let COUNTER=COUNTER+1 
done

sleep 15

echo "... deleting cluster $DDB_DB_CLUSTER_IDENTIFIER"

clusterDeleteInfo=`aws docdb delete-db-cluster \
    --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER \
    --skip-final-snapshot
    `

#dbClusterArn=`echo $clusterDeleteInfo | jq -r '.DBCluster.DBClusterArn'`

#echo "    ... arn = $dbClusterArn"

sleep 15
