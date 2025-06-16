from datetime import datetime, timedelta
import sys
import json
import pymongo
import time
import os
import argparse
import string
import math
import warnings


def reportCollectionInfo(appConfig):
    client = pymongo.MongoClient(appConfig['uri'])
    db = client[appConfig['databaseName']]
    
    collStats = db.command("collStats", appConfig['collectionName'])
    
    compressionRatio = collStats['size'] / collStats['storageSize']
    gbDivisor = 1024*1024*1024
    
    print("collection statistics | numDocs             = {0:12,d}".format(collStats['count']))
    print("collection statistics | avgObjSize          = {0:12,d}".format(int(collStats['avgObjSize'])))
    print("collection statistics | size (GB)           = {0:12,.4f}".format(collStats['size']/gbDivisor))
    print("collection statistics | storageSize (GB)    = {0:12,.4f} ".format(collStats['storageSize']/gbDivisor))
    print("collection statistics | compressionRatio    = {0:12,.4f}".format(compressionRatio))
    print("collection statistics | totalIndexSize (GB) = {0:12,.4f}".format(collStats['totalIndexSize']/gbDivisor))
    
    client.close()


def dropCollection(appConfig):
    databaseName = appConfig['databaseName']
    collectionName = appConfig['collectionName']

    client = pymongo.MongoClient(appConfig['uri'])
    db = client[databaseName]
    adminDb = client['admin']
    col = db[collectionName]
    nameSpace = "{}.{}".format(databaseName,collectionName)

    print("Dropping collection {}".format(nameSpace))
    startTime = time.time()
    col.drop()
    elapsedMs = int((time.time() - startTime) * 1000)
    print("  completed in {} ms".format(elapsedMs))
        
    client.close()


def dropDatabase(appConfig):
    databaseName = appConfig['databaseName']

    client = pymongo.MongoClient(appConfig['uri'])

    print("Dropping database {}".format(databaseName))
    startTime = time.time()
    client.drop_database(databaseName)
    elapsedMs = int((time.time() - startTime) * 1000)
    print("  completed in {} ms".format(elapsedMs))
        
    client.close()


def main():
    warnings.filterwarnings("ignore","You appear to be connected to a DocumentDB cluster.")

    parser = argparse.ArgumentParser(description='DocumentDB DDL Runner')

    commandGroup = parser.add_mutually_exclusive_group()
    commandGroup.add_argument('--drop-database',required=False,action="store_true",help='Drop a database')
    commandGroup.add_argument('--drop-collection',required=False,action="store_true",help='Drop a collection')
    commandGroup.add_argument('--collection-stats',required=False,action="store_true",help='Get collection stats')

    parser.add_argument('--uri',required=True,type=str,help='URI (connection string)')
    parser.add_argument('--namespace',required=True,type=str,help='Namespace for the action')

    args = parser.parse_args()
    
    appConfig = {}
    appConfig['uri'] = args.uri
    appConfig['databaseName'] = args.namespace.split('.')[0]
    if '.' in args.namespace:
        appConfig['collectionName'] = args.namespace.split('.')[1]
    else:
        appConfig['collectionName'] = None

    if args.drop_database:
        dropDatabase(appConfig)

    elif args.drop_collection:
        dropCollection(appConfig)

    elif args.collection_stats:
        reportCollectionInfo(appConfig)

    else:
        print("unrecognized command")
        sys.exit(1)


if __name__ == "__main__":
    main()
