#!/usr/bin/env python3
 
import boto3
from botocore.config import Config
import datetime as dt
import argparse
import requests
import json
import sys
import os
import time


def logIt(logMessage, appConfig):
    # elapsed hours, minutes, seconds
    elapsedSeconds = int(time.time() - appConfig['startTime'])
    thisHours, rem = divmod(elapsedSeconds, 3600)
    thisMinutes, thisSeconds = divmod(rem, 60)
    thisHMS = "{:0>2}:{:0>2}:{:0>2}".format(int(thisHours),int(thisMinutes),thisSeconds)
   
    # timestamp
    if sys.version_info[0] > 3 or (sys.version_info[0] == 3 and sys.version_info[1] >= 12):
        logTimeStamp = dt.datetime.now(dt.UTC).isoformat()[:-3] + 'Z'
    else:
        logTimeStamp = dt.datetime.utcnow().isoformat()[:-7] + 'Z'
    print("[{}] [{}] {}".format(logTimeStamp,thisHMS,logMessage))


def wait_for_cluster_deleted(appConfig, botoClient):
    clusterDeleted = False
    priorStatus = "<<NOT-A-VALID-STATUS>>"

    while not clusterDeleted:
        try:
            # check for timeout
            totSeconds = int(time.time()-appConfig['startTime'])
            if totSeconds >= appConfig['timeoutSeconds']:
                logIt("*** Script execution cancelled, timeout of {} seconds reached ***".format(appConfig['timeoutSeconds']), appConfig)
                sys.exit(1)

            response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
            if appConfig['verbose']:
                logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
            clusterStatus = response['DBClusters'][0].get('Status','UNKNOWN')
            if clusterStatus != priorStatus:
                logIt("    current cluster status is {}".format(clusterStatus), appConfig)
                priorStatus = clusterStatus
            time.sleep(appConfig['sleepSeconds'])
        except botoClient.exceptions.DBClusterNotFoundFault as e:
            clusterDeleted = True

        
def wait_for_cluster_available(appConfig, botoClient):
    clusterAvailable = False
    priorStatus = "<<NOT-A-VALID-STATUS>>"

    while not clusterAvailable:
        # check for timeout
        totSeconds = int(time.time()-appConfig['startTime'])
        if totSeconds >= appConfig['timeoutSeconds']:
            logIt("*** Script execution cancelled, timeout of {} seconds reached ***".format(appConfig['timeoutSeconds']), appConfig)
            sys.exit(1)

        response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
        if appConfig['verbose']:
            logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
        clusterStatus = response['DBClusters'][0].get('Status','UNKNOWN')
        if clusterStatus == "available":
            clusterAvailable = True
        else:
            if clusterStatus != priorStatus:
                logIt("  waiting for cluster status to change from {} to available".format(clusterStatus), appConfig)
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
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
    for thisInstance in response['DBClusters'][0]['DBClusterMembers']:
        instanceNameList.append(thisInstance['DBInstanceIdentifier'])
        instanceCount += 1
        
    while not allInstancesAvailable:
        # check for timeout
        totSeconds = int(time.time()-appConfig['startTime'])
        if totSeconds >= appConfig['timeoutSeconds']:
            logIt("*** Script execution cancelled, timeout of {} seconds reached ***".format(appConfig['timeoutSeconds']), appConfig)
            sys.exit(1)

        instancesAvailable = 0

        for thisInstance in instanceNameList:
            response = botoClient.describe_db_instances(DBInstanceIdentifier=thisInstance)
            if appConfig['verbose']:
                logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
            instanceStatus = response['DBInstances'][0].get('DBInstanceStatus','UNKNOWN')
            if instanceStatus == "available":
                instancesAvailable += 1

        if instancesAvailable < instanceCount:
            if instancesAvailable != priorAvailableCount:
                logIt("  {} of {} instances are available".format(instancesAvailable,instanceCount), appConfig)
                priorAvailableCount = instancesAvailable
            time.sleep(appConfig['sleepSeconds'])
        else:
            allInstancesAvailable = True


