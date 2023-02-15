if [ -z  "$1" ]; then
    numDrones=2
else
    numDrones=$(($1-1))
fi

for i in `seq 0 $numDrones`
do
    server_port=$((50050+$i))
    udp_port=$((14540+$i))
    gnome-terminal -- sh -c "./Wildfire/mavsdk_server -p $server_port udp://:$udp_port" 
done