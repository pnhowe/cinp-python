all:
	./setup.py build

install:
	./setup.py install --root $(DESTDIR) --install-purelib=/usr/lib/python3/dist-packages/ --prefix=/usr --no-compile -O0

clean:
	./setup.py clean
	$(RM) -fr build
	$(RM) -f dpkg
	$(RM) -f rpm
	dh_clean || true

dist-clean: clean
	$(RM) -fr debian
	$(RM) -fr rpmbuild
	$(RM) -f dpkg-setup
	$(RM) -f rpm-setup

.PHONY:: all install clean dist-clean

test-distros:
	echo ubuntu-xenial

lint-requires:
	echo flake8

lint:
	flake8 --ignore=E501,E201,E202,E111,E126,E114,E402,W605 --statistics --exclude=migrations .

test-requires:
	echo python3-cinp python3-pytest python3-pytest-cov

test:
	py.test-3 -x --cov=cinp --cov-report html --cov-report term -vv cinp

.PHONY:: test-distroy lint-requires lint test-requires test

dpkg-distros:
	echo ubuntu-trusty ubuntu-xenial ubuntu-bionic

dpkg-requires:
	echo dpkg-dev debhelper python3-dev python3-setuptools

dpkg-setup:
	./debian-setup
	touch dpkg-setup

dpkg:
	dpkg-buildpackage -b -us -uc
	touch dpkg

dpkg-file:
	echo $(shell ls ../python3-cinp_*.deb)

.PHONY:: dpkg-distros dpkg-requires dpkg-setup dpkg-file

rpm-distros:
	echo centos-6

rpm-requires:
	echo rpm-build

rpm-setup:
	./rpmbuild-setup
	touch rpm-setup

rpm:
	rpmbuild -v -bb rpmbuild/config.spec
	touch rpm

rpm-file:
	echo $(shell ls rpmbuild/RPMS/*/python3-cinp-*.rpm)

.PHONY:: rpm-distros rpm-requires rpm-setup rpm-file

demo:
	cd server_test && rm -f db.sqlite3 && ./manage.py migrate --noinput
	cd server_test && { ./run_server.py & echo $$! > /tmp/cinp_demo_server.pid; }
	sleep 2
	cd server_test && ./run_demo.py
	kill `cat /tmp/cinp_demo_server.pid`
	sleep 2
	rm /tmp/cinp_demo_server.pid
	rm server_test/db.sqlite3

.PHONY:: demo
