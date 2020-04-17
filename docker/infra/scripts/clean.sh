#!/bin/bash -i

read -p "[?] Are you sure you want to remove all Vault's data (y/n)? " answer
case ${answer:0:1} in
    y|Y )
        echo "[*] Removing files..."
        echo "[+] Removing: ./data/consul/"
        rm -rf ./data/consul/
        echo "[+] Removing: ./data/backup/"
		rm -rf ./data/backup/
        echo "[+] Removing: ./data/redis/"
		rm -rf ./data/redis/
		echo "[+] Removing: ./data/keys.txt"
		rm -f ./data/keys.txt
    ;;
    * )
        echo "[*] Aborting..."
    ;;
esac
