FROM alpine:latest

COPY . /build
WORKDIR /build

RUN apk add --update poetry make bison
RUN make venv
RUN make db
RUN apk del make bison

ENTRYPOINT ["poetry", "run", "axosyslog-cfg-helper"]
