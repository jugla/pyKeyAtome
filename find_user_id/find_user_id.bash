#!/bin/bash

USERNAME="foobar@network.com" #replace by your  mail
PASSWORD="passwd"    #replace by your password
CntID="1234567890"   #replace by your reference ID in Total Energy Account

SESSION=$(curl -s -D - -o /dev/null \
  -X POST "https://esoftlink.esoftthings.com/login_check" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-raw "_username=$USERNAME&_password=$PASSWORD" \
  | grep -i 'Set-Cookie: PHPSESSID=' \
  | sed -E 's/.*PHPSESSID=([^;]+).*/\1/')

if [ -z "$SESSION" ]; then
  echo "Login failed - no PHPSESSID"
  exit 1
fi

echo "[+] PHPSESSID=$SESSION"

#if needed you can change to increase
for ((UserId=1000; UserId<=900000; UserId++)); do


  URL="https://esoftlink.esoftthings.com/api/subscription/$UserId/$CntID/measure/live.json"

  #echo "Requête :"
  #echo "curl -s -b \"PHPSESSID=$SESSION\" \"$URL\""

  response=$(curl -s -b "PHPSESSID=$SESSION" "$URL")


  # Ignore les réponses contenant "error"
  if ! echo "$response" | grep -q '"error"'; then
    echo "UserId=$UserId"
    echo "$response"
    echo "----------------------"
  fi

done

