ROOT="$(dirname "$0")"
cd $ROOT
env/bin/uvicorn app:app --host 0.0.0.0 --port 5000 --workers 4 --log-level critical --no-access-log &
#env/bin/uvicorn app:app --host 0.0.0.0 --port 5000 --reload --log-level critical --no-access-log &
env/bin/rq worker -q &
