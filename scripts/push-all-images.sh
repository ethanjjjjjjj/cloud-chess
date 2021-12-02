for i in fen-worker game-worker gateway bot-worker healer
do
cd $i
docker build . -t eu.gcr.io/silent-relic-333216/$i:latest
docker push eu.gcr.io/silent-relic-333216/$i:latest
cd ..
done