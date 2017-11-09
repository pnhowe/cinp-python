all:

test:
	py.test-3 -x --cov=cinp --cov-report html --cov-report term -vv cinp

demo:
	cd server_test && rm -f db.sqlite3 && ./manage.py migrate --noinput
	cd server_test && { ./run_server.py & echo $$! > /tmp/cinp_demo_server.pid; }
	sleep 2
	cd server_test && ./run_demo.py
	kill `cat /tmp/cinp_demo_server.pid`
	sleep 2
	rm /tmp/cinp_demo_server.pid
	rm server_test/db.sqlite3

