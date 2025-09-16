DISTRO := $(shell lsb_release -si | tr A-Z a-z)
DISTRO_MAJOR_VERSION := $(shell lsb_release -sr | cut -d. -f1)
DISTRO_NAME := $(shell lsb_release -sc | tr A-Z a-z)
VERSION := $(shell head -n 1 debian-common/changelog | awk '{match( $$0, /\(.+?\)/); print substr( $$0, RSTART+1, RLENGTH-2 ) }' | cut -d- -f1 )

all:

install:
	pip3 install . --target="$(DESTDIR)/usr/lib/python3/dist-packages" --no-deps --no-compile --no-build-isolation

version:
	echo $(VERSION)

clean:
	$(RM) -r build
	$(RM) dpkg
	$(RM) rpm
	$(RM) -r htmlcov
	$(RM) cinp/django_settings.py || true
ifeq (ubuntu, $(DISTRO))
	dh_clean || true
endif
	find -name *.pyc -delete
	find -name __pycache__ -delete

dist-clean: clean
	$(RM) -fr debian
	$(RM) -fr rpmbuild
	$(RM) -f dpkg-setup
	$(RM) -f rpm-setup
	$(RM) -f test-setup
	$(RM) -fr dist
	$(RM) -fr cinp.egg-info

.PHONY:: all install version clean dist-clean

test-blueprints:
	echo ubuntu-noble-base

test-requires:
	echo flake8 python3-cinp python3-pytest python3-pytest-cov python3-pytest-mock python3-werkzeug python3-pip python3-django python3-pytest-django

test-setup:
	pip3 install -e .
	ln -s ../django_test.settings cinp/django_settings.py
	touch test-setup

lint:
	flake8 --ignore=E501,E201,E202,E111,E126,E114,E402,W503 --statistics --exclude=migrations,build . bin/djfhCleaner

test:
	py.test-3 -x --cov=cinp --cov-report html --cov-report term --ds=cinp.django_settings -vv cinp

.PHONY:: test-blueprints lint-requires lint test-requires test

dpkg-blueprints:
	echo ubuntu-xenial-base ubuntu-bionic-base ubuntu-noble-base

dpkg-requires:
	echo dpkg-dev debhelper python3-dev python3-setuptools dh-python

dpkg-setup:
	./debian-setup
	touch dpkg-setup

dpkg:
	dpkg-buildpackage -b -us -uc
	touch dpkg

dpkg-file:
	echo $(shell ls ../python3-cinp_*.deb)

.PHONY:: dpkg-blueprints dpkg-requires dpkg-setup dpkg-file

rpm-blueprints:
	echo centos-7-base

rpm-requires:
	echo rpm-build python36-setuptools

rpm-setup:
	./rpmbuild-setup
	touch rpm-setup

rpm:
	rpmbuild -v -bb rpmbuild/config.spec
	touch rpm

rpm-file:
	echo $(shell ls rpmbuild/RPMS/*/python3-cinp-*.rpm)

.PHONY:: rpm-blueprints rpm-requires rpm-setup rpm-file

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
