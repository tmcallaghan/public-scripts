#!/usr/bin/env python3
 
import boto3
import datetime
import argparse
import requests
import json
import sys
import os


def report_clusters(appConfig):
    print("Gathering cluster details.")

    if appConfig['endpointUrl'] == 'NONE':
        client = boto3.client('docdb',region_name=appConfig['region'])
    else:
        client = boto3.client('docdb',region_name=appConfig['region'],endpoint_url=appConfig['endpointUrl'])
    
    response = client.describe_db_clusters(Filters=[{'Name': 'engine','Values': ['docdb']}])
    
    clusterArr = {}
    for thisCluster in response['DBClusters']:
        thisClusterDict = {}
        thisClusterDict['ioType'] = thisCluster.get('StorageType','standard')
        thisClusterDict['engineVersionFull'] = thisCluster['EngineVersion']
        thisClusterDict['engineVersionMajor'] = int(thisClusterDict['engineVersionFull'].split('.')[0])
        thisClusterDict['status'] = thisCluster['Status']
        thisClusterDict['fullPayload'] = thisCluster

        thisClusterInstancesDict = {}
        numInstances = 0
        for thisInstance in thisCluster['DBClusterMembers']:
            # get instance type
            responseInstance = client.describe_db_instances(DBInstanceIdentifier=thisInstance['DBInstanceIdentifier'])
            #print("{}".format(responseInstance))
            thisClusterInstanceDict = {}            
            #thisClusterInstanceDict['DBInstanceIdentifier'] = responseInstance['DBInstances'][0]['DBInstanceIdentifier']
            thisClusterInstanceDict['DBInstanceClass'] = responseInstance['DBInstances'][0]['DBInstanceClass']
            thisClusterInstanceDict['fullPayload'] = responseInstance
            thisClusterInstancesDict[responseInstance['DBInstances'][0]['DBInstanceIdentifier']] = thisClusterInstanceDict.copy()
            numInstances += 1

        thisClusterDict['numInstances'] = numInstances
        #print("cluster = {} | IO type = {} | version = {} | instances = {:d}".format(thisCluster['DBClusterIdentifier'],thisClusterDict['ioType'],thisClusterDict['engineVersionFull'],numInstances))
        
        clusterArr[thisCluster['DBClusterIdentifier']] = {'clusterDetails':thisClusterDict.copy(), 'instanceDetails':thisClusterInstancesDict.copy()}
            
    client.close()
    
    clustersFound = False
    
    for thisDBClusterIdentifier in sorted(clusterArr.keys()):
        thisCluster = clusterArr[thisDBClusterIdentifier]
        includeThisCluster = False
        if appConfig['filterString'] == []:
            includeThisCluster = True
        else:
            for thisSearchString in appConfig['filterString']:
                if thisSearchString.casefold() in thisDBClusterIdentifier:
                    includeThisCluster = True
            
        #if (appConfig['filterString'] == 'NONENONENONE') or (appConfig['filterString'].casefold() in thisDBClusterIdentifier):
        if includeThisCluster:
            clustersFound = True
            print("")
            print("cluster = {} | IO type = {} | version = {} | instances = {:d} | status = {} | endpoint = {} | arn = {}".format(thisDBClusterIdentifier,thisCluster['clusterDetails']['ioType'],
                  thisCluster['clusterDetails']['engineVersionFull'],thisCluster['clusterDetails']['numInstances'],thisCluster['clusterDetails']['status'],
                  thisCluster['clusterDetails']['fullPayload'].get('Endpoint','<<missing>>'),thisCluster['clusterDetails']['fullPayload']['DBClusterArn']))
            #print("{}".format(thisCluster['instanceDetails']))
            #print("{}".format(thisCluster['clusterDetails']['fullPayload']['Endpoint']))
            #print("{}".format(thisCluster['clusterDetails']['fullPayload']))
            if appConfig['verbose']:
                print("{}".format(json.dumps(thisCluster,sort_keys=True,indent=4,default=str)))
                
            for DBInstanceIdentifier in sorted(thisCluster['instanceDetails'].keys()):
                #print("{}".format(DBInstanceIdentifier))
                thisInstance = thisCluster['instanceDetails'][DBInstanceIdentifier]
                print("  instance = {} | instance type = {} | availability zone = {} | status = {} | arn = {}".format(DBInstanceIdentifier,thisInstance['DBInstanceClass'],thisInstance['fullPayload']['DBInstances'][0].get('AvailabilityZone','UNKNOWN'),
                                                                                  thisInstance['fullPayload']['DBInstances'][0]['DBInstanceStatus'],thisInstance['fullPayload']['DBInstances'][0]['DBInstanceArn']))
                #print("{}".format(json.dumps(thisInstance['fullPayload'],sort_keys=True,indent=4,default=str)))
    
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

    args = parser.parse_args()
   
    appConfig = {}
    appConfig['region'] = args.region
    appConfig['endpointUrl'] = args.endpoint_url
    if args.filter_string == "NONENONENONE":
        appConfig['filterString'] = []
    else:
        appConfig['filterString'] = args.filter_string.split(",")
    
    appConfig['verbose'] = args.verbose

    report_clusters(appConfig)


if __name__ == "__main__":
    main()
