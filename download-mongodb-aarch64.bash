#! /bin/bash

wget https://fastdl.mongodb.org/linux/mongodb-linux-aarch64-ubuntu2404-8.0.9.tgz
wget https://fastdl.mongodb.org/linux/mongodb-linux-aarch64-ubuntu2204-7.0.20.tgz
wget https://fastdl.mongodb.org/linux/mongodb-linux-aarch64-ubuntu2204-6.0.23.tgz
wget https://fastdl.mongodb.org/linux/mongodb-linux-aarch64-ubuntu2004-5.0.31.tgz
wget https://fastdl.mongodb.org/linux/mongodb-linux-aarch64-ubuntu2004-4.4.29.tgz

wget https://downloads.mongodb.com/compass/mongosh-2.5.1-linux-arm64.tgz
wget https://github.com/mongodb-js/mongosh/releases/download/v1.5.0/mongosh-1.5.0-linux-arm64.tgz

wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2404-arm64-100.12.0.tgz
wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2004-arm64-100.5.2.tgz

wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2004-x86_64-100.5.2.tgz
wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2004-x86_64-100.7.4.tgz
wget https://fastdl.mongodb.org/tools/db/mongodb-database-tools-ubuntu2004-x86_64-100.9.4.tgz

tar xzvf mongodb-linux-aarch64-ubuntu2404-8.0.9.tgz
tar xzvf mongodb-linux-aarch64-ubuntu2204-7.0.20.tgz
tar xzvf mongodb-linux-aarch64-ubuntu2204-6.0.23.tgz
tar xzvf mongodb-linux-aarch64-ubuntu2004-5.0.31.tgz
tar xzvf mongodb-linux-aarch64-ubuntu2004-4.4.29.tgz

tar xzvf mongosh-2.5.1-linux-arm64.tgz
tar xzvf mongosh-1.5.0-linux-arm64.tgz

tar xzvf mongodb-database-tools-ubuntu2404-arm64-100.12.0.tgz
tar xzvf mongodb-database-tools-ubuntu2004-arm64-100.5.2.tgz 

rm -f *.tgz
