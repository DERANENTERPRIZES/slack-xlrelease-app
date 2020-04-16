#!/bin/bash -i

## CONFIG LOCAL ENV
echo "[*] Config local environment..."
#alias vault='docker-compose exec vault vault "$@"'
vault() {
    docker-compose exec vault vault "$@"
}
export -f vault
export VAULT_ADDR=http://127.0.0.1:8200

## INIT VAULT
echo "[*] Init vault..."
vault operator init -address=${VAULT_ADDR} | sed $'s,\x1b\\[[0-9;]*[a-zA-Z],,g' | tee ./data/keys.txt
export VAULT_TOKEN=$(grep 'Initial Root Token:' ./data/keys.txt | awk '{print substr($NF, 1, length($NF)-1)}')

## UNSEAL VAULT
echo "[*] Unseal vault..."
vault operator unseal -address=${VAULT_ADDR} $(grep 'Key 1:' ./data/keys.txt | awk '{print $NF}')
vault operator unseal -address=${VAULT_ADDR} $(grep 'Key 2:' ./data/keys.txt | awk '{print $NF}')
vault operator unseal -address=${VAULT_ADDR} $(grep 'Key 3:' ./data/keys.txt | awk '{print $NF}')

## AUTH
echo "[*] Auth..."
vault login -address=${VAULT_ADDR} token=${VAULT_TOKEN}

## CREATE USER
echo "[*] Create user... Remember to change the defaults!!"
vault auth enable -address=${VAULT_ADDR} userpass
vault policy write -address=${VAULT_ADDR} admin ./config/admin.hcl
vault write -address=${VAULT_ADDR} auth/userpass/users/webui password=webui policies=admin

## CREATE BACKUP TOKEN
echo "[*] Create backup token..."
vault token create -address=${VAULT_ADDR} -display-name="backup_token" | awk '/token/{i++}i==2' | awk '{print "backup_token: " $2}' >> ./data/keys.txt

## SAVE TOKEN IN ENV
sed -i '' -e "s/<VAULT_TOKEN>/$(grep 'Initial Root Token:' ./data/keys.txt | awk '{print substr($NF, 1, length($NF)-1)}')/g" ../.env
