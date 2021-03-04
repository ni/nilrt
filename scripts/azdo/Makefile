
GIT_SHORTHASH = $(shell git rev-parse --short HEAD)


.PHONY: all nilrt-nibuild nilrt-build .FORCE

all : nilrt-nibuild nilrt-build

nilrt-build : .FORCE
	cd ../docker && docker build \
		-t nilrt-build:$(GIT_SHORTHASH) \
		-f Dockerfile \
		.
	docker tag nilrt-build:$(GIT_SHORTHASH) nilrt-build:latest

nilrt-nibuild : nilrt-nibuild.Dockerfile nilrt-build .FORCE
	docker build \
		-t nilrt-nibuild:$(GIT_SHORTHASH) \
		-f $< \
		.
	docker tag nilrt-nibuild:$(GIT_SHORTHASH) nilrt-nibuild:latest
