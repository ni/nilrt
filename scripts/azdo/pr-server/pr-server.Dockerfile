FROM python:3

ARG PRSERVER_BB_REF=master
ARG PRSERVER_BB_REMOTE=git://git.openembedded.org/bitbake


# Create a `bitbake` user and group; which will actually run the server.
RUN adduser \
	--system \
	--group \
	--home /srv/bitbake \
	--shell /bin/bash \
	bitbake

RUN install \
	--mode=0775 \
	--owner=bitbake \
	--group=bitbake \
	-d \
		/srv/bitbake \
		/var/pr-server

COPY init.prserver.sh /init.prserver.sh

USER bitbake

RUN git clone \
	--verbose \
	--depth=1 \
	--branch ${PRSERVER_BB_REF} \
	${PRSERVER_BB_REMOTE} \
	/srv/bitbake

WORKDIR /srv/bitbake

ENV PYTHONPATH=/srv/bitbake
RUN python3 ./bin/bitbake-prserv --version
ENTRYPOINT ["/bin/bash", "/init.prserver.sh"]
