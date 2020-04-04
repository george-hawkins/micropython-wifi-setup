curl -v -H 'Accept: application/json;' 192.168.0.178/access-points

curl --trace-ascii - --data 'bssid=alpha&password=beta' 192.168.0.178/authenticate

curl -v 192.168.0.178

curl -v 192.168.0.178/unknown

curl -v 192.168.0.178/access-points

curl -v -H 'Accept: application/json' --data 'bssid=alpha&password=beta' 192.168.0.178/authenticate
curl -v --data 'bssid=alpha&passwor=beta' 192.168.0.178/authenticate

curl -v -X OPTIONS 192.168.0.178/unknown
