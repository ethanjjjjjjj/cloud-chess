for i in $(ls kube-manifests/deploy*)   
do
kubectl apply -f $i
done
