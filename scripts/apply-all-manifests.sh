for i in $(ls kube-manifests/deploy*)   
do
kubectl apply -f $i
done
for i in bot-worker fen-worker game-worker gateway
do
kubectl autoscale deploy/$i --max 10 --cpu-percent=80
done
