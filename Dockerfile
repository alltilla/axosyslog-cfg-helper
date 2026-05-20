FROM alpine:latest

COPY . /build
WORKDIR /build

RUN apk add --update poetry make bison gcc musl-dev python3-dev
RUN make venv
RUN make db
RUN apk del make bison gcc musl-dev python3-dev

ENTRYPOINT ["poetry", "run", "axosyslog-cfg-helper"]
