#!/usr/bin/env python3
 
import boto3
import datetime as dt
import argparse
import requests
import json
import sys
import os
import time


def logIt(logMessage):
    logTimeStamp = dt.datetime.now(dt.UTC).isoformat()[:-3] + 'Z'
    print("[{}] {}".format(logTimeStamp,logMessage))


def wait_for_cluster_deleted(appConfig, botoClient):
    clusterDeleted = False
    priorStatus = "<<NOT-A-VALID-STATUS>>"

    while not clusterDeleted:
        try:
            response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
            if appConfig['verbose']:
                logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
            clusterStatus = response['DBClusters'][0].get('Status','UNKNOWN')
            if clusterStatus != priorStatus:
                logIt("    current cluster status is {}".format(clusterStatus))
                priorStatus = clusterStatus
            time.sleep(appConfig['sleepSeconds'])
        except botoClient.exceptions.DBClusterNotFoundFault as e:
            clusterDeleted = True

        
def wait_for_cluster_available(appConfig, botoClient):
    clusterAvailable = False
    priorStatus = "<<NOT-A-VALID-STATUS>>"

    while not clusterAvailable:
        response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
        if appConfig['verbose']:
            logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
        clusterStatus = response['DBClusters'][0].get('Status','UNKNOWN')
        if clusterStatus == "available":
            clusterAvailable = True
        else:
            if clusterStatus != priorStatus:
                logIt("  waiting for cluster status to change from {} to available".format(clusterStatus))
                priorStatus = clusterStatus
            time.sleep(appConfig['sleepSeconds'])

        
def wait_for_instances_available(appConfig, botoClient):
    allInstancesAvailable = False
    instanceNameList = []
    instanceCount = 0
    priorAvailableCount = -1

    # get all instance identifiers
    response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
    for thisInstance in response['DBClusters'][0]['DBClusterMembers']:
        instanceNameList.append(thisInstance['DBInstanceIdentifier'])
        instanceCount += 1
        
    while not allInstancesAvailable:
        instancesAvailable = 0
        
        for thisInstance in instanceNameList:
            response = botoClient.describe_db_instances(DBInstanceIdentifier=thisInstance)
            if appConfig['verbose']:
                logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
            instanceStatus = response['DBInstances'][0].get('DBInstanceStatus','UNKNOWN')
            if instanceStatus == "available":
                instancesAvailable += 1

        if instancesAvailable < instanceCount:
            if instancesAvailable != priorAvailableCount:
                logIt("  {} of {} instances are available".format(instancesAvailable,instanceCount))
                priorAvailableCount = instancesAvailable
            time.sleep(appConfig['sleepSeconds'])
        else:
            allInstancesAvailable = True


def create_instance(appConfig, botoClient, instanceRole, readReplicaInstanceNum):
    if instanceRole == "primary":
        instanceName = "{}-p".format(appConfig['clusterIdentifier'])
        azName = appConfig['primaryAz']
        logIt("creating primary instance {} in AZ {}".format(instanceName,azName))
    else:
        instanceName = "{}-rr-{}".format(appConfig['clusterIdentifier'],readReplicaInstanceNum)
        azName = appConfig['readReplicaAz']
        logIt("creating read-replica instance {} in AZ {}".format(instanceName,azName))
    
    response = botoClient.create_db_instance(
                                    DBInstanceIdentifier=instanceName,
                                    DBInstanceClass=appConfig['instanceType'],
                                    Engine='docdb',
                                    AvailabilityZone=azName,
                                    DBClusterIdentifier=appConfig['clusterIdentifier'])

    #PreferredMaintenanceWindow='string',
    #AutoMinorVersionUpgrade=True|False,
    #Tags=[{'Key': 'string','Value': 'string'},],
    #CopyTagsToSnapshot=True|False,
    #PromotionTier=123,
    #EnablePerformanceInsights=True|False,
    #PerformanceInsightsKMSKeyId='string',
    #CACertificateIdentifier='string'
                                       
    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
    
        