def create_instance(appConfig, botoClient, instanceRole, readReplicaInstanceNum):
    if instanceRole == "primary":
        instanceName = "{}-p".format(appConfig['clusterIdentifier'])
        azName = appConfig['primaryAz']
        logIt("creating primary instance {} in AZ {}".format(instanceName,azName), appConfig)
    else:
        instanceName = "{}-rr-{}".format(appConfig['clusterIdentifier'],readReplicaInstanceNum)
        azName = appConfig['readReplicaAz']
        logIt("creating read-replica instance {} in AZ {}".format(instanceName,azName), appConfig)
    
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
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
    
        
def create_cluster(appConfig, botoClient):
    logIt("creating cluster {}".format(appConfig['clusterIdentifier']), appConfig)
    originalStartTime = time.time()

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
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
    
    # wait for cluster to be created
    wait_for_cluster_available(appConfig, botoClient)
    opElapsedSeconds = int(time.time() - opStartTime)
    logIt("  cluster created in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)

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
    logIt("  instances created in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)
    
    opElapsedSeconds = int(time.time() - originalStartTime)
    logIt("cluster creation complete in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)


def delete_cluster(appConfig, botoClient):
    logIt("deleting cluster {}".format(appConfig['clusterIdentifier']), appConfig)
    originalStartTime = time.time()
    
    # delete all instances
    primaryInstance = ""
    readReplicaInstances = []
    instanceCount = 0
    priorInstanceCount = -1

    opStartTime = time.time()
    response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)
        
    for thisInstance in response['DBClusters'][0]['DBClusterMembers']:
        if thisInstance['IsClusterWriter']:
            primaryInstance = thisInstance['DBInstanceIdentifier']
        else:
            readReplicaInstances.append(thisInstance['DBInstanceIdentifier'])
        instanceCount += 1

    if instanceCount == 0:
        logIt("  no instances found", appConfig)
        
    else:
        logIt("  deleting instances", appConfig)
            
        # delete read replicas first
        for thisInstance in readReplicaInstances:
            logIt("    deleting read-replica instance {}".format(thisInstance), appConfig)
            botoClient.delete_db_instance(DBInstanceIdentifier=thisInstance)
            
        # delete primary
        logIt("    deleting primary instance {}".format(primaryInstance), appConfig)
        botoClient.delete_db_instance(DBInstanceIdentifier=primaryInstance)
        
        # wait for instance count to go to zero
        while instanceCount > 0:
            # check for timeout
            totSeconds = int(time.time()-appConfig['startTime'])
            if totSeconds >= appConfig['timeoutSeconds']:
                logIt("*** Script execution cancelled, timeout of {} seconds reached ***".format(appConfig['timeoutSeconds']), appConfig)
                sys.exit(1)

            response = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
            instanceCount = len(response['DBClusters'][0]['DBClusterMembers'])
            
            if instanceCount != priorInstanceCount:
                logIt("    cluster contains {} instance(s), waiting for 0".format(instanceCount), appConfig)
                priorInstanceCount = instanceCount

        opElapsedSeconds = int(time.time() - opStartTime)
        logIt("  instances deleted in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)
    
    # delete the cluster
    opStartTime = time.time()
    logIt("  deleting cluster {}".format(appConfig['clusterIdentifier']), appConfig)
    response = botoClient.delete_db_cluster(DBClusterIdentifier=appConfig['clusterIdentifier'],
                                            SkipFinalSnapshot=True)

    if appConfig['verbose']:
        logIt("  response {}".format(json.dumps(response,sort_keys=True,indent=4,default=str)), appConfig)

    # wait for cluster to be deleted
    wait_for_cluster_deleted(appConfig, botoClient)
    opElapsedSeconds = int(time.time() - opStartTime)
    logIt("  cluster deleted in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)

    opElapsedSeconds = int(time.time() - originalStartTime)
    logIt("cluster deletion complete in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)


def add_tag(appConfig, botoClient):
    logIt("adding tag {}".format(appConfig['clusterIdentifier']), appConfig)
    originalStartTime = time.time()

    # get cluter information
    clusterInfo = botoClient.describe_db_clusters(DBClusterIdentifier=appConfig['clusterIdentifier'])
    clusterArn = clusterInfo['DBClusters'][0]['DBClusterArn']
    if appConfig['verbose']:
        logIt("  cluster arn =  {}".format(json.dumps(clusterArn,sort_keys=True,indent=4,default=str)), appConfig)

    # add tag to cluster
    logIt("  adding tag to cluster {}".format(appConfig['clusterIdentifier']), appConfig)
    response = botoClient.add_tags_to_resource(ResourceName=clusterArn,Tags=[{'Key':appConfig['tagKey'],'Value':appConfig['tagValue']}])

    # add tag to instances
    instanceCount = 0
    for thisInstance in clusterInfo['DBClusters'][0]['DBClusterMembers']:
        responseInstance = botoClient.describe_db_instances(DBInstanceIdentifier=thisInstance['DBInstanceIdentifier'])
        instanceArn = responseInstance['DBInstances'][0]['DBInstanceArn']

        logIt("  adding tag to instance {}".format(thisInstance['DBInstanceIdentifier']), appConfig)
        response = botoClient.add_tags_to_resource(ResourceName=instanceArn,Tags=[{'Key':appConfig['tagKey'],'Value':appConfig['tagValue']}])

        if appConfig['verbose']:
            logIt("  instance arn {}".format(json.dumps(instanceArn,sort_keys=True,indent=4,default=str)), appConfig)

        instanceCount += 1

    if instanceCount == 0:
        logIt("  no instances found", appConfig)

    opElapsedSeconds = int(time.time() - originalStartTime)
    logIt("  tags created in {}".format(str(dt.timedelta(seconds=opElapsedSeconds))), appConfig)


def validate_config(appConfig):
    # validate configuration
    validationPassed = True
    
    # check instance class
    validInstanceClasses=["db.r6g.large","db.r6g.xlarge","db.r6g.2xlarge","db.r6g.4xlarge","db.r6g.8xlarge","db.r6g.12xlarge","db.r6g.16xlarge",
                          "db.r6gd.large","db.r6gd.xlarge","db.r6gd.2xlarge","db.r6gd.4xlarge","db.r6gd.8xlarge","db.r6gd.12xlarge","db.r6gd.16xlarge",
                          "db.r7g.large","db.r7g.xlarge","db.r7g.2xlarge","db.r7g.4xlarge","db.r7g.8xlarge","db.r7g.12xlarge","db.r7g.16xlarge",
                          "db.r7gd.large","db.r7gd.xlarge","db.r7gd.2xlarge","db.r7gd.4xlarge","db.r7gd.8xlarge","db.r7gd.12xlarge","db.r7gd.16xlarge",
                          "db.r8g.large","db.r8g.xlarge","db.r8g.2xlarge","db.r8g.4xlarge","db.r8g.8xlarge","db.r8g.12xlarge","db.r8g.16xlarge","db.r8g.24xlarge","db.r8g.48xlarge",
                          "db.r5.large","db.r5.xlarge","db.r5.2xlarge","db.r5.4xlarge","db.r5.8xlarge","db.r5.12xlarge","db.r5.16xlarge","db.r5.24xlarge",
                          "db.t3.medium","db.t4g.medium"]

    if appConfig['instanceType'] not in validInstanceClasses:
        validationPassed = False
        print("ERROR - invalid instance class {}".format(appConfig['instanceType']))
        
    if not validationPassed:
        print("ERROR - failed one or more validation checks, exiting")
        sys.exit(1)
   

def main():
    parser = argparse.ArgumentParser(description='DocumentDB Admin Tool')

    commandGroup = parser.add_mutually_exclusive_group()
    commandGroup.add_argument('--create-cluster',required=False,action="store_true",help='Create a new DocumentDB cluster')
    commandGroup.add_argument('--delete-cluster',required=False,action="store_true",help='Delete an existing DocumentDB cluster')
    commandGroup.add_argument('--add-tag',required=False,action="store_true",help='Add a tage to an existing DocumentDB cluster and all instances')
    
    parser.add_argument('-i','--cluster-identifier',required=True,type=str,help='DocumentDB cluster identifier')
    parser.add_argument('-d','--defaults-file',required=False,default="defaults.json",type=str,help='JSON file containing defaults')
    parser.add_argument('-v','--verbose',required=False,action="store_true",help='Enable verbose output')
    parser.add_argument('--ss','--sleep-seconds',required=False,default=60,type=int,help='Seconds to sleep between AWS API calls')
    parser.add_argument('--it','--instance-type',required=False,type=str,help='DocumentDB instance type')
    parser.add_argument('--nrr','--num-read-replicas',required=False,type=int,help='Number of read replicas')
    parser.add_argument('--ev','--engine-version',required=False,type=str,choices=['3.6.0','4.0.0','5.0.0','5.0.dev'],help='DocumentDB version')
    parser.add_argument('--pg','--parameter-group',required=False,type=str,help='Parameter group')
    parser.add_argument('--tag-key',required=False,type=str,help='Key name for tag')
    parser.add_argument('--tag-value',required=False,type=str,help='Value for tag')
    parser.add_argument('--timeout-seconds',required=False,type=int,default=3600,help='Timeout in seconds (give up waiting for request to complete)')
    parser.add_argument('--primary-az',required=False,type=str,help='Availability zone for primary instance')

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
    appConfig['addTag'] = args.add_tag
    appConfig['tagKey'] = args.tag_key
    appConfig['tagValue'] = args.tag_value
    appConfig['startTime'] = time.time()
    appConfig['timeoutSeconds'] = int(args.timeout_seconds)

    if (not appConfig['createCluster']) and (not appConfig['deleteCluster']) and (not appConfig['addTag']):
        print("ERROR - must pass one of --create-cluster, --delete-cluster, or --add-tag")
        sys.exit(1)

    # command line overrides
    if args.it is not None:
        appConfig['instanceType'] = args.it
    if args.nrr is not None:
        appConfig['numReadReplicas'] = int(args.nrr)
    if args.ev is not None:
        appConfig['engineVersion'] = args.ev
    if args.pg is not None:
        appConfig['parameterGroup'] = args.pg
    if args.primary_az is not None:
        appConfig['primaryAz'] = args.primary_az
        
    #print("appConfig - {}".format(json.dumps(appConfig,sort_keys=True,indent=4,default=str)))

    # validate the configuration
    validate_config(appConfig)
    
    botoConfig = Config(retries={'max_attempts': 10,'mode': 'standard'})

    if appConfig['endpointUrl'] == 'NONE':
        botoClient = boto3.client('docdb',region_name=appConfig['region'],config=botoConfig)
    else:
        if appConfig['verbose']:
            logIt("  using custom endpoint {}".format(appConfig['endpointUrl']), appConfig)
        botoClient = boto3.client('docdb',region_name=appConfig['region'],endpoint_url=appConfig['endpointUrl'],config=botoConfig)

    if appConfig['createCluster']:
        create_cluster(appConfig, botoClient)
    elif appConfig['deleteCluster']:
        delete_cluster(appConfig, botoClient)
    elif appConfig['addTag']:
        add_tag(appConfig, botoClient)
    else:
        print("no command given, exiting")
        sys.exit(1)


if __name__ == "__main__":
    main()
