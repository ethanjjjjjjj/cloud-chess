for i in $(ls deploy*)   
do
kubectl apply -f $i
done