def create_cluster(appConfig):
    logIt("creating cluster {}".format(appConfig['clusterIdentifier']))
    originalStartTime = time.time()
    
    if appConfig['endpointUrl'] == 'NONE':
        botoClient = boto3.client('docdb',region_name=appConfig['region'])
    else:
        if appConfig['verbose']:
            logIt("  using custom endpoint {}".format(appConfig['endpointUrl']))
        botoClient = boto3.client('docdb',region_name=appConfig['region'],endpoint_url=appConfig['endpointUrl'])

    opStartTime = time.time()
    response = botoClient.create_db_cluster(
                                        DBClusterIdentifier=appConfig['clusterIdentifier'],
                                        DBClusterParameterGroupName=appConfig['parameterGroup'],
                                        VpcSecurityGroupIds=[appConfig['vpcSecurityGroup']],
                                        DBSubnetGroupName=appConfig['subnetGroup'],
                                        Engine='docdb',
                                        EngineVersion=appConfig['engineVersion'],
                                        Port=appConfig['serverPort'],
                                        MasterUsername=appConfig['userName'],
                                        MasterUserPassword=appConfig['userPassword'],
                                        StorageType=appConfig['storageType'])
                                       
    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
    
    # wait for cluster to be created
    wait_for_cluster_available(appConfig, botoClient)
    opElapsedSeconds = int(time.time() - opStartTime)
    logIt("  cluster created in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))))

    #AvailabilityZones=['string',],
    #BackupRetentionPeriod=123,
    #PreferredBackupWindow='string',
    #PreferredMaintenanceWindow='string',
    #Tags=[{'Key': 'string','Value': 'string'},],
    #StorageEncrypted=True|False,
    #KmsKeyId='string',
    #EnableCloudwatchLogsExports=['string',],
    #DeletionProtection=True|False,
    #GlobalClusterIdentifier='string',
    #SourceRegion='string'

    opStartTime = time.time()

    # primary instance
    create_instance(appConfig, botoClient, "primary", 0)
    
    # read replica instance(s)
    if appConfig['numReadReplicas'] > 0:
        for rrNum in range(1,appConfig['numReadReplicas']+1):
            create_instance(appConfig, botoClient, "readReplica", rrNum)

    # wait for all instances to be available
    wait_for_instances_available(appConfig, botoClient)
    opElapsedSeconds = int(time.time() - opStartTime)
    logIt("  instances created in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))))
    
    opElapsedSeconds = int(time.time() - originalStartTime)
    logIt("cluster creation complete in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))))


def delete_cluster(appConfig):
    logIt("deleting cluster {}".format(appConfig['clusterIdentifier']))
    originalStartTime = time.time()
    
    if appConfig['endpointUrl'] == 'NONE':
        botoClient = boto3.client('docdb',region_name=appConfig['region'])
    else:
        if appConfig['verbose']:
            logIt("  using custom endpoint {}".format(appConfig['endpointUrl']))
        botoClient = boto3.client('docdb',region_name=appConfig['region'],endpoint_url=appConfig['endpointUrl'])

    # delete all instances
    primaryInstance = ""
    readReplicaInstances = []
    instanceCount = 0
    priorInstanceCount = -1

    opStartTime = time.time()
    response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))
        
    for thisInstance in response['DBClusters'][0]['DBClusterMembers']:
        if thisInstance['IsClusterWriter']:
            primaryInstance = thisInstance['DBInstanceIdentifier']
        else:
            readReplicaInstances.append(thisInstance['DBInstanceIdentifier'])
        instanceCount += 1

    if instanceCount == 0:
        logIt("  no instances found")
        
    else:
        logIt("  deleting instances")
            
        # delete read replicas first
        for thisInstance in readReplicaInstances:
            logIt("    deleting read-replica instance {}".format(thisInstance))
            botoClient.delete_db_instance(DBInstanceIdentifier=thisInstance)
            
        # delete primary
        logIt("    deleting primary instance {}".format(primaryInstance))
        botoClient.delete_db_instance(DBInstanceIdentifier=primaryInstance)
        
        # wait for instance count to go to zero
        while instanceCount > 0:
            response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
            instanceCount = len(response['DBClusters'][0]['DBClusterMembers'])
            
            if instanceCount != priorInstanceCount:
                logIt("    cluster contains {} instance(s), waiting for 0".format(instanceCount))
                priorInstanceCount = instanceCount

        opElapsedSeconds = int(time.time() - opStartTime)
        logIt("  instances deleted in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))))
    
    # delete the cluster
    opStartTime = time.time()
    logIt("  deleting cluster {}".format(appConfig['clusterIdentifier']))
    response = botoClient.delete_db_cluster(DBClusterIdentifier=appConfig['clusterIdentifier'],
                                            SkipFinalSnapshot=True)

    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)))

    # wait for cluster to be deleted
    wait_for_cluster_deleted(appConfig, botoClient)
    opElapsedSeconds = int(time.time() - opStartTime)
    logIt("  cluster deleted in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))))

    opElapsedSeconds = int(time.time() - originalStartTime)
    logIt("cluster deletion complete in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))))

    
def main():
    parser = argparse.ArgumentParser(description='DocumentDB Admin Tool')

    commandGroup = parser.add_mutually_exclusive_group()
    commandGroup.add_argument('--create-cluster',required=False,action="store_true",help='Create a new DocumentDB cluster')
    commandGroup.add_argument('--delete-cluster',required=False,action="store_true",help='Delete an existing DocumentDB cluster')
    
    parser.add_argument('-i','--cluster-identifier',required=True,type=str,help='DocumentDB cluster identifier')
    parser.add_argument('-d','--defaults-file',required=False,default="defaults.json",type=str,help='JSON file containing defaults')
    parser.add_argument('-v','--verbose',required=False,action="store_true",help='Enable verbose output')
    parser.add_argument('--sleep-seconds',required=False,default=15,type=int,help='Seconds to sleep between AWS API calls')
    
    #parser.add_argument('--region',required=True,type=str,help='AWS Region')
    #parser.add_argument('--endpoint-url',required=False,type=str,default='NONE',help='Endpoint URL')
    #parser.add_argument('--filter-string',required=False,type=str,default='NONENONENONE',help='Only display clusters containing given string(s), comma separated')

    args = parser.parse_args()
    
    # read defaults file
    with open(args.defaults_file) as fh:
        defaultDict = json.load(fh)
        
    appConfig = {}
    
    for key in defaultDict:
        appConfig[key] = defaultDict[key]
    
    appConfig['clusterIdentifier'] = args.cluster_identifier
    appConfig['verbose'] = args.verbose
    appConfig['createCluster'] = args.create_cluster
    appConfig['deleteCluster'] = args.delete_cluster
    
    #appConfig['region'] = args.region
    #appConfig['endpointUrl'] = args.endpoint_url
    #if args.filter_string == "NONENONENONE":
    #    appConfig['filterString'] = []
    #else:
    #    appConfig['filterString'] = args.filter_string.split(",")

    if appConfig['createCluster']:
        create_cluster(appConfig)
    elif appConfig['deleteCluster']:
        delete_cluster(appConfig)
    else:
        print("no command given, exiting")
        sys.exit(1)


if __name__ == "__main__":
    main()
