#!/usr/bin/env python3
 
import boto3
from botocore.config import Config
import datetime
import argparse
import requests
import json
import sys
import os


def report_clusters(appConfig):
    print("Gathering cluster details.")

    botoConfig = Config(retries={'max_attempts': 10,'mode': 'standard'})

    maxClusterNameLength = 0
    maxClusterStatusLength = 0

    if appConfig['endpointUrl'] == 'NONE':
        client = boto3.client('docdb',region_name=appConfig['region'],config=botoConfig)
    else:
        client = boto3.client('docdb',region_name=appConfig['region'],endpoint_url=appConfig['endpointUrl'],config=botoConfig)
    
    response = client.describe_db_clusters(Filters=[{'Name': 'engine','Values': ['docdb']}])
    
    clusterArr = {}
    for thisCluster in response['DBClusters']:
        thisDBClusterIdentifier = thisCluster['DBClusterIdentifier']
        includeThisCluster = False
        if appConfig['filterString'] == []:
            includeThisCluster = True
        else:
            for thisSearchString in appConfig['filterString']:
                if thisSearchString.casefold() in thisDBClusterIdentifier:
                    includeThisCluster = True

        if includeThisCluster:
            thisClusterDict = {}
            thisClusterDict['ioType'] = thisCluster.get('StorageType','standard')
            thisClusterDict['engineVersionFull'] = thisCluster['EngineVersion']
            thisClusterDict['engineVersionMajor'] = int(thisClusterDict['engineVersionFull'].split('.')[0])
            thisClusterDict['status'] = thisCluster['Status']
            thisClusterDict['fullPayload'] = thisCluster

            maxClusterStatusLength = max(len(thisCluster['Status']),maxClusterStatusLength)
            maxClusterNameLength = max(len(thisCluster['DBClusterIdentifier']),maxClusterNameLength)

            thisClusterInstancesDict = {}
            numInstances = 0
            for thisInstance in thisCluster['DBClusterMembers']:
                # get instance type
                responseInstance = client.describe_db_instances(DBInstanceIdentifier=thisInstance['DBInstanceIdentifier'])
                thisClusterInstanceDict = {}
                thisClusterInstanceDict['DBInstanceClass'] = responseInstance['DBInstances'][0]['DBInstanceClass']
                thisClusterInstanceDict['fullPayload'] = responseInstance
                thisClusterInstancesDict[responseInstance['DBInstances'][0]['DBInstanceIdentifier']] = thisClusterInstanceDict.copy()
                numInstances += 1

            thisClusterDict['numInstances'] = numInstances

            clusterArr[thisCluster['DBClusterIdentifier']] = {'clusterDetails':thisClusterDict.copy(), 'instanceDetails':thisClusterInstancesDict.copy()}

    client.close()

    clustersFound = False
    for thisDBClusterIdentifier in sorted(clusterArr.keys()):
        thisCluster = clusterArr[thisDBClusterIdentifier]
        clustersFound = True
        if appConfig['compact']:
            print("{0:<{w1}} | IO type = {1} | version = {2} | instances = {3:d} | status = {4:<{w2}} | endpoint = {5}".format(thisDBClusterIdentifier,thisCluster['clusterDetails']['ioType'],
                  thisCluster['clusterDetails']['engineVersionFull'],thisCluster['clusterDetails']['numInstances'],thisCluster['clusterDetails']['status'],
                  thisCluster['clusterDetails']['fullPayload'].get('Endpoint','<<missing>>'),w1=maxClusterNameLength,w2=maxClusterStatusLength))
        else:
            print("")
            print("cluster = {} | IO type = {} | version = {} | instances = {:d} | status = {} | endpoint = {} | arn = {}".format(thisDBClusterIdentifier,thisCluster['clusterDetails']['ioType'],
                  thisCluster['clusterDetails']['engineVersionFull'],thisCluster['clusterDetails']['numInstances'],thisCluster['clusterDetails']['status'],
                  thisCluster['clusterDetails']['fullPayload'].get('Endpoint','<<missing>>'),thisCluster['clusterDetails']['fullPayload']['DBClusterArn']))

            for DBInstanceIdentifier in sorted(thisCluster['instanceDetails'].keys()):
                thisInstance = thisCluster['instanceDetails'][DBInstanceIdentifier]
                print("  instance = {} | instance type = {} | availability zone = {} | status = {} | arn = {}".format(DBInstanceIdentifier,thisInstance['DBInstanceClass'],thisInstance['fullPayload']['DBInstances'][0].get('AvailabilityZone','UNKNOWN'),
                      thisInstance['fullPayload']['DBInstances'][0]['DBInstanceStatus'],thisInstance['fullPayload']['DBInstances'][0]['DBInstanceArn']))

        if appConfig['verbose']:
            print("{}".format(json.dumps(thisCluster,sort_keys=True,indent=4,default=str)))
    
    if not clustersFound:
        if (appConfig['filterString'] == 'NONENONENONE'):
            print("  no clusters found")
        else:
            print("  no clusters found for filter {}".format(appConfig['filterString']))
        
    
def main():
    parser = argparse.ArgumentParser(description='DocumentDB Deployment Scanner')

    parser.add_argument('--region',required=True,type=str,help='AWS Region')
    parser.add_argument('--endpoint-url',required=False,type=str,default='NONE',help='Endpoint URL')
    parser.add_argument('--filter-string',required=False,type=str,default='NONENONENONE',help='Only display clusters containing given string(s), comma separated')
    parser.add_argument('--verbose',required=False,action="store_true",help='Enable verbose output')
    parser.add_argument('--compact',required=False,action="store_true",help='Enable compact output')

    args = parser.parse_args()
   
    appConfig = {}
    appConfig['region'] = args.region
    appConfig['endpointUrl'] = args.endpoint_url
    if args.filter_string == "NONENONENONE":
        appConfig['filterString'] = []
    else:
        appConfig['filterString'] = args.filter_string.split(",")
    
    appConfig['verbose'] = args.verbose
    appConfig['compact'] = args.compact

    report_clusters(appConfig)


if __name__ == "__main__":
    main()
