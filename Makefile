all:

test:
	py.test-3 -x --cov=cinp --cov-report html --cov-report term -vv cinp
