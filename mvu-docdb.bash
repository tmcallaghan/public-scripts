#! /bin/bash

# Clone and MVU a DocDB cluster

# make sure user passed correct number of parameters
if [ $# -ne 4 ] ; then
    echo "4 arguments required: <source-cluster-identifier> <clone-cluster-identifier> <clone-instance-class> <clone-instance-count>"
    exit 1
fi

DDB_SOURCE_CLUSTER_IDENTIFIER=$1
DDB_CLONE_CLUSTER_IDENTIFIER=$2
DDB_INSTANCE_CLASS=$3
DDB_INSTANCE_COUNT=$4

#DDB_INSTANCE_AZ_PRIMARY=$4
#DDB_INSTANCE_AZ_REPLICAS=$5
#DDB_DB_CLUSTER_PARAMETER_GROUP_NAME=$6
#DDB_VPC_SECURITY_GROUP_ID1=$7
#DDB_DB_SUBNET_GROUP_NAME=$8
#DDB_ENGINE_VERSION=$9

# number of seconds to wait before looking for progress
sleepSeconds=15

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

#DDB_BACKUP_RETENTION_PERIOD=1
#DDB_PORT=27017
#DDB_MASTER_USERNAME=${DOCDB_USERNAME:?Environment variable not set or empty}
#DDB_MASTER_USER_PASSWORD=${DOCDB_PASSWORD:?Environment variable not set or empty}



DDB_ENGINE="docdb"
PARAMETER_GROUP="tls-disabled-50"


# clone the existing cluster

echo "... cloning cluster $DDB_SOURCE_CLUSTER_IDENTIFIER to $DDB_CLONE_CLUSTER_IDENTIFIER"

cloneInfo=`aws docdb restore-db-cluster-to-point-in-time \
 --source-db-cluster-identifier $DDB_SOURCE_CLUSTER_IDENTIFIER \
 --db-cluster-identifier $DDB_CLONE_CLUSTER_IDENTIFIER \
 --restore-type copy-on-write \
 --use-latest-restorable-time`

#echo $cloneInfo

dbClusterArn=`echo $cloneInfo | jq -r '.DBCluster.DBClusterArn'`

# watch for cluster to be "available"

T="$(date +%s)"

clusterStatus='unknown'

while true ; do
    clusterInfo=`aws docdb describe-db-clusters --db-cluster-identifier $DDB_CLONE_CLUSTER_IDENTIFIER`

    clusterStatus=`echo $clusterInfo | jq -r '.DBClusters[0].Status'`

    T2="$(($(date +%s)-T))"

    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
    echo "$thisDuration | waiting for cluster creation to complete"

    if [[ "$clusterStatus" == "available" ]] ; then
        thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
        echo "$thisDuration | finished creating cluster in $thisDuration"
        break
    fi

    sleep $sleepSeconds
done


# create the instances

i=1
while [ $i -le $DDB_INSTANCE_COUNT ] ; do
    DDB_DB_INSTANCE_IDENTIFIER="${DDB_CLONE_CLUSTER_IDENTIFIER}-${i}"
	
    if [ $i -eq 1 ] ; then
        echo "... creating primary instance $DDB_DB_INSTANCE_IDENTIFIER"

        createInstanceInfo=`aws docdb create-db-instance \
          --db-instance-identifier ${DDB_DB_INSTANCE_IDENTIFIER} \
          --db-instance-class $DDB_INSTANCE_CLASS \
          --engine $DDB_ENGINE \
          --db-cluster-identifier $DDB_CLONE_CLUSTER_IDENTIFIER`
          
    else
        echo "... creating read replica instance $DDB_DB_INSTANCE_IDENTIFIER"
            
        createInstanceInfo=`aws docdb create-db-instance \
          --db-instance-identifier ${DDB_DB_INSTANCE_IDENTIFIER} \
          --db-instance-class $DDB_INSTANCE_CLASS \
          --engine $DDB_ENGINE \
          --db-cluster-identifier $DDB_CLONE_CLUSTER_IDENTIFIER`
              
    fi

    i=$(($i+1))
done

# watch for all instances to be "available"

instanceStatus='unknown'
instancePendingModifiedValues=1
TTIMER="$(date +%s)"

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
        T2="$(($(date +%s)-TTIMER))"
        thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
        echo "$thisDuration | finished creating all instances in $thisDuration"
        break
    fi

    sleep $sleepSeconds
done


echo "... performing MVU on cluster $DDB_CLONE_CLUSTER_IDENTIFIER"

mvuInfo=`aws docdb modify-db-cluster \
           --db-cluster-identifier $DDB_CLONE_CLUSTER_IDENTIFIER \
           --allow-major-version-upgrade \
           --engine-version 5.0 \
           --apply-immediately \
           --db-cluster-parameter-group-name $PARAMETER_GROUP \
           --region us-east-1`

#echo $mvuInfo


# watch for cluster to be "available"

clusterStatus='unknown'
TTIMER="$(date +%s)"
sleep $sleepSeconds
sleep $sleepSeconds
sleep $sleepSeconds
sleep $sleepSeconds

while true ; do
    clusterInfo=`aws docdb describe-db-clusters --db-cluster-identifier $DDB_CLONE_CLUSTER_IDENTIFIER`

    clusterStatus=`echo $clusterInfo | jq -r '.DBClusters[0].Status'`

    T2="$(($(date +%s)-T))"

    thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
    echo "$thisDuration | waiting for cluster MVU to complete"

    if [[ "$clusterStatus" == "available" ]] ; then
        T2="$(($(date +%s)-TTIMER))"
        thisDuration=`printf "%02d:%02d:%02d:%02d" "$((T2/86400))" "$((T2/3600%24))" "$((T2/60%60))" "$((T2%60))"`
        echo "$thisDuration | finished MVU in $thisDuration"
        break
    fi

    sleep $sleepSeconds
done

