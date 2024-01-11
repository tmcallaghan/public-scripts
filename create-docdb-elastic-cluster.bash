#! /bin/bash

# make sure user passed correct number of parameters
if [ $# -ne 4 ] ; then
    echo "4 arguments required: <cluster-identifier> <shard-capacity> <shard-count> <vpc-security-group>"
    exit 1
fi

DDB_DB_CLUSTER_IDENTIFIER=$1
DDB_DB_CLUSTER_IDENTIFIER="${DDB_DB_CLUSTER_IDENTIFIER//./-}"
DDB_SHARD_CAPACITY=$2
DDB_SHARD_COUNT=$3
DDB_VPC_SECURITY_GROUP_ID1=$4

# number of seconds to wait before looking for progress
sleepSeconds=5

# validate shard capacity and count
validShardCapacities=(2 4 8 16 32 64)
validShardCounts=(1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32)

validCapacity=0

for i in "${validShardCapacities[@]}" ; do
    if [ "$i" == "$DDB_SHARD_CAPACITY" ] ; then
        validCapacity=1
    fi
done

if [ $validCapacity -ne 1 ] ; then
    echo "invalid shard capacity requested : $DDB_SHARD_CAPACITY"
    exit 1
fi

validCount=0

for i in "${validShardCounts[@]}" ; do
    if [ "$i" == "$DDB_SHARD_COUNT" ] ; then
        validCount=1
    fi
done

if [ $validCount -ne 1 ] ; then
    echo "invalid shard count requested : $DDB_SHARD_COUNT"
    exit 1
fi

# bash stuff
# check if not set or empty
#   : "${BATCHNUM:?Variable not set or empty}"
# use default value if not set or empty
#   : "${BATCHNUM:=3}"


DDB_MASTER_USERNAME=${DOCDB_USERNAME:?Environment variable not set or empty}
DDB_MASTER_USER_PASSWORD=${DOCDB_PASSWORD:?Environment variable not set or empty}

# create the elastic cluster

echo "... creating elastic cluster $DDB_DB_CLUSTER_IDENTIFIER"

clusterCreateInfo=`aws docdb-elastic create-cluster \
  --admin-user-name $DDB_MASTER_USERNAME \
  --admin-user-password $DDB_MASTER_USER_PASSWORD \
  --auth-type PLAIN_TEXT \
  --cluster-name $DDB_DB_CLUSTER_IDENTIFIER \
  --shard-capacity $DDB_SHARD_CAPACITY \
  --shard-count $DDB_SHARD_COUNT \
  --vpc-security-group-ids "$DDB_VPC_SECURITY_GROUP_ID1"`

clusterArn=`echo $clusterCreateInfo | jq -r '.cluster.clusterArn'`

# watch for elastic cluster to be "ACTIVE"

T="$(date +%s)"

clusterStatus='unknown'

while true ; do
    clusterInfo=`aws docdb-elastic get-cluster --cluster-arn $clusterArn`

    clusterStatus=`echo $clusterInfo | jq -r '.cluster.status'`

    T2="$(($(date +%s)-T))"
    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
    echo "$thisDuration | waiting for elastic cluster $DDB_DB_CLUSTER_IDENTIFIER creation to complete"

    if [[ "$clusterStatus" == "ACTIVE" ]] ; then
        break
    fi

    sleep $sleepSeconds
done

sleep $sleepSeconds

T2="$(($(date +%s)-T))"
thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
echo "$thisDuration | elastic cluster $DDB_DB_CLUSTER_IDENTIFIER created"
