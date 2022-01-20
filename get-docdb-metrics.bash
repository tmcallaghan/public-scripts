#! /bin/bash

testJson="
[
  {
    "Id": "myId",
    "MetricStat": {
      "Metric": {
        "Namespace": "AWS/DocDB",
        "MetricName": "DocumentsInserted",
        "Dimensions": [
          {
            "Name": "DBInstanceIdentifier",
            "Value": "ddb4-max-insert-speed2"
          }
          ...
        ]
      },
      "Period": 10,
      "Stat": "Average",
      "Unit": "Seconds"|"Microseconds"|"Milliseconds"|"Bytes"|"Kilobytes"|"Megabytes"|"Gigabytes"|"Terabytes"|"Bits"|"Kilobits"|"Megabits"|"Gigabits"|"Terabits"|"Percent"|"Count"|"Bytes/Second"|"Kilobytes/Second"|"Megabytes/Second"|"Gigabytes/Second"|"Terabytes/Second"|"Bits/Second"|"Kilobits/Second"|"Megabits/Second"|"Gigabits/Second"|"Terabits/Second"|"Count/Second"|"None"
    },
    "Expression": "string",
    "Label": "string",
    "ReturnData": true|false,
    "Period": integer,
    "AccountId": "string"
  }
]
"

# make sure user passed correct number of parameters
if [ $# -ne 8 ] ; then
    echo "8 arguments required: <cluster-identifier> <instance-class> <instance-count> <availability-zone-primary> <availability-zone-replicas> <cluster-parameter-group-name> <vpc-security-group> <subnet-group>"
    exit 1
fi

DDB_DB_CLUSTER_IDENTIFIER=$1
DDB_INSTANCE_CLASS=$2
DDB_INSTANCE_COUNT=$3
DDB_INSTANCE_AZ_PRIMARY=$4
DDB_INSTANCE_AZ_REPLICAS=$5
DDB_DB_CLUSTER_PARAMETER_GROUP_NAME=$6
DDB_VPC_SECURITY_GROUP_ID1=$7
DDB_DB_SUBNET_GROUP_NAME=$8

# number of seconds to wait before looking for progress
sleepSeconds=5

# validate instance class
validInstanceClasses=(db.r6g.large db.r6g.xlarge db.r6g.2xlarge db.r6g.4xlarge db.r6g.8xlarge db.r6g.12xlarge db.r6g.16xlarge 
                      db.r5.large db.r5.xlarge db.r5.2xlarge db.r5.4xlarge db.r5.8xlarge db.r5.12xlarge db.r5.16xlarge db.r5.24xlarge
					  db.t3.medium db.t4g.medium)

validInstance=0

for i in "${validInstanceClasses[@]}" ; do
    if [ "$i" == "$DDB_INSTANCE_CLASS" ] ; then
        validInstance=1
    fi
done

if [ $validInstance -ne 1 ] ; then
    echo "invalid instance class requested : $DDB_INSTANCE_CLASS"
    exit 1
fi

# bash stuff
# check if not set or empty
#   : "${BATCHNUM:?Variable not set or empty}"
# use default value if not set or empty
#   : "${BATCHNUM:=3}"


DDB_BACKUP_RETENTION_PERIOD=1
DDB_ENGINE="docdb"
DDB_ENGINE_VERSION="4.0.0"
DDB_PORT=27017
DDB_MASTER_USERNAME=${DOCDB_USERNAME:?Environment variable not set or empty}
DDB_MASTER_USER_PASSWORD=${DOCDB_PASSWORD:?Environment variable not set or empty}

# create the cluster

echo "... creating cluster $DDB_DB_CLUSTER_IDENTIFIER"

clusterCreateInfo=`aws docdb create-db-cluster \
  --backup-retention-period $DDB_BACKUP_RETENTION_PERIOD \
  --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER \
  --db-cluster-parameter-group-name $DDB_DB_CLUSTER_PARAMETER_GROUP_NAME \
  --vpc-security-group-ids "$DDB_VPC_SECURITY_GROUP_ID1" \
  --db-subnet-group-name $DDB_DB_SUBNET_GROUP_NAME \
  --engine $DDB_ENGINE \
  --engine-version $DDB_ENGINE_VERSION \
  --port $DDB_PORT \
  --master-username $DDB_MASTER_USERNAME \
  --master-user-password $DDB_MASTER_USER_PASSWORD \
  --storage-encrypted \
  --no-deletion-protection`

dbClusterArn=`echo $clusterCreateInfo | jq -r '.DBCluster.DBClusterArn'`

# watch for cluster to be "available"

T="$(date +%s)"

clusterStatus='unknown'

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

# create the instances

i=1
while [ $i -le $DDB_INSTANCE_COUNT ] ; do
    DDB_DB_INSTANCE_IDENTIFIER="${DDB_DB_CLUSTER_IDENTIFIER}-${i}"
	
    if [ $i -eq 1 ] ; then
        echo "... creating primary instance $DDB_DB_INSTANCE_IDENTIFIER in availability zone $DDB_INSTANCE_AZ_PRIMARY"

        createInstanceInfo=`aws docdb create-db-instance \
          --db-instance-identifier ${DDB_DB_INSTANCE_IDENTIFIER} \
          --db-instance-class $DDB_INSTANCE_CLASS \
          --engine $DDB_ENGINE \
          --availability-zone $DDB_INSTANCE_AZ_PRIMARY \
          --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER`
          
    else
        if [[ "$DDB_INSTANCE_AZ_REPLICAS" == "any" ]] ; then
            echo "... creating read replica instance $DDB_DB_INSTANCE_IDENTIFIER in subnet group $DDB_DB_SUBNET_GROUP_NAME (multi AZ)"
            
            createInstanceInfo=`aws docdb create-db-instance \
              --db-instance-identifier ${DDB_DB_INSTANCE_IDENTIFIER} \
              --db-instance-class $DDB_INSTANCE_CLASS \
              --engine $DDB_ENGINE \
              --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER`
              
        else
            echo "... creating read replica instance $DDB_DB_INSTANCE_IDENTIFIER in availability zone $DDB_INSTANCE_AZ_REPLICAS (single AZ)"
            
            createInstanceInfo=`aws docdb create-db-instance \
              --db-instance-identifier ${DDB_DB_INSTANCE_IDENTIFIER} \
              --db-instance-class $DDB_INSTANCE_CLASS \
              --engine $DDB_ENGINE \
              --availability-zone $DDB_INSTANCE_AZ_REPLICAS \
              --db-cluster-identifier $DDB_DB_CLUSTER_IDENTIFIER`
        fi
	fi

    i=$(($i+1))
done

# watch for all instances to be "available"

instanceStatus='unknown'
instancePendingModifiedValues=1

while true ; do
    instanceInfo=`aws docdb describe-db-instances --filters Name=db-cluster-id,Values=${dbClusterArn}`

    i=0
    availableInstances=0
    instanceStatusString=""
    while [ $i -lt $DDB_INSTANCE_COUNT ] ; do
        instanceStatus=`echo $instanceInfo | jq -r ".DBInstances[${i}].DBInstanceStatus"`

        if [[ "$instanceStatus" == "available" ]] ; then
            availableInstances=$(($availableInstances+1))
        fi
        instanceStatusString="$instanceStatusString:$instanceStatus"

        i=$(($i+1))
    done

    T2="$(($(date +%s)-T))"
    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`

    instanceStatusString="$instanceStatusString:"
    echo "$thisDuration | $availableInstances instance(s) ready | statuses are $instanceStatusString"

    if [[ $availableInstances -eq $DDB_INSTANCE_COUNT ]] ; then
        break
    fi

    sleep $sleepSeconds
done
